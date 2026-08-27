from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from app.common.config import Settings
from app.simulation.exceptions import (
    InvalidTaskStateError,
    TaskNotFoundError,
)
from app.simulation.repository import SimulationRepository
from app.simulation.task_service import TERMINAL_STATUSES
from app.simulation.upload_repository import UploadSessionRepository
from app.simulation.workspace_manager import TaskWorkspaceManager


@dataclass(frozen=True)
class TaskQuota:
    owner_id: str
    limit: int
    retained_count: int
    reserved_count: int

    @property
    def used_count(self) -> int:
        return self.retained_count + self.reserved_count

    @property
    def remaining(self) -> int:
        return max(0, self.limit - self.used_count)

    @property
    def can_create(self) -> bool:
        return self.used_count < self.limit


class SimulationTaskManagementService:
    def __init__(
        self,
        *,
        settings: Settings,
        simulation_repository: SimulationRepository,
        upload_repository: UploadSessionRepository,
        workspace_manager: TaskWorkspaceManager,
    ) -> None:
        self.settings = settings
        self.simulation_repository = simulation_repository
        self.upload_repository = upload_repository
        self.workspace_manager = workspace_manager

    def get_quota(
        self,
        db: Session,
        owner_id: str,
    ) -> TaskQuota:
        retained_count = self.simulation_repository.count_tasks(
            db,
            owner_id=owner_id,
        )
        reserved_count = self.upload_repository.count_committing_for_owner(
            db,
            owner_id,
        )
        return TaskQuota(
            owner_id=owner_id,
            limit=self.settings.sim_user_task_limit,
            retained_count=retained_count,
            reserved_count=reserved_count,
        )

    def delete_task(
        self,
        db: Session,
        *,
        owner_id: str,
        task_id: str,
    ) -> list[str]:
        return self.delete_tasks(
            db,
            owner_id=owner_id,
            task_ids=[task_id],
        )

    def delete_tasks(
        self,
        db: Session,
        *,
        owner_id: str,
        task_ids: list[str],
    ) -> list[str]:
        unique_task_ids = list(dict.fromkeys(task_ids))
        if not unique_task_ids:
            return []

        tasks = []
        for task_id in unique_task_ids:
            task = self.simulation_repository.get_task_for_update(
                db,
                task_id,
            )
            # owner_id is derived from the authenticated server session by
            # the API layer; keep this service-level check as defense in depth.
            if task is None or task.owner_id != owner_id:
                raise TaskNotFoundError(
                    f"Simulation task not found: {task_id}"
                )

            if task.status not in TERMINAL_STATUSES:
                raise InvalidTaskStateError(
                    f"Task {task_id} cannot be deleted "
                    f"from status {task.status.value}; "
                    "cancel or terminate it first"
                )
            tasks.append(task)

        staged_workspaces: list[tuple[str, Path | None]] = []
        try:
            # 先把 workspace 原子移动到 TASK_ROOT/.deleting，避免数据库
            # 已删除但正式 runtime 目录仍对平台可见。若 DB 事务失败可恢复。
            for task in tasks:
                staged = self.workspace_manager.stage_task_workspace_for_delete(
                    task_id=task.task_id,
                    workspace_path=task.workspace_path,
                )
                staged_workspaces.append((task.task_id, staged))

            for task in tasks:
                self.simulation_repository.clear_rerun_parent_references(
                    db,
                    task.task_id,
                )
                self.upload_repository.delete_by_submitted_task_id(
                    db,
                    task.task_id,
                )
                self.simulation_repository.delete_task(db, task)

            db.commit()

        except Exception:
            db.rollback()
            for task_id, staged in reversed(staged_workspaces):
                self.workspace_manager.restore_staged_task_workspace(
                    task_id=task_id,
                    staged_path=staged,
                )
            raise

        # DB 已提交后再物理清理 .deleting。此时即使底层文件系统出现
        # 短暂清理失败，也不会再以正式 task workspace 形式暴露。
        for _task_id, staged in staged_workspaces:
            self.workspace_manager.purge_staged_task_workspace(staged)

        return unique_task_ids
