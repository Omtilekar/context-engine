from httpx import ASGITransport, AsyncClient

from app.main import app


async def test_health_returns_ok() -> None:
    """Health endpoint returns an ALB-friendly status payload."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "context-engine-backend"}


async def test_query_returns_placeholder_response() -> None:
    """Query endpoint returns the current structured placeholder shape."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/query", json={"query": "What are the key risks?"})

    payload = response.json()
    assert response.status_code == 200
    assert payload["route_decision"]["route"] == "semantic"
    assert payload["tokens_used"] == 0
