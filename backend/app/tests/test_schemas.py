from collections.abc import Sequence
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.main import app
from app.schemas.document import DocumentIngestRequest, SourceType
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
        response = await client.post("/query", json={"query": "What are the key risks?"})

    payload = response.json()

    assert response.status_code == 200
    assert set(payload) == {
        "answer",
        "route_decision",
        "sources",
        "verification",
        "tokens_used",
        "cost_usd",
    }
    assert set(payload["route_decision"]) == {"route", "confidence", "reasoning", "entities"}
    assert payload["route_decision"]["route"] == "semantic"
    assert isinstance(payload["sources"], list)
    assert set(payload["verification"]) == {"grounded", "conflicts", "confidence"}


async def test_ingest_endpoint_returns_placeholder_response_shape() -> None:
    """The ingest endpoint returns the current queued placeholder response."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/ingest",
            json={
                "source_type": "text",
                "title": "Demo document",
                "content": "alpha beta gamma",
            },
        )

    payload = response.json()

    assert response.status_code == 200
    assert UUID(payload["document_id"])
    assert payload["status"] == "queued"
    assert payload["source_type"] == "text"
    assert payload["chunks_planned"] == 1
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
