import pytest

from app.retrieval.reranker import DisabledReranker, FlashRankReranker, rerank_sources
from app.schemas.query import QueryRoute, SourceCitation


class FailingReranker:
    """Reranker test double that always fails."""

    async def rerank(
        self,
        query: str,
        sources: list[SourceCitation],
        top_k: int,
    ) -> list[SourceCitation]:
        """Raise to force fallback behavior."""
        raise RuntimeError("reranker unavailable")


def source(title: str, score: float) -> SourceCitation:
    """Build a source citation for reranker tests."""
    return SourceCitation(
        title=title,
        score=score,
        source_type=QueryRoute.SEMANTIC,
        snippet=f"{title} snippet",
        retrieval_mode="semantic",
    )


async def test_disabled_reranker_returns_existing_order() -> None:
    """Disabled reranker preserves merged score order and top_k."""
    sources = [source("first", 0.9), source("second", 0.8), source("third", 0.7)]

    reranked = await DisabledReranker().rerank("query", sources, top_k=2)

    assert [item.title for item in reranked] == ["first", "second"]


async def test_rerank_sources_falls_back_when_reranker_fails() -> None:
    """Reranker errors never fail the query."""
    sources = [source("first", 0.9), source("second", 0.8)]

    reranked = await rerank_sources("query", sources, top_k=1, reranker=FailingReranker())

    assert [item.title for item in reranked] == ["first"]


async def test_rerank_sources_returns_empty_for_empty_sources() -> None:
    """Empty inputs stay empty."""
    assert await rerank_sources("query", [], top_k=5) == []


async def test_flashrank_reranker_falls_back_when_package_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FlashRank mode falls back to merged order when loading fails."""
    sources = [source("first", 0.9), source("second", 0.8)]

    def fail_load(self: FlashRankReranker) -> tuple[object, object]:
        raise ImportError("flashrank not installed")

    monkeypatch.setattr(FlashRankReranker, "_load_flashrank", fail_load)

    reranked = await FlashRankReranker().rerank("query", sources, top_k=2)

    assert reranked == sources
