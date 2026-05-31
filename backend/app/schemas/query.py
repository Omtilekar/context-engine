from enum import StrEnum
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

MetadataValue = str | int | float | bool


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
    metadata: dict[str, MetadataValue] = Field(default_factory=dict)


class VerificationResult(BaseModel):
    """Grounding, conflict, and confidence result for an answer."""

    grounded: bool = False
    is_grounded: bool = False
    has_conflicts: bool = False
    warnings: list[str] = Field(default_factory=list)
    evidence_count: int = Field(default=0, ge=0)
    retrieval_modes: list[str] = Field(default_factory=list)
    conflict_notes: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def sync_legacy_fields(self) -> Self:
        """Keep legacy and detailed verification fields consistent."""
        grounded = self.grounded or self.is_grounded
        conflicts = [*self.conflicts, *self.conflict_notes]
        unique_conflicts = list(dict.fromkeys(conflicts))
        self.grounded = grounded
        self.is_grounded = grounded
        self.conflicts = unique_conflicts
        self.conflict_notes = unique_conflicts
        self.has_conflicts = self.has_conflicts or bool(unique_conflicts)
        return self


class ConfidenceResult(BaseModel):
    """Deterministic confidence score returned with each query response."""

    score: float = Field(ge=0.0, le=1.0)
    label: Literal["low", "medium", "high"]
    reasons: list[str] = Field(default_factory=list)
    explanation: str


class Citation(BaseModel):
    """Citation metadata exposed with generated answers."""

    title: str
    retrieval_mode: str
    score: float = Field(ge=0.0, le=1.0)


class GenerationMetadata(BaseModel):
    """Metadata describing answer generation behavior."""

    provider: str
    model: str
    tokens_used: int = Field(default=0, ge=0)
    cost_usd: float = Field(default=0.0, ge=0.0)
    citation_count: int = Field(default=0, ge=0)
    source_count: int = Field(default=0, ge=0)
    fallback_reason: str | None = None


class GenerationResult(BaseModel):
    """Answer synthesis output from the generation layer."""

    answer: str
    citations: list[Citation] = Field(default_factory=list)
    metadata: GenerationMetadata


class QueryResponse(BaseModel):
    """Structured response returned by the placeholder query pipeline."""

    answer: str
    route_decision: RouteDecision
    sources: list[SourceCitation] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    verification: VerificationResult
    confidence: ConfidenceResult
    generation_metadata: GenerationMetadata
    tokens_used: int = 0
    cost_usd: float = 0.0

    model_config = ConfigDict(from_attributes=True)
