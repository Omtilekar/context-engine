from collections.abc import Mapping
from typing import cast
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import TextClause
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.retrieval.keyword import (
    KEYWORD_SEARCH_SQL,
    keyword_row_to_source,
    normalize_keyword_rank,
    retrieve_keyword,
)
from app.schemas.query import QueryRoute, SourceCitation


class FakeMappingResult:
    """Small stand-in for SQLAlchemy's mapping result."""

    def __init__(self, rows: list[Mapping[str, object]]) -> None:
        """Store rows returned from a fake query."""
        self._rows = rows

    def all(self) -> list[Mapping[str, object]]:
        """Return all fake rows."""
        return self._rows


class FakeResult:
    """Small stand-in for SQLAlchemy's result object."""

    def __init__(self, rows: list[Mapping[str, object]]) -> None:
        """Store rows returned from a fake query."""
        self._rows = rows

    def mappings(self) -> FakeMappingResult:
        """Return fake mapping rows."""
        return FakeMappingResult(self._rows)


class FakeSession:
    """Small async session double for keyword retriever tests."""

    def __init__(self, rows: list[Mapping[str, object]]) -> None:
        """Store rows and capture the executed statement."""
        self._rows = rows
        self.statement: TextClause | None = None
        self.parameters: Mapping[str, object] | None = None

    async def execute(
        self,
        statement: TextClause,
        parameters: Mapping[str, object],
    ) -> FakeResult:
        """Capture query execution details and return fake rows."""
        self.statement = statement
        self.parameters = parameters
        return FakeResult(self._rows)


def keyword_row() -> dict[str, object]:
    """Build one fake PostgreSQL keyword result row."""
    return {
        "chunk_id": uuid4(),
        "document_id": uuid4(),
        "content": "PostgreSQL full-text search powers keyword retrieval.",
        "chunk_index": 2,
        "page_number": None,
        "document_title": "Keyword Demo",
        "document_source_type": "text",
        "rank": 0.8,
        "normalized_score": 0.4444,
    }


async def test_retrieve_keyword_returns_empty_for_blank_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Blank keyword queries return no results without opening a database session."""

    def fail_if_database_is_used() -> None:
        raise AssertionError("blank query should not request a database session")

    monkeypatch.setattr("app.retrieval.keyword.get_session_maker", fail_if_database_is_used)

    assert await retrieve_keyword("   ", top_k=5) == []


def test_keyword_sql_uses_parameterized_full_text_search() -> None:
    """Keyword SQL keeps user input in bound parameters."""
    assert "websearch_to_tsquery('english', :query)" in KEYWORD_SEARCH_SQL
    assert "ts_rank_cd(to_tsvector('english', c.content), search_query.tsq)" in KEYWORD_SEARCH_SQL
    assert "LIMIT :top_k" in KEYWORD_SEARCH_SQL
    assert "DROP TABLE" not in KEYWORD_SEARCH_SQL.upper()


def test_keyword_row_to_source_returns_expected_schema() -> None:
    """Keyword result rows map to SourceCitation with chunk and document metadata."""
    source = keyword_row_to_source(keyword_row())

    assert source.source_type == QueryRoute.BM25
    assert source.retrieval_mode == "keyword"
    assert source.source_id == source.chunk_id
    assert source.document_id is not None
    assert source.title == "Keyword Demo"
    assert source.snippet == "PostgreSQL full-text search powers keyword retrieval."
    assert 0.0 <= source.score <= 1.0
    assert source.metadata["chunk_index"] == "2"
    assert source.metadata["document_source_type"] == "text"


def test_keyword_rank_normalization_stays_in_score_range() -> None:
    """PostgreSQL text-search ranks normalize into a stable score range."""
    assert normalize_keyword_rank(-1.0) == 0.0
    assert normalize_keyword_rank(0.0) == 0.0
    assert 0.0 < normalize_keyword_rank(0.8) < 1.0
    assert normalize_keyword_rank(10_000.0) <= 1.0


async def test_retrieve_keyword_executes_parameterized_statement() -> None:
    """Keyword retrieval sends user query as SQLAlchemy parameters."""
    malicious_query = "pgvector'); DROP TABLE chunks; --"
    fake_session = FakeSession([keyword_row()])

    sources = await retrieve_keyword(
        malicious_query,
        top_k=3,
        session=cast(AsyncSession, fake_session),
    )

    assert len(sources) == 1
    assert fake_session.statement is not None
    assert fake_session.parameters == {"query": malicious_query, "top_k": 3}
    assert malicious_query not in str(fake_session.statement)


async def test_query_endpoint_returns_mocked_keyword_contexts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The query endpoint includes keyword contexts when the BM25 retriever returns them."""

    async def fake_retrieve_keyword(query: str, top_k: int) -> list[SourceCitation]:
        """Return one fake keyword source for endpoint wiring."""
        assert query == "Find exact keyword pgvector"
        assert top_k == 5
        return [
            SourceCitation(
                title="Mock keyword source",
                score=0.91,
                source_type=QueryRoute.BM25,
                snippet="pgvector appears in the seeded keyword document.",
                source_id="chunk-1",
                chunk_id="chunk-1",
                document_id="document-1",
                retrieval_mode="keyword",
                metadata={"rank": "0.910000"},
            )
        ]

    monkeypatch.setattr("app.retrieval.router.retrieve_keyword", fake_retrieve_keyword)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/query", json={"query": "Find exact keyword pgvector"})

    payload = response.json()

    assert response.status_code == 200
    assert payload["route_decision"]["route"] == "bm25"
    assert payload["sources"][0]["retrieval_mode"] == "keyword"
    assert payload["sources"][0]["chunk_id"] == "chunk-1"
    assert payload["sources"][0]["document_id"] == "document-1"
