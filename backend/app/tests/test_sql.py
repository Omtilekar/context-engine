import asyncio
from collections.abc import Mapping
from typing import cast

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.retrieval.sql import (
    BLOCKED_SQL_PATTERN,
    SQL_ROW_LIMIT,
    SQL_TIMEOUT_SECONDS,
    _extract_table_name,
    _rows_to_sources,
    extract_table_names,
    has_semicolon_chaining,
    is_safe_select,
    retrieve_sql,
)
from app.schemas.query import QueryRoute, SourceCitation

# ---------------------------------------------------------------------------
# Fake session infrastructure
# ---------------------------------------------------------------------------


class FakeMappingResult:
    """Stand-in for SQLAlchemy's mapping result."""

    def __init__(self, rows: list[Mapping[str, object]]) -> None:
        self._rows = rows

    def all(self) -> list[Mapping[str, object]]:
        return self._rows


class FakeResult:
    """Stand-in for SQLAlchemy's result object."""

    def __init__(self, rows: list[Mapping[str, object]]) -> None:
        self._rows = rows

    def mappings(self) -> FakeMappingResult:
        return FakeMappingResult(self._rows)


class FakeSession:
    """Async session double for SQL retriever tests."""

    def __init__(self, rows: list[Mapping[str, object]]) -> None:
        self._rows = rows
        self.last_statement: object = None

    async def execute(
        self,
        statement: object,
        parameters: Mapping[str, object] | None = None,
    ) -> FakeResult:
        self.last_statement = statement
        return FakeResult(self._rows)


class SlowFakeSession:
    """Async session that never returns, used to test timeout enforcement."""

    async def execute(
        self,
        statement: object,
        parameters: Mapping[str, object] | None = None,
    ) -> FakeResult:
        await asyncio.sleep(9999)
        return FakeResult([])


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------


def sql_row() -> dict[str, object]:
    """One fake product_catalog result row."""
    return {
        "id": 1,
        "name": "ContextEngine Pro",
        "category": "Software",
        "price": 299.00,
        "stock_qty": 500,
        "description": "Hybrid RAG pipeline with 6-route classifier.",
    }


async def _simple_generator(query: str, schema: str) -> str:
    """Test sql_generator that always returns a valid SELECT."""
    return "SELECT * FROM product_catalog"


async def _injection_generator(query: str, schema: str) -> str:
    """Test sql_generator that returns an injection attempt."""
    return "DROP TABLE product_catalog"


async def _update_injection_generator(query: str, schema: str) -> str:
    """Test sql_generator returning UPDATE disguised in SELECT context."""
    return "SELECT id FROM product_catalog; UPDATE product_catalog SET price=0"


async def _comment_injection_generator(query: str, schema: str) -> str:
    """Test sql_generator returning a comment-based injection attempt."""
    return "SELECT * FROM product_catalog -- hide the rest"


async def _block_comment_injection_generator(query: str, schema: str) -> str:
    """Test sql_generator returning a block-comment injection attempt."""
    return "SELECT /* sneaky */ * FROM product_catalog"


async def _unknown_table_generator(query: str, schema: str) -> str:
    """Test sql_generator returning a SELECT against an unknown table."""
    return "SELECT * FROM users"


async def _join_unknown_table_generator(query: str, schema: str) -> str:
    """Test sql_generator joining an allowlisted table to an unknown table."""
    return "SELECT p.name, u.email FROM product_catalog p JOIN users u ON p.id = u.id"


async def _empty_generator(query: str, schema: str) -> str:
    """Test sql_generator that returns empty string (no SQL generated)."""
    return ""


async def _raising_generator(query: str, schema: str) -> str:
    """Test sql_generator that raises an exception."""
    raise RuntimeError("OpenAI rate limit exceeded")


