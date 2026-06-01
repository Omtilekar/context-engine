import re
from collections.abc import Mapping
from typing import cast

from sqlalchemy import TextClause, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.connection import get_session_maker
from app.schemas.query import QueryRoute, SourceCitation

logger = get_logger(__name__)

MAX_WIKI_SNIPPET_CHARS = 700

WIKI_SEARCH_SQL = """
WITH search_query AS (
    SELECT websearch_to_tsquery('english', :query) AS tsq
),
ranked_pages AS (
    SELECT
        id::text AS page_id,
        title AS page_title,
        content AS content,
        CASE
            WHEN lower(title) = lower(:query) THEN 'exact'
            WHEN lower(title) LIKE :partial_query THEN 'partial'
            ELSE 'content'
        END AS match_type,
        ts_rank_cd(to_tsvector('english', content), search_query.tsq) AS content_rank
    FROM wiki_pages
    CROSS JOIN search_query
    WHERE lower(title) = lower(:query)
       OR lower(title) LIKE :partial_query
       OR to_tsvector('english', content) @@ search_query.tsq
       OR lower(content) LIKE :partial_query
)
SELECT
    page_id,
    page_title,
    content,
    match_type,
    CASE
        WHEN match_type = 'exact' THEN 1.0
        WHEN match_type = 'partial' THEN 0.88
        ELSE LEAST(0.80, GREATEST(0.35, content_rank / (content_rank + 1.0)))
    END AS wiki_score
FROM ranked_pages
ORDER BY wiki_score DESC, page_title ASC
LIMIT :top_k
"""

WIKI_INTENT_PREFIX_PATTERN = re.compile(
    r"^(?:"
    r"what\s+(?:is|are)|"
    r"explain|"
    r"define|"
    r"definition\s+of|"
    r"documentation\s+(?:for|of|on|about)|"
    r"docs\s+(?:for|of|on|about)|"
    r"guide\s+(?:to|for|of|on)|"
    r"tutorial\s+(?:for|of|on|about)|"
    r"how\s+does|"
    r"overview\s+of|"
    r"wiki\s+(?:for|of|on|about)"
    r")\s+",
    re.IGNORECASE,
)
TRAILING_HELPER_PATTERN = re.compile(r"\s+(?:work|works|mean|means)\s*$", re.IGNORECASE)
TRIM_PATTERN = re.compile(r"^[\s\"'`]+|[\s\"'`?.!,;:]+$")


def build_wiki_search_statement() -> TextClause:
    """Build the parameterized PostgreSQL wiki search statement."""
    return text(WIKI_SEARCH_SQL)


async def retrieve_wiki(
    query: str,
    top_k: int,
    session: AsyncSession | None = None,
) -> list[SourceCitation]:
    """Retrieve wiki memory pages from PostgreSQL.

    Args:
        query: User query text used for title and content search.
        top_k: Maximum number of wiki pages to return.
        session: Optional async SQLAlchemy session for tests or orchestration.

    Returns:
        Source citations representing matching wiki pages.
    """
    search_query = normalize_wiki_query(query)
    if not search_query or top_k <= 0:
        return []

    bounded_top_k = min(top_k, 50)
    if session is not None:
        return await _retrieve_wiki_with_session(search_query, bounded_top_k, session)

    session_maker = get_session_maker()
    try:
        async with session_maker() as database_session:
            return await _retrieve_wiki_with_session(search_query, bounded_top_k, database_session)
    except (OSError, SQLAlchemyError) as error:
        logger.warning("Wiki retrieval failed", extra={"error": str(error)})
        return []


async def _retrieve_wiki_with_session(
    query: str,
    top_k: int,
    session: AsyncSession,
) -> list[SourceCitation]:
    """Execute wiki search with an existing database session."""
    result = await session.execute(
        build_wiki_search_statement(),
        {
            "query": query,
            "partial_query": f"%{query.lower()}%",
            "top_k": top_k,
        },
    )
    return [wiki_row_to_source(cast(Mapping[str, object], row)) for row in result.mappings().all()]


def wiki_row_to_source(row: Mapping[str, object]) -> SourceCitation:
    """Convert a wiki_pages row into a source citation."""
    page_title = _string_value(row, "page_title") or "Untitled wiki page"
    match_type = _string_value(row, "match_type") or "content"
    score = normalize_wiki_score(_float_value(row, "wiki_score"))

    return SourceCitation(
        title=page_title,
        score=score,
        source_type=QueryRoute.WIKI,
        snippet=trim_wiki_content(_string_value(row, "content") or ""),
        source_id=_string_value(row, "page_id"),
        retrieval_mode="wiki",
        retrieval_modes=["wiki"],
        metadata={
            "page_title": page_title,
            "match_type": match_type,
            "wiki_score": score,
        },
    )


def normalize_wiki_query(query: str) -> str:
    """Extract the likely wiki page/search term from a documentation-style query."""
    cleaned = TRIM_PATTERN.sub("", " ".join(query.strip().split()))
    cleaned = WIKI_INTENT_PREFIX_PATTERN.sub("", cleaned).strip()
    cleaned = TRAILING_HELPER_PATTERN.sub("", cleaned).strip()
    cleaned = TRIM_PATTERN.sub("", cleaned)
    return cleaned


def normalize_wiki_score(value: float) -> float:
    """Clamp wiki ranking output into the SourceCitation score range."""
    return round(max(0.0, min(1.0, value)), 4)


def trim_wiki_content(content: str) -> str:
    """Trim wiki page content to a stable one-line snippet."""
    normalized = " ".join(content.split())
    if len(normalized) <= MAX_WIKI_SNIPPET_CHARS:
        return normalized
    return normalized[: MAX_WIKI_SNIPPET_CHARS - 3].rstrip() + "..."


def _float_value(row: Mapping[str, object], key: str) -> float:
    """Read a numeric row value as a float."""
    value = row.get(key)
    if value is None:
        return 0.0
    if isinstance(value, int | float):
        return float(value)
    return float(str(value))


def _string_value(row: Mapping[str, object], key: str) -> str | None:
    """Read a row value as a string when present."""
    value = row.get(key)
    if value is None:
        return None
    return str(value)
