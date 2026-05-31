from app.schemas.query import QueryRoute, SourceCitation


async def retrieve_semantic(query: str, top_k: int) -> list[SourceCitation]:
    """Return placeholder semantic retrieval results."""
    return [
        SourceCitation(
            title="Semantic retrieval placeholder",
            score=0.0,
            source_type=QueryRoute.SEMANTIC,
            snippet=f"Vector search over pgvector will retrieve up to {top_k} chunks for: {query}",
        )
    ]
