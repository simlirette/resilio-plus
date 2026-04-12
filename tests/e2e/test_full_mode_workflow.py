# tests/e2e/test_full_mode_workflow.py
"""
E2E: Full Coaching mode workflow.

Scenario: onboarding (full) → checkin → readiness → workflow/create-plan → approve

All tests share the module-scoped `e2e_client` fixture (one in-memory DB per module).
_state carries token + athlete_id + thread_id across sequential tests.
"""
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

_state: dict = {}


def _next_monday() -> str:
    today = date.today()
    days_ahead = (7 - today.weekday()) % 7 or 7
    return str(today + timedelta(days=days_ahead))


def _onboarding_payload() -> dict:
    return {
        "email": "full@resilio.test",
        "password": "fullpass123",
        "plan_start_date": _next_monday(),
        "name": "Full Mode Athlete",
        "age": 30,
        "sex": "M",
        "weight_kg": 75.0,
        "height_cm": 180.0,
        "primary_sport": "running",
        "sports": ["running"],
        "goals": ["run a 10K"],
        "available_days": [0, 2, 4],
        "hours_per_week": 8.0,
        "coaching_mode": "full",
    }


def test_01_onboarding_full_mode(e2e_client):
    """POST /athletes/onboarding → 201, athlete is in full coaching mode."""
    resp = e2e_client.post("/athletes/onboarding", json=_onboarding_payload())
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert "access_token" in body
    assert body["athlete"]["coaching_mode"] == "full"
    _state["token"] = body["access_token"]
    _state["athlete_id"] = body["athlete"]["id"]


def test_02_readiness_before_checkin(e2e_client):
    """GET /athletes/{id}/readiness before any checkin → 404 (no snapshot)."""
    headers = {"Authorization": f"Bearer {_state['token']}"}
    resp = e2e_client.get(f"/athletes/{_state['athlete_id']}/readiness", headers=headers)
    # Service raises 404 when no snapshot exists
    assert resp.status_code == 404, resp.text


def test_03_submit_checkin(e2e_client):
    """POST /athletes/{id}/checkin → 201, ReadinessResponse shape validated."""
    headers = {"Authorization": f"Bearer {_state['token']}"}
    resp = e2e_client.post(
        f"/athletes/{_state['athlete_id']}/checkin",
        json={
            "work_intensity": "normal",
            "stress_level": "mild",
            "legs_feeling": "normal",
            "energy_global": "ok",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert "final_readiness" in body
    assert "traffic_light" in body
    assert body["traffic_light"] in ("green", "yellow", "red")
    assert "intensity_cap" in body
    assert 0.0 <= body["intensity_cap"] <= 1.0
    assert "insights" in body
    assert isinstance(body["insights"], list)


def test_04_readiness_after_checkin(e2e_client):
    """GET /athletes/{id}/readiness → 200 after checkin, returns ReadinessResponse."""
    headers = {"Authorization": f"Bearer {_state['token']}"}
    resp = e2e_client.get(f"/athletes/{_state['athlete_id']}/readiness", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "final_readiness" in body
    assert "traffic_light" in body
    assert "divergence_flag" in body
    assert body["divergence_flag"] in ("none", "moderate", "high")


def test_05_create_plan_via_workflow(e2e_client):
    """POST /athletes/{id}/workflow/create-plan → 200, thread_id + requires_approval."""
    headers = {"Authorization": f"Bearer {_state['token']}"}
    athlete_id = _state["athlete_id"]
    thread_id = f"{athlete_id}:test-thread-001"

    mock_plan = {
        "sessions": [{"sport": "running", "duration_min": 45}],
        "phase": "base",
        "readiness_level": "green",
    }

    with patch("app.routes.workflow.CoachingService") as MockService:
        mock_instance = MagicMock()
        mock_instance.create_plan.return_value = (thread_id, mock_plan)
        MockService.return_value = mock_instance

        resp = e2e_client.post(
            f"/athletes/{athlete_id}/workflow/create-plan",
            json={"start_date": _next_monday(), "weeks": 8},
            headers=headers,
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["success"] is True
    assert body["requires_approval"] is True
    assert body["thread_id"] == thread_id
    assert body["sessions_total"] == 1
    _state["thread_id"] = body["thread_id"]


def test_06_approve_plan(e2e_client):
    """POST /athletes/{id}/workflow/plans/{thread_id}/approve → 200, success."""
    headers = {"Authorization": f"Bearer {_state['token']}"}
    athlete_id = _state["athlete_id"]
    thread_id = _state["thread_id"]

    mock_final = {
        "sessions": [{"sport": "running", "duration_min": 45}],
        "phase": "base",
        "db_plan_id": "mock-plan-id-001",
    }

    with patch("app.routes.workflow.CoachingService") as MockService:
        mock_instance = MagicMock()
        mock_instance.resume_plan.return_value = mock_final
        MockService.return_value = mock_instance

        resp = e2e_client.post(
            f"/athletes/{athlete_id}/workflow/plans/{thread_id}/approve",
            headers=headers,
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["success"] is True


def test_07_full_mode_has_training_plan(e2e_client):
    """GET /athletes/{id}/plans → at least one plan exists for a full-mode athlete."""
    headers = {"Authorization": f"Bearer {_state['token']}"}
    resp = e2e_client.get(f"/athletes/{_state['athlete_id']}/plans", headers=headers)
    assert resp.status_code == 200, resp.text
    plans = resp.json()
    assert len(plans) >= 1
