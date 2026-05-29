"""Add commit_sha, branch_name, analysis_mode to runs.

Revision ID: 006
Revises: 005
Create Date: 2026-05-29
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("runs", sa.Column("commit_sha", sa.String(40), server_default=""))
    op.add_column("runs", sa.Column("branch_name", sa.String(255), server_default=""))
    op.add_column("runs", sa.Column("analysis_mode", sa.String(50), server_default="baseline"))


def downgrade() -> None:
    op.drop_column("runs", "analysis_mode")
    op.drop_column("runs", "branch_name")
    op.drop_column("runs", "commit_sha")
