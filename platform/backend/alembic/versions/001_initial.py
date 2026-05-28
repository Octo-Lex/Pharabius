"""Initial schema — all 10 tables.

Revision ID: 001_initial
Revises: None
Create Date: 2026-05-28
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Organizations
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), unique=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )

    # Repositories
    op.create_table(
        "repositories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("vcs_url", sa.String(500), server_default=""),
        sa.Column("default_branch", sa.String(255), server_default="main"),
        sa.Column("last_uploaded_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Artifact Bundles
    op.create_table(
        "artifact_bundles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "repository_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("repositories.id"),
            nullable=False,
        ),
        sa.Column("upload_source", sa.String(50), server_default="manual"),
        sa.Column("file_size_bytes", sa.Integer, nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False, index=True),
        sa.Column("storage_path", sa.String(500), nullable=False),
        sa.Column("parser_version", sa.String(20), server_default="2.2.1"),
        sa.Column("is_valid", sa.Boolean, server_default=sa.text("false")),
        sa.Column("validation_report", postgresql.JSON, nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True)),
    )

    # Runs
    op.create_table(
        "runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "bundle_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("artifact_bundles.id"),
            nullable=False,
        ),
        sa.Column(
            "repository_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("repositories.id"),
            nullable=False,
        ),
        sa.Column("run_id", sa.String(100), nullable=False),
        sa.Column("pharabius_version", sa.String(20), server_default=""),
        sa.Column("run_timestamp", sa.DateTime(timezone=True)),
        sa.Column("total_findings", sa.Integer, server_default="0"),
        sa.Column("critical", sa.Integer, server_default="0"),
        sa.Column("high", sa.Integer, server_default="0"),
        sa.Column("medium", sa.Integer, server_default="0"),
        sa.Column("low", sa.Integer, server_default="0"),
        sa.Column("readiness_status", sa.String(50), server_default="unknown"),
        sa.Column("gate_result", sa.String(20), server_default="unknown"),
    )

    # Findings
    op.create_table(
        "findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("runs.id"),
            nullable=False,
        ),
        sa.Column("finding_id", sa.String(100), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("issue_type", sa.String(50), server_default="technical_debt"),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("confidence", sa.String(20), server_default="Medium"),
        sa.Column("risk_score", sa.Integer, server_default="0"),
        sa.Column("priority", sa.String(20), server_default="Medium"),
    )

    # Quality Gate Results
    op.create_table(
        "quality_gate_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("runs.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("passed", sa.Boolean, nullable=False),
        sa.Column("max_critical", sa.Integer, server_default="0"),
        sa.Column("max_high", sa.Integer, server_default="0"),
        sa.Column("max_total", sa.Integer, server_default="0"),
        sa.Column("rule_results", postgresql.JSON, nullable=True),
    )

    # Trend Snapshots
    op.create_table(
        "trend_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "repository_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("repositories.id"),
            nullable=False,
        ),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("runs.id"),
            nullable=False,
        ),
        sa.Column("total_findings", sa.Integer, server_default="0"),
        sa.Column("critical", sa.Integer, server_default="0"),
        sa.Column("high", sa.Integer, server_default="0"),
        sa.Column("medium", sa.Integer, server_default="0"),
        sa.Column("low", sa.Integer, server_default="0"),
        sa.Column("trajectory", sa.String(30), server_default="insufficient_data"),
        sa.Column("snapshot_date", sa.Date, nullable=False),
    )

    # Claims
    op.create_table(
        "claims",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "bundle_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("artifact_bundles.id"),
            nullable=False,
        ),
        sa.Column(
            "repository_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("repositories.id"),
            nullable=False,
        ),
        sa.Column("claim_id", sa.String(100), nullable=False),
        sa.Column("claim_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("confidence", sa.String(20), nullable=False),
        sa.Column("description", sa.Text, server_default=""),
    )

    # Gaps
    op.create_table(
        "gaps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "bundle_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("artifact_bundles.id"),
            nullable=False,
        ),
        sa.Column(
            "repository_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("repositories.id"),
            nullable=False,
        ),
        sa.Column("gap_id", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("severity", sa.String(20), server_default="Medium"),
    )

    # API Keys
    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column("key_hash", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("key_type", sa.String(20), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("active", sa.Boolean, server_default=sa.text("true")),
    )


def downgrade() -> None:
    op.drop_table("api_keys")
    op.drop_table("gaps")
    op.drop_table("claims")
    op.drop_table("trend_snapshots")
    op.drop_table("quality_gate_results")
    op.drop_table("findings")
    op.drop_table("runs")
    op.drop_table("artifact_bundles")
    op.drop_table("repositories")
    op.drop_table("organizations")
