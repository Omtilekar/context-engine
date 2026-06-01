from pathlib import Path

from app.db.models import Base

BACKEND_ROOT = Path(__file__).resolve().parents[2]
INITIAL_MIGRATION = BACKEND_ROOT / "alembic" / "versions" / "0001_initial_schema.py"
QUERY_AUDIT_MIGRATION = BACKEND_ROOT / "alembic" / "versions" / "0002_query_audit_metadata.py"


def test_model_metadata_contains_initial_schema_tables() -> None:
    """SQLAlchemy metadata includes all tables in the initial migration."""
    expected_tables = {
        "chunks",
        "documents",
        "entity_relations",
        "query_logs",
        "retrieval_runs",
        "wiki_pages",
    }

    assert expected_tables.issubset(Base.metadata.tables.keys())
    assert "memory_items" not in Base.metadata.tables


def test_initial_migration_declares_extensions_and_indexes() -> None:
    """Initial migration creates required extensions and core indexes."""
    migration = INITIAL_MIGRATION.read_text(encoding="utf-8")

    required_snippets = [
        "CREATE EXTENSION IF NOT EXISTS vector",
        "CREATE EXTENSION IF NOT EXISTS pg_trgm",
        "ix_documents_source_type",
        "ix_documents_s3_key",
        "ix_chunks_document_id",
        "ix_chunks_embedding_hnsw",
        "ix_chunks_content_tsvector",
        "ix_retrieval_runs_created_at",
        "ix_query_logs_created_at",
    ]

    for snippet in required_snippets:
        assert snippet in migration


def test_alembic_async_environment_is_configured() -> None:
    """Alembic environment uses SQLAlchemy's async migration engine."""
    env_py = (BACKEND_ROOT / "alembic" / "env.py").read_text(encoding="utf-8")

    assert "async_engine_from_config" in env_py
    assert "asyncio.run(run_migrations_online())" in env_py
    assert "get_settings().database_url" in env_py


def test_query_audit_migration_adds_metadata_columns() -> None:
    """Query audit migration adds JSONB metadata and query-log linkage."""
    migration = QUERY_AUDIT_MIGRATION.read_text(encoding="utf-8")

    required_snippets = [
        "route_confidence",
        "confidence_label",
        "source_count",
        "citation_count",
        "query_log_id",
        "source_scores",
        "metadata",
        "ix_retrieval_runs_query_log_id",
        "fk_retrieval_runs_query_log_id_query_logs",
    ]

    for snippet in required_snippets:
        assert snippet in migration
