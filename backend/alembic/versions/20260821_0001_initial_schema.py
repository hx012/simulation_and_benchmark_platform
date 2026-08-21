"""Create simulation task and upload session tables.

Revision ID: 20260821_0001
Revises:
Create Date: 2026-08-21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260821_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "simulation_tasks",
        sa.Column("queue_seq", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("task_name", sa.String(length=255), nullable=False),
        sa.Column("owner_id", sa.String(length=128), nullable=False),
        sa.Column("simulator_version", sa.String(length=64), nullable=False),
        sa.Column("chip_variant", sa.String(length=64), nullable=True),
        sa.Column(
            "simulation_mode",
            sa.Enum("SINGLE_CHIP", "MULTI_CHIP", name="simulationmode", native_enum=False),
            nullable=False,
        ),
        sa.Column("rerun_from_task_id", sa.String(length=64), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "QUEUED",
                "RUNNING",
                "COMPLETED",
                "FAILED",
                "CANCELLED",
                "TERMINATED",
                name="taskstatus",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "execution_phase",
            sa.Enum(
                "WAITING",
                "PREPARING",
                "STARTING",
                "EXECUTING",
                "COLLECTING",
                "FINISHED",
                name="executionphase",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("worker_id", sa.String(length=128), nullable=True),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pid", sa.Integer(), nullable=True),
        sa.Column("pgid", sa.Integer(), nullable=True),
        sa.Column("exit_code", sa.Integer(), nullable=True),
        sa.Column("current_cycle", sa.BigInteger(), nullable=True),
        sa.Column("log_read_offset", sa.BigInteger(), nullable=False),
        sa.Column("cancel_requested", sa.Boolean(), nullable=False),
        sa.Column("terminate_requested", sa.Boolean(), nullable=False),
        sa.Column("workspace_path", sa.Text(), nullable=False),
        sa.Column("total_cycle", sa.BigInteger(), nullable=True),
        sa.Column("runtime_seconds", sa.Float(), nullable=True),
        sa.Column("simulated_time_seconds", sa.Float(), nullable=True),
        sa.Column(
            "trace_status",
            sa.Enum(
                "NOT_REQUESTED",
                "PENDING",
                "GENERATING",
                "READY",
                "FAILED",
                name="tracestatus",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("error_code", sa.String(length=128), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "submit_time",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived", sa.Boolean(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("queue_seq"),
        sa.UniqueConstraint("task_id"),
    )
    op.create_index(
        "ix_simulation_tasks_owner_submit_time",
        "simulation_tasks",
        ["owner_id", "submit_time"],
        unique=False,
    )
    op.create_index(
        "ix_simulation_tasks_status_queue_seq",
        "simulation_tasks",
        ["status", "queue_seq"],
        unique=False,
    )

    op.create_table(
        "upload_sessions",
        sa.Column("upload_session_id", sa.String(length=64), nullable=False),
        sa.Column("owner_id", sa.String(length=128), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "UPLOADING",
                "READY",
                "VALIDATING",
                "INVALID",
                "COMMITTING",
                "SUBMITTED",
                "EXPIRED",
                name="uploadsessionstatus",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("temp_path", sa.Text(), nullable=False),
        sa.Column("submitted_task_id", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_activity_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("upload_session_id"),
        sa.UniqueConstraint("submitted_task_id"),
    )
    op.create_index(
        "ix_upload_sessions_owner_status",
        "upload_sessions",
        ["owner_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_upload_sessions_owner_status", table_name="upload_sessions")
    op.drop_table("upload_sessions")
    op.drop_index("ix_simulation_tasks_status_queue_seq", table_name="simulation_tasks")
    op.drop_index("ix_simulation_tasks_owner_submit_time", table_name="simulation_tasks")
    op.drop_table("simulation_tasks")
