import logging
import os
import shutil
from pathlib import Path
from uuid import uuid4

from app.common.config import Settings
from app.simulation.exceptions import TaskWorkspaceError


logger = logging.getLogger(__name__)


class TaskWorkspaceManager:
    def __init__(self, settings: Settings) -> None:
        self.task_root = Path(settings.task_root).resolve()

    def create_from_upload(
        self,
        *,
        task_id: str,
        upload_temp_path: str,
        replace_existing_orphan: bool = False,
    ) -> Path:
        upload_root = Path(upload_temp_path).resolve()

        chip_config = upload_root / "chip_config"
        workload = upload_root / "workload"

        if not chip_config.is_dir():
            raise TaskWorkspaceError(
                f"chip_config directory does not exist: {chip_config}"
            )

        if not workload.is_dir():
            raise TaskWorkspaceError(
                f"workload directory does not exist: {workload}"
            )

        staging, final_workspace = self._prepare_staging(
            task_id=task_id,
            replace_existing_orphan=replace_existing_orphan,
        )

        try:
            input_root = staging / "input"
            input_root.mkdir(parents=True, exist_ok=True)

            shutil.copytree(
                chip_config,
                input_root / "chip_config",
            )
            shutil.copytree(
                workload,
                input_root / "workload",
            )

            self._create_runtime_directories(staging)
            os.replace(staging, final_workspace)
            return final_workspace

        except Exception:
            shutil.rmtree(staging, ignore_errors=True)
            raise

    def clone_from_task(
        self,
        *,
        task_id: str,
        source_workspace_path: str,
    ) -> Path:
        source_workspace = Path(
            source_workspace_path
        ).resolve()
        source_input = source_workspace / "input"

        if not source_input.is_dir():
            raise TaskWorkspaceError(
                f"Source task input directory does not exist: "
                f"{source_input}"
            )

        staging, final_workspace = self._prepare_staging(
            task_id=task_id,
            replace_existing_orphan=False,
        )

        try:
            shutil.copytree(
                source_input,
                staging / "input",
            )

            self._create_runtime_directories(staging)
            os.replace(staging, final_workspace)
            return final_workspace

        except Exception:
            shutil.rmtree(staging, ignore_errors=True)
            raise


    def stage_task_workspace_for_delete(
        self,
        *,
        task_id: str,
        workspace_path: str,
    ) -> Path | None:
        self._validate_task_id(task_id)
        expected_workspace = self._task_workspace(task_id)
        workspace = Path(workspace_path).resolve()

        if workspace != expected_workspace:
            # Legacy/sample rows may contain an obsolete absolute workspace
            # path (for example /tmp/SIM-TEST-003). Never delete that
            # database-supplied path. Continue with the canonical location
            # derived from the configured TASK_ROOT and validated task ID so
            # the stale database record can still be removed safely.
            logger.warning(
                "Ignoring mismatched task workspace during deletion: "
                "task_id=%s stored=%s expected=%s",
                task_id,
                workspace,
                expected_workspace,
            )
            workspace = expected_workspace

        # 清理可能残留的 staging。
        shutil.rmtree(
            self._staging_workspace(task_id),
            ignore_errors=True,
        )

        if not workspace.exists():
            return None

        deleting_root = self.task_root / ".deleting"
        deleting_root.mkdir(parents=True, exist_ok=True)
        staged_path = (
            deleting_root
            / f"{task_id}-{uuid4().hex}"
        ).resolve()

        os.replace(workspace, staged_path)
        return staged_path

    def restore_staged_task_workspace(
        self,
        *,
        task_id: str,
        staged_path: Path | None,
    ) -> None:
        if staged_path is None or not staged_path.exists():
            return

        target = self._task_workspace(task_id)
        if target.exists():
            return
        os.replace(staged_path, target)

    def purge_staged_task_workspace(
        self,
        staged_path: Path | None,
    ) -> None:
        if staged_path is None:
            return

        staged = staged_path.resolve()
        deleting_root = (self.task_root / ".deleting").resolve()
        try:
            staged.relative_to(deleting_root)
        except ValueError as exc:
            raise TaskWorkspaceError(
                f"Delete staging path is outside TASK_ROOT/.deleting: {staged}"
            ) from exc

        # 已经从正式 workspace 原子移出；这里做最终物理清理。
        shutil.rmtree(staged, ignore_errors=True)

    def remove_task_workspace(
        self,
        task_id: str,
    ) -> None:
        workspace = self._task_workspace(task_id)
        shutil.rmtree(workspace, ignore_errors=True)

        staging = self._staging_workspace(task_id)
        shutil.rmtree(staging, ignore_errors=True)

    def remove_orphan_workspace(
        self,
        task_id: str | None,
    ) -> None:
        if not task_id:
            return
        self.remove_task_workspace(task_id)

    def _prepare_staging(
        self,
        *,
        task_id: str,
        replace_existing_orphan: bool,
    ) -> tuple[Path, Path]:
        self._validate_task_id(task_id)

        self.task_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        creating_root = (
            self.task_root / ".creating"
        )
        creating_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        staging = self._staging_workspace(task_id)
        final_workspace = self._task_workspace(task_id)

        shutil.rmtree(staging, ignore_errors=True)

        if final_workspace.exists():
            if not replace_existing_orphan:
                raise TaskWorkspaceError(
                    f"Task workspace already exists: "
                    f"{final_workspace}"
                )
            shutil.rmtree(
                final_workspace,
                ignore_errors=False,
            )

        staging.mkdir(
            parents=True,
            exist_ok=False,
        )

        return staging, final_workspace

    @staticmethod
    def _create_runtime_directories(
        workspace: Path,
    ) -> None:
        directories = [
            workspace / "runtime",
            workspace / "logs",
            workspace / "result",
            workspace / "result" / "trace" / "dumps",
        ]

        for directory in directories:
            directory.mkdir(
                parents=True,
                exist_ok=True,
            )

    def _task_workspace(self, task_id: str) -> Path:
        self._validate_task_id(task_id)
        return (self.task_root / task_id).resolve()

    def _staging_workspace(self, task_id: str) -> Path:
        self._validate_task_id(task_id)
        return (
            self.task_root
            / ".creating"
            / task_id
        ).resolve()

    @staticmethod
    def _validate_task_id(task_id: str) -> None:
        if (
            not task_id
            or "/" in task_id
            or "\\" in task_id
            or task_id in {".", ".."}
        ):
            raise TaskWorkspaceError(
                f"Invalid task_id for workspace: {task_id}"
            )
