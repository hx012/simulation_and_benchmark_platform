import re
import shutil
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile

from sqlalchemy.orm import Session

from app.simulation.enums import UploadSessionStatus
from app.simulation.exceptions import (
    InvalidUploadSessionStateError,
    UploadSessionNotFoundError,
)
from app.simulation.upload_repository import UploadSessionRepository
from app.simulation.simulator.profiles import SimulatorProfile


class SimulationSampleService:
    def __init__(
        self,
        upload_repository: UploadSessionRepository,
    ) -> None:
        self.upload_repository = upload_repository
    @staticmethod
    def _template_roots(profile: SimulatorProfile) -> tuple[Path, Path]:
        chip_root = profile.chip_config_template_path.resolve()
        workload_root = profile.workload_template_path.resolve()
        missing = [str(path) for path in (chip_root, workload_root) if not path.is_dir()]
        if missing:
            raise ValueError("Simulation template directory is not installed: " + ", ".join(missing))
        return chip_root, workload_root

    def build_workload_template_archive(
        self,
        *,
        profile: SimulatorProfile,
    ) -> tuple[str, bytes]:
        workload_root = profile.workload_template_path.resolve()
        if not workload_root.is_dir():
            raise ValueError(
                "Simulation workload template directory is not installed: "
                + str(workload_root)
            )

        buffer = BytesIO()
        with ZipFile(buffer, mode="w", compression=ZIP_DEFLATED) as archive:
            archive.writestr("workload/", b"")
            for path in sorted(workload_root.rglob("*")):
                if not path.is_file() or path.is_symlink():
                    continue
                resolved_path = path.resolve()
                if not resolved_path.is_relative_to(workload_root):
                    continue
                relative_path = resolved_path.relative_to(workload_root)
                archive.writestr(
                    (Path("workload") / relative_path).as_posix(),
                    resolved_path.read_bytes(),
                )

        safe_parts = [
            re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-") or "default"
            for value in (
                profile.simulator_version,
                profile.chip_variant_key,
                profile.simulation_mode.value.lower(),
            )
        ]
        filename = "mskpp_workload_template_" + "_".join(safe_parts) + ".zip"
        return filename, buffer.getvalue()

    def apply_sample(
        self,
        db: Session,
        *,
        upload_session_id: str,
        profile: SimulatorProfile,
    ) -> tuple[int, int]:
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
                "Sample cannot be applied from status "
                f"{upload_session.status.value}"
            )

        chip_source, workload_source = self._template_roots(profile)

        temp_root = Path(upload_session.temp_path).resolve()
        temp_root.mkdir(parents=True, exist_ok=True)
        staging_root = temp_root / f".sample-copy-{uuid4().hex}"

        try:
            staging_root.mkdir(parents=True, exist_ok=False)
            shutil.copytree(chip_source, staging_root / "chip_config")
            shutil.copytree(workload_source, staging_root / "workload")

            chip_count = sum(
                1
                for path in (staging_root / "chip_config").rglob("*")
                if path.is_file()
            )
            workload_count = sum(
                1
                for path in (staging_root / "workload").rglob("*")
                if path.is_file()
            )

            shutil.rmtree(temp_root / "chip_config", ignore_errors=True)
            shutil.rmtree(temp_root / "workload", ignore_errors=True)
            (staging_root / "chip_config").replace(temp_root / "chip_config")
            (staging_root / "workload").replace(temp_root / "workload")
        finally:
            shutil.rmtree(staging_root, ignore_errors=True)

        upload_session.status = UploadSessionStatus.UPLOADING
        upload_session.last_activity_at = datetime.now(timezone.utc)
        self.upload_repository.save(db, upload_session)
        return chip_count, workload_count

    def apply_chip_config(
        self,
        db: Session,
        *,
        upload_session_id: str,
        profile: SimulatorProfile,
    ) -> int:
        upload_session = self.upload_repository.get_for_update(db, upload_session_id)
        if upload_session is None:
            raise UploadSessionNotFoundError(f"Upload session not found: {upload_session_id}")
        if upload_session.status not in {
            UploadSessionStatus.UPLOADING,
            UploadSessionStatus.INVALID,
            UploadSessionStatus.READY,
        }:
            raise InvalidUploadSessionStateError(
                f"Chip Config cannot be prepared from status {upload_session.status.value}"
            )

        chip_source, _ = self._template_roots(profile)
        temp_root = Path(upload_session.temp_path).resolve()
        temp_root.mkdir(parents=True, exist_ok=True)
        staging_root = temp_root / f".chip-config-copy-{uuid4().hex}"
        try:
            shutil.copytree(chip_source, staging_root)
            count = sum(1 for path in staging_root.rglob("*") if path.is_file())
            shutil.rmtree(temp_root / "chip_config", ignore_errors=True)
            staging_root.replace(temp_root / "chip_config")
        finally:
            shutil.rmtree(staging_root, ignore_errors=True)

        upload_session.status = UploadSessionStatus.UPLOADING
        upload_session.last_activity_at = datetime.now(timezone.utc)
        self.upload_repository.save(db, upload_session)
        return count
