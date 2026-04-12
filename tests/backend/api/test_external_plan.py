"""API integration tests for ExternalPlan endpoints."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.db import models  # noqa: registers all ORM models
from app.dependencies import get_db
from app.main import app


def _make_test_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


@pytest.fixture()
def client():
    engine = _make_test_engine()
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(engine)

    def override_get_db():
        with TestSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def _base_onboarding(**overrides):
    from datetime import date
    base = {
        "name": "Alice",
        "age": 30,
        "sex": "F",
        "weight_kg": 60.0,
        "height_cm": 168.0,
        "sports": ["running"],
        "primary_sport": "running",
        "goals": ["stay fit"],
        "available_days": [0, 2, 4],
        "hours_per_week": 8.0,
        "email": "alice@test.com",
        "password": "password123",
        "plan_start_date": str(date.today()),
    }
    return {**base, **overrides}


def _register(client, **overrides):
    """Register an athlete and return (token, athlete_id)."""
    payload = _base_onboarding(**overrides)
    resp = client.post("/athletes/onboarding", json=payload)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    return body["access_token"], body["athlete"]["id"]


def _authed(client, token):
    """Return client with Authorization header set."""
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


# ---------------------------------------------------------------------------
# Mode guard — full mode must be rejected
# ---------------------------------------------------------------------------

def test_create_plan_rejected_for_full_mode_athlete(client):
    token, athlete_id = _register(client)  # default: full mode
    _authed(client, token)
    resp = client.post(
        f"/athletes/{athlete_id}/external-plan",
        json={"title": "Coach Plan"},
    )
    assert resp.status_code == 403


def test_get_plan_rejected_for_full_mode_athlete(client):
    token, athlete_id = _register(client)
    _authed(client, token)
    resp = client.get(f"/athletes/{athlete_id}/external-plan")
    assert resp.status_code == 403


def test_add_session_rejected_for_full_mode_athlete(client):
    token, athlete_id = _register(client)
    _authed(client, token)
    resp = client.post(
        f"/athletes/{athlete_id}/external-plan/sessions",
        json={"session_date": "2026-05-05", "sport": "running", "title": "Run"},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /athletes/{id}/external-plan — create plan
# ---------------------------------------------------------------------------

def test_create_external_plan_success(client):
    token, athlete_id = _register(client, email="tracker@test.com", coaching_mode="tracking_only")
    _authed(client, token)
    resp = client.post(
        f"/athletes/{athlete_id}/external-plan",
        json={"title": "My Coach Plan", "start_date": "2026-05-01", "end_date": "2026-07-31"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["title"] == "My Coach Plan"
    assert body["status"] == "active"
    assert body["source"] == "manual"
    assert body["start_date"] == "2026-05-01"
    assert body["sessions"] == []


def test_create_plan_without_dates_succeeds(client):
    token, athlete_id = _register(client, email="t2@test.com", coaching_mode="tracking_only")
    _authed(client, token)
    resp = client.post(
        f"/athletes/{athlete_id}/external-plan",
        json={"title": "Minimal Plan"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["start_date"] is None
    assert body["end_date"] is None


def test_create_second_plan_archives_first(client):
    token, athlete_id = _register(client, email="t3@test.com", coaching_mode="tracking_only")
    _authed(client, token)
    client.post(f"/athletes/{athlete_id}/external-plan", json={"title": "Plan A"})
    resp2 = client.post(f"/athletes/{athlete_id}/external-plan", json={"title": "Plan B"})
    assert resp2.status_code == 201
    # GET should now return Plan B
    get_resp = client.get(f"/athletes/{athlete_id}/external-plan")
    assert get_resp.status_code == 200
    assert get_resp.json()["title"] == "Plan B"


# ---------------------------------------------------------------------------
# GET /athletes/{id}/external-plan — get active plan
# ---------------------------------------------------------------------------

def test_get_active_plan_returns_404_when_none(client):
    token, athlete_id = _register(client, email="t4@test.com", coaching_mode="tracking_only")
    _authed(client, token)
    resp = client.get(f"/athletes/{athlete_id}/external-plan")
    assert resp.status_code == 404


def test_get_active_plan_returns_plan_with_sessions(client):
    token, athlete_id = _register(client, email="t5@test.com", coaching_mode="tracking_only")
    _authed(client, token)
    client.post(f"/athletes/{athlete_id}/external-plan", json={"title": "Plan"})
    client.post(
        f"/athletes/{athlete_id}/external-plan/sessions",
        json={"session_date": "2026-05-05", "sport": "running", "title": "Easy 5k"},
    )
    resp = client.get(f"/athletes/{athlete_id}/external-plan")
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "Plan"
    assert len(body["sessions"]) == 1
    assert body["sessions"][0]["title"] == "Easy 5k"


# ---------------------------------------------------------------------------
# POST /athletes/{id}/external-plan/sessions — add session
# ---------------------------------------------------------------------------

def test_add_session_without_active_plan_returns_404(client):
    token, athlete_id = _register(client, email="t6@test.com", coaching_mode="tracking_only")
    _authed(client, token)
    resp = client.post(
        f"/athletes/{athlete_id}/external-plan/sessions",
        json={"session_date": "2026-05-05", "sport": "running", "title": "Run"},
    )
    assert resp.status_code == 404


def test_add_session_success(client):
    token, athlete_id = _register(client, email="t7@test.com", coaching_mode="tracking_only")
    _authed(client, token)
    client.post(f"/athletes/{athlete_id}/external-plan", json={"title": "Plan"})
    resp = client.post(
        f"/athletes/{athlete_id}/external-plan/sessions",
        json={
            "session_date": "2026-05-05",
            "sport": "running",
            "title": "Easy 5k",
            "description": "Recovery run",
            "duration_min": 30,
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["sport"] == "running"
    assert body["title"] == "Easy 5k"
    assert body["duration_min"] == 30
    assert body["status"] == "planned"


def test_add_multiple_sessions(client):
    token, athlete_id = _register(client, email="t8@test.com", coaching_mode="tracking_only")
    _authed(client, token)
    client.post(f"/athletes/{athlete_id}/external-plan", json={"title": "Plan"})
    client.post(
        f"/athletes/{athlete_id}/external-plan/sessions",
        json={"session_date": "2026-05-05", "sport": "running", "title": "Run 1"},
    )
    client.post(
        f"/athletes/{athlete_id}/external-plan/sessions",
        json={"session_date": "2026-05-07", "sport": "lifting", "title": "Strength"},
    )
    resp = client.get(f"/athletes/{athlete_id}/external-plan")
    assert resp.status_code == 200
    assert len(resp.json()["sessions"]) == 2


# ---------------------------------------------------------------------------
# PATCH /athletes/{id}/external-plan/sessions/{session_id} — update session
# ---------------------------------------------------------------------------

def test_update_session_partial(client):
    token, athlete_id = _register(client, email="t9@test.com", coaching_mode="tracking_only")
    _authed(client, token)
    client.post(f"/athletes/{athlete_id}/external-plan", json={"title": "Plan"})
    add_resp = client.post(
        f"/athletes/{athlete_id}/external-plan/sessions",
        json={"session_date": "2026-05-05", "sport": "running", "title": "Run"},
    )
    session_id = add_resp.json()["id"]
    resp = client.patch(
        f"/athletes/{athlete_id}/external-plan/sessions/{session_id}",
        json={"title": "Long Run", "duration_min": 90, "status": "completed"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["title"] == "Long Run"
    assert body["duration_min"] == 90
    assert body["status"] == "completed"
    assert body["sport"] == "running"  # unchanged


def test_update_session_not_found(client):
    token, athlete_id = _register(client, email="t10@test.com", coaching_mode="tracking_only")
    _authed(client, token)
    resp = client.patch(
        f"/athletes/{athlete_id}/external-plan/sessions/ghost-id",
        json={"title": "X"},
    )
    assert resp.status_code == 404


def test_update_session_requires_tracking_mode(client):
    token, athlete_id = _register(client, email="t11@test.com")  # full mode
    _authed(client, token)
    resp = client.patch(
        f"/athletes/{athlete_id}/external-plan/sessions/some-id",
        json={"title": "X"},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# DELETE /athletes/{id}/external-plan/sessions/{session_id} — delete session
# ---------------------------------------------------------------------------

def test_delete_session_success(client):
    token, athlete_id = _register(client, email="t12@test.com", coaching_mode="tracking_only")
    _authed(client, token)
    client.post(f"/athletes/{athlete_id}/external-plan", json={"title": "Plan"})
    sess_resp = client.post(
        f"/athletes/{athlete_id}/external-plan/sessions",
        json={"session_date": "2026-05-05", "sport": "running", "title": "Run"},
    )
    session_id = sess_resp.json()["id"]
    resp = client.delete(
        f"/athletes/{athlete_id}/external-plan/sessions/{session_id}"
    )
    assert resp.status_code == 204
    # Verify it's gone
    get_resp = client.get(f"/athletes/{athlete_id}/external-plan")
    assert get_resp.json()["sessions"] == []


def test_delete_session_not_found_returns_404(client):
    token, athlete_id = _register(client, email="t13@test.com", coaching_mode="tracking_only")
    _authed(client, token)
    client.post(f"/athletes/{athlete_id}/external-plan", json={"title": "Plan"})
    resp = client.delete(
        f"/athletes/{athlete_id}/external-plan/sessions/ghost-session-id"
    )
    assert resp.status_code == 404


def test_delete_session_requires_tracking_mode(client):
    token, athlete_id = _register(client, email="t14@test.com")  # full mode
    _authed(client, token)
    resp = client.delete(
        f"/athletes/{athlete_id}/external-plan/sessions/some-id"
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Unauthenticated requests
# ---------------------------------------------------------------------------

def test_unauthenticated_get_plan_rejected(client):
    resp = client.get("/athletes/some-id/external-plan")
    assert resp.status_code == 401


def test_unauthenticated_create_plan_rejected(client):
    resp = client.post("/athletes/some-id/external-plan", json={"title": "X"})
    assert resp.status_code == 401
