import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

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

        variant_key = (chip_variant or "default").strip() or "default"
        if variant_key.lower() == "default":
            variant_key = "default"
        mode_key = simulation_mode.value.lower()

        # New multi-profile layout:
        #   <root>/<version>/<variant>/<mode>/chip_config
        #   <root>/<version>/<variant>/<mode>/workload
        # Keep the legacy <root>/<version>/sample layout as a fallback so
        # existing V310 sample installations continue to work unchanged.
        candidate_roots = [
            (
                self.template_root
                / simulator_version
                / variant_key
                / mode_key
            ).resolve(),
        ]
        if (
            variant_key == "default"
            and simulation_mode == SimulationMode.SINGLE_CHIP
        ):
            candidate_roots.append(
                (
                    self.template_root
                    / simulator_version
                    / "sample"
                ).resolve()
            )

        sample_root = next(
            (
                path
                for path in candidate_roots
                if (path / "chip_config").is_dir()
                and (path / "workload").is_dir()
            ),
            None,
        )
        if sample_root is None:
            expected = " or ".join(str(path) for path in candidate_roots)
            raise ValueError(
                "Simulation sample is not installed for "
                f"version={simulator_version}, variant={variant_key}, "
                f"mode={simulation_mode.value}. Expected: {expected}"
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
