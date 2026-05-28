"""Add description, locations, evidence_ids to findings.

Revision ID: 003
Revises: 002
Create Date: 2026-05-29
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "findings",
        sa.Column("description", sa.Text(), server_default=""),
    )
    op.add_column(
        "findings",
        sa.Column("locations", sa.JSON(), nullable=True),
    )
    op.add_column(
        "findings",
        sa.Column("evidence_ids", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("findings", "evidence_ids")
    op.drop_column("findings", "locations")
    op.drop_column("findings", "description")
