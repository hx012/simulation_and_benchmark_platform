"""Add team membership and achievement archives.

Revision ID: 20260827_0010
Revises: 20260826_0009
Create Date: 2026-08-27
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260827_0010"
down_revision: Union[str, Sequence[str], None] = "20260826_0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("is_team_member", sa.Boolean(), server_default=sa.false(), nullable=False))

    op.create_table(
        "team_achievement_records",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner_user_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("completion_date", sa.Date(), nullable=False),
        sa.Column("reference_url", sa.String(length=2048), nullable=False),
        sa.Column("representative", sa.Boolean(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_team_achievement_owner_completion", "team_achievement_records", ["owner_user_id", "completion_date"])
    op.create_index("ix_team_achievement_representative", "team_achievement_records", ["representative"])


def downgrade() -> None:
    op.drop_index("ix_team_achievement_representative", table_name="team_achievement_records")
    op.drop_index("ix_team_achievement_owner_completion", table_name="team_achievement_records")
    op.drop_table("team_achievement_records")
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("is_team_member")
