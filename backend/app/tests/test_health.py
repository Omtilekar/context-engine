from collections.abc import Sequence

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.schemas.query import SourceCitation


async def test_health_returns_ok() -> None:
    """Health endpoint returns an ALB-friendly status payload."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "context-engine-backend"}


async def test_query_returns_placeholder_response(monkeypatch: pytest.MonkeyPatch) -> None:
    """Query endpoint returns the current structured placeholder shape."""

    async def fake_retrieve_semantic(
        query: str,
        top_k: int,
        query_embedding: Sequence[float] | None,
    ) -> list[SourceCitation]:
        """Avoid live database access in the health-adjacent query smoke test."""
        return []

    monkeypatch.setattr("app.retrieval.router.retrieve_semantic", fake_retrieve_semantic)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/query", json={"query": "What are the key risks?"})

    payload = response.json()
    assert response.status_code == 200
    assert payload["route_decision"]["route"] == "semantic"
    assert payload["tokens_used"] == 0
