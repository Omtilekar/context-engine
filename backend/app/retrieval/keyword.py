from collections.abc import Mapping
from typing import cast

from sqlalchemy import TextClause, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.connection import get_session_maker
from app.schemas.query import QueryRoute, SourceCitation

logger = get_logger(__name__)

KEYWORD_SEARCH_SQL = """
WITH search_query AS (
    SELECT websearch_to_tsquery('english', :query) AS tsq
),
ranked_chunks AS (
    SELECT
        c.id AS chunk_id,
        c.document_id AS document_id,
        c.content AS content,
        c.chunk_index AS chunk_index,
        c.page_number AS page_number,
        d.filename AS document_title,
        d.source_type AS document_source_type,
        ts_rank_cd(to_tsvector('english', c.content), search_query.tsq) AS rank
    FROM chunks c
    JOIN documents d ON d.id = c.document_id
    CROSS JOIN search_query
    WHERE to_tsvector('english', c.content) @@ search_query.tsq
)
SELECT
    chunk_id,
    document_id,
    content,
    chunk_index,
    page_number,
    document_title,
    document_source_type,
    rank,
    rank / (rank + 1.0) AS normalized_score
FROM ranked_chunks
ORDER BY rank DESC, chunk_index ASC
LIMIT :top_k
"""


def build_keyword_search_statement() -> TextClause:
    """Build the parameterized PostgreSQL full-text search statement."""
    return text(KEYWORD_SEARCH_SQL)


def normalize_keyword_rank(rank: float) -> float:
    """Normalize a PostgreSQL text-search rank into the SourceCitation score range."""
    if rank <= 0:
        return 0.0
    return round(min(1.0, rank / (rank + 1.0)), 4)


def keyword_row_to_source(row: Mapping[str, object]) -> SourceCitation:
    """Convert a keyword search database row into a source citation."""
    raw_rank = _float_value(row, "rank")
    normalized_score = _float_value(row, "normalized_score")
    score = normalized_score if normalized_score > 0 else normalize_keyword_rank(raw_rank)
    chunk_id = _string_value(row, "chunk_id")
    document_id = _string_value(row, "document_id")
    chunk_index = _string_value(row, "chunk_index")
    page_number = _string_value(row, "page_number")
    document_source_type = _string_value(row, "document_source_type")
    metadata = {
        "rank": f"{raw_rank:.6f}",
    }
    if chunk_index is not None:
        metadata["chunk_index"] = chunk_index
    if page_number is not None:
        metadata["page_number"] = page_number
    if document_source_type is not None:
        metadata["document_source_type"] = document_source_type

    return SourceCitation(
        title=_string_value(row, "document_title") or "Untitled document",
        score=score,
        source_type=QueryRoute.BM25,
        snippet=_string_value(row, "content") or "",
        source_id=chunk_id,
        chunk_id=chunk_id,
        document_id=document_id,
        retrieval_mode="keyword",
        metadata=metadata,
    )


async def retrieve_keyword(
    query: str,
    top_k: int,
    session: AsyncSession | None = None,
) -> list[SourceCitation]:
    """Retrieve keyword matches from PostgreSQL full-text search over chunks.

    Args:
        query: User query text to search against chunk content.
        top_k: Maximum number of chunks to return.
        session: Optional async SQLAlchemy session for tests or orchestration.

    Returns:
        Source citations ordered by PostgreSQL text-search rank.
    """
    stripped_query = query.strip()
    if not stripped_query or top_k <= 0:
        return []

    bounded_top_k = min(top_k, 50)
    if session is not None:
        return await _retrieve_keyword_with_session(stripped_query, bounded_top_k, session)

    session_maker = get_session_maker()
    try:
        async with session_maker() as database_session:
            return await _retrieve_keyword_with_session(
                stripped_query,
                bounded_top_k,
                database_session,
            )
    except SQLAlchemyError as error:
        logger.warning("Keyword retrieval failed", extra={"error": str(error)})
        return []


async def _retrieve_keyword_with_session(
    query: str,
    top_k: int,
    session: AsyncSession,
) -> list[SourceCitation]:
    """Execute the keyword search query with an existing database session."""
    result = await session.execute(
        build_keyword_search_statement(),
        {
            "query": query,
            "top_k": top_k,
        },
    )
    return [
        keyword_row_to_source(cast(Mapping[str, object], row)) for row in result.mappings().all()
    ]


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
