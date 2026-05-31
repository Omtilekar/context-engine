from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class QueryRoute(StrEnum):
    """Supported query routes for ContextEngine retrieval."""

    WIKI = "wiki"
    SEMANTIC = "semantic"
    BM25 = "bm25"
    SQL = "sql"
    GRAPH = "graph"
    HYBRID = "hybrid"


class QueryRequest(BaseModel):
    """User query request accepted by the backend."""

    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    session_id: str | None = None

    model_config = ConfigDict(str_strip_whitespace=True)


class RouteDecision(BaseModel):
    """Classifier output describing how a query should be retrieved."""

    route: QueryRoute
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    entities: list[str] = Field(default_factory=list)


class SourceCitation(BaseModel):
    """Candidate source returned by a retrieval strategy."""

    title: str
    score: float = Field(ge=0.0, le=1.0)
    source_type: QueryRoute
    snippet: str
    source_id: str | None = None
    chunk_id: str | None = None
    document_id: str | None = None
    retrieval_mode: str | None = None
    retrieval_modes: list[str] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)


class VerificationResult(BaseModel):
    """Grounding, conflict, and confidence result for an answer."""

    grounded: bool
    conflicts: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


class QueryResponse(BaseModel):
    """Structured response returned by the placeholder query pipeline."""

    answer: str
    route_decision: RouteDecision
    sources: list[SourceCitation] = Field(default_factory=list)
    verification: VerificationResult
    tokens_used: int = 0
    cost_usd: float = 0.0

    model_config = ConfigDict(from_attributes=True)
