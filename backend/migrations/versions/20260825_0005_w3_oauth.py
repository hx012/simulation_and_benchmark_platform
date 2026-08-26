"""Add W3 identity bindings and one-time OAuth2 login transactions.

Revision ID: 20260825_0005
Revises: 20260823_0004
Create Date: 2026-08-25
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260825_0005"
down_revision: Union[str, Sequence[str], None] = "20260823_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("w3_global_user_id", sa.String(length=255), nullable=True))
    op.create_index("ix_users_w3_global_user_id", "users", ["w3_global_user_id"], unique=True)
    op.create_table(
        "oauth_login_transactions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("state_hash", sa.String(length=64), nullable=False),
        sa.Column("code_verifier", sa.String(length=128), nullable=False),
        sa.Column("next_path", sa.String(length=2048), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("state_hash"),
    )
    op.create_index("ix_oauth_login_transactions_expires", "oauth_login_transactions", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_oauth_login_transactions_expires", table_name="oauth_login_transactions")
    op.drop_table("oauth_login_transactions")
    op.drop_index("ix_users_w3_global_user_id", table_name="users")
    op.drop_column("users", "w3_global_user_id")