# ---------------------------------------------------------------------------
# is_safe_select — injection guard
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "keyword",
    [
        "DROP",
        "drop",
        "Drop",
        "DELETE",
        "delete",
        "INSERT",
        "insert",
        "UPDATE",
        "update",
        "TRUNCATE",
        "truncate",
        "ALTER",
        "alter",
        "CREATE",
        "create",
        "EXEC",
        "exec",
        "EXECUTE",
        "execute",
        "GRANT",
        "grant",
        "REVOKE",
        "revoke",
    ],
)
def test_is_safe_select_blocks_all_destructive_keywords(keyword: str) -> None:
    """Every blocked keyword is rejected, regardless of case."""
    assert not is_safe_select(f"SELECT * FROM t WHERE x = 1; {keyword} TABLE t")


def test_is_safe_select_blocks_non_select_statements() -> None:
    """Statements that do not start with SELECT are unconditionally rejected."""
    assert not is_safe_select("INSERT INTO t VALUES (1)")
    assert not is_safe_select("UPDATE t SET x = 1")
    assert not is_safe_select("  DELETE FROM t")
    assert not is_safe_select("DROP TABLE t")


def test_is_safe_select_allows_valid_select() -> None:
    """Plain SELECT statements without blocked keywords are approved."""
    assert is_safe_select("SELECT * FROM product_catalog")
    assert is_safe_select("SELECT id, name FROM product_catalog WHERE price > 100")
    assert is_safe_select("  SELECT COUNT(*) FROM product_catalog  ")


def test_is_safe_select_allows_single_trailing_semicolon() -> None:
    """A single trailing SQL terminator is accepted and stripped before execution."""
    assert is_safe_select("SELECT * FROM product_catalog;")


@pytest.mark.parametrize(
    "statement",
    [
        "SELECT * FROM product_catalog; SELECT * FROM product_catalog",
        "SELECT * FROM product_catalog; UPDATE product_catalog SET price=0",
        "SELECT * FROM product_catalog;DROP TABLE product_catalog",
    ],
)
def test_is_safe_select_blocks_semicolon_chaining(statement: str) -> None:
    """Semicolon-delimited multi-statement SQL is rejected."""
    assert not is_safe_select(statement)


@pytest.mark.parametrize(
    "statement",
    [
        "SELECT * FROM product_catalog -- trailing comment",
        "SELECT /* inline comment */ * FROM product_catalog",
        "SELECT * FROM product_catalog /* block comment */",
    ],
)
def test_is_safe_select_blocks_sql_comments(statement: str) -> None:
    """Line and block comments are rejected by the SQL guard."""
    assert not is_safe_select(statement)


@pytest.mark.parametrize(
    "statement",
    [
        "SELECT * FROM users",
        "SELECT * FROM documents",
        "SELECT * FROM product_catalog JOIN users ON users.id = product_catalog.id",
    ],
)
def test_is_safe_select_blocks_unknown_tables(statement: str) -> None:
    """Generated SQL can only access allowlisted structured tables."""
    assert not is_safe_select(statement)


def test_is_safe_select_rejects_select_without_table_reference() -> None:
    """SELECT without a FROM table is rejected for a tight single-purpose SQL retriever."""
    assert not is_safe_select("SELECT 1")


def test_blocked_sql_pattern_covers_all_required_keywords() -> None:
    """BLOCKED_SQL_PATTERN matches every keyword the spec requires."""
    required = {
        "drop",
        "delete",
        "insert",
        "update",
        "truncate",
        "alter",
        "create",
        "exec",
        "execute",
        "grant",
        "revoke",
    }
    for kw in required:
        assert BLOCKED_SQL_PATTERN.search(kw), f"Pattern should match '{kw}'"


def test_sql_row_limit_is_fifty() -> None:
    """SQL_ROW_LIMIT constant is exactly 50."""
    assert SQL_ROW_LIMIT == 50


def test_sql_timeout_is_five_seconds() -> None:
    """SQL_TIMEOUT_SECONDS constant is exactly 5.0."""
    assert SQL_TIMEOUT_SECONDS == 5.0


