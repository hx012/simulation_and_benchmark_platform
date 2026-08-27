"""End-to-end check for session auth, admin accounts, and permission policy."""

import sys
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.auth import models as auth_models  # noqa: F401
from app.api import simulation as simulation_api
from app.common.config import get_settings
from app.common.database import Base, get_db
from app.main import create_app
from app.simulation import models as simulation_models  # noqa: F401
from app.simulation.enums import SimulationMode, TaskStatus


engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSession = sessionmaker(bind=engine, expire_on_commit=False)
Base.metadata.create_all(engine)


def override_db():
    with TestingSession() as session:
        yield session


settings = get_settings()
settings.platform_bootstrap_admin_id = "admin"
settings.platform_bootstrap_admin_password = "AdminTest2026!"
app = create_app()
app.dependency_overrides[get_db] = override_db
alice_client = TestClient(app)
admin_client = TestClient(app)


alice = alice_client.post("/api/auth/login", json={"employee_id": "permission-alice", "auth_mode": "normal"})
assert alice.status_code == 200, alice.text
assert alice.json()["permissions"] == ["normal"]
assert alice.json()["role"] == "normal"

blocked_benchmark = alice_client.get("/api/benchmark/status")
assert blocked_benchmark.status_code == 403, blocked_benchmark.text

for permission in ("benchmark_access", "simulation_log"):
    submitted = alice_client.post(
        "/api/permissions/requests",
        json={"permission_code": permission, "reason": "automated test"},
    )
    assert submitted.status_code == 200, submitted.text

bad_admin = admin_client.post("/api/auth/login", json={
    "employee_id": "admin", "auth_mode": "admin", "password": "wrong-password",
})
assert bad_admin.status_code == 401

admin = admin_client.post("/api/auth/login", json={
    "employee_id": "admin", "auth_mode": "admin", "password": "AdminTest2026!",
})
assert admin.status_code == 200, admin.text
assert admin.json()["role"] == "admin"
assert set(admin.json()["permissions"]) == {
    "normal", "benchmark_access", "simulation_log",
    "performance_access", "team_access", "demand_access",
}

capabilities = admin_client.get("/api/simulation/capabilities")
assert capabilities.status_code == 200, capabilities.text
assert "mskpp_guide_url" in capabilities.json()

config_template = admin_client.get(
    "/api/simulation/config-template",
    params={
        "simulator_version": "v310",
        "chip_variant": "default",
        "simulation_mode": "SINGLE_CHIP",
    },
)
assert config_template.status_code == 200, config_template.text
assert config_template.headers["content-type"].startswith("application/zip")
assert "mskpp_config_template_v310_default_single_chip.zip" in (
    config_template.headers["content-disposition"]
)
with ZipFile(BytesIO(config_template.content)) as archive:
    expected_template_files = {
        "chip_config/simulator_config.yml",
        "chip_config/daw_config.yml",
        "workload/workload.yml",
    }
    assert expected_template_files.issubset(set(archive.namelist()))
    v310_template_content = {
        name: archive.read(name) for name in expected_template_files
    }

v320_template = admin_client.get(
    "/api/simulation/config-template",
    params={
        "simulator_version": "v320",
        "chip_variant": "default",
        "simulation_mode": "SINGLE_CHIP",
    },
)
assert v320_template.status_code == 200, v320_template.text
with ZipFile(BytesIO(v320_template.content)) as archive:
    assert {
        name: archive.read(name) for name in expected_template_files
    } == v310_template_content

multi_chip_template = admin_client.get(
    "/api/simulation/config-template",
    params={
        "simulator_version": "v320",
        "chip_variant": "high_perf",
        "simulation_mode": "MULTI_CHIP",
    },
)
assert multi_chip_template.status_code == 200, multi_chip_template.text
with ZipFile(BytesIO(multi_chip_template.content)) as archive:
    assert b"mode: MULTI_CHIP" in archive.read(
        "chip_config/simulator_config.yml"
    )
    assert b"chip_count: 2" in archive.read("chip_config/daw_config.yml")

