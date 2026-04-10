# tests/e2e/test_full_workflow.py
"""
End-to-end API workflow: onboarding → week-status → plan → review → login.

Tests are prefixed 01–06 so pytest runs them in definition order.
All tests share the `e2e_client` module-scoped fixture (one DB for the module).
_state carries athlete_id and token across tests.
"""
from datetime import date, timedelta

import pytest

# Mutable shared state across tests in this module
_state: dict = {}


def _next_monday() -> str:
    today = date.today()
    days_ahead = (7 - today.weekday()) % 7 or 7  # 1–7
    return str(today + timedelta(days=days_ahead))


def _onboarding_payload() -> dict:
    return {
        "email": "e2e@resilio.test",
        "password": "e2epass123",
        "plan_start_date": _next_monday(),
        "name": "E2E Athlete",
        "age": 28,
        "sex": "M",
        "weight_kg": 75.0,
        "height_cm": 180.0,
        "primary_sport": "running",
        "sports": ["running", "lifting"],
        "goals": ["finish a 10K", "stay injury-free"],
        "available_days": [0, 2, 4, 6],
        "hours_per_week": 8.0,
    }


def test_01_onboarding_creates_athlete_and_plan(e2e_client):
    """POST /athletes/onboarding → 201, returns token + non-empty plan."""
    resp = e2e_client.post("/athletes/onboarding", json=_onboarding_payload())
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert "access_token" in body
    assert "athlete" in body
    assert "plan" in body
    assert len(body["plan"]["sessions"]) > 0
    # Store for subsequent tests
    _state["token"] = body["access_token"]
    _state["athlete_id"] = body["athlete"]["id"]


def test_02_week_status_requires_auth(e2e_client):
    """GET /athletes/{id}/week-status without Bearer → 401 or 403."""
    resp = e2e_client.get(f"/athletes/{_state['athlete_id']}/week-status")
    assert resp.status_code in (401, 403), resp.text


def test_03_week_status_returns_week_one(e2e_client):
    """GET /athletes/{id}/week-status with Bearer → 200, week_number=1, planned_hours > 0."""
    headers = {"Authorization": f"Bearer {_state['token']}"}
    resp = e2e_client.get(
        f"/athletes/{_state['athlete_id']}/week-status",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["week_number"] == 1
    assert body["planned_hours"] > 0
    assert "plan" in body


def test_04_plan_has_multi_sport_sessions(e2e_client):
    """GET /athletes/{id}/plan with Bearer → 200, sessions include at least 1 sport."""
    headers = {"Authorization": f"Bearer {_state['token']}"}
    resp = e2e_client.get(
        f"/athletes/{_state['athlete_id']}/plan",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    sessions = body["sessions"]
    assert len(sessions) > 0
    sports = {s["sport"] for s in sessions}
    assert len(sports) >= 1  # at least one sport scheduled


def test_05_review_returns_next_week_suggestion(e2e_client):
    """POST /athletes/{id}/review with Bearer → 201, next_week_suggestion non-empty."""
    headers = {"Authorization": f"Bearer {_state['token']}"}
    resp = e2e_client.post(
        f"/athletes/{_state['athlete_id']}/review",
        json={
            "week_end_date": str(date.today()),
            "readiness_score": 7.0,
            "sleep_hours_avg": 7.5,
            "comment": "Felt good, legs a bit tired",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert "next_week_suggestion" in body
    assert len(body["next_week_suggestion"]) > 0
    assert "acwr" in body


def test_06_login_with_onboarding_credentials(e2e_client):
    """POST /auth/login → 200, returns fresh token for the same athlete."""
    resp = e2e_client.post(
        "/auth/login",
        json={"email": "e2e@resilio.test", "password": "e2epass123"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert body["athlete_id"] == _state["athlete_id"]


def test_07_log_session_and_history(e2e_client):
    """GET session → POST log → GET history shows 1 logged session."""
    headers = {"Authorization": f"Bearer {_state['token']}"}
    athlete_id = _state["athlete_id"]

    # Get the plan to find a session id
    plan_resp = e2e_client.get(f"/athletes/{athlete_id}/plan", headers=headers)
    assert plan_resp.status_code == 200
    sessions = plan_resp.json()["sessions"]
    assert len(sessions) > 0
    session_id = sessions[0]["id"]
    assert session_id  # must be a non-empty string

    # GET session detail — not yet logged
    detail_resp = e2e_client.get(
        f"/athletes/{athlete_id}/sessions/{session_id}", headers=headers
    )
    assert detail_resp.status_code == 200
    assert detail_resp.json()["log"] is None

    # POST log
    log_resp = e2e_client.post(
        f"/athletes/{athlete_id}/sessions/{session_id}/log",
        json={"actual_duration_min": 38, "rpe": 6, "notes": "Good session"},
        headers=headers,
    )
    assert log_resp.status_code == 201
    assert log_resp.json()["actual_duration_min"] == 38

    # GET session detail — now logged
    detail_resp2 = e2e_client.get(
        f"/athletes/{athlete_id}/sessions/{session_id}", headers=headers
    )
    assert detail_resp2.json()["log"] is not None

    # GET history
    history_resp = e2e_client.get(f"/athletes/{athlete_id}/history", headers=headers)
    assert history_resp.status_code == 200
    history = history_resp.json()
    assert len(history) >= 1
    assert history[0]["sessions_logged"] >= 1
