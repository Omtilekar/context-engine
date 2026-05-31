from collections.abc import Mapping, Sequence
from typing import cast

from sqlalchemy import TextClause, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.connection import get_session_maker
from app.embeddings.provider import DEFAULT_EMBEDDING_DIMENSION
from app.schemas.query import QueryRoute, SourceCitation

logger = get_logger(__name__)

SEMANTIC_SEARCH_SQL = """
WITH query_embedding AS (
    SELECT CAST(:query_embedding AS vector) AS embedding
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
        c.embedding <=> query_embedding.embedding AS distance
    FROM chunks c
    JOIN documents d ON d.id = c.document_id
    CROSS JOIN query_embedding
    WHERE c.embedding IS NOT NULL
)
SELECT
    chunk_id,
    document_id,
    content,
    chunk_index,
    page_number,
    document_title,
    document_source_type,
    distance,
    1.0 - distance AS similarity_score
FROM ranked_chunks
ORDER BY distance ASC, chunk_index ASC
LIMIT :top_k
"""


def build_semantic_search_statement() -> TextClause:
    """Build the parameterized pgvector semantic search statement."""
    return text(SEMANTIC_SEARCH_SQL)


def vector_to_pg_literal(embedding: Sequence[float]) -> str:
    """Format an embedding as a pgvector literal for a bound SQL parameter."""
    return "[" + ",".join(f"{value:.8f}" for value in embedding) + "]"


def normalize_cosine_distance(distance: float) -> float:
    """Convert pgvector cosine distance into the SourceCitation score range."""
    return round(max(0.0, min(1.0, 1.0 - distance)), 4)


def semantic_row_to_source(row: Mapping[str, object]) -> SourceCitation:
    """Convert a semantic search database row into a source citation."""
    distance = _float_value(row, "distance")
    score = normalize_cosine_distance(distance)
    chunk_id = _string_value(row, "chunk_id")
    document_id = _string_value(row, "document_id")
    chunk_index = _string_value(row, "chunk_index")
    page_number = _string_value(row, "page_number")
    document_source_type = _string_value(row, "document_source_type")
    metadata = {
        "distance": f"{distance:.6f}",
        "similarity_score": f"{score:.6f}",
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
        source_type=QueryRoute.SEMANTIC,
        snippet=_string_value(row, "content") or "",
        source_id=chunk_id,
        chunk_id=chunk_id,
        document_id=document_id,
        retrieval_mode="semantic",
        metadata=metadata,
    )


async def retrieve_semantic(
    query: str,
    top_k: int,
    query_embedding: Sequence[float] | None = None,
    session: AsyncSession | None = None,
) -> list[SourceCitation]:
    """Retrieve semantic matches from PostgreSQL pgvector over chunk embeddings.

    Args:
        query: User query text. Used for validation and logging; the embedding drives search.
        top_k: Maximum number of chunks to return.
        query_embedding: Embedded query vector matching the chunks.embedding dimension.
        session: Optional async SQLAlchemy session for tests or orchestration.

    Returns:
        Source citations ordered by closest cosine distance.
    """
    stripped_query = query.strip()
    if not stripped_query or top_k <= 0:
        return []
    if query_embedding is None or len(query_embedding) != DEFAULT_EMBEDDING_DIMENSION:
        return []

    bounded_top_k = min(top_k, 50)
    vector_literal = vector_to_pg_literal(query_embedding)
    if session is not None:
        return await _retrieve_semantic_with_session(vector_literal, bounded_top_k, session)

    session_maker = get_session_maker()
    try:
        async with session_maker() as database_session:
            return await _retrieve_semantic_with_session(
                vector_literal,
                bounded_top_k,
                database_session,
            )
    except (OSError, SQLAlchemyError) as error:
        logger.warning("Semantic retrieval failed", extra={"error": str(error)})
        return []


async def _retrieve_semantic_with_session(
    query_embedding: str,
    top_k: int,
    session: AsyncSession,
) -> list[SourceCitation]:
    """Execute semantic search with an existing database session."""
    result = await session.execute(
        build_semantic_search_statement(),
        {
            "query_embedding": query_embedding,
            "top_k": top_k,
        },
    )
    return [
        semantic_row_to_source(cast(Mapping[str, object], row)) for row in result.mappings().all()
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
