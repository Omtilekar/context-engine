import asyncio
import json
import re
from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import Any, cast

from sqlalchemy import text
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.connection import get_engine, get_session_maker
from app.schemas.query import QueryRoute, SourceCitation

logger = get_logger(__name__)

SQL_ROW_LIMIT = 50
SQL_TIMEOUT_SECONDS = 5.0

BLOCKED_SQL_PATTERN = re.compile(
    r"\b(drop|delete|insert|update|truncate|alter|create|exec|execute|grant|revoke)\b",
    re.IGNORECASE,
)

SqlGenerator = Callable[[str, str], Awaitable[str]]


def is_safe_select(statement: str) -> bool:
    """Return whether a SQL statement satisfies the SELECT-only injection guard.

    Args:
        statement: Raw SQL statement to evaluate.

    Returns:
        True only when the statement starts with SELECT and contains no blocked keywords.
    """
    stripped = statement.strip()
    if not stripped.upper().startswith("SELECT"):
        return False
    return BLOCKED_SQL_PATTERN.search(stripped) is None


def _inspect_schema(sync_conn: Any) -> str:
    """Introspect table names and columns from a synchronous DB connection."""
    from sqlalchemy import inspect as sa_inspect

    insp = sa_inspect(sync_conn)
    schema_lines: list[str] = []
    for table_name in sorted(insp.get_table_names()):
        columns = insp.get_columns(table_name)
        col_defs = ", ".join(f"{c['name']} {c['type']}" for c in columns)
        schema_lines.append(f"{table_name}({col_defs})")
    if not schema_lines:
        return "No tables found."
    return "Available tables:\n" + "\n".join(schema_lines)


async def fetch_schema_context() -> str:
    """Return a human-readable schema description for the SQL generator prompt.

    Returns:
        Newline-separated table and column description, or fallback message on error.
    """
    engine = get_engine()
    try:
        async with engine.connect() as connection:
            return await connection.run_sync(_inspect_schema)
    except (OSError, SQLAlchemyError) as error:
        logger.warning("Schema introspection failed", extra={"error": str(error)})
        return "Schema unavailable."


