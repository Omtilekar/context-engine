from collections.abc import Sequence
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.main import app
from app.schemas.document import DocumentIngestRequest, IngestResponse, SourceType
from app.schemas.query import QueryRequest, SourceCitation


def test_query_request_validation_strips_query_text() -> None:
    """Query requests normalize surrounding whitespace."""
    request = QueryRequest(query="  What are the risks?  ", top_k=3)

    assert request.query == "What are the risks?"
    assert request.top_k == 3


@pytest.mark.parametrize("top_k", [0, 21])
def test_query_request_rejects_invalid_top_k(top_k: int) -> None:
    """Query requests keep top_k within the retrieval cap."""
    with pytest.raises(ValidationError):
        QueryRequest(query="valid query", top_k=top_k)


def test_ingest_request_validation_strips_title() -> None:
    """Ingest requests normalize title text and coerce source types."""
    request = DocumentIngestRequest(source_type="text", title="  Demo document  ")

    assert request.source_type == SourceType.TEXT
    assert request.title == "Demo document"


def test_ingest_request_rejects_empty_title() -> None:
    """Ingest requests reject empty and whitespace-only titles."""
    with pytest.raises(ValidationError):
        DocumentIngestRequest(source_type=SourceType.TEXT, title="")

    with pytest.raises(ValidationError):
        DocumentIngestRequest(source_type=SourceType.TEXT, title="   ")


async def test_query_endpoint_returns_placeholder_response_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The query endpoint returns the current extendable placeholder response."""

    async def fake_retrieve_semantic(
        query: str,
        top_k: int,
        query_embedding: Sequence[float] | None,
    ) -> list[SourceCitation]:
        """Avoid live database access in schema endpoint tests."""
        return []

    monkeypatch.setattr("app.retrieval.router.retrieve_semantic", fake_retrieve_semantic)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/query", json={"query": "Which design risks matter most?"})

    payload = response.json()

    assert response.status_code == 200
    assert set(payload) == {
        "answer",
        "route_decision",
        "sources",
        "citations",
        "verification",
        "confidence",
        "generation_metadata",
        "tokens_used",
        "cost_usd",
    }
    assert set(payload["route_decision"]) == {"route", "confidence", "reasoning", "entities"}
    assert payload["route_decision"]["route"] == "semantic"
    assert isinstance(payload["sources"], list)
    assert {
        "grounded",
        "is_grounded",
        "has_conflicts",
        "warnings",
        "evidence_count",
        "retrieval_modes",
        "conflict_notes",
        "conflicts",
        "confidence",
    }.issubset(payload["verification"])
    assert set(payload["confidence"]) == {"score", "label", "reasons", "explanation"}
    assert isinstance(payload["citations"], list)
    assert set(payload["generation_metadata"]) == {
        "provider",
        "model",
        "tokens_used",
        "cost_usd",
        "citation_count",
        "source_count",
        "fallback_reason",
    }


async def test_ingest_endpoint_returns_ingestion_response_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The ingest endpoint returns the current ingestion response shape."""

    async def fake_ingest(
        self: object,
        request: DocumentIngestRequest,
    ) -> IngestResponse:
        """Avoid live database access in schema endpoint tests."""
        return IngestResponse(
            document_id=uuid4(),
            status="completed",
            source_type=request.source_type,
            chunks_planned=1,
            chunk_count=1,
            title=request.title,
            filename=request.filename or request.title,
            metadata=request.metadata,
            message="Ingestion completed with 1 embedded chunks.",
        )

    monkeypatch.setattr("app.main.IngestionPipeline.ingest", fake_ingest)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/ingest",
            json={
                "source_type": "text",
                "title": "Demo document",
                "filename": "demo.txt",
                "content": "alpha beta gamma",
                "metadata": {"source": "schema-test"},
            },
        )

    payload = response.json()

    assert response.status_code == 200
    assert UUID(payload["document_id"])
    assert payload["status"] == "completed"
    assert payload["source_type"] == "text"
    assert payload["chunks_planned"] == 1
    assert payload["chunk_count"] == 1
    assert payload["title"] == "Demo document"
    assert payload["filename"] == "demo.txt"
    assert payload["metadata"] == {"source": "schema-test"}
    assert payload["message"]


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("/query", {"query": ""}),
        ("/query", {"query": "   "}),
        ("/ingest", {}),
        ("/ingest", {"source_type": "unknown", "title": "Demo"}),
    ],
)
async def test_endpoints_reject_invalid_or_empty_payloads(
    path: str,
    payload: dict[str, str],
) -> None:
    """Placeholder endpoints reject invalid request bodies through schema validation."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(path, json=payload)

    assert response.status_code == 422