# Normal users are server-bound to their own tasks. Admin mode can read every
# task, but task mutations remain owner-only.
with TestingSession() as session:
    session.add_all([
        simulation_models.SimulationTask(
            queue_seq=1,
            task_id="SIM-PERMISSION-ALICE",
            task_name="Alice task",
            owner_id="permission-alice",
            simulator_version="mock",
            chip_variant=None,
            simulation_mode=SimulationMode.SINGLE_CHIP,
            status=TaskStatus.COMPLETED,
            workspace_path="/tmp/SIM-PERMISSION-ALICE",
        ),
        simulation_models.SimulationTask(
            queue_seq=2,
            task_id="SIM-PERMISSION-BOB",
            task_name="Bob task",
            owner_id="permission-bob",
            simulator_version="mock",
            chip_variant=None,
            simulation_mode=SimulationMode.SINGLE_CHIP,
            status=TaskStatus.COMPLETED,
            workspace_path="/tmp/SIM-PERMISSION-BOB",
        ),
    ])
    session.commit()

alice_tasks = alice_client.get(
    "/api/simulation/tasks",
    params={"owner_id": "permission-bob"},
)
assert alice_tasks.status_code == 200, alice_tasks.text
assert [item["task_id"] for item in alice_tasks.json()["items"]] == ["SIM-PERMISSION-ALICE"]
assert alice_client.get("/api/simulation/tasks/SIM-PERMISSION-BOB").status_code == 404

admin_tasks = admin_client.get("/api/simulation/tasks")
assert admin_tasks.status_code == 200, admin_tasks.text
assert {item["task_id"] for item in admin_tasks.json()["items"]} == {
    "SIM-PERMISSION-ALICE", "SIM-PERMISSION-BOB",
}
assert admin_client.get("/api/simulation/tasks/SIM-PERMISSION-BOB").status_code == 200
assert admin_client.post("/api/simulation/tasks/SIM-PERMISSION-BOB/cancel").status_code == 404

with TemporaryDirectory() as task_root:
    task_root_path = Path(task_root).resolve()
    bob_workspace = task_root_path / "SIM-PERMISSION-BOB"
    viewer_path = bob_workspace / "result" / "trace" / "trace.html"
    viewer_path.parent.mkdir(parents=True)
    viewer_path.write_text("<html><body>Trace viewer</body></html>", encoding="utf-8")
    simulation_api.task_io_service.task_root = task_root_path
    with TestingSession() as session:
        bob_task = session.get(simulation_models.SimulationTask, 2)
        assert bob_task is not None
        bob_task.workspace_path = str(bob_workspace)
        session.commit()

    assert alice_client.get(
        "/api/simulation/tasks/SIM-PERMISSION-BOB/trace/viewer"
    ).status_code == 404
    admin_viewer = admin_client.get(
        "/api/simulation/tasks/SIM-PERMISSION-BOB/trace/viewer"
    )
    assert admin_viewer.status_code == 200, admin_viewer.text
    assert "MSKPP&amp;AIBench + admin" in admin_viewer.text

pending = admin_client.get("/api/admin/permission-requests")
assert pending.status_code == 200, pending.text
for item in pending.json():
    reviewed = admin_client.post(
        f"/api/admin/permission-requests/{item['request_id']}/review",
        json={"decision": "approved", "comment": "approved by test"},
    )
    assert reviewed.status_code == 200, reviewed.text

refreshed = alice_client.get("/api/auth/me")
assert set(refreshed.json()["permissions"]) == {"normal", "benchmark_access", "simulation_log"}
assert alice_client.get("/api/benchmark/status").status_code == 200

