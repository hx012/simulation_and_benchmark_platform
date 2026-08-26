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
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    analytics_columns = {
        column["name"] for column in inspector.get_columns("analytics_events")
    }
    target_columns = {
        "target_type": sa.String(length=64),
        "target_id": sa.String(length=512),
        "target_name": sa.String(length=255),
    }
    for name, column_type in target_columns.items():
        if name not in analytics_columns:
            op.add_column(
                "analytics_events",
                sa.Column(name, column_type, nullable=True),
            )

    inspector = sa.inspect(bind)
    if "recent_activities" not in inspector.get_table_names():
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

    existing_indexes = {
        index["name"] for index in sa.inspect(bind).get_indexes("recent_activities")
    }
    if "ix_recent_activities_user_occurred" not in existing_indexes:
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
