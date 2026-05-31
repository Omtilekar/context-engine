from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.db.connection import close_database_connections
from app.ingestion.pipeline import IngestionPipeline
from app.retrieval.router import RetrievalRouter
from app.schemas.document import DocumentIngestRequest, IngestResponse, StatusResponse
from app.schemas.query import ConfidenceResult, QueryRequest, QueryResponse, VerificationResult
from app.verification.confidence import score_confidence
from app.verification.verifier import verify_response

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Configure application resources for the FastAPI lifespan."""
    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info("Starting ContextEngine backend", extra={"environment": settings.environment})
    yield
    await close_database_connections()
    logger.info("Stopped ContextEngine backend")


app = FastAPI(
    title="ContextEngine API",
    description="Hybrid RAG and vectorless retrieval backend.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health() -> dict[str, str]:
    """Return a lightweight ALB-compatible health response."""
    return {"status": "ok", "service": "context-engine-backend"}


@app.get("/status", response_model=StatusResponse)
async def status() -> StatusResponse:
    """Return runtime feature status without requiring external service calls."""
    settings = get_settings()
    return StatusResponse(
        service="context-engine-backend",
        environment=settings.environment,
        database_configured=bool(settings.database_url),
        vector_support="pgvector-placeholder",
        wiki_enabled=settings.wiki_enabled,
        graph_enabled=settings.graph_enabled,
        verification_enabled=settings.verification_enabled,
        memory_update_enabled=settings.memory_update_enabled,
    )


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest) -> QueryResponse:
    """Route a query and return an extendable placeholder answer."""
    router = RetrievalRouter()
    route_decision = await router.route(request)
    sources = await router.retrieve(request, route_decision)
    base_answer = (
        "ContextEngine backend foundation is online. Full retrieval and LLM generation "
        "will be implemented in the next Phase 3 tasks."
    )
    verification = verify_response(
        query=request.query,
        answer=base_answer,
        route_confidence=route_decision.confidence,
        sources=sources,
    )
    confidence = score_confidence(sources, route_decision.confidence, verification)
    answer = build_placeholder_answer(base_answer, verification, confidence)
    return QueryResponse(
        answer=answer,
        route_decision=route_decision,
        sources=sources,
        verification=verification,
        confidence=confidence,
        tokens_used=0,
        cost_usd=0.0,
    )


@app.post("/ingest", response_model=IngestResponse)
async def ingest(request: DocumentIngestRequest) -> IngestResponse:
    """Accept an ingestion request and return a queued placeholder job."""
    pipeline = IngestionPipeline()
    return await pipeline.ingest(request)


def build_placeholder_answer(
    base_answer: str,
    verification: VerificationResult,
    confidence: ConfidenceResult,
) -> str:
    """Return a deterministic placeholder answer that reflects evidence quality."""
    if not verification.is_grounded:
        return (
            f"{base_answer} No supporting evidence was retrieved yet, so this response "
            "should be treated as low confidence."
        )
    if verification.has_conflicts:
        return (
            f"{base_answer} Retrieved evidence is available, but deterministic checks found "
            "possible conflicts that should be resolved before final answer generation."
        )
    if confidence.label == "low":
        return (
            f"{base_answer} Retrieved evidence is weak, so the answer generator should "
            "request stronger citations before making a firm claim."
        )
    return f"{base_answer} Retrieved evidence passed deterministic verification checks."