resources = admin_client.get("/api/admin/resources").json()
resource_modes = {item["code"]: item["access_mode"] for item in resources}
assert resource_modes == {
    "admin.manage": "admin",
    "analytics.usage": "admin",
    "benchmark.view": "permission",
    "demand.view": "normal",
    "performance.view": "normal",
    "permission.manage": "admin",
    "simulation.log": "permission",
    "simulation.task": "normal",
    "team.view": "normal",
}
benchmark_resource = next(item for item in resources if item["code"] == "benchmark.view")
assert benchmark_resource["authorized_users"] == [{
    "user_id": "permission-alice", "display_name": "permission-alice",
}]
admin_users = admin_client.get("/api/admin/users").json()
assert admin_users[0]["role"] == "admin"
bootstrap_admin = next(item for item in admin_users if item["user_id"] == "admin")
assert bootstrap_admin["bootstrap_admin"] is True

# A DB policy change immediately makes Benchmark a normal-user module.
resource = benchmark_resource
resource["access_mode"] = "normal"
resource["permission_codes"] = []
updated = admin_client.put("/api/admin/resources/benchmark.view", json=resource)
assert updated.status_code == 200, updated.text

bob_client = TestClient(app)
bob = bob_client.post("/api/auth/login", json={"employee_id": "permission-bob", "auth_mode": "normal"})
assert "benchmark.view" in bob.json()["resources"]
assert bob_client.get("/api/benchmark/status").status_code == 200

# Switching back to approval mode reuses the hidden permission mapping.
resource = updated.json()
resource["access_mode"] = "permission"
resource["permission_codes"] = []
restricted_again = admin_client.put("/api/admin/resources/benchmark.view", json=resource)
assert restricted_again.status_code == 200, restricted_again.text
assert restricted_again.json()["permission_codes"] == ["benchmark_access"]
assert bob_client.get("/api/benchmark/status").status_code == 403

# Admin account can deliberately use ordinary mode and then has no admin API access.
ordinary_admin_client = TestClient(app)
ordinary_admin = ordinary_admin_client.post("/api/auth/login", json={"employee_id": "admin", "auth_mode": "normal"})
assert ordinary_admin.json()["role"] == "normal"
assert ordinary_admin.json()["account_role"] == "admin"
assert ordinary_admin_client.get("/api/admin/users").status_code == 403

# Usage events are available to authenticated users, while reports remain admin-only.
tracked = alice_client.post("/api/analytics/events", json={
    "event_id": "permission-test-event-0001",
    "session_id": "permission-test-session-01",
    "event_name": "page_view",
    "page_key": "home",
})
assert tracked.status_code == 202, tracked.text
recent = alice_client.get("/api/recent-activities")
assert recent.status_code == 200, recent.text
assert recent.json()["items"] == []
assert alice_client.get("/api/admin/analytics/overview").status_code == 403
assert admin_client.get("/api/admin/analytics/overview").status_code == 200

# Blocking a user immediately revokes existing sessions and prevents a new
# login, while unblocking restores login without deleting the account.
blocked_bob = admin_client.put("/api/admin/users/permission-bob", json={
    "role": "normal",
    "display_name": "permission-bob",
    "active": False,
})
assert blocked_bob.status_code == 200, blocked_bob.text
assert blocked_bob.json()["active"] is False
assert bob_client.get("/api/auth/me").status_code == 401
blocked_bob_login = TestClient(app).post("/api/auth/login", json={
    "employee_id": "permission-bob", "auth_mode": "normal",
})
assert blocked_bob_login.status_code == 403, blocked_bob_login.text

unblocked_bob = admin_client.put("/api/admin/users/permission-bob", json={
    "role": "normal",
    "display_name": "permission-bob",
    "active": True,
})
assert unblocked_bob.status_code == 200, unblocked_bob.text
assert TestClient(app).post("/api/auth/login", json={
    "employee_id": "permission-bob", "auth_mode": "normal",
}).status_code == 200

print("permission and administrator workflow checks passed")
