"""Recent activity projection limit, deduplication, and rendering checks."""

from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import sys

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app.analytics.models import AnalyticsEvent
from app.analytics.schemas import AnalyticsEventCreate
from app.analytics.service import create_event
from app.auth.models import User, UserSession
from app.auth.service import AuthenticatedUser
from app.common.config import get_settings
from app.common.database import Base
from app.recent_activity.models import RecentActivity
from app.recent_activity.service import list_recent_activities
from app.simulation.enums import SimulationMode
from app.simulation.models import SimulationTask


def main() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        user = User(employee_id="recent-user", display_name="Recent User", role="normal")
        db.add(user)
        db.commit()
        session = UserSession(
            user_id=user.id,
            token_hash="recent-activity-session-token-hash",
            auth_mode="normal",
            last_seen_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        current = AuthenticatedUser(user=user, session=session)

        for index in range(6):
            task = SimulationTask(
                queue_seq=index + 1,
                task_id=f"SIM-RECENT-{index}",
                task_name=f"Recent task {index}",
                owner_id=user.employee_id,
                simulator_version="v310",
                simulation_mode=SimulationMode.SINGLE_CHIP,
                workspace_path=f"/tmp/recent-{index}",
            )
            db.add(task)
            db.commit()
            create_event(db, user, AnalyticsEventCreate(
                event_id=f"recent-event-{index:04d}",
                session_id="recent-session-0001",
                event_name="simulation.task_create_success",
                page_key="simulation.create",
                result="success",
                target_type="simulation_task",
                target_id=task.task_id,
                target_name=task.task_name,
            ))

        stored = db.scalar(select(func.count()).select_from(RecentActivity)) or 0
        raw_events = db.scalar(select(func.count()).select_from(AnalyticsEvent)) or 0
        assert stored == 5
        assert raw_events == 6

        response = list_recent_activities(db, current, get_settings())
        assert len(response.items) == 3
        assert response.items[0].title == "Recent task 5"
        assert response.items[0].href == "/simulation/tasks/SIM-RECENT-5"

        create_event(db, user, AnalyticsEventCreate(
            event_id="recent-event-deduplicate",
            session_id="recent-session-0001",
            event_name="simulation.task_create_success",
            page_key="simulation.create",
            result="success",
            target_type="simulation_task",
            target_id="SIM-RECENT-5",
            target_name="Recent task 5",
        ))
        assert (db.scalar(select(func.count()).select_from(RecentActivity)) or 0) == 5

    print("Recent activity tests passed")


if __name__ == "__main__":
    main()
