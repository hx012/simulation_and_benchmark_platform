"""Add feedback and demand pool tables.

Revision ID: 20260823_0004
Revises: 20260822_0003
Create Date: 2026-08-23
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260823_0004"
down_revision: Union[str, Sequence[str], None] = "20260822_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "feedback_entries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("feedback_type", sa.String(length=32), nullable=False),
        sa.Column("page_title", sa.String(length=255), nullable=False),
        sa.Column("page_path", sa.String(length=512), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_feedback_entries_created", "feedback_entries", ["created_at"])
    op.create_table(
        "demands",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("request_no", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("domain", sa.String(length=64), nullable=False),
        sa.Column("expected_time", sa.String(length=64), nullable=False),
        sa.Column("background", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("business_value", sa.Text(), nullable=False),
        sa.Column("contact", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_no"),
    )
    op.create_index("ix_demands_user_created", "demands", ["user_id", "created_at"])
    op.create_index("ix_demands_domain_created", "demands", ["domain", "created_at"])
    op.create_table(
        "demand_votes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("demand_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["demand_id"], ["demands.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("demand_id", "user_id", name="uq_demand_vote"),
    )
    op.create_index("ix_demand_votes_demand", "demand_votes", ["demand_id"])


def downgrade() -> None:
    op.drop_index("ix_demand_votes_demand", table_name="demand_votes")
    op.drop_table("demand_votes")
    op.drop_index("ix_demands_domain_created", table_name="demands")
    op.drop_index("ix_demands_user_created", table_name="demands")
    op.drop_table("demands")
    op.drop_index("ix_feedback_entries_created", table_name="feedback_entries")
    op.drop_table("feedback_entries")
