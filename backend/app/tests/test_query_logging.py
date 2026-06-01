from collections.abc import Mapping, Sequence
from typing import cast
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import QueryLog, RetrievalRun
from app.db.query_logging import (
    QueryPersistenceResult,
    build_query_log_payload,
    build_retrieval_run_payload,
    persist_query_audit,
)
from app.generation.provider import DisabledAnswerProvider
from app.main import app
from app.schemas.query import (
    Citation,
    ConfidenceResult,
    GenerationMetadata,
    GenerationResult,
    QueryRequest,
    QueryRoute,
    RouteDecision,
    SourceCitation,
    VerificationResult,
)


class FakeSession:
    """Async session double for query logging tests."""

    def __init__(self, fail_commit: bool = False) -> None:
        """Track added ORM objects and optionally fail on commit."""
        self.fail_commit = fail_commit
        self.added: list[object] = []
        self.commits = 0
        self.rollbacks = 0

    def add(self, item: object) -> None:
        """Capture an added ORM object."""
        self.added.append(item)

    async def commit(self) -> None:
        """Commit or raise to simulate a database failure."""
        self.commits += 1
        if self.fail_commit:
            raise RuntimeError("database logging unavailable")

    async def rollback(self) -> None:
        """Track rollback calls."""
        self.rollbacks += 1


class FakeSessionContext:
    """Async context manager returning a fake session."""

    def __init__(self, session: FakeSession) -> None:
        """Store the fake session."""
        self.session = session

    async def __aenter__(self) -> FakeSession:
        """Return the fake session."""
        return self.session

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        """Leave the fake context."""


def fake_session_maker(session: FakeSession) -> object:
    """Return a fake async session maker."""

    def make_session() -> FakeSessionContext:
        return FakeSessionContext(session)

    return make_session


def source(
    retrieval_mode: str = "semantic",
    source_type: QueryRoute = QueryRoute.SEMANTIC,
    source_id: str = "source-1",
    chunk_id: str = "chunk-1",
    score: float = 0.82,
) -> SourceCitation:
    """Build one source citation for query logging tests."""
    return SourceCitation(
        title=f"{retrieval_mode.title()} source",
        score=score,
        source_type=source_type,
        snippet="ContextEngine combines retrieval modes.",
        source_id=source_id,
        chunk_id=chunk_id,
        document_id="document-1",
        retrieval_mode=retrieval_mode,
        retrieval_modes=[retrieval_mode],
        metadata={"document_source_type": "text"},
    )


def request() -> QueryRequest:
    """Build a query request."""
    return QueryRequest(query="What retrieval modes are combined?", top_k=5)


def route_decision() -> RouteDecision:
    """Build a route decision."""
    return RouteDecision(
        route=QueryRoute.HYBRID,
        confidence=0.82,
        reasoning="The query combines multiple retrieval modes.",
    )


def verification() -> VerificationResult:
    """Build a verification result."""
    return VerificationResult(
        grounded=True,
        is_grounded=True,
        has_conflicts=False,
        warnings=["single_source_evidence"],
        evidence_count=1,
        retrieval_modes=["semantic"],
        conflict_notes=[],
        conflicts=[],
        confidence=0.65,
    )


def confidence() -> ConfidenceResult:
    """Build a confidence result."""
    return ConfidenceResult(
        score=0.65,
        label="medium",
        reasons=["route_confidence=0.82", "evidence_count=1"],
        explanation="route_confidence=0.82; evidence_count=1",
    )


def generation() -> GenerationResult:
    """Build a generation result."""
    return GenerationResult(
        answer="ContextEngine combines semantic, keyword, SQL, graph, and wiki retrieval [1].",
        citations=[Citation(title="Semantic source", retrieval_mode="semantic", score=0.82)],
        metadata=GenerationMetadata(
            provider="disabled",
            model="gpt-4o",
            tokens_used=0,
            cost_usd=0.0,
            citation_count=1,
            source_count=1,
            fallback_reason="llm_provider_disabled",
        ),
    )


def test_query_log_payload_includes_audit_fields() -> None:
    """Query log payload captures response, confidence, verification, and counts."""
    payload = build_query_log_payload(
        request=request(),
        route_decision=route_decision(),
        sources=[source()],
        verification=verification(),
        confidence=confidence(),
        generation=generation(),
        latency_ms=42,
    )

    assert payload.query == "What retrieval modes are combined?"
    assert payload.route_decision == "hybrid"
    assert payload.route_confidence == 0.82
    assert payload.confidence == 0.65
    assert payload.confidence_label == "medium"
    assert payload.answer.startswith("ContextEngine combines")
    assert payload.grounded is True
    assert payload.has_conflicts is False
    assert payload.source_count == 1
    assert payload.citation_count == 1
    assert payload.latency_ms == 42
    assert payload.audit_metadata["generation_provider"] == "disabled"


