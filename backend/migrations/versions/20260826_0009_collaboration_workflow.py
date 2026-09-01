"""Persist feedback and demand processing workflows.

Revision ID: 20260826_0009
Revises: 20260826_0008
Create Date: 2026-08-26
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260826_0009"
down_revision: Union[str, Sequence[str], None] = "20260826_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("feedback_entries") as batch_op:
        batch_op.add_column(sa.Column("resolution", sa.Text(), server_default="", nullable=False))
        batch_op.add_column(sa.Column("handler_user_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False))
        batch_op.add_column(sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_foreign_key("fk_feedback_handler_user", "users", ["handler_user_id"], ["id"], ondelete="SET NULL")
        batch_op.create_index("ix_feedback_entries_status_updated", ["status", "updated_at"])

    op.create_table(
        "feedback_messages",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("feedback_id", sa.String(length=36), nullable=False),
        sa.Column("author_user_id", sa.String(length=36), nullable=True),
        sa.Column("author_role", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["feedback_id"], ["feedback_entries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_feedback_messages_feedback_created", "feedback_messages", ["feedback_id", "created_at"])

    with op.batch_alter_table("demands") as batch_op:
        batch_op.add_column(sa.Column("status", sa.String(length=32), server_default="pending", nullable=False))
        batch_op.add_column(sa.Column("conclusion", sa.Text(), server_default="", nullable=False))
        batch_op.add_column(sa.Column("visibility", sa.String(length=32), server_default="private", nullable=False))
        batch_op.add_column(sa.Column("priority", sa.String(length=32), server_default="normal", nullable=False))
        batch_op.add_column(sa.Column("planned_time", sa.String(length=64), server_default="", nullable=False))
        batch_op.add_column(sa.Column("handler_user_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_foreign_key("fk_demand_handler_user", "users", ["handler_user_id"], ["id"], ondelete="SET NULL")
        batch_op.create_index("ix_demands_visibility_status", ["visibility", "status"])

    op.create_table(
        "demand_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("demand_id", sa.String(length=36), nullable=False),
        sa.Column("actor_user_id", sa.String(length=36), nullable=True),
        sa.Column("actor_role", sa.String(length=32), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("from_status", sa.String(length=32), nullable=False),
        sa.Column("to_status", sa.String(length=32), nullable=False),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["demand_id"], ["demands.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_demand_events_demand_created", "demand_events", ["demand_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_demand_events_demand_created", table_name="demand_events")
    op.drop_table("demand_events")
    with op.batch_alter_table("demands") as batch_op:
        batch_op.drop_index("ix_demands_visibility_status")
        batch_op.drop_constraint("fk_demand_handler_user", type_="foreignkey")
        batch_op.drop_column("withdrawn_at")
        batch_op.drop_column("handler_user_id")
        batch_op.drop_column("planned_time")
        batch_op.drop_column("priority")
        batch_op.drop_column("visibility")
        batch_op.drop_column("conclusion")
        batch_op.drop_column("status")
    op.drop_index("ix_feedback_messages_feedback_created", table_name="feedback_messages")
    op.drop_table("feedback_messages")
    with op.batch_alter_table("feedback_entries") as batch_op:
        batch_op.drop_index("ix_feedback_entries_status_updated")
        batch_op.drop_constraint("fk_feedback_handler_user", type_="foreignkey")
        batch_op.drop_column("withdrawn_at")
        batch_op.drop_column("resolved_at")
        batch_op.drop_column("updated_at")
        batch_op.drop_column("handler_user_id")
        batch_op.drop_column("resolution")
