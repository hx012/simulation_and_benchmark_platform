import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.common.config import Settings
from app.simulation.enums import UploadSessionStatus
from app.simulation.exceptions import (
    InvalidUploadSessionStateError,
    UploadSessionNotFoundError,
)
from app.simulation.models import UploadSession
from app.simulation.repository import SimulationRepository
from app.simulation.upload_repository import UploadSessionRepository


@dataclass(frozen=True)
class ExpiredUploadSession:
    upload_session_id: str
    temp_path: Path
    orphan_task_id: str | None


class UploadSessionService:
    def __init__(
        self,
        settings: Settings,
        repository: UploadSessionRepository,
        simulation_repository: SimulationRepository | None = None,
    ) -> None:
        self.settings = settings
        self.repository = repository
        self.simulation_repository = (
            simulation_repository or SimulationRepository()
        )

    def create_session(
        self,
        db: Session,
        owner_id: str,
    ) -> UploadSession:
        upload_session_id = f"UP-{uuid4().hex}"

        upload_root = (
            Path(self.settings.task_root)
            / ".uploads"
        ).resolve()

        temp_path = upload_root / upload_session_id
        temp_path.mkdir(parents=True, exist_ok=False)

        upload_session = UploadSession(
            upload_session_id=upload_session_id,
            owner_id=owner_id,
            status=UploadSessionStatus.UPLOADING,
            temp_path=str(temp_path),
        )

        try:
            return self.repository.create(db, upload_session)
        except Exception:
            shutil.rmtree(temp_path, ignore_errors=True)
            raise

    def get_session(
        self,
        db: Session,
        upload_session_id: str,
    ) -> UploadSession:
        upload_session = self.repository.get(db, upload_session_id)

        if upload_session is None:
            raise UploadSessionNotFoundError(
                f"Upload session not found: {upload_session_id}"
            )

        return upload_session

    def upload_files(
        self,
        db: Session,
        upload_session_id: str,
        package_type: str,
        files: list[UploadFile],
        relative_paths: list[str],
    ) -> int:
        """Replace one complete package atomically-ish inside the upload session.

        A new chip-config/workload upload is treated as the complete current package,
        so stale files from a previous sample or upload cannot survive accidentally.
        """
        upload_session = self.repository.get_for_update(
            db,
            upload_session_id,
        )

        if upload_session is None:
            raise UploadSessionNotFoundError(
                f"Upload session not found: {upload_session_id}"
            )

        if upload_session.status not in {
            UploadSessionStatus.UPLOADING,
            UploadSessionStatus.INVALID,
            UploadSessionStatus.READY,
        }:
            raise InvalidUploadSessionStateError(
                "Upload session cannot accept files from status "
                f"{upload_session.status.value}"
            )

        if package_type not in {"chip_config", "workload"}:
            raise ValueError(
                f"Unsupported package type: {package_type}"
            )

        if not files:
            raise ValueError("No files provided")

        if len(files) != len(relative_paths):
            raise ValueError(
                "files and relative_paths must have the same length"
            )

        temp_root = Path(upload_session.temp_path).resolve()
        temp_root.mkdir(parents=True, exist_ok=True)

        package_root = (temp_root / package_type).resolve()
        staging_root = (
            temp_root
            / f".{package_type}.uploading-{uuid4().hex}"
        ).resolve()
        staging_root.mkdir(parents=True, exist_ok=False)

        uploaded_count = 0
        try:
            for upload_file, relative_path in zip(
                files,
                relative_paths,
            ):
                safe_relative_path = self._validate_relative_path(
                    relative_path
                )
                target_path = (
                    staging_root / safe_relative_path
                ).resolve()

                try:
                    target_path.relative_to(staging_root)
                except ValueError as exc:
                    raise ValueError(
                        f"Invalid relative path: {relative_path}"
                    ) from exc

                target_path.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                with target_path.open("wb") as output:
                    while True:
                        chunk = upload_file.file.read(1024 * 1024)
                        if not chunk:
                            break
                        output.write(chunk)

                uploaded_count += 1

            shutil.rmtree(package_root, ignore_errors=True)
            staging_root.replace(package_root)
        except Exception:
            shutil.rmtree(staging_root, ignore_errors=True)
            raise
        finally:
            for upload_file in files:
                try:
                    upload_file.file.close()
                except Exception:
                    pass

        upload_session.status = UploadSessionStatus.UPLOADING
        upload_session.last_activity_at = datetime.now(timezone.utc)
        self.repository.save(db, upload_session)
        return uploaded_count

    def begin_validation(
        self,
        db: Session,
        upload_session_id: str,
    ) -> UploadSession:
        upload_session = self.repository.get_for_update(
            db,
            upload_session_id,
        )

        if upload_session is None:
            raise UploadSessionNotFoundError(
                f"Upload session not found: {upload_session_id}"
            )

        if upload_session.status not in {
            UploadSessionStatus.UPLOADING,
            UploadSessionStatus.INVALID,
            UploadSessionStatus.READY,
        }:
            raise InvalidUploadSessionStateError(
                "Upload session cannot be validated from status "
                f"{upload_session.status.value}"
            )

        upload_session.status = UploadSessionStatus.VALIDATING
        upload_session.last_activity_at = datetime.now(timezone.utc)
        self.repository.save(db, upload_session)
        return upload_session

    def finish_validation(
        self,
        db: Session,
        upload_session_id: str,
        *,
        valid: bool,
    ) -> UploadSession:
        upload_session = self.repository.get_for_update(
            db,
            upload_session_id,
        )

        if upload_session is None:
            raise UploadSessionNotFoundError(
                f"Upload session not found: {upload_session_id}"
            )

        if upload_session.status != UploadSessionStatus.VALIDATING:
            raise InvalidUploadSessionStateError(
                "Upload session is not VALIDATING"
            )

        upload_session.status = (
            UploadSessionStatus.READY
            if valid
            else UploadSessionStatus.INVALID
        )
        upload_session.last_activity_at = datetime.now(timezone.utc)
        self.repository.save(db, upload_session)
        return upload_session

    def expire_stale_sessions(
        self,
        db: Session,
        *,
        now: datetime | None = None,
    ) -> list[ExpiredUploadSession]:
        now = now or datetime.now(timezone.utc)
        cutoff = now - timedelta(
            hours=self.settings.upload_session_ttl_hours
        )

        stale_sessions = self.repository.list_stale_sessions(
            db,
            cutoff=cutoff,
            limit=self.settings.upload_cleanup_batch_size,
        )

        expired: list[ExpiredUploadSession] = []

        for upload_session in stale_sessions:
            reserved_task_id = upload_session.submitted_task_id

            if reserved_task_id is not None:
                task = self.simulation_repository.get_task(
                    db,
                    reserved_task_id,
                )

                if task is not None:
                    upload_session.status = UploadSessionStatus.SUBMITTED
                    upload_session.last_activity_at = now
                    self.repository.save(db, upload_session)
                    continue

            upload_session.status = UploadSessionStatus.EXPIRED
            upload_session.last_activity_at = now
            self.repository.save(db, upload_session)

            expired.append(
                ExpiredUploadSession(
                    upload_session_id=upload_session.upload_session_id,
                    temp_path=Path(upload_session.temp_path).resolve(),
                    orphan_task_id=reserved_task_id,
                )
            )

        return expired

    @staticmethod
    def remove_expired_files(
        expired_sessions: list[ExpiredUploadSession],
    ) -> None:
        for expired in expired_sessions:
            shutil.rmtree(expired.temp_path, ignore_errors=True)

    def _validate_relative_path(
        self,
        relative_path: str,
    ) -> Path:
        normalized = relative_path.replace("\\", "/").strip()

        if not normalized:
            raise ValueError("Relative path cannot be empty")

        path = PurePosixPath(normalized)

        if path.is_absolute():
            raise ValueError(
                f"Absolute path is not allowed: {relative_path}"
            )

        if ".." in path.parts:
            raise ValueError(
                f"Parent traversal is not allowed: {relative_path}"
            )

        if path.parts and ":" in path.parts[0]:
            raise ValueError(
                f"Drive-qualified path is not allowed: {relative_path}"
            )

        cleaned_parts = [
            part
            for part in path.parts
            if part not in {"", "."}
        ]

        if not cleaned_parts:
            raise ValueError("Relative path cannot be empty")

        return Path(*cleaned_parts)
