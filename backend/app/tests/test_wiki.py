import os
from collections.abc import Mapping
from typing import cast
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import TextClause
from sqlalchemy.ext.asyncio import AsyncSession

from app.generation.generator import extract_used_citations
from app.main import app
from app.retrieval.router import RetrievalRouter
from app.retrieval.wiki import (
    WIKI_SEARCH_SQL,
    normalize_wiki_query,
    retrieve_wiki,
    wiki_row_to_source,
)
from app.schemas.query import QueryRequest, QueryRoute, SourceCitation


class FakeMappingResult:
    """Small stand-in for SQLAlchemy's mapping result."""

    def __init__(self, rows: list[Mapping[str, object]]) -> None:
        """Store fake mapping rows."""
        self._rows = rows

    def all(self) -> list[Mapping[str, object]]:
        """Return all fake rows."""
        return self._rows


class FakeResult:
    """Small stand-in for SQLAlchemy's result object."""

    def __init__(self, rows: list[Mapping[str, object]]) -> None:
        """Store fake result rows."""
        self._rows = rows

    def mappings(self) -> FakeMappingResult:
        """Return fake mapping result rows."""
        return FakeMappingResult(self._rows)


class FakeSession:
    """Async session double for wiki retriever tests."""

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


def wiki_row(
    page_title: str = "ContextEngine",
    match_type: str = "exact",
    wiki_score: float = 1.0,
) -> dict[str, object]:
    """Build one fake PostgreSQL wiki result row."""
    return {
        "page_id": uuid4(),
        "page_title": page_title,
        "content": (
            "ContextEngine is a hybrid RAG system with wiki memory, semantic search, "
            "BM25 keyword retrieval, graph traversal, SQL retrieval, and verification."
        ),
        "match_type": match_type,
        "wiki_score": wiki_score,
    }


def test_normalize_wiki_query_extracts_documentation_terms() -> None:
    """Wiki query normalization strips common documentation-style prefixes."""
    assert normalize_wiki_query("What is ContextEngine?") == "ContextEngine"
    assert normalize_wiki_query("definition of Hybrid RAG") == "Hybrid RAG"
    assert normalize_wiki_query("How does pgvector work?") == "pgvector"
    assert normalize_wiki_query("  docs for FlashRank  ") == "FlashRank"


