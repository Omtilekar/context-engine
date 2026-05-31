from app.schemas.query import QueryRoute, SourceCitation


async def retrieve_graph(query: str, top_k: int) -> list[SourceCitation]:
    """Return placeholder graph retrieval results."""
    snippet = f"Entity graph traversal will inspect up to {top_k} facts for: {query}"
    return [
        SourceCitation(
            title="Graph retrieval placeholder",
            score=0.0,
            source_type=QueryRoute.GRAPH,
            snippet=snippet,
        )
    ]
