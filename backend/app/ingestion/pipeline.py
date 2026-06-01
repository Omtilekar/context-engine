import uuid

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.connection import get_session_maker
from app.db.models import Chunk, Document
from app.embeddings.provider import EmbeddingProvider, get_embedding_provider
from app.ingestion.chunking import TextChunk, chunk_text
from app.schemas.document import DocumentIngestRequest, IngestResponse

logger = get_logger(__name__)


class IngestionPipeline:
    """Persist text ingestion into documents and embedded chunks."""

    def __init__(self, embedding_provider: EmbeddingProvider | None = None) -> None:
        """Create an ingestion pipeline.

        Args:
            embedding_provider: Optional provider override for tests.
        """
        self.embedding_provider = embedding_provider

    async def ingest(
        self,
        request: DocumentIngestRequest,
        session: AsyncSession | None = None,
    ) -> IngestResponse:
        """Persist a source document and its embedded chunks.

        Args:
            request: Ingestion request from the API.
            session: Optional async database session for tests or orchestration.

        Returns:
            Structured ingestion result with document id, status, and chunk count.
        """
        if session is not None:
            return await self._ingest_with_session(request, session)

        session_maker = get_session_maker()
        try:
            async with session_maker() as database_session:
                return await self._ingest_with_session(request, database_session)
        except (OSError, SQLAlchemyError) as error:
            logger.warning(
                "Ingestion failed before a session was available", extra={"error": str(error)}
            )
            return failed_response(
                request=request,
                document_id=uuid.uuid4(),
                message="Ingestion failed before the database session was available.",
            )

    async def _ingest_with_session(
        self,
        request: DocumentIngestRequest,
        session: AsyncSession,
    ) -> IngestResponse:
        """Run ingestion with an existing database session."""
        document_id = uuid.uuid4()
        filename = document_filename(request)
        text = document_text(request)
        metadata = response_metadata(request)

        document = Document(
            id=document_id,
            filename=filename,
            source_type=request.source_type.value,
            s3_key=request.metadata.get("s3_key"),
            status="processing",
        )

        if not text:
            document.status = "failed"
            session.add(document)
            await session.commit()
            return failed_response(
                request=request,
                document_id=document_id,
                filename=filename,
                metadata=metadata,
                message="Ingestion failed because no text content was provided.",
            )

        chunks = chunk_text(text)
        if not chunks:
            document.status = "failed"
            session.add(document)
            await session.commit()
            return failed_response(
                request=request,
                document_id=document_id,
                filename=filename,
                metadata=metadata,
                message="Ingestion failed because the text produced no chunks.",
            )

        try:
            session.add(document)
            await session.flush()
            await self._add_chunks(session, document_id, chunks)
            document.status = "completed"
            await session.commit()
        except Exception as error:
            await rollback_session(session)
            await mark_document_failed(session, document_id, request)
            logger.warning("Ingestion failed while persisting chunks", extra={"error": str(error)})
            return failed_response(
                request=request,
                document_id=document_id,
                filename=filename,
                metadata=metadata,
                message="Ingestion failed while persisting document chunks.",
            )

        return IngestResponse(
            document_id=document_id,
            status="completed",
            source_type=request.source_type,
            chunks_planned=len(chunks),
            chunk_count=len(chunks),
            title=request.title,
            filename=filename,
            metadata=metadata,
            message=f"Ingestion completed with {len(chunks)} embedded chunks.",
        )

    async def _add_chunks(
        self,
        session: AsyncSession,
        document_id: uuid.UUID,
        chunks: list[TextChunk],
    ) -> None:
        """Create embedded chunk rows for a document."""
        embedding_provider = self.embedding_provider or get_embedding_provider()
        for text_chunk in chunks:
            session.add(
                Chunk(
                    id=uuid.uuid4(),
                    document_id=document_id,
                    content=text_chunk.content,
                    embedding=await embedding_provider.embed_document(text_chunk.content),
                    chunk_index=text_chunk.chunk_index,
                )
            )


def document_text(request: DocumentIngestRequest) -> str:
    """Return normalized source text that can be chunked locally."""
    if request.content is None:
        return ""
    return " ".join(request.content.split())


def document_filename(request: DocumentIngestRequest) -> str:
    """Return the filename stored in the documents table."""
    return request.filename or request.metadata.get("filename") or request.title


def response_metadata(request: DocumentIngestRequest) -> dict[str, str]:
    """Return stable source metadata for the ingestion response."""
    metadata = dict(request.metadata)
    if request.url:
        metadata.setdefault("url", request.url)
    return metadata


def failed_response(
    request: DocumentIngestRequest,
    document_id: uuid.UUID,
    message: str,
    filename: str | None = None,
    metadata: dict[str, str] | None = None,
) -> IngestResponse:
    """Build a structured failed ingestion response."""
    return IngestResponse(
        document_id=document_id,
        status="failed",
        source_type=request.source_type,
        chunks_planned=0,
        chunk_count=0,
        title=request.title,
        filename=filename or document_filename(request),
        metadata=metadata or response_metadata(request),
        message=message,
    )


async def rollback_session(session: AsyncSession) -> None:
    """Rollback a session, ignoring rollback failures."""
    try:
        await session.rollback()
    except Exception as error:
        logger.warning("Ingestion rollback failed", extra={"error": str(error)})


async def mark_document_failed(
    session: AsyncSession,
    document_id: uuid.UUID,
    request: DocumentIngestRequest,
) -> None:
    """Record a failed document row after a rollback when possible."""
    try:
        session.add(
            Document(
                id=document_id,
                filename=document_filename(request),
                source_type=request.source_type.value,
                s3_key=request.metadata.get("s3_key"),
                status="failed",
            )
        )
        await session.commit()
    except Exception as error:
        logger.warning("Could not mark document failed", extra={"error": str(error)})
        await rollback_session(session)
