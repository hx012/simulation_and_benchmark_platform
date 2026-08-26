"""End-to-end check for session auth, admin accounts, and permission policy."""

import sys
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.auth import models as auth_models  # noqa: F401
from app.common.config import get_settings
from app.common.database import Base, get_db
from app.main import create_app
from app.simulation import models as simulation_models  # noqa: F401


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
assert set(admin.json()["permissions"]) == {"normal", "benchmark_access", "simulation_log"}

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
benchmark_resource = next(item for item in resources if item["code"] == "benchmark.view")
assert benchmark_resource["authorized_users"] == [{
    "user_id": "permission-alice", "display_name": "permission-alice",
}]
admin_users = admin_client.get("/api/admin/users").json()
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

print("permission and administrator workflow checks passed")