async def test_retrieve_wiki_returns_empty_for_blank_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Blank wiki queries return no results without opening a database session."""

    def fail_if_database_is_used() -> None:
        raise AssertionError("blank query should not request a database session")

    monkeypatch.setattr("app.retrieval.wiki.get_session_maker", fail_if_database_is_used)

    assert await retrieve_wiki("   ", top_k=5) == []
    assert await retrieve_wiki("???", top_k=5) == []


def test_wiki_sql_uses_parameterized_search() -> None:
    """Wiki SQL keeps user input in bound parameters and searches title/content."""
    assert "websearch_to_tsquery('english', :query)" in WIKI_SEARCH_SQL
    assert "lower(title) = lower(:query)" in WIKI_SEARCH_SQL
    assert "lower(title) LIKE :partial_query" in WIKI_SEARCH_SQL
    assert "to_tsvector('english', content)" in WIKI_SEARCH_SQL
    assert "LIMIT :top_k" in WIKI_SEARCH_SQL
    assert "DROP TABLE" not in WIKI_SEARCH_SQL.upper()


def test_wiki_row_to_source_returns_expected_schema() -> None:
    """Wiki rows map to SourceCitation with wiki metadata."""
    source = wiki_row_to_source(wiki_row())

    assert source.source_type == QueryRoute.WIKI
    assert source.retrieval_mode == "wiki"
    assert source.retrieval_modes == ["wiki"]
    assert source.title == "ContextEngine"
    assert source.source_id is not None
    assert source.score == 1.0
    assert source.metadata == {
        "page_title": "ContextEngine",
        "match_type": "exact",
        "wiki_score": 1.0,
    }


async def test_retrieve_wiki_exact_title_lookup() -> None:
    """Wiki retriever supports exact title lookup from a fake session."""
    fake_session = FakeSession([wiki_row()])

    sources = await retrieve_wiki(
        "What is ContextEngine?",
        top_k=5,
        session=cast(AsyncSession, fake_session),
    )

    assert len(sources) == 1
    assert sources[0].metadata["match_type"] == "exact"
    assert fake_session.parameters == {
        "query": "ContextEngine",
        "partial_query": "%contextengine%",
        "top_k": 5,
    }
    assert fake_session.statement is not None
    assert "What is ContextEngine?" not in str(fake_session.statement)


async def test_retrieve_wiki_partial_title_lookup() -> None:
    """Wiki retriever supports partial title matches."""
    fake_session = FakeSession([wiki_row("Hybrid RAG", "partial", 0.88)])

    sources = await retrieve_wiki(
        "guide to Hybrid",
        top_k=3,
        session=cast(AsyncSession, fake_session),
    )

    assert sources[0].title == "Hybrid RAG"
    assert sources[0].metadata["match_type"] == "partial"
    assert sources[0].metadata["wiki_score"] == 0.88
    assert fake_session.parameters is not None
    assert fake_session.parameters["query"] == "Hybrid"
    assert fake_session.parameters["top_k"] == 3


async def test_retrieve_wiki_content_search() -> None:
    """Wiki retriever supports full-text content matches."""
    fake_session = FakeSession([wiki_row("Verification Layer", "content", 0.64)])

    sources = await retrieve_wiki(
        "overview of confidence scoring",
        top_k=2,
        session=cast(AsyncSession, fake_session),
    )

    assert sources[0].title == "Verification Layer"
    assert sources[0].score == 0.64
    assert sources[0].metadata["match_type"] == "content"
    assert fake_session.parameters is not None
    assert fake_session.parameters["query"] == "confidence scoring"


async def test_router_detects_wiki_documentation_queries() -> None:
    """Router sends documentation/definition/tutorial queries to wiki retrieval."""
    router = RetrievalRouter()
    queries = [
        "What is ContextEngine?",
        "Explain pgvector",
        "Definition of Hybrid RAG",
        "Documentation for PostgreSQL",
        "Docs for FlashRank",
        "Guide to Verification Layer",
        "Tutorial for Hybrid RAG",
        "How does pgvector work?",
        "Overview of ContextEngine",
    ]

    for query in queries:
        decision = await router.route(QueryRequest(query=query))
        assert decision.route == QueryRoute.WIKI


def test_wiki_citation_schema_uses_retrieval_mode_wiki() -> None:
    """Wiki sources produce public citations with retrieval_mode=wiki."""
    source = wiki_row_to_source(wiki_row())
    citations = extract_used_citations("ContextEngine is documented in wiki memory [1].", [source])

    assert citations[0].title == "ContextEngine"
    assert citations[0].retrieval_mode == "wiki"
    assert citations[0].score == 1.0


async def test_wiki_query_endpoint_returns_wiki_answer_and_citations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The query endpoint integrates wiki retrieval with generation and citations."""

    async def fake_retrieve_wiki(query: str, top_k: int) -> list[SourceCitation]:
        """Return one wiki source without touching a database."""
        assert query == "What is ContextEngine?"
        assert top_k == 5
        return [wiki_row_to_source(wiki_row())]

    monkeypatch.setattr("app.retrieval.router.retrieve_wiki", fake_retrieve_wiki)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/query", json={"query": "What is ContextEngine?"})

    payload = response.json()

    assert response.status_code == 200
    assert payload["route_decision"]["route"] == "wiki"
    assert payload["sources"][0]["retrieval_mode"] == "wiki"
    assert payload["sources"][0]["metadata"]["page_title"] == "ContextEngine"
    assert payload["sources"][0]["metadata"]["match_type"] == "exact"
    assert payload["citations"][0]["retrieval_mode"] == "wiki"
    assert payload["answer"].startswith("Based on 1 retrieved source")


@pytest.mark.skipif(
    not os.getenv("RUN_WIKI_INTEGRATION_TESTS"),
    reason="set RUN_WIKI_INTEGRATION_TESTS=1 with local Compose DB to run",
)
async def test_optional_wiki_integration_against_local_database() -> None:
    """Optionally exercise wiki retrieval against the local seeded database."""
    sources = await retrieve_wiki("What is ContextEngine?", top_k=3)

    assert any(source.title == "ContextEngine" for source in sources)
