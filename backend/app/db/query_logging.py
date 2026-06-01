import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.connection import get_session_maker
from app.db.models import QueryLog, RetrievalRun
from app.schemas.query import (
    ConfidenceResult,
    GenerationResult,
    QueryRequest,
    RouteDecision,
    SourceCitation,
    VerificationResult,
)
from app.verification.confidence import collect_retrieval_modes

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class QueryLogPayload:
    """Structured payload used to persist one query log row."""

    id: uuid.UUID
    query: str
    route_decision: str
    confidence: float
    route_confidence: float
    answer: str
    confidence_label: str
    retrievers_used: list[str]
    latency_ms: int | None
    tokens_used: int
    cost_usd: float
    grounded: bool
    has_conflicts: bool
    source_count: int
    citation_count: int
    conflicts: list[str]
    audit_metadata: dict[str, object]


@dataclass(frozen=True, slots=True)
class RetrievalRunPayload:
    """Structured payload used to persist one retrieval run row."""

    id: uuid.UUID
    query_log_id: uuid.UUID
    query: str
    route_decision: str
    confidence: float
    retrievers_used: list[str]
    top_k: int
    source_ids: list[str]
    chunk_ids: list[str]
    source_scores: dict[str, float]
    audit_metadata: dict[str, object]
    status: str
    latency_ms: int | None
    completed_at: datetime


@dataclass(frozen=True, slots=True)
class QueryPersistenceResult:
    """IDs returned after best-effort query persistence."""

    query_log_id: uuid.UUID | None = None
    retrieval_run_id: uuid.UUID | None = None


async def persist_query_audit(
    request: QueryRequest,
    route_decision: RouteDecision,
    sources: Sequence[SourceCitation],
    verification: VerificationResult,
    confidence: ConfidenceResult,
    generation: GenerationResult,
    latency_ms: int | None,
    session: AsyncSession | None = None,
) -> QueryPersistenceResult:
    """Persist query logs and retrieval run metadata without breaking query responses.

    Args:
        request: Original query request.
        route_decision: Selected retrieval route.
        sources: Retrieved sources returned to the user.
        verification: Verification result for the response.
        confidence: Confidence score for the response.
        generation: Generated answer and citation metadata.
        latency_ms: End-to-end query latency in milliseconds, if measured.
        session: Optional async session for tests or orchestration.

    Returns:
        Persisted query log and retrieval run identifiers when storage succeeds.
    """
    query_log_payload = build_query_log_payload(
        request=request,
        route_decision=route_decision,
        sources=sources,
        verification=verification,
        confidence=confidence,
        generation=generation,
        latency_ms=latency_ms,
    )
    retrieval_run_payload = build_retrieval_run_payload(
        request=request,
        route_decision=route_decision,
        sources=sources,
        verification=verification,
        generation=generation,
        latency_ms=latency_ms,
        query_log_id=query_log_payload.id,
    )

    try:
        if session is not None:
            return await persist_query_payloads(
                session,
                query_log_payload,
                retrieval_run_payload,
            )

        session_maker = get_session_maker()
        async with session_maker() as database_session:
            try:
                return await persist_query_payloads(
                    database_session,
                    query_log_payload,
                    retrieval_run_payload,
                )
            except (OSError, SQLAlchemyError, RuntimeError):
                await rollback_logging_session(database_session)
                raise
    except (OSError, SQLAlchemyError, RuntimeError) as error:
        logger.warning("Query audit persistence failed", extra={"error": str(error)})
        if session is not None:
            await rollback_logging_session(session)
        return QueryPersistenceResult()


async def persist_query_payloads(
    session: AsyncSession,
    query_log_payload: QueryLogPayload,
    retrieval_run_payload: RetrievalRunPayload,
) -> QueryPersistenceResult:
    """Persist prepared query audit payloads with an existing session."""
    session.add(query_log_from_payload(query_log_payload))
    session.add(retrieval_run_from_payload(retrieval_run_payload))
    await session.commit()
    return QueryPersistenceResult(
        query_log_id=query_log_payload.id,
        retrieval_run_id=retrieval_run_payload.id,
    )