# ---------------------------------------------------------------------------
# table extraction
# ---------------------------------------------------------------------------


def test_extract_table_name_from_simple_select() -> None:
    """Table name is parsed from a simple FROM clause."""
    assert _extract_table_name("SELECT * FROM product_catalog") == "product_catalog"


def test_extract_table_name_returns_unknown_when_missing() -> None:
    """Returns 'unknown' when no FROM clause is found."""
    assert _extract_table_name("SELECT 1") == "unknown"


def test_extract_table_names_finds_from_and_join_tables() -> None:
    """Table extraction captures FROM and JOIN references for allowlist validation."""
    statement = "SELECT p.name FROM public.product_catalog p JOIN users u ON p.id = u.id"
    assert extract_table_names(statement) == {"product_catalog", "users"}


def test_has_semicolon_chaining_detects_multiple_statements() -> None:
    """Semicolon chaining detection allows one trailing terminator only."""
    assert not has_semicolon_chaining("SELECT * FROM product_catalog;")
    assert has_semicolon_chaining("SELECT * FROM product_catalog; SELECT * FROM users")


# ---------------------------------------------------------------------------
# _rows_to_sources
# ---------------------------------------------------------------------------


def test_rows_to_sources_returns_expected_schema() -> None:
    """SQL result rows map to SourceCitation with correct fields."""
    rows = [sql_row()]
    sources = _rows_to_sources(rows, "SELECT * FROM product_catalog", "product_catalog")

    assert len(sources) == 1
    source = sources[0]
    assert source.source_type == QueryRoute.SQL
    assert source.retrieval_mode == "sql"
    assert source.score == 1.0
    assert source.title == "SQL: product_catalog"
    assert "ContextEngine Pro" in source.snippet
    assert "generated_sql" in source.metadata


def test_rows_to_sources_truncates_long_sql_in_metadata() -> None:
    """Generated SQL longer than 120 chars is truncated in metadata."""
    long_sql = "SELECT " + ", ".join(f"col_{i}" for i in range(30)) + " FROM product_catalog"
    sources = _rows_to_sources([sql_row()], long_sql, "product_catalog")
    assert sources[0].metadata["generated_sql"].endswith("...")


def test_rows_to_sources_handles_none_values() -> None:
    """None values in result rows are serialized as null in JSON snippet."""
    row: dict[str, object] = {"id": 1, "description": None}
    sources = _rows_to_sources([row], "SELECT * FROM t", "t")
    assert '"description": null' in sources[0].snippet


# ---------------------------------------------------------------------------
# retrieve_sql — unit tests with injected session and generator
# ---------------------------------------------------------------------------


