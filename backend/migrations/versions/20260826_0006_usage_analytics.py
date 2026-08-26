"""Add usage analytics events.

Revision ID: 20260826_0006
Revises: 20260825_0005
Create Date: 2026-08-26
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260826_0006"
down_revision: Union[str, Sequence[str], None] = "20260825_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "analytics_events" not in inspector.get_table_names():
        op.create_table(
            "analytics_events",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("event_id", sa.String(length=64), nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("session_id", sa.String(length=64), nullable=False),
            sa.Column("event_name", sa.String(length=128), nullable=False),
            sa.Column("page_key", sa.String(length=128), nullable=False),
            sa.Column("result", sa.String(length=32), nullable=False),
            sa.Column("active_seconds", sa.Integer(), nullable=False),
            sa.Column("vendor", sa.String(length=128), nullable=True),
            sa.Column("chip", sa.String(length=128), nullable=True),
            sa.Column("benchmark_name", sa.String(length=255), nullable=True),
            sa.Column("benchmark_type", sa.String(length=64), nullable=True),
            sa.Column("test_target", sa.String(length=128), nullable=True),
            sa.Column("simulator_version", sa.String(length=128), nullable=True),
            sa.Column("chip_variant", sa.String(length=128), nullable=True),
            sa.Column("simulation_mode", sa.String(length=64), nullable=True),
            sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("event_id", name="uq_analytics_events_event_id"),
        )

    existing_indexes = {
        index["name"] for index in sa.inspect(bind).get_indexes("analytics_events")
    }
    indexes = {
        "ix_analytics_events_occurred": ["occurred_at"],
        "ix_analytics_events_user_occurred": ["user_id", "occurred_at"],
        "ix_analytics_events_page_occurred": ["page_key", "occurred_at"],
        "ix_analytics_events_name_occurred": ["event_name", "occurred_at"],
        "ix_analytics_events_chip_occurred": ["chip", "occurred_at"],
        "ix_analytics_events_benchmark_occurred": ["benchmark_name", "occurred_at"],
    }
    for name, columns in indexes.items():
        if name not in existing_indexes:
            op.create_index(name, "analytics_events", columns)


def downgrade() -> None:
    op.drop_index("ix_analytics_events_benchmark_occurred", table_name="analytics_events")
    op.drop_index("ix_analytics_events_chip_occurred", table_name="analytics_events")
    op.drop_index("ix_analytics_events_name_occurred", table_name="analytics_events")
    op.drop_index("ix_analytics_events_page_occurred", table_name="analytics_events")
    op.drop_index("ix_analytics_events_user_occurred", table_name="analytics_events")
    op.drop_index("ix_analytics_events_occurred", table_name="analytics_events")
    op.drop_table("analytics_events")
