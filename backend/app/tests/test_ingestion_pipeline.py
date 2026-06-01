import os
from collections.abc import Mapping
from typing import Any, cast
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.embeddings.provider import DEFAULT_EMBEDDING_DIMENSION, LocalHashEmbeddingProvider
from app.ingestion.pipeline import IngestionPipeline
from app.main import app
from app.schemas.document import DocumentIngestRequest


class StaticEmbeddingProvider:
    """Deterministic embedding provider test double."""

    dimension = DEFAULT_EMBEDDING_DIMENSION

    def __init__(self, fail: bool = False) -> None:
        """Create a provider that can optionally fail during embedding."""
        self.fail = fail
        self.calls: list[str] = []

    async def embed_query(self, text: str) -> list[float]:
        """Embed query text with the same deterministic vector."""
        return await self.embed_document(text)

    async def embed_document(self, text: str) -> list[float]:
        """Return a deterministic vector or raise when configured."""
        self.calls.append(text)
        if self.fail:
            raise RuntimeError("embedding failed")
        vector = [0.0] * DEFAULT_EMBEDDING_DIMENSION
        vector[0] = 1.0
        return vector


class FakeSession:
    """Small async session double for ingestion tests."""

    def __init__(self) -> None:
        """Track added ORM objects and transaction calls."""
        self.added: list[object] = []
        self.commits = 0
        self.rollbacks = 0
        self.flushes = 0

    def add(self, item: object) -> None:
        """Capture an added ORM object."""
        self.added.append(item)

    async def flush(self) -> None:
        """Track flush calls."""
        self.flushes += 1

    async def commit(self) -> None:
        """Track commit calls."""
        self.commits += 1

    async def rollback(self) -> None:
        """Track rollback calls."""
        self.rollbacks += 1


class FakeSessionContext:
    """Async context manager returning a fake session."""

    def __init__(self, session: FakeSession) -> None:
        """Store the fake session returned on enter."""
        self.session = session

    async def __aenter__(self) -> FakeSession:
        """Return the fake session."""
        return self.session

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        """Leave the fake session context."""


def fake_session_maker(session: FakeSession) -> object:
    """Return a fake async session maker compatible with get_session_maker."""

    def make_session() -> FakeSessionContext:
        return FakeSessionContext(session)

    return make_session


def objects_by_class(session: FakeSession, class_name: str) -> list[Any]:
    """Return fake session objects matching a SQLAlchemy model class name."""
    return [item for item in session.added if item.__class__.__name__ == class_name]


def many_words(count: int) -> str:
    """Return deterministic source text with the requested word count."""
    return " ".join(f"word{index}" for index in range(count))


async def test_pipeline_persists_document_chunks_and_embeddings() -> None:
    """Ingestion creates a completed document and embedded chunk rows."""
    provider = StaticEmbeddingProvider()
    session = FakeSession()
    pipeline = IngestionPipeline(embedding_provider=provider)
    request = DocumentIngestRequest(
        source_type="text",
        title="Long demo document",
        filename="long-demo.txt",
        content=many_words(600),
        metadata={"source": "unit-test"},
    )

    response = await pipeline.ingest(request, session=cast(AsyncSession, session))

    documents = objects_by_class(session, "Document")
    chunks = objects_by_class(session, "Chunk")

    assert response.status == "completed"
    assert response.chunk_count == 2
    assert response.chunks_planned == 2
    assert response.filename == "long-demo.txt"
    assert response.metadata == {"source": "unit-test"}
    assert len(documents) == 1
    assert documents[0].status == "completed"
    assert len(chunks) == 2
    assert [chunk.chunk_index for chunk in chunks] == [0, 1]
    assert all(chunk.embedding[0] == 1.0 for chunk in chunks)
    assert provider.calls == [chunk.content for chunk in chunks]
    assert session.flushes == 1
    assert session.commits == 1
    assert session.rollbacks == 0


