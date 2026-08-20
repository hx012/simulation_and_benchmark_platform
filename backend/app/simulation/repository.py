from datetime import datetime, timezone

from sqlalchemy import func, select, text, update
from sqlalchemy.orm import Session

from app.simulation.enums import ExecutionPhase, TaskStatus
from app.simulation.models import SimulationTask


class SimulationRepository:
    def create_task(
        self,
        db: Session,
        task: SimulationTask,
    ) -> SimulationTask:
        db.add(task)
        db.flush()
        db.refresh(task)
        return task

    def get_task(
        self,
        db: Session,
        task_id: str,
    ) -> SimulationTask | None:
        stmt = (
            select(SimulationTask)
            .where(SimulationTask.task_id == task_id)
        )
        return db.scalar(stmt)

    def get_task_for_update(
        self,
        db: Session,
        task_id: str,
    ) -> SimulationTask | None:
        stmt = (
            select(SimulationTask)
            .where(SimulationTask.task_id == task_id)
            .with_for_update()
        )
        return db.scalar(stmt)

    def list_tasks(
        self,
        db: Session,
        *,
        owner_id: str | None = None,
        status: TaskStatus | None = None,
        archived: bool | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[SimulationTask]:
        stmt = select(SimulationTask)

        if owner_id is not None:
            stmt = stmt.where(
                SimulationTask.owner_id == owner_id
            )

        if status is not None:
            stmt = stmt.where(
                SimulationTask.status == status
            )

        if archived is not None:
            stmt = stmt.where(
                SimulationTask.archived.is_(archived)
            )

        stmt = (
            stmt
            .order_by(SimulationTask.queue_seq.desc())
            .offset(offset)
            .limit(limit)
        )

        return list(db.scalars(stmt).all())

    def count_tasks(
        self,
        db: Session,
        *,
        owner_id: str | None = None,
        status: TaskStatus | None = None,
        archived: bool | None = None,
    ) -> int:
        stmt = select(
            func.count(SimulationTask.queue_seq)
        )

        if owner_id is not None:
            stmt = stmt.where(
                SimulationTask.owner_id == owner_id
            )

        if status is not None:
            stmt = stmt.where(
                SimulationTask.status == status
            )

        if archived is not None:
            stmt = stmt.where(
                SimulationTask.archived.is_(archived)
            )

        return int(db.scalar(stmt) or 0)

    def count_queued_tasks_ahead(
        self,
        db: Session,
        task: SimulationTask,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(SimulationTask)
            .where(
                SimulationTask.status == TaskStatus.QUEUED,
                SimulationTask.worker_id.is_(None),
                SimulationTask.cancel_requested.is_(False),
                SimulationTask.queue_seq < task.queue_seq,
            )
        )

        return int(db.scalar(stmt) or 0)

    def claim_next_queued_task(
        self,
        db: Session,
        worker_id: str,
    ) -> SimulationTask | None:
        stmt = (
            select(SimulationTask)
            .where(
                SimulationTask.status == TaskStatus.QUEUED,
                SimulationTask.worker_id.is_(None),
                SimulationTask.cancel_requested.is_(False),
            )
            .order_by(SimulationTask.queue_seq.asc())
            .limit(1)
            .with_for_update(skip_locked=True)
        )

        task = db.scalar(stmt)

        if task is None:
            return None

        task.worker_id = worker_id
        task.claimed_at = datetime.now(timezone.utc)
        task.execution_phase = ExecutionPhase.PREPARING

        db.flush()
        return task

    def list_worker_owned_incomplete_tasks(
        self,
        db: Session,
        worker_id: str,
    ) -> list[SimulationTask]:
        stmt = (
            select(SimulationTask)
            .where(
                SimulationTask.worker_id == worker_id,
                SimulationTask.status.in_(
                    [
                        TaskStatus.QUEUED,
                        TaskStatus.RUNNING,
                    ]
                ),
            )
            .order_by(SimulationTask.queue_seq.asc())
        )

        return list(db.scalars(stmt).all())

    def list_task_names_for_owner(
        self,
        db: Session,
        owner_id: str,
    ) -> list[str]:
        stmt = (
            select(SimulationTask.task_name)
            .where(SimulationTask.owner_id == owner_id)
        )
        return list(db.scalars(stmt).all())


    def acquire_owner_quota_lock(
        self,
        db: Session,
        owner_id: str,
    ) -> None:
        bind = db.get_bind()
        if bind.dialect.name != "postgresql":
            return

        db.execute(
            text(
                "SELECT pg_advisory_xact_lock("
                "hashtext(:lock_key))"
            ),
            {"lock_key": f"simulation-task-quota:{owner_id}"},
        )

    def clear_rerun_parent_references(
        self,
        db: Session,
        task_id: str,
    ) -> None:
        db.execute(
            update(SimulationTask)
            .where(SimulationTask.rerun_from_task_id == task_id)
            .values(rerun_from_task_id=None)
        )
        db.flush()

    def delete_task(
        self,
        db: Session,
        task: SimulationTask,
    ) -> None:
        db.delete(task)
        db.flush()

    def save(
        self,
        db: Session,
        task: SimulationTask,
    ) -> SimulationTask:
        db.add(task)
        db.flush()
        return task

    def update_progress(
        self,
        db: Session,
        task_id: str,
        current_cycle: int | None,
        log_read_offset: int,
        runtime_seconds: float | None = None,
    ) -> None:
        task = self.get_task(
            db,
            task_id,
        )

        if task is None:
            return

        if current_cycle is not None:
            task.current_cycle = current_cycle

        if runtime_seconds is not None:
            task.runtime_seconds = runtime_seconds

        task.log_read_offset = log_read_offset
        db.flush()
