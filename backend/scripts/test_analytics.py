"""Usage analytics aggregation and dimension checks."""

import os
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import Session


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app.analytics.models import AnalyticsEvent
from app.analytics.schemas import AnalyticsEventCreate
from app.analytics.service import create_event, get_overview, get_user_detail, list_users
from app.auth.models import User
from app.collaboration.models import Demand, FeedbackEntry
from app.common.database import Base
from app.simulation.enums import SimulationMode, TaskStatus
from app.simulation.models import SimulationTask


def event(event_id: str, **values) -> AnalyticsEventCreate:
    return AnalyticsEventCreate(
        event_id=event_id,
        session_id=values.pop("session_id", "session-analytics-001"),
        **values,
    )


def main() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        alice = User(employee_id="alice", display_name="Alice", role="normal")
        bob = User(employee_id="bob", display_name="Bob", role="normal")
        db.add_all([alice, bob])
        db.commit()

        create_event(db, alice, event(
            "event-page-alice-001",
            event_name="page_view",
            page_key="benchmark.detail",
            vendor="acme",
            chip="chip-a",
            benchmark_name="vector_add",
        ))
        create_event(db, alice, event(
            "event-duration-alice-001",
            event_name="page_active_time",
            page_key="benchmark.detail",
            active_seconds=125,
            vendor="acme",
            chip="chip-a",
            benchmark_name="vector_add",
        ))
        create_event(db, alice, event(
            "event-benchmark-alice-001",
            event_name="benchmark.detail_view",
            page_key="benchmark.detail",
            vendor="acme",
            chip="chip-a",
            benchmark_name="vector_add",
            benchmark_type="MICRO",
            test_target="Cube",
        ))
        create_event(db, bob, event(
            "event-page-bob-00001",
            session_id="session-analytics-002",
            event_name="page_view",
            page_key="simulation.create",
        ))

        task = SimulationTask(
            queue_seq=1,
            task_id="SIM-ANALYTICS-001",
            task_name="Analytics test",
            owner_id="alice",
            simulator_version="v310",
            chip_variant="chip-a",
            simulation_mode=SimulationMode.SINGLE_CHIP,
            status=TaskStatus.COMPLETED,
            workspace_path="/tmp/analytics-test",
        )
        demand = Demand(
            request_no="REQ-ANALYTICS-001",
            user_id=alice.id,
            title="Trace compare",
            domain="仿真",
            background="test",
            description="test",
            business_value="test",
        )
        feedback = FeedbackEntry(
            user_id=alice.id,
            feedback_type="experience",
            page_title="Benchmark",
            page_path="/benchmark",
            content="test",
        )
        db.add_all([task, demand, feedback])
        db.commit()

        overview = get_overview(db, 30)
        assert overview.summary.active_users == 2
        assert overview.summary.visits == 2
        assert overview.summary.page_views == 2
        assert overview.summary.active_seconds == 125
        assert overview.summary.simulation_tasks == 1
        assert overview.summary.demand_feedback == 2
        assert overview.chips[0].chip == "chip-a"
        assert overview.benchmarks[0].benchmark_name == "vector_add"
        assert overview.simulation_dimensions[0].chip_variant == "chip-a"

        users = list_users(
            db,
            days=30,
            search="Ali",
            sort_by="simulation_tasks",
            sort_order="desc",
            page=1,
            page_size=20,
        )
        assert users.total == 1
        assert users.items[0].user_id == "alice"
        assert users.items[0].simulation_tasks == 1
        assert users.items[0].demand_feedback == 2

        detail = get_user_detail(db, "alice", 30)
        assert detail is not None
        assert detail.pages[0].page_key == "benchmark.detail"
        assert detail.pages[0].active_seconds == 125
        assert detail.recent_events[0].event_name == "benchmark.detail_view"

    print("Analytics tests passed")


if __name__ == "__main__":
    main()
