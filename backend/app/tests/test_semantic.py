from collections.abc import Mapping, Sequence
from typing import cast
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import TextClause
from sqlalchemy.ext.asyncio import AsyncSession

from app.embeddings.provider import DEFAULT_EMBEDDING_DIMENSION
from app.main import app
from app.retrieval.semantic import (
    SEMANTIC_SEARCH_SQL,
    normalize_cosine_distance,
    retrieve_semantic,
    semantic_row_to_source,
    vector_to_pg_literal,
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
    """Small async session double for semantic retriever tests."""

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


def semantic_embedding() -> list[float]:
    """Build one valid deterministic test embedding."""
    embedding = [0.0] * DEFAULT_EMBEDDING_DIMENSION
    embedding[0] = 1.0
    return embedding


def semantic_row() -> dict[str, object]:
    """Build one fake PostgreSQL semantic result row."""
    return {
        "chunk_id": uuid4(),
        "document_id": uuid4(),
        "content": "Semantic search uses vector distance for related meaning.",
        "chunk_index": 1,
        "page_number": None,
        "document_title": "Semantic Demo",
        "document_source_type": "text",
        "distance": 0.18,
        "similarity_score": 0.82,
    }


async def test_retrieve_semantic_returns_empty_for_blank_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Blank semantic queries return no results without opening a database session."""

    def fail_if_database_is_used() -> None:
        raise AssertionError("blank query should not request a database session")

    monkeypatch.setattr("app.retrieval.semantic.get_session_maker", fail_if_database_is_used)

    assert await retrieve_semantic("   ", top_k=5, query_embedding=semantic_embedding()) == []


async def test_retrieve_semantic_returns_empty_for_missing_embedding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing query embeddings return no results without opening a database session."""

    def fail_if_database_is_used() -> None:
        raise AssertionError("missing embedding should not request a database session")

    monkeypatch.setattr("app.retrieval.semantic.get_session_maker", fail_if_database_is_used)

    assert await retrieve_semantic("meaning-based question", top_k=5, query_embedding=None) == []
    assert await retrieve_semantic("meaning-based question", top_k=5, query_embedding=[1.0]) == []


def test_semantic_sql_uses_parameterized_pgvector_distance() -> None:
    """Semantic SQL keeps embeddings in bound parameters and uses pgvector distance."""
    assert "CAST(:query_embedding AS vector)" in SEMANTIC_SEARCH_SQL
    assert "c.embedding <=> query_embedding.embedding" in SEMANTIC_SEARCH_SQL
    assert "LIMIT :top_k" in SEMANTIC_SEARCH_SQL
    assert "DROP TABLE" not in SEMANTIC_SEARCH_SQL.upper()


def test_vector_literal_format_is_stable() -> None:
    """Embeddings are formatted as pgvector literals before binding."""
    assert vector_to_pg_literal([1.0, 0.5, -0.25]) == "[1.00000000,0.50000000,-0.25000000]"


def test_semantic_row_to_source_returns_expected_schema() -> None:
    """Semantic result rows map to SourceCitation with chunk and document metadata."""
    source = semantic_row_to_source(semantic_row())

    assert source.source_type == QueryRoute.SEMANTIC
    assert source.retrieval_mode == "semantic"
    assert source.source_id == source.chunk_id
    assert source.document_id is not None
    assert source.title == "Semantic Demo"
    assert source.snippet == "Semantic search uses vector distance for related meaning."
    assert source.score == 0.82
    assert source.metadata["chunk_index"] == "1"
    assert source.metadata["document_source_type"] == "text"
    assert source.metadata["distance"] == "0.180000"


def test_cosine_distance_normalization_stays_in_score_range() -> None:
    """Cosine distances normalize into a stable score range."""
    assert normalize_cosine_distance(-0.1) == 1.0
    assert normalize_cosine_distance(0.0) == 1.0
    assert normalize_cosine_distance(0.25) == 0.75
    assert normalize_cosine_distance(2.0) == 0.0


async def test_retrieve_semantic_executes_parameterized_statement() -> None:
    """Semantic retrieval sends query embeddings as SQLAlchemy parameters."""
    fake_session = FakeSession([semantic_row()])

    sources = await retrieve_semantic(
        "semantic search query",
        top_k=3,
        query_embedding=semantic_embedding(),
        session=cast(AsyncSession, fake_session),
    )

    assert len(sources) == 1
    assert fake_session.statement is not None
    assert fake_session.parameters is not None
    assert fake_session.parameters["top_k"] == 3
    assert str(fake_session.parameters["query_embedding"]).startswith("[1.00000000,")
    assert "semantic search query" not in str(fake_session.statement)


async def test_query_endpoint_returns_mocked_semantic_contexts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The query endpoint includes semantic contexts when semantic retrieval returns them."""

    async def fake_retrieve_semantic(
        query: str,
        top_k: int,
        query_embedding: Sequence[float] | None,
    ) -> list[SourceCitation]:
        """Return one fake semantic source for endpoint wiring."""
        assert query == "Which retrieval approach finds related meaning?"
        assert top_k == 5
        assert query_embedding is not None
        assert len(query_embedding) == DEFAULT_EMBEDDING_DIMENSION
        return [
            SourceCitation(
                title="Mock semantic source",
                score=0.88,
                source_type=QueryRoute.SEMANTIC,
                snippet="Semantic retrieval uses vector distance.",
                source_id="chunk-semantic-1",
                chunk_id="chunk-semantic-1",
                document_id="document-semantic-1",
                retrieval_mode="semantic",
                metadata={"distance": "0.120000"},
            )
        ]

    monkeypatch.setattr("app.retrieval.router.retrieve_semantic", fake_retrieve_semantic)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/query",
            json={"query": "Which retrieval approach finds related meaning?"},
        )

    payload = response.json()

    assert response.status_code == 200
    assert payload["route_decision"]["route"] == "semantic"
    assert payload["sources"][0]["retrieval_mode"] == "semantic"
    assert payload["sources"][0]["chunk_id"] == "chunk-semantic-1"


async def test_hybrid_query_can_return_semantic_and_keyword_contexts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Hybrid query retrieval includes both semantic and keyword contexts when available."""

    async def fake_retrieve_semantic(
        query: str,
        top_k: int,
        query_embedding: Sequence[float] | None,
    ) -> list[SourceCitation]:
        """Return one fake semantic source."""
        return [
            SourceCitation(
                title="Hybrid semantic source",
                score=0.8,
                source_type=QueryRoute.SEMANTIC,
                snippet="Meaning-based context.",
                retrieval_mode="semantic",
            )
        ]

    async def fake_retrieve_keyword(query: str, top_k: int) -> list[SourceCitation]:
        """Return one fake keyword source."""
        return [
            SourceCitation(
                title="Hybrid keyword source",
                score=0.7,
                source_type=QueryRoute.BM25,
                snippet="Exact keyword context.",
                retrieval_mode="keyword",
            )
        ]

    monkeypatch.setattr("app.retrieval.router.retrieve_semantic", fake_retrieve_semantic)
    monkeypatch.setattr("app.retrieval.router.retrieve_keyword", fake_retrieve_keyword)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/query",
            json={"query": "Compare exact keyword retrieval across semantic meaning"},
        )

    payload = response.json()
    modes = {source["retrieval_mode"] for source in payload["sources"]}

    assert response.status_code == 200
    assert payload["route_decision"]["route"] == "hybrid"
    assert {"semantic", "keyword"}.issubset(modes)
