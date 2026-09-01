"""Isolated smoke test for Simulation task quota and deletion.

This script does not touch the platform PostgreSQL database or TASK_ROOT.
"""

import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.common.config import Settings
from app.common.database import Base
from app.simulation.enums import SimulationMode, TaskStatus, UploadSessionStatus
from app.simulation.models import SimulationTask, UploadSession
from app.simulation.repository import SimulationRepository
from app.simulation.task_management_service import SimulationTaskManagementService
from app.simulation.upload_repository import UploadSessionRepository
from app.simulation.workspace_manager import TaskWorkspaceManager


def main() -> None:
    with TemporaryDirectory() as temp_dir:
        task_root = Path(temp_dir) / "runtime"
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)

        settings = Settings(
            task_root=task_root,
            sim_user_task_limit=30,
            database_url="sqlite:///:memory:",
        )
        repository = SimulationRepository()
        upload_repository = UploadSessionRepository()
        workspace_manager = TaskWorkspaceManager(settings)
        service = SimulationTaskManagementService(
            settings=settings,
            simulation_repository=repository,
            upload_repository=upload_repository,
            workspace_manager=workspace_manager,
        )

        task_id = "SIM-TASK-MGMT-SMOKE"
        workspace = task_root / task_id
        (workspace / "logs").mkdir(parents=True)
        (workspace / "logs" / "davinci_sim.log").write_text(
            "smoke test\n",
            encoding="utf-8",
        )

        with Session(engine) as db:
            db.add(
                SimulationTask(
                    queue_seq=1,
                    task_id=task_id,
                    task_name="Task Management Smoke",
                    owner_id="smoke-user",
                    simulator_version="mock",
                    chip_variant=None,
                    simulation_mode=SimulationMode.SINGLE_CHIP,
                    status=TaskStatus.COMPLETED,
                    workspace_path=str(workspace),
                )
            )
            db.add(
                UploadSession(
                    upload_session_id="UP-TASK-MGMT-SMOKE",
                    owner_id="smoke-user",
                    status=UploadSessionStatus.SUBMITTED,
                    temp_path=str(task_root / ".uploads" / "UP-TASK-MGMT-SMOKE"),
                    submitted_task_id=task_id,
                )
            )
            db.commit()

            quota = service.get_quota(db, "smoke-user")
            assert quota.retained_count == 1
            assert quota.limit == 30
            assert quota.can_create

            deleted = service.delete_task(
                db,
                owner_id="smoke-user",
                task_id=task_id,
            )
            assert deleted == [task_id]
            assert repository.get_task(db, task_id) is None
            assert upload_repository.get(db, "UP-TASK-MGMT-SMOKE") is None
            assert not workspace.exists()

            quota = service.get_quota(db, "smoke-user")
            assert quota.retained_count == 0

            legacy_task_id = "SIM-TASK-MGMT-LEGACY"
            canonical_workspace = task_root / legacy_task_id
            canonical_workspace.mkdir(parents=True)
            external_workspace = Path(temp_dir) / "legacy-external" / legacy_task_id
            external_workspace.mkdir(parents=True)
            external_marker = external_workspace / "must-not-delete.txt"
            external_marker.write_text("preserve", encoding="utf-8")
            db.add(
                SimulationTask(
                    queue_seq=2,
                    task_id=legacy_task_id,
                    task_name="Legacy Workspace Task",
                    owner_id="smoke-user",
                    simulator_version="mock",
                    chip_variant=None,
                    simulation_mode=SimulationMode.SINGLE_CHIP,
                    status=TaskStatus.COMPLETED,
                    workspace_path=str(external_workspace),
                )
            )
            db.commit()

            assert service.delete_task(
                db,
                owner_id="smoke-user",
                task_id=legacy_task_id,
            ) == [legacy_task_id]
            assert repository.get_task(db, legacy_task_id) is None
            assert not canonical_workspace.exists()
            assert external_marker.read_text(encoding="utf-8") == "preserve"

    print("Simulation task management smoke test: PASS")


if __name__ == "__main__":
    main()
