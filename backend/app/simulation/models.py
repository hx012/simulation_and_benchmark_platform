from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum as SqlEnum,
    Float,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.common.database import Base
from app.simulation.enums import (
    ExecutionPhase,
    SimulationMode,
    TaskStatus,
    TraceStatus,
    UploadSessionStatus,
)


def enum_column(enum_type: type):
    return SqlEnum(
        enum_type,
        native_enum=False,
        validate_strings=True,
    )


class SimulationTask(Base):
    __tablename__ = "simulation_tasks"

    # queue_seq 同时作为数据库内部主键和 FIFO 顺序号。
    # 用户/API 不使用它标识任务，而使用 task_id。
    queue_seq: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    # 对外任务 ID，例如 SIM-20260815-XXXXXX。
    task_id: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
    )

    task_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    owner_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    # Simulator selection
    simulator_version: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    chip_variant: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
    )

    simulation_mode: Mapped[SimulationMode] = mapped_column(
        enum_column(SimulationMode),
        nullable=False,
    )

    rerun_from_task_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
    )

    # Task state
    status: Mapped[TaskStatus] = mapped_column(
        enum_column(TaskStatus),
        nullable=False,
        default=TaskStatus.QUEUED,
    )

    execution_phase: Mapped[ExecutionPhase] = mapped_column(
        enum_column(ExecutionPhase),
        nullable=False,
        default=ExecutionPhase.WAITING,
    )

    # Worker claim
    worker_id: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
    )

    claimed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Simulator process
    pid: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )

    pgid: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )

    exit_code: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )

    # Runtime progress
    current_cycle: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
    )

    log_read_offset: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
    )

    # Control flags
    cancel_requested: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    terminate_requested: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    # Task workspace root
    workspace_path: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Result
    total_cycle: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
    )

    runtime_seconds: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    simulated_time_seconds: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    trace_status: Mapped[TraceStatus] = mapped_column(
        enum_column(TraceStatus),
        nullable=False,
        default=TraceStatus.NOT_REQUESTED,
    )

    # Failure information
    error_code: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
    )

    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Time
    submit_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    start_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    end_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Archive is independent from task status.
    archived: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    archived_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        Index(
            "ix_simulation_tasks_status_queue_seq",
            "status",
            "queue_seq",
        ),
        Index(
            "ix_simulation_tasks_owner_submit_time",
            "owner_id",
            "submit_time",
        ),
    )


class UploadSession(Base):
    __tablename__ = "upload_sessions"

    upload_session_id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )

    owner_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    status: Mapped[UploadSessionStatus] = mapped_column(
        enum_column(UploadSessionStatus),
        nullable=False,
        default=UploadSessionStatus.UPLOADING,
    )

    temp_path: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    submitted_task_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        unique=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        Index(
            "ix_upload_sessions_owner_status",
            "owner_id",
            "status",
        ),
    )
