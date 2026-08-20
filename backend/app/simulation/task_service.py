from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.simulation.enums import ExecutionPhase, TaskStatus, TraceStatus
from app.simulation.exceptions import (
    InvalidTaskStateError,
    TaskNotFoundError,
)
from app.simulation.models import SimulationTask
from app.simulation.repository import SimulationRepository


TERMINAL_STATUSES = {
    TaskStatus.COMPLETED,
    TaskStatus.FAILED,
    TaskStatus.CANCELLED,
    TaskStatus.TERMINATED,
}


class SimulationTaskService:
    def __init__(
        self,
        repository: SimulationRepository | None = None,
    ) -> None:
        self.repository = repository or SimulationRepository()

    def get_task(
        self,
        db: Session,
        task_id: str,
    ) -> SimulationTask:
        task = self.repository.get_task(db, task_id)

        if task is None:
            raise TaskNotFoundError(
                f"Simulation task not found: {task_id}"
            )

        return task

    def get_queue_ahead(
        self,
        db: Session,
        task_id: str,
    ) -> int:
        task = self.get_task(db, task_id)

        if task.status != TaskStatus.QUEUED:
            return 0

        if task.worker_id is not None:
            return 0

        if task.cancel_requested:
            return 0

        return self.repository.count_queued_tasks_ahead(
            db,
            task,
        )

    def request_cancel(
        self,
        db: Session,
        task_id: str,
    ) -> SimulationTask:
        task = self.repository.get_task_for_update(
            db,
            task_id,
        )

        if task is None:
            raise TaskNotFoundError(
                f"Simulation task not found: {task_id}"
            )

        if task.status != TaskStatus.QUEUED:
            raise InvalidTaskStateError(
                f"Task {task_id} cannot be cancelled "
                f"from status {task.status.value}"
            )

        now = datetime.now(timezone.utc)

        if task.worker_id is None:
            task.status = TaskStatus.CANCELLED
            task.execution_phase = ExecutionPhase.FINISHED
            task.end_time = now
        else:
            # Worker 已 claim，但还未真正启动 SST。
            # 由 Worker 在 prepare_start() 中完成 CANCELLED 落库。
            task.cancel_requested = True

        self.repository.save(db, task)
        return task

    def request_terminate(
        self,
        db: Session,
        task_id: str,
    ) -> SimulationTask:
        task = self.repository.get_task_for_update(
            db,
            task_id,
        )

        if task is None:
            raise TaskNotFoundError(
                f"Simulation task not found: {task_id}"
            )

        if task.status != TaskStatus.RUNNING:
            raise InvalidTaskStateError(
                f"Task {task_id} cannot be terminated "
                f"from status {task.status.value}"
            )

        task.terminate_requested = True
        self.repository.save(db, task)
        return task

    def archive_task(
        self,
        db: Session,
        task_id: str,
    ) -> SimulationTask:
        task = self.repository.get_task_for_update(
            db,
            task_id,
        )

        if task is None:
            raise TaskNotFoundError(
                f"Simulation task not found: {task_id}"
            )

        if task.status not in TERMINAL_STATUSES:
            raise InvalidTaskStateError(
                f"Task {task_id} cannot be archived "
                f"from status {task.status.value}"
            )

        if not task.archived:
            task.archived = True
            task.archived_at = datetime.now(timezone.utc)

        self.repository.save(db, task)
        return task

    def unarchive_task(
        self,
        db: Session,
        task_id: str,
    ) -> SimulationTask:
        task = self.repository.get_task_for_update(
            db,
            task_id,
        )

        if task is None:
            raise TaskNotFoundError(
                f"Simulation task not found: {task_id}"
            )

        task.archived = False
        task.archived_at = None

        self.repository.save(db, task)
        return task

    def prepare_start(
        self,
        db: Session,
        task_id: str,
        worker_id: str,
    ) -> bool:
        """
        Worker 在真正启动 SST 前调用。

        True  -> 可以继续启动。
        False -> 已收到取消请求，任务已转 CANCELLED。
        """
        task = self.repository.get_task_for_update(
            db,
            task_id,
        )

        if task is None:
            raise TaskNotFoundError(
                f"Simulation task not found: {task_id}"
            )

        if task.worker_id != worker_id:
            raise InvalidTaskStateError(
                f"Task {task_id} is not owned by worker {worker_id}"
            )

        if task.status != TaskStatus.QUEUED:
            raise InvalidTaskStateError(
                f"Task {task_id} cannot start "
                f"from status {task.status.value}"
            )

        if task.cancel_requested:
            task.status = TaskStatus.CANCELLED
            task.execution_phase = ExecutionPhase.FINISHED
            task.end_time = datetime.now(timezone.utc)

            self.repository.save(db, task)
            return False

        task.execution_phase = ExecutionPhase.STARTING
        self.repository.save(db, task)
        return True

    def mark_running(
        self,
        db: Session,
        task_id: str,
        worker_id: str,
        pid: int,
        pgid: int,
    ) -> SimulationTask:
        task = self.repository.get_task_for_update(
            db,
            task_id,
        )

        if task is None:
            raise TaskNotFoundError(
                f"Simulation task not found: {task_id}"
            )

        if task.worker_id != worker_id:
            raise InvalidTaskStateError(
                f"Task {task_id} is not owned by worker {worker_id}"
            )

        if (
            task.status != TaskStatus.QUEUED
            or task.execution_phase != ExecutionPhase.STARTING
        ):
            raise InvalidTaskStateError(
                f"Task {task_id} cannot enter RUNNING "
                f"from status={task.status.value}, "
                f"phase={task.execution_phase.value}"
            )

        task.status = TaskStatus.RUNNING
        task.execution_phase = ExecutionPhase.EXECUTING
        task.pid = pid
        task.pgid = pgid
        task.start_time = datetime.now(timezone.utc)

        self.repository.save(db, task)
        return task

    def mark_collecting(
        self,
        db: Session,
        task_id: str,
        exit_code: int,
    ) -> SimulationTask:
        task = self.repository.get_task_for_update(
            db,
            task_id,
        )

        if task is None:
            raise TaskNotFoundError(
                f"Simulation task not found: {task_id}"
            )

        if task.status != TaskStatus.RUNNING:
            raise InvalidTaskStateError(
                f"Task {task_id} cannot collect results "
                f"from status {task.status.value}"
            )

        task.exit_code = exit_code
        task.execution_phase = ExecutionPhase.COLLECTING

        self.repository.save(db, task)
        return task

    def mark_completed(
        self,
        db: Session,
        task_id: str,
        total_cycle: int | None = None,
        simulated_time_seconds: float | None = None,
        runtime_seconds: float | None = None,
    ) -> SimulationTask:
        task = self.repository.get_task_for_update(
            db,
            task_id,
        )

        if task is None:
            raise TaskNotFoundError(
                f"Simulation task not found: {task_id}"
            )

        if (
            task.status != TaskStatus.RUNNING
            or task.execution_phase != ExecutionPhase.COLLECTING
        ):
            raise InvalidTaskStateError(
                f"Task {task_id} cannot complete "
                f"from status={task.status.value}, "
                f"phase={task.execution_phase.value}"
            )

        task.status = TaskStatus.COMPLETED
        task.execution_phase = ExecutionPhase.FINISHED
        task.total_cycle = total_cycle
        task.simulated_time_seconds = simulated_time_seconds
        task.runtime_seconds = runtime_seconds
        task.end_time = datetime.now(timezone.utc)

        self.repository.save(db, task)
        return task

    def mark_failed(
        self,
        db: Session,
        task_id: str,
        error_code: str,
        error_message: str,
        exit_code: int | None = None,
    ) -> SimulationTask:
        task = self.repository.get_task_for_update(
            db,
            task_id,
        )

        if task is None:
            raise TaskNotFoundError(
                f"Simulation task not found: {task_id}"
            )

        if task.status in TERMINAL_STATUSES:
            raise InvalidTaskStateError(
                f"Task {task_id} is already terminal: "
                f"{task.status.value}"
            )

        task.status = TaskStatus.FAILED
        task.execution_phase = ExecutionPhase.FINISHED
        task.error_code = error_code
        task.error_message = error_message
        task.exit_code = exit_code
        task.end_time = datetime.now(timezone.utc)

        self.repository.save(db, task)
        return task

    def mark_terminated(
        self,
        db: Session,
        task_id: str,
        exit_code: int | None = None,
    ) -> SimulationTask:
        task = self.repository.get_task_for_update(
            db,
            task_id,
        )

        if task is None:
            raise TaskNotFoundError(
                f"Simulation task not found: {task_id}"
            )

        if task.status != TaskStatus.RUNNING:
            raise InvalidTaskStateError(
                f"Task {task_id} cannot be terminated "
                f"from status {task.status.value}"
            )

        task.status = TaskStatus.TERMINATED
        task.execution_phase = ExecutionPhase.FINISHED
        task.exit_code = exit_code
        task.end_time = datetime.now(timezone.utc)

        self.repository.save(db, task)
        return task

    def mark_trace_generating(
        self,
        db: Session,
        task_id: str,
    ) -> SimulationTask:
        task = self.get_task(db, task_id)
        task.trace_status = TraceStatus.GENERATING
        self.repository.save(db, task)
        return task

    def mark_trace_ready(
        self,
        db: Session,
        task_id: str,
    ) -> SimulationTask:
        task = self.get_task(db, task_id)
        task.trace_status = TraceStatus.READY
        self.repository.save(db, task)
        return task

    def mark_trace_failed(
        self,
        db: Session,
        task_id: str,
    ) -> SimulationTask:
        task = self.get_task(db, task_id)
        task.trace_status = TraceStatus.FAILED
        self.repository.save(db, task)
        return task

    def reset_claim_after_worker_restart(
        self,
        db: Session,
        task_id: str,
        worker_id: str,
    ) -> SimulationTask:
        """
        V1 单 Worker 恢复逻辑：
        Worker 重启后，将旧进程 claim 但尚未 RUNNING 的任务重新放回 FIFO。
        """
        task = self.repository.get_task_for_update(
            db,
            task_id,
        )

        if task is None:
            raise TaskNotFoundError(
                f"Simulation task not found: {task_id}"
            )

        if task.worker_id != worker_id:
            raise InvalidTaskStateError(
                f"Task {task_id} is not owned by worker {worker_id}"
            )

        if task.status != TaskStatus.QUEUED:
            raise InvalidTaskStateError(
                f"Task {task_id} cannot reset claim "
                f"from status {task.status.value}"
            )

        task.worker_id = None
        task.claimed_at = None
        task.pid = None
        task.pgid = None

        if task.cancel_requested:
            task.status = TaskStatus.CANCELLED
            task.execution_phase = ExecutionPhase.FINISHED
            task.end_time = datetime.now(timezone.utc)
        else:
            task.execution_phase = ExecutionPhase.WAITING

        self.repository.save(db, task)
        return task
