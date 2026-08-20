from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from sqlalchemy.orm import Session

from app.common.config import Settings
from app.simulation.enums import UploadSessionStatus
from app.simulation.exceptions import (
    InvalidUploadSessionStateError,
    UploadSessionNotFoundError,
)
from app.simulation.upload_repository import UploadSessionRepository


EDITABLE_SUFFIXES = {".yml", ".yaml", ".json"}


@dataclass(frozen=True)
class UploadFileInfo:
    path: str
    name: str
    size_bytes: int
    editable: bool


class UploadSessionFileService:
    def __init__(
        self,
        settings: Settings,
        upload_repository: UploadSessionRepository,
    ) -> None:
        self.settings = settings
        self.upload_repository = upload_repository

    def list_files(
        self,
        db: Session,
        *,
        upload_session_id: str,
        package_type: str,
    ) -> list[UploadFileInfo]:
        upload_session = self._get_session(db, upload_session_id)
        package_root = self._package_root(upload_session.temp_path, package_type)
        if not package_root.is_dir():
            return []

        result: list[UploadFileInfo] = []
        for path in sorted(
            (p for p in package_root.rglob("*") if p.is_file()),
            key=lambda p: p.as_posix(),
        ):
            relative = path.relative_to(package_root).as_posix()
            result.append(
                UploadFileInfo(
                    path=relative,
                    name=path.name,
                    size_bytes=path.stat().st_size,
                    editable=path.suffix.lower() in EDITABLE_SUFFIXES,
                )
            )
        return result

    def read_content(
        self,
        db: Session,
        *,
        upload_session_id: str,
        package_type: str,
        relative_path: str,
    ) -> tuple[UploadFileInfo, str | None]:
        upload_session = self._get_session(db, upload_session_id)
        file_path, package_root = self._resolve_file(
            upload_session.temp_path,
            package_type,
            relative_path,
        )
        if not file_path.is_file():
            raise ValueError(f"Upload file not found: {relative_path}")

        info = UploadFileInfo(
            path=file_path.relative_to(package_root).as_posix(),
            name=file_path.name,
            size_bytes=file_path.stat().st_size,
            editable=file_path.suffix.lower() in EDITABLE_SUFFIXES,
        )

        if not info.editable:
            return info, None
        if info.size_bytes > self.settings.sim_online_edit_max_bytes:
            raise ValueError(
                "Config file is too large for online editing: "
                f"{info.size_bytes} bytes"
            )

        return info, file_path.read_text(
            encoding="utf-8",
            errors="replace",
        )

    def write_content(
        self,
        db: Session,
        *,
        upload_session_id: str,
        package_type: str,
        relative_path: str,
        content: str,
    ) -> UploadFileInfo:
        upload_session = self.upload_repository.get_for_update(
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
                "Upload files cannot be edited from status "
                f"{upload_session.status.value}"
            )

        file_path, package_root = self._resolve_file(
            upload_session.temp_path,
            package_type,
            relative_path,
        )
        if not file_path.is_file():
            raise ValueError(f"Upload file not found: {relative_path}")
        if file_path.suffix.lower() not in EDITABLE_SUFFIXES:
            raise ValueError(
                f"File does not support online editing: {relative_path}"
            )

        encoded = content.encode("utf-8")
        if len(encoded) > self.settings.sim_online_edit_max_bytes:
            raise ValueError(
                "Edited config exceeds online edit size limit"
            )

        temp_path = file_path.with_name(file_path.name + ".editing")
        temp_path.write_bytes(encoded)
        temp_path.replace(file_path)

        upload_session.status = UploadSessionStatus.UPLOADING
        upload_session.last_activity_at = datetime.now(timezone.utc)
        self.upload_repository.save(db, upload_session)

        return UploadFileInfo(
            path=file_path.relative_to(package_root).as_posix(),
            name=file_path.name,
            size_bytes=file_path.stat().st_size,
            editable=True,
        )

    def _get_session(self, db: Session, upload_session_id: str):
        upload_session = self.upload_repository.get(db, upload_session_id)
        if upload_session is None:
            raise UploadSessionNotFoundError(
                f"Upload session not found: {upload_session_id}"
            )
        return upload_session

    @staticmethod
    def _package_root(temp_path: str, package_type: str) -> Path:
        if package_type not in {"chip_config", "workload"}:
            raise ValueError(f"Unsupported package type: {package_type}")
        return (Path(temp_path).resolve() / package_type).resolve()

    def _resolve_file(
        self,
        temp_path: str,
        package_type: str,
        relative_path: str,
    ) -> tuple[Path, Path]:
        package_root = self._package_root(temp_path, package_type)
        normalized = relative_path.replace("\\", "/").strip()
        path = PurePosixPath(normalized)
        if (
            not normalized
            or path.is_absolute()
            or ".." in path.parts
            or (path.parts and ":" in path.parts[0])
        ):
            raise ValueError(f"Invalid relative path: {relative_path}")

        file_path = (package_root / Path(*path.parts)).resolve()
        try:
            file_path.relative_to(package_root)
        except ValueError as exc:
            raise ValueError(
                f"File path escapes package: {relative_path}"
            ) from exc
        return file_path, package_root
