from collections.abc import Mapping
from typing import cast

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import TextClause
from sqlalchemy.ext.asyncio import AsyncSession

from app.generation.generator import extract_used_citations
from app.main import app
from app.retrieval.graph import (
    GRAPH_ONE_HOP_SQL,
    GRAPH_TWO_HOP_SQL,
    extract_graph_entities,
    graph_row_to_source,
    retrieve_graph,
)
from app.retrieval.router import RetrievalRouter
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
    """Async session double for graph retriever tests."""

    def __init__(self, row_groups: list[list[Mapping[str, object]]]) -> None:
        """Store rows returned on each execute call."""
        self._row_groups = row_groups
        self.statements: list[TextClause] = []
        self.parameters: list[Mapping[str, object]] = []

    async def execute(
        self,
        statement: TextClause,
        parameters: Mapping[str, object],
    ) -> FakeResult:
        """Capture query details and return the next fake row group."""
        self.statements.append(statement)
        self.parameters.append(parameters)
        rows = self._row_groups.pop(0) if self._row_groups else []
        return FakeResult(rows)


def graph_row(
    source_entity: str = "ContextEngine",
    relationship_type: str = "uses",
    target_entity: str = "PostgreSQL",
    relation_id: str = "rel-1",
    hop_count: int = 1,
    intermediate_entity: str | None = None,
    confidence: float = 0.95,
) -> dict[str, object]:
    """Build one graph retriever row."""
    return {
        "relation_id": relation_id,
        "source_entity": source_entity,
        "relationship_type": relationship_type,
        "target_entity": target_entity,
        "source_chunk_id": None,
        "confidence": confidence,
        "hop_count": hop_count,
        "intermediate_entity": intermediate_entity,
    }


def test_extract_graph_entities_from_supported_queries() -> None:
    """Graph entity extraction handles relation, connected, linked, and quoted queries."""
    assert extract_graph_entities("How is ContextEngine related to PostgreSQL?") == [
        "contextengine",
        "postgresql",
    ]
    assert extract_graph_entities("What is connected to pgvector?") == ["pgvector"]
    assert extract_graph_entities("Show relationships for FlashRank") == ["flashrank"]
    assert extract_graph_entities('Which entities are linked to "AWS"?') == ["aws"]


def test_graph_sql_uses_bound_entity_parameters() -> None:
    """Graph SQL uses bind parameters instead of interpolating user text."""
    assert "IN :entities" in GRAPH_ONE_HOP_SQL
    assert "IN :entities" in GRAPH_TWO_HOP_SQL
    assert "DROP TABLE" not in GRAPH_ONE_HOP_SQL.upper()
    assert "DROP TABLE" not in GRAPH_TWO_HOP_SQL.upper()


def test_graph_row_to_source_returns_expected_schema() -> None:
    """Graph rows map to citation-friendly SourceCitation values."""
    source = graph_row_to_source(graph_row())

    assert source.source_type == QueryRoute.GRAPH
    assert source.retrieval_mode == "graph"
    assert source.retrieval_modes == ["graph"]
    assert source.title == "Graph: ContextEngine -> PostgreSQL"
    assert source.snippet == "ContextEngine uses PostgreSQL."
    assert source.metadata["source_entity"] == "ContextEngine"
    assert source.metadata["target_entity"] == "PostgreSQL"
    assert source.metadata["relationship_type"] == "uses"
    assert source.metadata["hop_count"] == 1


async def test_retrieve_graph_returns_one_hop_relationships() -> None:
    """Graph retriever returns 1-hop entity relationships from a fake session."""
    fake_session = FakeSession([[graph_row()]])

    sources = await retrieve_graph(
        "What is connected to ContextEngine?",
        top_k=5,
        session=cast(AsyncSession, fake_session),
        include_two_hop=False,
    )

    assert len(sources) == 1
    assert sources[0].metadata["hop_count"] == 1
    assert sources[0].metadata["source_entity"] == "ContextEngine"
    assert fake_session.parameters[0]["entities"] == ("contextengine",)


async def test_retrieve_graph_can_return_two_hop_paths() -> None:
    """Graph retriever can include directed 2-hop paths."""
    two_hop_row = graph_row(
        source_entity="ContextEngine",
        relationship_type="uses -> stored_in",
        target_entity="PostgreSQL",
        relation_id="rel-2:rel-3",
        hop_count=2,
        intermediate_entity="pgvector",
        confidence=0.81,
    )
    fake_session = FakeSession([[graph_row()], [two_hop_row]])

    sources = await retrieve_graph(
        "How is ContextEngine related to PostgreSQL?",
        top_k=5,
        session=cast(AsyncSession, fake_session),
    )

    assert len(sources) == 2
    two_hop_source = next(source for source in sources if source.metadata["hop_count"] == 2)
    assert "then pgvector stored in PostgreSQL" in two_hop_source.snippet
    assert two_hop_source.metadata["intermediate_entity"] == "pgvector"


async def test_retrieve_graph_returns_empty_for_blank_or_unknown_entity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Blank or unparseable graph queries return empty results without opening DB sessions."""

    def fail_if_database_is_used() -> None:
        raise AssertionError("graph retriever should not request a database session")

    monkeypatch.setattr("app.retrieval.graph.get_session_maker", fail_if_database_is_used)

    assert await retrieve_graph("   ", top_k=5) == []
    assert await retrieve_graph("relationship?", top_k=5) == []


async def test_router_detects_graph_relationship_queries() -> None:
    """Router sends relationship/linked/dependency/graph queries to graph retrieval."""
    router = RetrievalRouter()
    queries = [
        "Which entities are linked to ContextEngine?",
        "Show relationships for pgvector",
        "What dependency is connected to FlashRank?",
        "Graph for ContextEngine",
    ]

    for query in queries:
        decision = await router.route(QueryRequest(query=query))
        assert decision.route == QueryRoute.GRAPH


def test_graph_citation_schema_uses_retrieval_mode_graph() -> None:
    """Graph sources produce public citations with retrieval_mode=graph."""
    source = graph_row_to_source(graph_row())
    citations = extract_used_citations("ContextEngine uses PostgreSQL [1].", [source])

    assert citations[0].title == "Graph: ContextEngine -> PostgreSQL"
    assert citations[0].retrieval_mode == "graph"
    assert citations[0].score == 0.95


async def test_graph_query_endpoint_returns_graph_answer_and_citations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The query endpoint integrates graph retrieval with generation and citations."""

    async def fake_retrieve_graph(query: str, top_k: int) -> list[SourceCitation]:
        """Return one graph source without touching a database."""
        return [graph_row_to_source(graph_row())]

    monkeypatch.setattr("app.retrieval.router.retrieve_graph", fake_retrieve_graph)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/query",
            json={"query": "Which entities are linked to ContextEngine?"},
        )

    payload = response.json()

    assert response.status_code == 200
    assert payload["route_decision"]["route"] == "graph"
    assert payload["sources"][0]["retrieval_mode"] == "graph"
    assert payload["sources"][0]["metadata"]["hop_count"] == 1
    assert payload["citations"][0]["retrieval_mode"] == "graph"
    assert payload["answer"].startswith("Based on 1 retrieved source")
