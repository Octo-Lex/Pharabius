"""Add evidence_records table.

Revision ID: 004
Revises: 003
Create Date: 2026-05-29
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "evidence_records",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "repository_id", sa.UUID(), sa.ForeignKey("repositories.id"), nullable=False, index=True
        ),
        sa.Column("run_id", sa.UUID(), sa.ForeignKey("runs.id"), nullable=False, index=True),
        sa.Column("evidence_id", sa.String(100), nullable=False),
        sa.Column("source", sa.String(100), server_default="unknown"),
        sa.Column("type", sa.String(100), server_default="unknown"),
        sa.Column("category", sa.String(100), server_default="unknown"),
        sa.Column("file_path", sa.String(500), server_default=""),
        sa.Column("line_start", sa.Integer(), nullable=True),
        sa.Column("line_end", sa.Integer(), nullable=True),
        sa.Column("subject", sa.Text(), server_default=""),
        sa.Column("object", sa.Text(), server_default=""),
        sa.Column("summary", sa.Text(), server_default=""),
        sa.Column("raw_observation", sa.Text(), server_default=""),
        sa.Column("confidence", sa.String(20), server_default="Medium"),
        sa.Column("collected_at", sa.String(100), server_default=""),
        sa.Column("evidence_metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_evidence_records_repo_run_evid",
        "evidence_records",
        ["repository_id", "run_id", "evidence_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_evidence_records_repo_run_evid")
    op.drop_table("evidence_records")
