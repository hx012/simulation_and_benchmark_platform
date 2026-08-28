"""Add optional demand delivery feedback.

Revision ID: 20260828_0014
Revises: 20260828_0013
Create Date: 2026-08-28
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260828_0014"
down_revision: Union[str, Sequence[str], None] = "20260828_0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("demands") as batch_op:
        batch_op.add_column(sa.Column("delivery_feedback", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("delivery_feedback_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("demands") as batch_op:
        batch_op.drop_column("delivery_feedback_at")
        batch_op.drop_column("delivery_feedback")