def build_query_log_payload(
    request: QueryRequest,
    route_decision: RouteDecision,
    sources: Sequence[SourceCitation],
    verification: VerificationResult,
    confidence: ConfidenceResult,
    generation: GenerationResult,
    latency_ms: int | None,
) -> QueryLogPayload:
    """Build the normalized query log payload."""
    retrieval_modes = collect_retrieval_modes(sources)
    return QueryLogPayload(
        id=uuid.uuid4(),
        query=request.query,
        route_decision=route_decision.route.value,
        confidence=confidence.score,
        route_confidence=route_decision.confidence,
        answer=generation.answer,
        confidence_label=confidence.label,
        retrievers_used=retrieval_modes,
        latency_ms=latency_ms,
        tokens_used=generation.metadata.tokens_used,
        cost_usd=generation.metadata.cost_usd,
        grounded=verification.is_grounded,
        has_conflicts=verification.has_conflicts,
        source_count=len(sources),
        citation_count=len(generation.citations),
        conflicts=list(verification.conflict_notes),
        audit_metadata={
            "route_reasoning": route_decision.reasoning,
            "confidence_reasons": list(confidence.reasons),
            "verification_warnings": list(verification.warnings),
            "generation_provider": generation.metadata.provider,
            "generation_model": generation.metadata.model,
            "fallback_reason": generation.metadata.fallback_reason,
        },
    )


def build_retrieval_run_payload(
    request: QueryRequest,
    route_decision: RouteDecision,
    sources: Sequence[SourceCitation],
    verification: VerificationResult,
    generation: GenerationResult,
    latency_ms: int | None,
    query_log_id: uuid.UUID,
) -> RetrievalRunPayload:
    """Build the normalized retrieval run payload."""
    settings = get_settings()
    retrieval_modes = collect_retrieval_modes(sources)
    return RetrievalRunPayload(
        id=uuid.uuid4(),
        query_log_id=query_log_id,
        query=request.query,
        route_decision=route_decision.route.value,
        confidence=route_decision.confidence,
        retrievers_used=retrieval_modes,
        top_k=request.top_k,
        source_ids=source_ids(sources),
        chunk_ids=chunk_ids(sources),
        source_scores=source_scores(sources),
        audit_metadata={
            "reranker_mode": settings.reranker_mode,
            "verification_warnings": list(verification.warnings),
            "generation_provider": generation.metadata.provider,
            "source_count": len(sources),
            "citation_count": len(generation.citations),
            "has_conflicts": verification.has_conflicts,
        },
        status="completed",
        latency_ms=latency_ms,
        completed_at=datetime.now(UTC),
    )


def query_log_from_payload(payload: QueryLogPayload) -> QueryLog:
    """Convert a query log payload into an ORM object."""
    return QueryLog(
        id=payload.id,
        query=payload.query,
        route_decision=payload.route_decision,
        confidence=payload.confidence,
        route_confidence=payload.route_confidence,
        answer=payload.answer,
        confidence_label=payload.confidence_label,
        retrievers_used=payload.retrievers_used,
        latency_ms=payload.latency_ms,
        tokens_used=payload.tokens_used,
        cost_usd=payload.cost_usd,
        grounded=payload.grounded,
        has_conflicts=payload.has_conflicts,
        source_count=payload.source_count,
        citation_count=payload.citation_count,
        conflicts=payload.conflicts,
        audit_metadata=payload.audit_metadata,
    )


def retrieval_run_from_payload(payload: RetrievalRunPayload) -> RetrievalRun:
    """Convert a retrieval run payload into an ORM object."""
    return RetrievalRun(
        id=payload.id,
        query_log_id=payload.query_log_id,
        query=payload.query,
        route_decision=payload.route_decision,
        confidence=payload.confidence,
        retrievers_used=payload.retrievers_used,
        top_k=payload.top_k,
        source_ids=payload.source_ids,
        chunk_ids=payload.chunk_ids,
        source_scores=payload.source_scores,
        audit_metadata=payload.audit_metadata,
        status=payload.status,
        latency_ms=payload.latency_ms,
        completed_at=payload.completed_at,
    )


def source_ids(sources: Sequence[SourceCitation]) -> list[str]:
    """Return source identifiers when available."""
    ids: list[str] = []
    for source in sources:
        identifier = source.source_id or source.document_id
        if identifier and identifier not in ids:
            ids.append(identifier)
    return ids


def chunk_ids(sources: Sequence[SourceCitation]) -> list[str]:
    """Return chunk identifiers when available."""
    ids: list[str] = []
    for source in sources:
        if source.chunk_id and source.chunk_id not in ids:
            ids.append(source.chunk_id)
    return ids


def source_scores(sources: Sequence[SourceCitation]) -> dict[str, float]:
    """Return source scores keyed by stable source or positional identifiers."""
    scores: dict[str, float] = {}
    for index, source in enumerate(sources, start=1):
        key = source.source_id or source.chunk_id or source.document_id or f"source_{index}"
        scores[key] = round(source.score, 4)
    return scores


async def rollback_logging_session(session: AsyncSession) -> None:
    """Rollback a logging session while keeping logging failure-safe."""
    try:
        await session.rollback()
    except Exception as error:
        logger.warning("Query audit rollback failed", extra={"error": str(error)})
