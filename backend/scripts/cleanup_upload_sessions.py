import os
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))
os.chdir(BACKEND_ROOT)

from app.common.config import get_settings  # noqa: E402
from app.common.database import SessionLocal  # noqa: E402
from app.simulation.repository import SimulationRepository  # noqa: E402
from app.simulation.upload_repository import UploadSessionRepository  # noqa: E402
from app.simulation.upload_service import UploadSessionService  # noqa: E402
from app.simulation.workspace_manager import TaskWorkspaceManager  # noqa: E402


def main() -> None:
    settings = get_settings()
    simulation_repository = SimulationRepository()
    upload_repository = UploadSessionRepository()
    upload_service = UploadSessionService(
        settings=settings,
        repository=upload_repository,
        simulation_repository=simulation_repository,
    )
    workspace_manager = TaskWorkspaceManager(settings)

    with SessionLocal.begin() as db:
        expired = upload_service.expire_stale_sessions(db)

    upload_service.remove_expired_files(expired)

    # COMMITTING 中断可能已经创建了正式 workspace，
    # 但数据库里尚无 SimulationTask。只清理确认无任务记录的 orphan。
    for item in expired:
        if not item.orphan_task_id:
            continue

        with SessionLocal() as db:
            task = simulation_repository.get_task(
                db,
                item.orphan_task_id,
            )

        if task is None:
            workspace_manager.remove_orphan_workspace(
                item.orphan_task_id
            )

    print(
        f"expired_upload_sessions={len(expired)}"
    )
    for item in expired:
        print(
            f"expired {item.upload_session_id} "
            f"reserved_task_id={item.orphan_task_id}"
        )


if __name__ == "__main__":
    main()
