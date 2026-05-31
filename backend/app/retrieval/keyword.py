from app.schemas.query import QueryRoute, SourceCitation


async def retrieve_keyword(query: str, top_k: int) -> list[SourceCitation]:
    """Return placeholder keyword retrieval results."""
    return [
        SourceCitation(
            title="Keyword retrieval placeholder",
            score=0.0,
            source_type=QueryRoute.BM25,
            snippet=f"PostgreSQL full-text search will retrieve up to {top_k} matches for: {query}",
        )
    ]