def test_retrieval_run_payload_includes_sources_and_metadata() -> None:
    """Retrieval run payload captures source IDs, scores, top_k, and metadata."""
    query_log_id = UUID("00000000-0000-0000-0000-000000000001")
    payload = build_retrieval_run_payload(
        request=request(),
        route_decision=route_decision(),
        sources=[source()],
        verification=verification(),
        generation=generation(),
        latency_ms=42,
        query_log_id=query_log_id,
    )

    assert payload.query_log_id == query_log_id
    assert payload.route_decision == "hybrid"
    assert payload.confidence == 0.82
    assert payload.retrievers_used == ["semantic"]
    assert payload.top_k == 5
    assert payload.source_ids == ["source-1"]
    assert payload.chunk_ids == ["chunk-1"]
    assert payload.source_scores == {"source-1": 0.82}
    assert payload.audit_metadata["reranker_mode"] == "disabled"
    assert payload.audit_metadata["verification_warnings"] == ["single_source_evidence"]


async def test_persist_query_audit_with_mocked_session() -> None:
    """Successful query audit persistence adds query and retrieval rows."""
    session = FakeSession()

    result = await persist_query_audit(
        request=request(),
        route_decision=route_decision(),
        sources=[source()],
        verification=verification(),
        confidence=confidence(),
        generation=generation(),
        latency_ms=12,
        session=cast(AsyncSession, session),
    )

    assert result.query_log_id is not None
    assert result.retrieval_run_id is not None
    assert session.commits == 1
    assert any(isinstance(item, QueryLog) for item in session.added)
    assert any(isinstance(item, RetrievalRun) for item in session.added)
    retrieval_run = next(item for item in session.added if isinstance(item, RetrievalRun))
    assert retrieval_run.query_log_id == result.query_log_id


async def test_persist_query_audit_failure_returns_empty_result() -> None:
    """Database logging failures are swallowed and rollback is attempted."""
    session = FakeSession(fail_commit=True)

    result = await persist_query_audit(
        request=request(),
        route_decision=route_decision(),
        sources=[source()],
        verification=verification(),
        confidence=confidence(),
        generation=generation(),
        latency_ms=12,
        session=cast(AsyncSession, session),
    )

    assert result == QueryPersistenceResult()
    assert session.commits == 1
    assert session.rollbacks == 1


async def test_query_endpoint_includes_persistence_ids_when_logging_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The query endpoint returns query_log_id and retrieval_run_id after persistence."""
    session = FakeSession()

    async def fake_retrieve_semantic(
        query: str,
        top_k: int,
        query_embedding: Sequence[float] | None,
    ) -> list[SourceCitation]:
        """Return one source without touching a database."""
        return [source()]

    monkeypatch.setattr("app.retrieval.router.retrieve_semantic", fake_retrieve_semantic)
    monkeypatch.setattr(
        "app.db.query_logging.get_session_maker", lambda: fake_session_maker(session)
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/query",
            json={"query": "Which retrieval modes matter?"},
        )

    payload: Mapping[str, object] = response.json()

    assert response.status_code == 200
    assert UUID(str(payload["query_log_id"]))
    assert UUID(str(payload["retrieval_run_id"]))
    assert session.commits == 1


async def test_query_endpoint_succeeds_when_persistence_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Query responses still succeed when audit persistence fails."""
    session = FakeSession(fail_commit=True)

    async def fake_retrieve_semantic(
        query: str,
        top_k: int,
        query_embedding: Sequence[float] | None,
    ) -> list[SourceCitation]:
        """Return one source without touching a database."""
        return [source()]

    monkeypatch.setattr("app.retrieval.router.retrieve_semantic", fake_retrieve_semantic)
    monkeypatch.setattr(
        "app.db.query_logging.get_session_maker", lambda: fake_session_maker(session)
    )
    monkeypatch.setattr(
        "app.generation.generator.get_generation_provider",
        lambda: DisabledAnswerProvider(),
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/query",
            json={"query": "Which retrieval modes matter?"},
        )

    payload = response.json()

    assert response.status_code == 200
    assert "query_log_id" not in payload
    assert "retrieval_run_id" not in payload
    assert payload["answer"].startswith("Based on 1 retrieved source")
    assert session.rollbacks == 1
