"""Reconcile W3 auth schema for databases stamped at revision 0005.

Revision ID: 20260826_0008
Revises: 20260826_0007
Create Date: 2026-08-26

Some development databases were stamped at revision 0005 without all of that
revision's DDL being present. Keep this repair migration idempotent so it is
safe for both those databases and databases created normally from scratch.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260826_0008"
down_revision: Union[str, Sequence[str], None] = "20260826_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "w3_global_user_id" not in user_columns:
        op.add_column(
            "users",
            sa.Column("w3_global_user_id", sa.String(length=255), nullable=True),
        )

    inspector = sa.inspect(bind)
    user_indexes = {index["name"] for index in inspector.get_indexes("users")}
    if "ix_users_w3_global_user_id" not in user_indexes:
        op.create_index(
            "ix_users_w3_global_user_id",
            "users",
            ["w3_global_user_id"],
            unique=True,
        )

    table_names = set(inspector.get_table_names())
    if "oauth_login_transactions" not in table_names:
        op.create_table(
            "oauth_login_transactions",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("state_hash", sa.String(length=64), nullable=False),
            sa.Column("code_verifier", sa.String(length=128), nullable=False),
            sa.Column("next_path", sa.String(length=2048), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("state_hash"),
        )
        op.create_index(
            "ix_oauth_login_transactions_expires",
            "oauth_login_transactions",
            ["expires_at"],
        )
    else:
        oauth_indexes = {
            index["name"]
            for index in sa.inspect(bind).get_indexes("oauth_login_transactions")
        }
        if "ix_oauth_login_transactions_expires" not in oauth_indexes:
            op.create_index(
                "ix_oauth_login_transactions_expires",
                "oauth_login_transactions",
                ["expires_at"],
            )


def downgrade() -> None:
    # This migration only reconciles objects that revision 0005 already owns.
    # Removing them here could destroy schema that predated this repair.
    pass
