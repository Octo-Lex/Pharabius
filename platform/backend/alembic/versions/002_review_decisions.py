"""Add review_decisions table for hosted finding review workflow.

Revision ID: 002_review_decisions
Revises: 001_initial
Create Date: 2026-05-28
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "002_review_decisions"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "review_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "repository_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("repositories.id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("runs.id"),
            nullable=True,
        ),
        sa.Column("finding_id", sa.String(100), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("previous_status", sa.String(30), server_default=""),
        sa.Column("reviewer", sa.String(255), server_default=""),
        sa.Column("rationale", sa.Text, server_default=""),
        sa.Column("ticket_url", sa.String(500), server_default=""),
        sa.Column("owner_area", sa.String(255), server_default=""),
        sa.Column("target_release", sa.String(100), server_default=""),
        sa.Column("notes", sa.Text, server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", sa.String(255), server_default=""),
        sa.Column("delete_reason", sa.Text, server_default=""),
    )
    op.create_index(
        "ix_review_decisions_repo_finding",
        "review_decisions",
        ["repository_id", "finding_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_review_decisions_repo_finding")
    op.drop_table("review_decisions")
