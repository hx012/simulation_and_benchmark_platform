"""Add achievement evaluations and audit context.

Revision ID: 20260828_0011
Revises: 20260827_0010
Create Date: 2026-08-28
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260828_0011"
down_revision: Union[str, Sequence[str], None] = "20260827_0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("team_achievement_records") as batch_op:
        batch_op.add_column(sa.Column("evaluation", sa.Text(), server_default="", nullable=False))
        batch_op.add_column(sa.Column("scored_by_user_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("scored_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_foreign_key(
            "fk_team_achievement_scored_by_user",
            "users",
            ["scored_by_user_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_team_achievement_scored_by", ["scored_by_user_id"])

    with op.batch_alter_table("analytics_events") as batch_op:
        batch_op.add_column(sa.Column("target_user_id", sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column("auth_mode", sa.String(length=32), server_default="", nullable=False))
        batch_op.add_column(sa.Column("change_summary", sa.Text(), server_default="", nullable=False))


def downgrade() -> None:
    with op.batch_alter_table("analytics_events") as batch_op:
        batch_op.drop_column("change_summary")
        batch_op.drop_column("auth_mode")
        batch_op.drop_column("target_user_id")

    with op.batch_alter_table("team_achievement_records") as batch_op:
        batch_op.drop_index("ix_team_achievement_scored_by")
        batch_op.drop_constraint("fk_team_achievement_scored_by_user", type_="foreignkey")
        batch_op.drop_column("scored_at")
        batch_op.drop_column("scored_by_user_id")
        batch_op.drop_column("evaluation")