async def test_pipeline_marks_empty_text_failed() -> None:
    """Empty text produces a failed document without chunk rows."""
    session = FakeSession()
    pipeline = IngestionPipeline(embedding_provider=StaticEmbeddingProvider())
    request = DocumentIngestRequest(source_type="text", title="Empty demo", content="   ")

    response = await pipeline.ingest(request, session=cast(AsyncSession, session))

    documents = objects_by_class(session, "Document")
    chunks = objects_by_class(session, "Chunk")

    assert response.status == "failed"
    assert response.chunk_count == 0
    assert response.chunks_planned == 0
    assert "no text content" in response.message
    assert len(documents) == 1
    assert documents[0].status == "failed"
    assert chunks == []
    assert session.commits == 1
    assert session.rollbacks == 0


async def test_pipeline_rolls_back_and_marks_failed_on_embedding_error() -> None:
    """Embedding failures rollback chunk writes and record a failed document."""
    session = FakeSession()
    pipeline = IngestionPipeline(embedding_provider=StaticEmbeddingProvider(fail=True))
    request = DocumentIngestRequest(
        source_type="text",
        title="Failure demo",
        content="this content should fail during embedding",
    )

    response = await pipeline.ingest(request, session=cast(AsyncSession, session))

    documents = objects_by_class(session, "Document")

    assert response.status == "failed"
    assert response.chunk_count == 0
    assert "persisting document chunks" in response.message
    assert session.rollbacks >= 1
    assert session.commits == 1
    assert any(document.status == "failed" for document in documents)


async def test_local_embedding_assignment_is_deterministic() -> None:
    """Pipeline chunk embeddings match the deterministic local embedding provider."""
    provider = LocalHashEmbeddingProvider()
    session = FakeSession()
    pipeline = IngestionPipeline(embedding_provider=provider)
    request = DocumentIngestRequest(
        source_type="text",
        title="Embedding demo",
        content="ContextEngine deterministic embedding assignment",
    )

    response = await pipeline.ingest(request, session=cast(AsyncSession, session))
    chunks = objects_by_class(session, "Chunk")
    stored_embedding = chunks[0].embedding
    expected_embedding = await provider.embed_document(chunks[0].content)

    assert response.status == "completed"
    assert response.chunk_count == 1
    assert stored_embedding == expected_embedding
    assert len(stored_embedding) == DEFAULT_EMBEDDING_DIMENSION


async def test_ingest_endpoint_uses_pipeline_without_live_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The ingest endpoint returns the real pipeline response shape with a fake session."""
    session = FakeSession()
    monkeypatch.setattr(
        "app.ingestion.pipeline.get_session_maker",
        lambda: fake_session_maker(session),
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/ingest",
            json={
                "source_type": "text",
                "title": "Endpoint demo",
                "filename": "endpoint-demo.txt",
                "content": "alpha beta gamma",
                "metadata": {"owner": "tests"},
            },
        )

    payload: Mapping[str, object] = response.json()

    assert response.status_code == 200
    assert UUID(str(payload["document_id"]))
    assert payload["status"] == "completed"
    assert payload["source_type"] == "text"
    assert payload["chunks_planned"] == 1
    assert payload["chunk_count"] == 1
    assert payload["title"] == "Endpoint demo"
    assert payload["filename"] == "endpoint-demo.txt"
    assert payload["metadata"] == {"owner": "tests"}


@pytest.mark.skipif(
    not os.getenv("RUN_INGESTION_INTEGRATION_TESTS"),
    reason="set RUN_INGESTION_INTEGRATION_TESTS=1 with local Compose DB to run",
)
async def test_optional_ingestion_integration_against_local_database() -> None:
    """Optionally ingest a text document against the local Compose database."""
    pipeline = IngestionPipeline()
    response = await pipeline.ingest(
        DocumentIngestRequest(
            source_type="text",
            title="Optional ingestion integration",
            content="ContextEngine local ingestion integration test content.",
        )
    )

    assert response.status == "completed"
    assert response.chunk_count >= 1
