from collections.abc import Sequence

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.schemas.query import QueryRoute, SourceCitation


async def test_hybrid_query_returns_merged_reranked_mocked_contexts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Hybrid endpoint output is merged, deduped, and reranked from mocked retrievers."""

    async def fake_retrieve_semantic(
        query: str,
        top_k: int,
        query_embedding: Sequence[float] | None,
    ) -> list[SourceCitation]:
        """Return a semantic source that duplicates keyword by chunk_id."""
        return [
            SourceCitation(
                title="Semantic duplicate",
                score=0.82,
                source_type=QueryRoute.SEMANTIC,
                snippet="Semantic version of shared chunk",
                chunk_id="shared-chunk",
                source_id="shared-chunk",
                retrieval_mode="semantic",
            ),
            SourceCitation(
                title="Semantic only",
                score=0.7,
                source_type=QueryRoute.SEMANTIC,
                snippet="Semantic-only context",
                chunk_id="semantic-only",
                source_id="semantic-only",
                retrieval_mode="semantic",
            ),
        ]

    async def fake_retrieve_keyword(query: str, top_k: int) -> list[SourceCitation]:
        """Return a keyword source that duplicates semantic by chunk_id."""
        return [
            SourceCitation(
                title="Keyword duplicate",
                score=0.74,
                source_type=QueryRoute.BM25,
                snippet="Keyword version of shared chunk",
                chunk_id="shared-chunk",
                source_id="shared-chunk",
                retrieval_mode="keyword",
            )
        ]

    async def fake_rerank_sources(
        query: str,
        sources: list[SourceCitation],
        top_k: int,
    ) -> list[SourceCitation]:
        """Reverse order to prove the router uses reranking output."""
        return list(reversed(sources))[:top_k]

    monkeypatch.setattr("app.retrieval.router.retrieve_semantic", fake_retrieve_semantic)
    monkeypatch.setattr("app.retrieval.router.retrieve_keyword", fake_retrieve_keyword)
    monkeypatch.setattr("app.retrieval.router.rerank_sources", fake_rerank_sources)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/query",
            json={"query": "Compare exact keyword retrieval across semantic meaning"},
        )

    payload = response.json()
    sources = payload["sources"]

    assert response.status_code == 200
    assert payload["route_decision"]["route"] == "hybrid"
    assert len(sources) == 2
    assert {source["chunk_id"] for source in sources} == {"shared-chunk", "semantic-only"}
    shared = next(source for source in sources if source["chunk_id"] == "shared-chunk")
    assert shared["retrieval_modes"] == ["semantic", "keyword"]
    assert shared["metadata"]["retrieval_modes"] == "semantic,keyword"


async def test_hybrid_query_can_include_sql_without_flashrank(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Hybrid retrieval can merge optional SQL contexts without passing them to FlashRank."""

    async def fake_retrieve_semantic(
        query: str,
        top_k: int,
        query_embedding: Sequence[float] | None,
    ) -> list[SourceCitation]:
        """Return one semantic source."""
        return [
            SourceCitation(
                title="Semantic source",
                score=0.7,
                source_type=QueryRoute.SEMANTIC,
                snippet="Semantic context",
                retrieval_mode="semantic",
            )
        ]

    async def fake_retrieve_keyword(query: str, top_k: int) -> list[SourceCitation]:
        """Return one keyword source."""
        return [
            SourceCitation(
                title="Keyword source",
                score=0.8,
                source_type=QueryRoute.BM25,
                snippet="Keyword context",
                retrieval_mode="keyword",
            )
        ]

    async def fake_retrieve_sql(query: str, top_k: int) -> list[SourceCitation]:
        """Return one SQL source."""
        return [
            SourceCitation(
                title="SQL: product_catalog",
                score=1.0,
                source_type=QueryRoute.SQL,
                snippet='{"count": "7"}',
                retrieval_mode="sql",
            )
        ]

    async def fake_rerank_sources(
        query: str,
        sources: list[SourceCitation],
        top_k: int,
    ) -> list[SourceCitation]:
        """Assert only non-SQL sources are passed to FlashRank-style reranking."""
        assert all(source.source_type != QueryRoute.SQL for source in sources)
        return sources[:top_k]

    monkeypatch.setattr("app.retrieval.router.retrieve_semantic", fake_retrieve_semantic)
    monkeypatch.setattr("app.retrieval.router.retrieve_keyword", fake_retrieve_keyword)
    monkeypatch.setattr("app.retrieval.router.retrieve_sql", fake_retrieve_sql)
    monkeypatch.setattr("app.retrieval.router.rerank_sources", fake_rerank_sources)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/query",
            json={"query": "Compare exact keyword retrieval and total records"},
        )

    payload = response.json()
    modes = {source["retrieval_mode"] for source in payload["sources"]}

    assert response.status_code == 200
    assert payload["route_decision"]["route"] == "hybrid"
    assert "sql" in modes
