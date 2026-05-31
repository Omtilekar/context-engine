"""Create initial ContextEngine database schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-05-31 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create extensions, core tables, and retrieval indexes."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "documents",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("s3_key", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=50), server_default="pending", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_documents_source_type", "documents", ["source_type"])
    op.create_index("ix_documents_s3_key", "documents", ["s3_key"])
    op.create_index("ix_documents_status", "documents", ["status"])

    op.create_table(
        "chunks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chunks_document_id", "chunks", ["document_id"])

    # HNSW is pgvector-specific, so it is written explicitly instead of relying on
    # Alembic autogeneration. The table is empty at first deploy, which is the safest
    # time to build this index.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_chunks_embedding_hnsw "
        "ON chunks USING hnsw (embedding vector_cosine_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_chunks_content_tsvector "
        "ON chunks USING gin(to_tsvector('english', content))"
    )

    op.create_table(
        "entity_relations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("entity_a", sa.String(length=255), nullable=False),
        sa.Column("relation_type", sa.String(length=100), nullable=False),
        sa.Column("entity_b", sa.String(length=255), nullable=False),
        sa.Column("source_chunk_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("confidence", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["source_chunk_id"], ["chunks.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_entity_relations_entity_a", "entity_relations", ["entity_a"])
    op.create_index("ix_entity_relations_entity_b", "entity_relations", ["entity_b"])

    op.create_table(
        "wiki_pages",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tags", postgresql.ARRAY(sa.Text()), server_default=sa.text("'{}'::text[]")),
        sa.Column(
            "source_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            server_default=sa.text("'{}'::uuid[]"),
        ),
        sa.Column(
            "wikilinks",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("title"),
    )
    op.create_index("ix_wiki_pages_tags", "wiki_pages", ["tags"], postgresql_using="gin")
    op.create_index(
        "ix_wiki_pages_wikilinks",
        "wiki_pages",
        ["wikilinks"],
        postgresql_using="gin",
    )

    op.create_table(
        "retrieval_runs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("route_decision", sa.String(length=50), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column(
            "retrievers_used",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column("status", sa.String(length=50), server_default="started", nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_retrieval_runs_created_at", "retrieval_runs", ["created_at"])
    op.create_index("ix_retrieval_runs_route_decision", "retrieval_runs", ["route_decision"])
    op.create_index("ix_retrieval_runs_status", "retrieval_runs", ["status"])

    op.create_table(
        "query_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("route_decision", sa.String(length=50), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column(
            "retrievers_used",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("tokens_used", sa.Integer(), server_default="0", nullable=False),
        sa.Column("cost_usd", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("grounded", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column(
            "conflicts",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_query_logs_created_at", "query_logs", ["created_at"])
    op.create_index("ix_query_logs_route_decision", "query_logs", ["route_decision"])


def downgrade() -> None:
    """Drop initial schema objects."""
    op.drop_index("ix_query_logs_route_decision", table_name="query_logs")
    op.drop_index("ix_query_logs_created_at", table_name="query_logs")
    op.drop_table("query_logs")

    op.drop_index("ix_retrieval_runs_status", table_name="retrieval_runs")
    op.drop_index("ix_retrieval_runs_route_decision", table_name="retrieval_runs")
    op.drop_index("ix_retrieval_runs_created_at", table_name="retrieval_runs")
    op.drop_table("retrieval_runs")

    op.drop_index("ix_wiki_pages_wikilinks", table_name="wiki_pages")
    op.drop_index("ix_wiki_pages_tags", table_name="wiki_pages")
    op.drop_table("wiki_pages")

    op.drop_index("ix_entity_relations_entity_b", table_name="entity_relations")
    op.drop_index("ix_entity_relations_entity_a", table_name="entity_relations")
    op.drop_table("entity_relations")

    op.execute("DROP INDEX IF EXISTS ix_chunks_content_tsvector")
    op.execute("DROP INDEX IF EXISTS ix_chunks_embedding_hnsw")
    op.drop_index("ix_chunks_document_id", table_name="chunks")
    op.drop_table("chunks")

    op.drop_index("ix_documents_status", table_name="documents")
    op.drop_index("ix_documents_s3_key", table_name="documents")
    op.drop_index("ix_documents_source_type", table_name="documents")
    op.drop_table("documents")

    op.execute("DROP EXTENSION IF EXISTS vector")
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
    op.execute("DROP EXTENSION IF EXISTS pgcrypto")
