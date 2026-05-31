from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_name: str = "ContextEngine"
    environment: str = Field(default="development", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    database_url: str = Field(
        default="postgresql+asyncpg://context_engine:context_engine@localhost:5432/contextengine",
        alias="DATABASE_URL",
    )
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    aws_region: str = Field(default="us-east-1", alias="AWS_REGION")
    s3_documents_bucket: str | None = Field(default=None, alias="S3_DOCUMENTS_BUCKET")
    s3_wiki_bucket: str | None = Field(default=None, alias="S3_WIKI_BUCKET")
    sqs_ingest_queue_url: str | None = Field(default=None, alias="SQS_INGEST_QUEUE_URL")
    cognito_user_pool_id: str | None = Field(default=None, alias="COGNITO_USER_POOL_ID")
    cognito_client_id: str | None = Field(default=None, alias="COGNITO_CLIENT_ID")
    cognito_region: str = Field(default="us-east-1", alias="COGNITO_REGION")
    wiki_enabled: bool = Field(default=True, alias="WIKI_ENABLED")
    graph_enabled: bool = Field(default=True, alias="GRAPH_ENABLED")
    verification_enabled: bool = Field(default=True, alias="VERIFICATION_ENABLED")
    memory_update_enabled: bool = Field(default=True, alias="MEMORY_UPDATE_ENABLED")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
