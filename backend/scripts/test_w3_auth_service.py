"""Focused checks for W3 identity binding and OAuth state handling."""

import sys
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.auth import models as auth_models  # noqa: F401
from app.auth.service import (
    consume_w3_login_transaction,
    create_w3_login_transaction,
    login_w3_user,
)
from app.common.database import Base


engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSession = sessionmaker(bind=engine, expire_on_commit=False)
Base.metadata.create_all(engine)

with TestingSession() as db:
    state, verifier, challenge = create_w3_login_transaction(db, "/simulation/tasks")
    assert state and verifier and challenge
    consumed_verifier, next_path = consume_w3_login_transaction(db, state)
    assert consumed_verifier == verifier
    assert next_path == "/simulation/tasks"
    try:
        consume_w3_login_transaction(db, state)
        raise AssertionError("OAuth state must not be consumed twice")
    except HTTPException as error:
        assert error.status_code == 400

    current, raw_session = login_w3_user(
        db,
        global_user_id="w3-global-user-001",
        employee_id="h00517730",
        display_name="cn=郝雪桐,en=haoxuetong",
    )
    assert raw_session
    assert current.user.employee_id == "h00517730"
    assert current.user.w3_global_user_id == "w3-global-user-001"
    assert current.user.display_name == "郝雪桐"

    updated, _ = login_w3_user(
        db,
        global_user_id="w3-global-user-001",
        employee_id="h00517731",
        display_name="cn=郝雪桐,en=haoxuetong",
    )
    assert updated.user.id == current.user.id
    assert updated.user.employee_id == "h00517731"

print("W3 OAuth state and identity-binding checks passed")
