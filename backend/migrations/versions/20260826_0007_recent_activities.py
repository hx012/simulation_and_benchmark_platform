"""Add recent activity projection and analytics targets.

Revision ID: 20260826_0007
Revises: 20260826_0006
Create Date: 2026-08-26
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260826_0007"
down_revision: Union[str, Sequence[str], None] = "20260826_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("analytics_events", sa.Column("target_type", sa.String(length=64), nullable=True))
    op.add_column("analytics_events", sa.Column("target_id", sa.String(length=512), nullable=True))
    op.add_column("analytics_events", sa.Column("target_name", sa.String(length=255), nullable=True))
    op.create_table(
        "recent_activities",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("event_name", sa.String(length=128), nullable=False),
        sa.Column("dedupe_key", sa.String(length=512), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.String(length=512), nullable=False),
        sa.Column("target_name", sa.String(length=255), nullable=False),
        sa.Column("context", sa.JSON(), nullable=False),
        sa.Column("last_occurred_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "dedupe_key", name="uq_recent_activities_user_dedupe"),
    )
    op.create_index(
        "ix_recent_activities_user_occurred",
        "recent_activities",
        ["user_id", "last_occurred_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_recent_activities_user_occurred", table_name="recent_activities")
    op.drop_table("recent_activities")
    op.drop_column("analytics_events", "target_name")
    op.drop_column("analytics_events", "target_id")
    op.drop_column("analytics_events", "target_type")