async def test_retrieve_sql_returns_empty_for_blank_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Blank queries return empty results without touching any generator or session."""

    async def fail_generator(q: str, s: str) -> str:
        raise AssertionError("blank query should not call sql_generator")

    result = await retrieve_sql(
        "   ",
        top_k=5,
        sql_generator=fail_generator,
        schema_context="product_catalog(id, name)",
    )
    assert result == []


async def test_retrieve_sql_returns_empty_for_zero_top_k() -> None:
    """top_k=0 returns empty results immediately."""
    result = await retrieve_sql(
        "how many products",
        top_k=0,
        sql_generator=_simple_generator,
        schema_context="product_catalog(id, name)",
    )
    assert result == []


async def test_retrieve_sql_blocks_injection_attempt() -> None:
    """Injection attempt from sql_generator returns empty list with no exception."""
    fake_session = FakeSession([sql_row()])
    result = await retrieve_sql(
        "drop everything",
        top_k=5,
        session=cast(object, fake_session),  # type: ignore[arg-type]
        sql_generator=_injection_generator,
        schema_context="product_catalog(id, name)",
    )
    assert result == []


async def test_retrieve_sql_blocks_multi_statement_injection() -> None:
    """Multi-statement injection (SELECT ... ; UPDATE ...) is rejected."""
    fake_session = FakeSession([sql_row()])
    result = await retrieve_sql(
        "get all products and reset prices",
        top_k=5,
        session=cast(object, fake_session),  # type: ignore[arg-type]
        sql_generator=_update_injection_generator,
        schema_context="product_catalog(id, name, price)",
    )
    assert result == []


async def test_retrieve_sql_blocks_line_comment_injection() -> None:
    """Line comments from sql_generator are rejected."""
    fake_session = FakeSession([sql_row()])
    result = await retrieve_sql(
        "show products",
        top_k=5,
        session=cast(object, fake_session),  # type: ignore[arg-type]
        sql_generator=_comment_injection_generator,
        schema_context="product_catalog(id, name, price)",
    )
    assert result == []


async def test_retrieve_sql_blocks_block_comment_injection() -> None:
    """Block comments from sql_generator are rejected."""
    fake_session = FakeSession([sql_row()])
    result = await retrieve_sql(
        "show products",
        top_k=5,
        session=cast(object, fake_session),  # type: ignore[arg-type]
        sql_generator=_block_comment_injection_generator,
        schema_context="product_catalog(id, name, price)",
    )
    assert result == []


async def test_retrieve_sql_blocks_unknown_table_access() -> None:
    """Generated SQL against unknown tables is rejected before execution."""
    fake_session = FakeSession([sql_row()])
    result = await retrieve_sql(
        "show users",
        top_k=5,
        session=cast(object, fake_session),  # type: ignore[arg-type]
        sql_generator=_unknown_table_generator,
        schema_context="product_catalog(id, name, price)",
    )
    assert result == []


async def test_retrieve_sql_blocks_join_to_unknown_table() -> None:
    """Generated SQL cannot join allowlisted tables to unknown tables."""
    fake_session = FakeSession([sql_row()])
    result = await retrieve_sql(
        "show product users",
        top_k=5,
        session=cast(object, fake_session),  # type: ignore[arg-type]
        sql_generator=_join_unknown_table_generator,
        schema_context="product_catalog(id, name, price)",
    )
    assert result == []


async def test_retrieve_sql_without_openai_key_returns_empty_before_db(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Default text-to-SQL path is disabled when OPENAI_API_KEY is absent."""

    class FakeSettings:
        openai_api_key: str | None = None
        sql_allowed_tables = "product_catalog"

    async def fail_fetch_schema_context(*args: object, **kwargs: object) -> str:
        raise AssertionError("schema should not be fetched without OPENAI_API_KEY")

    monkeypatch.setattr("app.retrieval.sql.get_settings", lambda: FakeSettings())
    monkeypatch.setattr("app.retrieval.sql.fetch_schema_context", fail_fetch_schema_context)

    result = await retrieve_sql("how many products", top_k=5)

    assert result == []


async def test_retrieve_sql_returns_empty_when_generator_returns_nothing() -> None:
    """Empty string from sql_generator returns empty list."""
    result = await retrieve_sql(
        "any query",
        top_k=5,
        sql_generator=_empty_generator,
        schema_context="product_catalog(id, name)",
    )
    assert result == []


async def test_retrieve_sql_returns_empty_when_generator_raises() -> None:
    """Exception from sql_generator is caught and returns empty list."""
    result = await retrieve_sql(
        "any query",
        top_k=5,
        sql_generator=_raising_generator,
        schema_context="product_catalog(id, name)",
    )
    assert result == []


