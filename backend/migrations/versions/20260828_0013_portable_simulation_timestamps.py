"""Use portable timestamp defaults for simulation tables.

Revision ID: 20260828_0013
Revises: 20260828_0012
Create Date: 2026-08-28
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260828_0013"
down_revision: Union[str, Sequence[str], None] = "20260828_0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _set_timestamp_defaults(default: sa.TextClause) -> None:
    with op.batch_alter_table("simulation_tasks") as batch_op:
        batch_op.alter_column(
            "submit_time",
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=False,
            server_default=default,
        )

    with op.batch_alter_table("upload_sessions") as batch_op:
        for column_name in ("created_at", "last_activity_at"):
            batch_op.alter_column(
                column_name,
                existing_type=sa.DateTime(timezone=True),
                existing_nullable=False,
                server_default=default,
            )


def upgrade() -> None:
    _set_timestamp_defaults(sa.text("CURRENT_TIMESTAMP"))


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        _set_timestamp_defaults(sa.text("now()"))
    else:
        _set_timestamp_defaults(sa.text("CURRENT_TIMESTAMP"))