async def _openai_sql_generator(query: str, schema_context: str) -> str:
    """Generate a SELECT statement from a natural-language query using GPT-4o-mini.

    Args:
        query: Natural-language user query.
        schema_context: Human-readable database schema description.

    Returns:
        A SELECT SQL statement string, or empty string when generation is unavailable.
    """
    try:
        from openai import AsyncOpenAI
    except ImportError:
        logger.warning("openai package not installed; SQL generation unavailable")
        return ""

    settings = get_settings()
    api_key = settings.openai_api_key
    if not api_key:
        logger.warning("OPENAI_API_KEY not set; SQL generation unavailable")
        return ""

    client = AsyncOpenAI(api_key=api_key)
    system_prompt = (
        "You are a SQL expert. Given a database schema and a natural-language query, "
        "generate a single valid SELECT statement. "
        "Return ONLY the SQL statement with no explanation or markdown code fences. "
        "Never use DROP, DELETE, INSERT, UPDATE, TRUNCATE, ALTER, CREATE, EXEC, EXECUTE, "
        "GRANT, or REVOKE.\n\n"
        f"Database schema:\n{schema_context}"
    )
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ],
        temperature=0.0,
        max_tokens=256,
    )
    raw = response.choices[0].message.content or ""
    raw = re.sub(r"```sql\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"```\s*", "", raw)
    return raw.strip()


def _extract_table_name(statement: str) -> str:
    """Extract the primary table name from a SELECT statement."""
    match = re.search(r"\bFROM\s+(\w+)", statement, re.IGNORECASE)
    return match.group(1) if match else "unknown"


def _rows_to_sources(
    rows: Sequence[Mapping[str, Any]],
    generated_sql: str,
    table_name: str,
) -> list[SourceCitation]:
    """Convert SQL result rows into SourceCitation objects.

    Args:
        rows: Database result rows.
        generated_sql: Original LLM-generated SQL for metadata.
        table_name: Extracted primary table name for result titles.

    Returns:
        One SourceCitation per result row.
    """
    sql_preview = (generated_sql[:120] + "...") if len(generated_sql) > 120 else generated_sql
    sources: list[SourceCitation] = []
    for row in rows:
        snippet = json.dumps(
            {k: str(v) if v is not None else None for k, v in row.items()},
            ensure_ascii=False,
        )
        sources.append(
            SourceCitation(
                title=f"SQL: {table_name}",
                score=1.0,
                source_type=QueryRoute.SQL,
                snippet=snippet,
                retrieval_mode="sql",
                metadata={"generated_sql": sql_preview},
            )
        )
    return sources


async def _execute_sql_with_session(
    session: AsyncSession,
    sql: str,
    generated_sql: str,
    table_name: str,
    timeout: float,
) -> list[SourceCitation]:
    """Execute a validated SELECT statement and return SourceCitation rows.

    Args:
        session: Async SQLAlchemy session.
        sql: LIMIT-bounded SELECT statement ready for execution.
        generated_sql: Original generated SQL for metadata.
        table_name: Extracted table name for result titles.
        timeout: Maximum execution seconds before cancellation.

    Returns:
        Source citations for each result row, or empty list on timeout or DB error.
    """
    try:
        result = await asyncio.wait_for(
            session.execute(text(sql)),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        logger.warning("SQL query timed out", extra={"timeout_seconds": timeout})
        return []
    except (OperationalError, SQLAlchemyError) as error:
        logger.warning("SQL execution error", extra={"error": str(error)})
        return []

    rows = cast(list[Mapping[str, Any]], list(result.mappings().all()))
    return _rows_to_sources(rows, generated_sql, table_name)


async def retrieve_sql(
    query: str,
    top_k: int,
    session: AsyncSession | None = None,
    sql_generator: SqlGenerator | None = None,
    schema_context: str | None = None,
    timeout: float = SQL_TIMEOUT_SECONDS,
) -> list[SourceCitation]:
    """Retrieve structured SQL results for a natural-language query.

    Text-to-SQL is performed by GPT-4o-mini using live schema introspection. All
    generated statements are validated by an injection guard before execution. Results
    are capped at SQL_ROW_LIMIT rows and execution is bounded by a hard timeout.

    Args:
        query: User natural-language query.
        top_k: Maximum rows to return, capped at SQL_ROW_LIMIT.
        session: Optional async SQLAlchemy session (tests and orchestration).
        sql_generator: Optional callable that replaces the OpenAI SQL generator.
        schema_context: Optional pre-fetched schema string; skips DB introspection.
        timeout: Query execution timeout in seconds.

    Returns:
        Source citations for each result row, or empty list on guard rejection or error.
    """
    stripped = query.strip()
    if not stripped or top_k <= 0:
        return []

    bounded_top_k = min(top_k, SQL_ROW_LIMIT)
    effective_schema = (
        schema_context if schema_context is not None else await fetch_schema_context()
    )

    generator = sql_generator or _openai_sql_generator
    try:
        generated_sql = await generator(stripped, effective_schema)
    except Exception as error:
        logger.warning("SQL generation raised an exception", extra={"error": str(error)})
        return []

    if not generated_sql.strip():
        return []

    if not is_safe_select(generated_sql):
        logger.warning(
            "SQL injection guard blocked statement",
            extra={"sql_preview": generated_sql[:200]},
        )
        return []

    table_name = _extract_table_name(generated_sql)
    limited_sql = f"SELECT * FROM ({generated_sql.rstrip(';')}) AS _result LIMIT {bounded_top_k}"

    if session is not None:
        return await _execute_sql_with_session(
            session, limited_sql, generated_sql, table_name, timeout
        )

    session_maker = get_session_maker()
    try:
        async with session_maker() as database_session:
            return await _execute_sql_with_session(
                database_session, limited_sql, generated_sql, table_name, timeout
            )
    except (OSError, SQLAlchemyError) as error:
        logger.warning("SQL retrieval failed", extra={"error": str(error)})
        return []
