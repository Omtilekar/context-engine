from app.retrieval.sql import SqlGenerator, is_safe_select, retrieve_sql
from app.schemas.query import SourceCitation

__all__ = ["is_safe_select", "retrieve_structured"]


async def retrieve_structured(
    query: str,
    top_k: int,
    sql_generator: SqlGenerator | None = None,
    schema_context: str | None = None,
) -> list[SourceCitation]:
    """Delegate structured SQL retrieval to the sql retriever."""
    return await retrieve_sql(
        query,
        top_k,
        sql_generator=sql_generator,
        schema_context=schema_context,
    )
