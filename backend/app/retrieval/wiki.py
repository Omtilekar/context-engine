from app.schemas.query import QueryRoute, SourceCitation


async def retrieve_wiki(query: str, top_k: int) -> list[SourceCitation]:
    """Return placeholder wiki retrieval results."""
    return [
        SourceCitation(
            title="Wiki retrieval placeholder",
            score=0.0,
            source_type=QueryRoute.WIKI,
            snippet=f"Wiki memory lookup will inspect up to {top_k} pages for: {query}",
        )
    ]
