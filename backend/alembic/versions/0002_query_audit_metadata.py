"""Add query audit metadata fields.

Revision ID: 0002_query_audit_metadata
Revises: 0001_initial_schema
Create Date: 2026-05-31 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002_query_audit_metadata"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add detailed query and retrieval-run audit columns."""
    op.add_column("query_logs", sa.Column("route_confidence", sa.Float(), nullable=True))
    op.add_column("query_logs", sa.Column("answer", sa.Text(), nullable=True))
    op.add_column("query_logs", sa.Column("confidence_label", sa.String(length=20), nullable=True))
    op.add_column(
        "query_logs",
        sa.Column("has_conflicts", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "query_logs",
        sa.Column("source_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "query_logs",
        sa.Column("citation_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "query_logs",
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )

    op.add_column("retrieval_runs", sa.Column("query_log_id", postgresql.UUID(), nullable=True))
    op.add_column("retrieval_runs", sa.Column("top_k", sa.Integer(), nullable=True))
    op.add_column(
        "retrieval_runs",
        sa.Column(
            "source_ids",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'::text[]"),
            nullable=False,
        ),
    )
    op.add_column(
        "retrieval_runs",
        sa.Column(
            "chunk_ids",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'::text[]"),
            nullable=False,
        ),
    )
    op.add_column(
        "retrieval_runs",
        sa.Column(
            "source_scores",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "retrieval_runs",
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_retrieval_runs_query_log_id",
        "retrieval_runs",
        ["query_log_id"],
    )
    op.create_foreign_key(
        "fk_retrieval_runs_query_log_id_query_logs",
        "retrieval_runs",
        "query_logs",
        ["query_log_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Remove detailed query and retrieval-run audit columns."""
    op.drop_constraint(
        "fk_retrieval_runs_query_log_id_query_logs",
        "retrieval_runs",
        type_="foreignkey",
    )
    op.drop_index("ix_retrieval_runs_query_log_id", table_name="retrieval_runs")
    op.drop_column("retrieval_runs", "metadata")
    op.drop_column("retrieval_runs", "source_scores")
    op.drop_column("retrieval_runs", "chunk_ids")
    op.drop_column("retrieval_runs", "source_ids")
    op.drop_column("retrieval_runs", "top_k")
    op.drop_column("retrieval_runs", "query_log_id")

    op.drop_column("query_logs", "metadata")
    op.drop_column("query_logs", "citation_count")
    op.drop_column("query_logs", "source_count")
    op.drop_column("query_logs", "has_conflicts")
    op.drop_column("query_logs", "confidence_label")
    op.drop_column("query_logs", "answer")
    op.drop_column("query_logs", "route_confidence")
