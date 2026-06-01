from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SourceType(StrEnum):
    """Supported ingestion source types."""

    PDF = "pdf"
    DOCX = "docx"
    WEB = "web"
    DATABASE = "database"
    API = "api"
    SPREADSHEET = "spreadsheet"
    TEXT = "text"


class DocumentIngestRequest(BaseModel):
    """Document ingestion request accepted by the ingestion pipeline."""

    source_type: SourceType
    title: str = Field(min_length=1)
    filename: str | None = Field(default=None, min_length=1)
    content: str | None = None
    url: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)

    model_config = ConfigDict(str_strip_whitespace=True)


class IngestResponse(BaseModel):
    """Response returned after an ingestion request is processed."""

    document_id: UUID
    status: str
    source_type: SourceType
    chunks_planned: int
    chunk_count: int
    title: str
    filename: str
    metadata: dict[str, str] = Field(default_factory=dict)
    message: str


class StatusResponse(BaseModel):
    """Runtime status for local and deployed backend checks."""

    service: str
    environment: str
    database_configured: bool
    vector_support: str
    wiki_enabled: bool
    graph_enabled: bool
    verification_enabled: bool
    memory_update_enabled: bool
