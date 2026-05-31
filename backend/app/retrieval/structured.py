import re

from app.schemas.query import QueryRoute, SourceCitation

BLOCKED_SQL_PATTERN = re.compile(
    r"\b(drop|delete|insert|update|truncate|alter|create|exec)\b",
    re.IGNORECASE,
)


def is_safe_select(statement: str) -> bool:
    """Return whether a SQL statement satisfies the SELECT-only safety guard."""
    stripped = statement.strip().lower()
    return stripped.startswith("select") and BLOCKED_SQL_PATTERN.search(stripped) is None


async def retrieve_structured(query: str, top_k: int) -> list[SourceCitation]:
    """Return placeholder structured SQL retrieval results."""
    snippet = f"Text-to-SQL will generate safe SELECT queries capped at {top_k} rows for: {query}"
    return [
        SourceCitation(
            title="Structured SQL retrieval placeholder",
            score=0.0,
            source_type=QueryRoute.SQL,
            snippet=snippet,
        )
    ]
