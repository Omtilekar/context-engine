from app.retrieval.merger import merge_sources, source_identity_key
from app.schemas.query import QueryRoute, SourceCitation


def source(
    title: str,
    snippet: str,
    score: float,
    source_type: QueryRoute,
    retrieval_mode: str,
    chunk_id: str | None = None,
) -> SourceCitation:
    """Build a source citation for merger tests."""
    return SourceCitation(
        title=title,
        score=score,
        source_type=source_type,
        snippet=snippet,
        chunk_id=chunk_id,
        source_id=chunk_id,
        retrieval_mode=retrieval_mode,
    )


def test_merge_sources_dedupes_by_chunk_id() -> None:
    """Sources with the same chunk_id merge into one candidate."""
    keyword_source = source("Doc", "same chunk", 0.7, QueryRoute.BM25, "keyword", "chunk-1")
    semantic_source = source("Doc", "same chunk", 0.8, QueryRoute.SEMANTIC, "semantic", "chunk-1")

    merged = merge_sources([[keyword_source], [semantic_source]], top_k=5)

    assert len(merged) == 1
    assert merged[0].chunk_id == "chunk-1"
    assert merged[0].score == 0.9
    assert merged[0].retrieval_modes == ["keyword", "semantic"]


def test_merge_sources_dedupes_by_normalized_title_and_snippet_fallback() -> None:
    """Sources without chunk_id use normalized title/snippet dedupe."""
    first = source(" Doc ", "Same   snippet", 0.6, QueryRoute.BM25, "keyword")
    second = source("doc", "same snippet", 0.75, QueryRoute.SEMANTIC, "semantic")

    merged = merge_sources([[first], [second]], top_k=5)

    assert len(merged) == 1
    assert merged[0].score == 0.85
    assert merged[0].retrieval_modes == ["keyword", "semantic"]


def test_merge_sources_combines_scores_and_caps_at_one() -> None:
    """Duplicate score fusion adds provenance bonus and caps at 1.0."""
    keyword_source = source("Doc", "chunk", 0.95, QueryRoute.BM25, "keyword", "chunk-1")
    semantic_source = source("Doc", "chunk", 0.9, QueryRoute.SEMANTIC, "semantic", "chunk-1")

    merged = merge_sources([[keyword_source], [semantic_source]], top_k=5)

    assert merged[0].score == 1.0


def test_merge_sources_preserves_provenance_metadata() -> None:
    """Merged sources include retrieval mode provenance and per-mode scores."""
    keyword_source = source("Doc", "chunk", 0.65, QueryRoute.BM25, "keyword", "chunk-1")
    semantic_source = source("Doc", "chunk", 0.85, QueryRoute.SEMANTIC, "semantic", "chunk-1")

    merged = merge_sources([[keyword_source], [semantic_source]], top_k=5)
    metadata = merged[0].metadata

    assert metadata["retrieval_modes"] == "keyword,semantic"
    assert metadata["score_keyword"] == "0.650000"
    assert metadata["score_semantic"] == "0.850000"


def test_merge_sources_enforces_top_k() -> None:
    """Merged source output is capped to top_k."""
    sources = [
        source(f"Doc {index}", f"snippet {index}", 1.0 - index / 10, QueryRoute.BM25, "keyword")
        for index in range(5)
    ]

    merged = merge_sources([sources], top_k=2)

    assert len(merged) == 2
    assert [item.title for item in merged] == ["Doc 0", "Doc 1"]


def test_merge_sources_orders_ties_deterministically() -> None:
    """Tie ordering is deterministic by title then snippet."""
    beta = source("Beta", "same", 0.8, QueryRoute.BM25, "keyword")
    alpha = source("Alpha", "same", 0.8, QueryRoute.BM25, "keyword")

    merged = merge_sources([[beta, alpha]], top_k=5)

    assert [item.title for item in merged] == ["Alpha", "Beta"]


def test_source_identity_key_prefers_chunk_id() -> None:
    """Chunk id wins over title/snippet fallback identity."""
    item = source("Doc", "snippet", 0.8, QueryRoute.BM25, "keyword", "chunk-7")

    assert source_identity_key(item) == "chunk:chunk-7"
