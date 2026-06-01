from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.db.connection import close_database_connections
from app.db.query_logging import persist_query_audit
from app.generation.generator import generate_answer
from app.ingestion.pipeline import IngestionPipeline
from app.retrieval.router import RetrievalRouter
from app.schemas.document import DocumentIngestRequest, IngestResponse, StatusResponse
from app.schemas.query import QueryRequest, QueryResponse
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


@app.post("/query", response_model=QueryResponse, response_model_exclude_none=True)
async def query(request: QueryRequest) -> QueryResponse:
    """Route a query and return an extendable placeholder answer."""
    start_time = perf_counter()
    router = RetrievalRouter()
    route_decision = await router.route(request)
    sources = await router.retrieve(request, route_decision)
    verification = verify_response(
        query=request.query,
        answer="",
        route_confidence=route_decision.confidence,
        sources=sources,
    )
    confidence = score_confidence(sources, route_decision.confidence, verification)
    generation = await generate_answer(
        query=request.query,
        sources=sources,
        verification=verification,
        confidence=confidence,
    )
    latency_ms = int((perf_counter() - start_time) * 1000)
    persistence = await persist_query_audit(
        request=request,
        route_decision=route_decision,
        sources=sources,
        verification=verification,
        confidence=confidence,
        generation=generation,
        latency_ms=latency_ms,
    )
    return QueryResponse(
        answer=generation.answer,
        route_decision=route_decision,
        sources=sources,
        citations=generation.citations,
        verification=verification,
        confidence=confidence,
        generation_metadata=generation.metadata,
        query_log_id=persistence.query_log_id,
        retrieval_run_id=persistence.retrieval_run_id,
        tokens_used=generation.metadata.tokens_used,
        cost_usd=generation.metadata.cost_usd,
    )


@app.post("/ingest", response_model=IngestResponse)
async def ingest(request: DocumentIngestRequest) -> IngestResponse:
    """Persist a text ingestion request into document and chunk tables."""
    pipeline = IngestionPipeline()
    return await pipeline.ingest(request)