async def test_retrieve_sql_returns_source_citations_for_valid_select() -> None:
    """Valid SELECT + fake session returns SourceCitation list."""
    from sqlalchemy.ext.asyncio import AsyncSession

    fake_session = FakeSession([sql_row()])

    sources = await retrieve_sql(
        "list all products",
        top_k=5,
        session=cast(AsyncSession, fake_session),
        sql_generator=_simple_generator,
        schema_context="product_catalog(id, name, category, price)",
    )

    assert len(sources) == 1
    assert sources[0].source_type == QueryRoute.SQL
    assert sources[0].retrieval_mode == "sql"
    assert sources[0].score == 1.0
    assert "ContextEngine Pro" in sources[0].snippet


async def test_retrieve_sql_caps_rows_at_sql_row_limit() -> None:
    """top_k is silently capped at SQL_ROW_LIMIT regardless of input."""
    from sqlalchemy.ext.asyncio import AsyncSession

    fake_session = FakeSession([sql_row()])

    await retrieve_sql(
        "list products",
        top_k=999,
        session=cast(AsyncSession, fake_session),
        sql_generator=_simple_generator,
        schema_context="product_catalog(id, name)",
    )

    last_sql = str(fake_session.last_statement)
    assert f"LIMIT {SQL_ROW_LIMIT}" in last_sql


async def test_retrieve_sql_returns_empty_on_timeout() -> None:
    """Slow session execution is cancelled after timeout and returns empty list."""
    from sqlalchemy.ext.asyncio import AsyncSession

    slow_session = SlowFakeSession()

    sources = await retrieve_sql(
        "how many products",
        top_k=5,
        session=cast(AsyncSession, slow_session),
        sql_generator=_simple_generator,
        schema_context="product_catalog(id, name)",
        timeout=0.01,
    )

    assert sources == []


async def test_retrieve_sql_returns_empty_for_no_results() -> None:
    """Empty result set from a valid query returns empty list."""
    from sqlalchemy.ext.asyncio import AsyncSession

    fake_session = FakeSession([])

    sources = await retrieve_sql(
        "show products with price over 9999",
        top_k=5,
        session=cast(AsyncSession, fake_session),
        sql_generator=_simple_generator,
        schema_context="product_catalog(id, name, price)",
    )

    assert sources == []


# ---------------------------------------------------------------------------
# Router endpoint wiring
# ---------------------------------------------------------------------------


async def test_query_endpoint_returns_mocked_sql_contexts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The query endpoint includes SQL contexts when the SQL retriever returns them."""

    async def fake_retrieve_sql(query: str, top_k: int) -> list[SourceCitation]:
        assert "how many" in query.lower()
        return [
            SourceCitation(
                title="SQL: product_catalog",
                score=1.0,
                source_type=QueryRoute.SQL,
                snippet='{"id": "1", "name": "ContextEngine Pro", "count": "7"}',
                retrieval_mode="sql",
                metadata={"generated_sql": "SELECT * FROM product_catalog"},
            )
        ]

    monkeypatch.setattr("app.retrieval.router.retrieve_sql", fake_retrieve_sql)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/query",
            json={"query": "how many products are in the catalog?"},
        )

    payload = response.json()

    assert response.status_code == 200
    assert payload["route_decision"]["route"] == "sql"
    assert payload["sources"][0]["retrieval_mode"] == "sql"
    assert payload["sources"][0]["source_type"] == "sql"
    assert payload["sources"][0]["score"] == 1.0


async def test_query_endpoint_sql_guard_never_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SQL injection attempt through the query endpoint returns a clean response."""

    async def injection_sql_retrieve(query: str, top_k: int) -> list[SourceCitation]:
        from app.retrieval.sql import is_safe_select

        generated = "DROP TABLE chunks"
        if not is_safe_select(generated):
            return []
        return [
            SourceCitation(
                title="SQL: chunks",
                score=1.0,
                source_type=QueryRoute.SQL,
                snippet="{}",
                retrieval_mode="sql",
                metadata={},
            )
        ]

    monkeypatch.setattr("app.retrieval.router.retrieve_sql", injection_sql_retrieve)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/query",
            json={"query": "how many records in total?"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["sources"] == []
