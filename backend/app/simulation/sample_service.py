import re
import shutil
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile

from sqlalchemy.orm import Session

from app.common.config import Settings
from app.simulation.enums import SimulationMode, UploadSessionStatus
from app.simulation.exceptions import (
    InvalidUploadSessionStateError,
    UploadSessionNotFoundError,
)
from app.simulation.upload_repository import UploadSessionRepository


class SimulationSampleService:
    def __init__(
        self,
        settings: Settings,
        upload_repository: UploadSessionRepository,
    ) -> None:
        self.settings = settings
        self.upload_repository = upload_repository
        self.template_root = Path(
            settings.sim_sample_template_root
        ).resolve()

    def _resolve_sample_root(
        self,
        *,
        simulator_version: str,
        chip_variant: str | None,
        simulation_mode: SimulationMode,
    ) -> tuple[Path, str, str]:
        variant_key = (chip_variant or "default").strip() or "default"
        if variant_key.lower() == "default":
            variant_key = "default"
        mode_key = simulation_mode.value.lower()

        # Templates are shared by every simulator version and chip variant.
        # Only the execution topology changes the folder that is loaded:
        #   <root>/default/single_chip/{chip_config,workload}
        #   <root>/default/multi_chip/{chip_config,workload}
        sample_root = (self.template_root / "default" / mode_key).resolve()
        if not (
            (sample_root / "chip_config").is_dir()
            and (sample_root / "workload").is_dir()
        ):
            raise ValueError(
                "Simulation sample is not installed for "
                f"version={simulator_version}, variant={variant_key}, "
                f"mode={simulation_mode.value}. Expected: {sample_root}"
            )

        return sample_root, variant_key, mode_key

    def build_template_archive(
        self,
        *,
        simulator_version: str,
        chip_variant: str | None,
        simulation_mode: SimulationMode,
    ) -> tuple[str, bytes]:
        sample_root, variant_key, mode_key = self._resolve_sample_root(
            simulator_version=simulator_version,
            chip_variant=chip_variant,
            simulation_mode=simulation_mode,
        )

        buffer = BytesIO()
        with ZipFile(buffer, mode="w", compression=ZIP_DEFLATED) as archive:
            for package_name in ("chip_config", "workload"):
                package_root = (sample_root / package_name).resolve()
                archive.writestr(f"{package_name}/", b"")
                for path in sorted(package_root.rglob("*")):
                    if not path.is_file() or path.is_symlink():
                        continue
                    resolved_path = path.resolve()
                    if not resolved_path.is_relative_to(package_root):
                        continue
                    relative_path = resolved_path.relative_to(package_root)
                    archive.writestr(
                        (Path(package_name) / relative_path).as_posix(),
                        resolved_path.read_bytes(),
                    )

        safe_parts = [
            re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-") or "default"
            for value in (simulator_version, variant_key, mode_key)
        ]
        filename = "mskpp_config_template_" + "_".join(safe_parts) + ".zip"
        return filename, buffer.getvalue()

    def apply_sample(
        self,
        db: Session,
        *,
        upload_session_id: str,
        simulator_version: str,
        chip_variant: str | None,
        simulation_mode: SimulationMode,
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

        sample_root, _, _ = self._resolve_sample_root(
            simulator_version=simulator_version,
            chip_variant=chip_variant,
            simulation_mode=simulation_mode,
        )

        chip_source = sample_root / "chip_config"
        workload_source = sample_root / "workload"

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
