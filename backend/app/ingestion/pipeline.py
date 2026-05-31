import uuid

from app.ingestion.chunking import chunk_text
from app.schemas.document import DocumentIngestRequest, IngestResponse


class IngestionPipeline:
    """Placeholder ingestion pipeline for documents and external sources."""

    async def ingest(self, request: DocumentIngestRequest) -> IngestResponse:
        """Accept a source and estimate chunk fan-out for future async processing."""
        chunks = chunk_text(request.content or request.url or request.title)
        return IngestResponse(
            document_id=uuid.uuid4(),
            status="queued",
            source_type=request.source_type,
            chunks_planned=len(chunks),
            message="Ingestion accepted. Parser, embedding, wiki, and graph writes are pending.",
        )
