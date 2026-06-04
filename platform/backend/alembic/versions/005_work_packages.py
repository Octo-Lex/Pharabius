"""Add work_packages and work_package_findings tables.

Revision ID: 005
Revises: 004
Create Date: 2026-05-29
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "work_packages",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "repository_id",
            sa.UUID(),
            sa.ForeignKey("repositories.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("run_id", sa.UUID(), sa.ForeignKey("runs.id"), nullable=False, index=True),
        sa.Column("package_id", sa.String(50), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("objective", sa.Text(), server_default=""),
        sa.Column("current_risk", sa.Text(), server_default=""),
        sa.Column("recommended_engineering_approach", sa.JSON(), server_default="[]"),
        sa.Column("expected_affected_areas", sa.JSON(), server_default="[]"),
        sa.Column("preconditions", sa.JSON(), server_default="[]"),
        sa.Column("verification_recommendations", sa.JSON(), server_default="[]"),
        sa.Column("risks_and_cautions", sa.JSON(), server_default="[]"),
        sa.Column("definition_of_done", sa.JSON(), server_default="[]"),
        sa.Column("estimated_effort", sa.String(100), server_default=""),
        sa.Column("expected_risk_reduction", sa.String(100), server_default=""),
        sa.Column("suggested_owner_area", sa.String(255), server_default=""),
        sa.Column("status", sa.String(100), server_default=""),
        sa.Column("declared_evidence_ids", sa.JSON(), server_default="[]"),
        sa.Column("raw_payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_work_packages_repo_run_pkg",
        "work_packages",
        ["repository_id", "run_id", "package_id"],
        unique=True,
    )

    op.create_table(
        "work_package_findings",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "work_package_id",
            sa.UUID(),
            sa.ForeignKey("work_packages.id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "finding_id",
            sa.UUID(),
            sa.ForeignKey("findings.id"),
            nullable=True,
        ),
        sa.Column("debt_item_id", sa.String(100), nullable=False),
        sa.Column("resolution_status", sa.String(30), server_default="unresolved"),
        sa.Column("reason", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_wp_findings_wp_debt",
        "work_package_findings",
        ["work_package_id", "debt_item_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_wp_findings_wp_debt")
    op.drop_table("work_package_findings")
    op.drop_index("ix_work_packages_repo_run_pkg")
    op.drop_table("work_packages")
