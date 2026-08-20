import json
import os
import re
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from app.common.config import Settings
from app.simulation.enums import SimulationMode, UploadSessionStatus
from app.simulation.exceptions import (
    InvalidTaskStateError,
    InvalidUploadSessionStateError,
    TaskNotFoundError,
    TaskQuotaExceededError,
    TaskSubmissionError,
    UploadSessionNotFoundError,
)
from app.simulation.models import SimulationTask
from app.simulation.repository import SimulationRepository
from app.simulation.simulator.profiles import (
    SimulatorProfileNotFoundError,
    SimulatorProfileRegistry,
)
from app.simulation.task_service import TERMINAL_STATUSES
from app.simulation.upload_repository import UploadSessionRepository
from app.simulation.workspace_manager import TaskWorkspaceManager


class SimulationSubmissionService:
    def __init__(
        self,
        *,
        settings: Settings,
        simulation_repository: SimulationRepository,
        upload_repository: UploadSessionRepository,
        workspace_manager: TaskWorkspaceManager,
        profile_registry: SimulatorProfileRegistry,
    ) -> None:
        self.settings = settings
        self.simulation_repository = simulation_repository
        self.upload_repository = upload_repository
        self.workspace_manager = workspace_manager
        self.profile_registry = profile_registry

    def submit_upload(
        self,
        db: Session,
        *,
        upload_session_id: str,
        task_name: str,
        simulator_version: str,
        chip_variant: str | None,
        simulation_mode: SimulationMode,
    ) -> SimulationTask:
        upload_session = self.upload_repository.get_for_update(
            db,
            upload_session_id,
        )

        if upload_session is None:
            raise UploadSessionNotFoundError(
                f"Upload session not found: {upload_session_id}"
            )

        # 成功提交后的重复请求直接返回原任务，保证幂等。
        if upload_session.status == UploadSessionStatus.SUBMITTED:
            return self._get_submitted_task(
                db,
                upload_session.submitted_task_id,
            )

        self._validate_profile(
            simulator_version=simulator_version,
            chip_variant=chip_variant,
            simulation_mode=simulation_mode,
        )

        if upload_session.status not in {
            UploadSessionStatus.READY,
            UploadSessionStatus.COMMITTING,
        }:
            raise InvalidUploadSessionStateError(
                "Upload session cannot be submitted from status "
                f"{upload_session.status.value}"
            )

        lock_path = self._acquire_submission_lock(
            upload_session.temp_path
        )

        try:
            if upload_session.status == UploadSessionStatus.READY:
                self._ensure_owner_task_capacity(
                    db,
                    upload_session.owner_id,
                )
                task_id = self._generate_task_id()

                self._write_submission_manifest(
                    temp_path=upload_session.temp_path,
                    task_id=task_id,
                    task_name=task_name,
                    simulator_version=simulator_version,
                    chip_variant=chip_variant,
                    simulation_mode=simulation_mode,
                )

                upload_session.status = UploadSessionStatus.COMMITTING
                upload_session.submitted_task_id = task_id
                upload_session.last_activity_at = datetime.now(timezone.utc)
                self.upload_repository.save(db, upload_session)

                # 先持久化 reserved task_id，崩溃后可恢复同一个提交。
                db.commit()

            else:
                task_id = upload_session.submitted_task_id
                if not task_id:
                    raise TaskSubmissionError(
                        "COMMITTING upload session has no reserved task_id"
                    )

                manifest = self._read_submission_manifest(
                    upload_session.temp_path
                )
                self._validate_retry_request(
                    manifest=manifest,
                    task_name=task_name,
                    simulator_version=simulator_version,
                    chip_variant=chip_variant,
                    simulation_mode=simulation_mode,
                )

            existing_task = self.simulation_repository.get_task(
                db,
                task_id,
            )

            if existing_task is not None:
                self._repair_submitted_session(
                    db,
                    upload_session_id=upload_session_id,
                    task_id=task_id,
                )
                self._cleanup_upload_temp(
                    upload_session.temp_path
                )
                return existing_task

            manifest = self._read_submission_manifest(
                upload_session.temp_path
            )

            workspace = self.workspace_manager.create_from_upload(
                task_id=task_id,
                upload_temp_path=upload_session.temp_path,
                replace_existing_orphan=True,
            )

            task = SimulationTask(
                task_id=task_id,
                task_name=manifest["task_name"],
                owner_id=upload_session.owner_id,
                simulator_version=manifest["simulator_version"],
                chip_variant=manifest.get("chip_variant"),
                simulation_mode=SimulationMode(
                    manifest["simulation_mode"]
                ),
                workspace_path=str(workspace),
            )

            try:
                upload_session = self.upload_repository.get_for_update(
                    db,
                    upload_session_id,
                )

                if upload_session is None:
                    raise UploadSessionNotFoundError(
                        f"Upload session not found: {upload_session_id}"
                    )

                if (
                    upload_session.status != UploadSessionStatus.COMMITTING
                    or upload_session.submitted_task_id != task_id
                ):
                    raise InvalidUploadSessionStateError(
                        "Upload session changed while committing"
                    )

                self.simulation_repository.create_task(
                    db,
                    task,
                )

                upload_session.status = UploadSessionStatus.SUBMITTED
                upload_session.last_activity_at = datetime.now(timezone.utc)
                self.upload_repository.save(db, upload_session)
                db.commit()

            except Exception:
                db.rollback()

                persisted = self.simulation_repository.get_task(
                    db,
                    task_id,
                )

                if persisted is None:
                    self.workspace_manager.remove_task_workspace(
                        task_id
                    )
                raise

            self._cleanup_upload_temp(upload_session.temp_path)
            return task

        finally:
            self._release_submission_lock(lock_path)

    def rerun_task(
        self,
        db: Session,
        *,
        source_task_id: str,
        task_name: str | None = None,
    ) -> SimulationTask:
        source = self.simulation_repository.get_task(
            db,
            source_task_id,
        )

        if source is None:
            raise TaskNotFoundError(
                f"Simulation task not found: {source_task_id}"
            )

        if source.status not in TERMINAL_STATUSES:
            raise InvalidTaskStateError(
                f"Task {source_task_id} cannot be rerun "
                f"from status {source.status.value}"
            )

        self._validate_profile(
            simulator_version=source.simulator_version,
            chip_variant=source.chip_variant,
            simulation_mode=source.simulation_mode,
        )

        self._ensure_owner_task_capacity(
            db,
            source.owner_id,
        )

        new_task_id = self._generate_task_id()
        new_task_name = (
            task_name[:255]
            if task_name is not None
            else self._next_rerun_task_name(
                db,
                source,
            )
        )

        workspace = self.workspace_manager.clone_from_task(
            task_id=new_task_id,
            source_workspace_path=source.workspace_path,
        )

        new_task = SimulationTask(
            task_id=new_task_id,
            task_name=new_task_name,
            owner_id=source.owner_id,
            simulator_version=source.simulator_version,
            chip_variant=source.chip_variant,
            simulation_mode=source.simulation_mode,
            rerun_from_task_id=source.task_id,
            workspace_path=str(workspace),
        )

        try:
            self.simulation_repository.create_task(
                db,
                new_task,
            )
            db.commit()
        except Exception:
            db.rollback()
            self.workspace_manager.remove_task_workspace(
                new_task_id
            )
            raise

        return new_task

    def _next_rerun_task_name(
        self,
        db: Session,
        source: SimulationTask,
    ) -> str:
        """Generate stable rerun names: <root_name>_1, _2, _3, ...

        The root task name is recovered through rerun_from_task_id so rerunning
        either the root task or any descendant continues the same sequence.
        """
        root = source
        visited: set[str] = set()

        while root.rerun_from_task_id:
            if root.task_id in visited:
                break
            visited.add(root.task_id)

            parent = self.simulation_repository.get_task(
                db,
                root.rerun_from_task_id,
            )
            if parent is None:
                break
            root = parent

        base_name = root.task_name
        existing_names = self.simulation_repository.list_task_names_for_owner(
            db,
            source.owner_id,
        )

        pattern = re.compile(
            rf"^{re.escape(base_name)}_(\d+)$"
        )
        max_index = 0
        for existing_name in existing_names:
            match = pattern.fullmatch(existing_name)
            if match is not None:
                max_index = max(
                    max_index,
                    int(match.group(1)),
                )

        next_index = max_index + 1
        suffix = f"_{next_index}"
        trimmed_base = base_name[: max(0, 255 - len(suffix))]
        return f"{trimmed_base}{suffix}"

    def _get_submitted_task(
        self,
        db: Session,
        task_id: str | None,
    ) -> SimulationTask:
        if not task_id:
            raise TaskSubmissionError(
                "SUBMITTED upload session has no submitted_task_id"
            )

        task = self.simulation_repository.get_task(
            db,
            task_id,
        )
        if task is None:
            raise TaskSubmissionError(
                f"Submitted task not found: {task_id}"
            )
        return task

    def _ensure_owner_task_capacity(
        self,
        db: Session,
        owner_id: str,
    ) -> None:
        # PostgreSQL 下使用 owner 级 advisory transaction lock，
        # 防止同一用户并发提交时越过 30 个任务的硬上限。
        self.simulation_repository.acquire_owner_quota_lock(
            db,
            owner_id,
        )

        retained_count = self.simulation_repository.count_tasks(
            db,
            owner_id=owner_id,
        )
        reserved_count = self.upload_repository.count_committing_for_owner(
            db,
            owner_id,
        )
        used_count = retained_count + reserved_count
        limit = self.settings.sim_user_task_limit

        if used_count >= limit:
            raise TaskQuotaExceededError(
                "Simulation task retention limit reached: "
                f"{used_count}/{limit}. "
                "Delete tasks you no longer need before creating a new one."
            )

    def _validate_profile(
        self,
        *,
        simulator_version: str,
        chip_variant: str | None,
        simulation_mode: SimulationMode,
    ) -> None:
        if simulator_version == "mock":
            return

        try:
            self.profile_registry.get_profile(
                simulator_version=simulator_version,
                chip_variant=chip_variant,
                simulation_mode=simulation_mode,
            )
        except SimulatorProfileNotFoundError as exc:
            raise TaskSubmissionError(str(exc)) from exc

    @staticmethod
    def _generate_task_id() -> str:
        now = datetime.now(timezone.utc).strftime(
            "%Y%m%d-%H%M%S"
        )
        suffix = uuid4().hex[:8].upper()
        return f"SIM-{now}-{suffix}"

    @staticmethod
    def _write_submission_manifest(
        *,
        temp_path: str,
        task_id: str,
        task_name: str,
        simulator_version: str,
        chip_variant: str | None,
        simulation_mode: SimulationMode,
    ) -> None:
        root = Path(temp_path).resolve()
        root.mkdir(parents=True, exist_ok=True)

        manifest_path = root / ".submission.json"
        temp_manifest_path = root / ".submission.json.tmp"

        payload = {
            "task_id": task_id,
            "task_name": task_name,
            "simulator_version": simulator_version,
            "chip_variant": chip_variant,
            "simulation_mode": simulation_mode.value,
        }

        with temp_manifest_path.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                payload,
                file,
                ensure_ascii=False,
                indent=2,
            )

        temp_manifest_path.replace(manifest_path)

    @staticmethod
    def _read_submission_manifest(
        temp_path: str,
    ) -> dict:
        manifest_path = (
            Path(temp_path).resolve()
            / ".submission.json"
        )

        if not manifest_path.is_file():
            raise TaskSubmissionError(
                f"Submission manifest not found: {manifest_path}"
            )

        try:
            with manifest_path.open(
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(file)
        except Exception as exc:
            raise TaskSubmissionError(
                f"Invalid submission manifest: {exc}"
            ) from exc

        required = {
            "task_id",
            "task_name",
            "simulator_version",
            "simulation_mode",
        }
        missing = required - set(data)
        if missing:
            raise TaskSubmissionError(
                "Submission manifest missing fields: "
                + ", ".join(sorted(missing))
            )

        return data

    @staticmethod
    def _validate_retry_request(
        *,
        manifest: dict,
        task_name: str,
        simulator_version: str,
        chip_variant: str | None,
        simulation_mode: SimulationMode,
    ) -> None:
        expected = {
            "task_name": task_name,
            "simulator_version": simulator_version,
            "chip_variant": chip_variant,
            "simulation_mode": simulation_mode.value,
        }

        actual = {
            "task_name": manifest.get("task_name"),
            "simulator_version": manifest.get("simulator_version"),
            "chip_variant": manifest.get("chip_variant"),
            "simulation_mode": manifest.get("simulation_mode"),
        }

        if actual != expected:
            raise TaskSubmissionError(
                "Upload session is already COMMITTING with "
                "different submission parameters"
            )

    def _repair_submitted_session(
        self,
        db: Session,
        *,
        upload_session_id: str,
        task_id: str,
    ) -> None:
        upload_session = self.upload_repository.get_for_update(
            db,
            upload_session_id,
        )

        if upload_session is None:
            raise UploadSessionNotFoundError(
                f"Upload session not found: {upload_session_id}"
            )

        upload_session.status = UploadSessionStatus.SUBMITTED
        upload_session.submitted_task_id = task_id
        upload_session.last_activity_at = datetime.now(timezone.utc)
        self.upload_repository.save(db, upload_session)
        db.commit()

    def _acquire_submission_lock(
        self,
        temp_path: str,
    ) -> Path:
        root = Path(temp_path).resolve()
        root.mkdir(parents=True, exist_ok=True)
        lock_path = root / ".submit.lock"

        for _ in range(2):
            try:
                fd = os.open(
                    lock_path,
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                    0o600,
                )
                try:
                    payload = (
                        f"pid={os.getpid()} "
                        f"time={time.time()}\n"
                    )
                    os.write(fd, payload.encode("utf-8"))
                finally:
                    os.close(fd)
                return lock_path

            except FileExistsError:
                try:
                    age_seconds = (
                        time.time()
                        - lock_path.stat().st_mtime
                    )
                except FileNotFoundError:
                    continue

                if (
                    age_seconds
                    > self.settings.upload_submit_lock_stale_seconds
                ):
                    lock_path.unlink(missing_ok=True)
                    continue

                raise InvalidUploadSessionStateError(
                    "Upload session submission is already in progress"
                )

        raise InvalidUploadSessionStateError(
            "Unable to acquire upload submission lock"
        )

    @staticmethod
    def _release_submission_lock(
        lock_path: Path,
    ) -> None:
        lock_path.unlink(missing_ok=True)

    @staticmethod
    def _cleanup_upload_temp(temp_path: str) -> None:
        shutil.rmtree(
            Path(temp_path).resolve(),
            ignore_errors=True,
        )
