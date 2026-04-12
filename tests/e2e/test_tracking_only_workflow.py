# tests/e2e/test_tracking_only_workflow.py
"""
E2E: Tracking Only mode workflow.

Scenario: onboarding (tracking_only) → full-mode route blocked →
          external-plan CRUD → checkin → readiness → delete session

All tests share the module-scoped `e2e_client` fixture.
_state carries token + ids across sequential tests.
"""
from datetime import date, timedelta

_state: dict = {}


def _next_monday() -> str:
    today = date.today()
    days_ahead = (7 - today.weekday()) % 7 or 7
    return str(today + timedelta(days=days_ahead))


def _onboarding_payload() -> dict:
    return {
        "email": "tracking@resilio.test",
        "password": "trackpass123",
        "plan_start_date": _next_monday(),
        "name": "Tracking Athlete",
        "age": 28,
        "sex": "F",
        "weight_kg": 60.0,
        "height_cm": 165.0,
        "primary_sport": "running",
        "sports": ["running"],
        "goals": ["stay active"],
        "available_days": [1, 3, 5],
        "hours_per_week": 6.0,
        "coaching_mode": "tracking_only",
    }


def test_01_onboarding_tracking_only(e2e_client):
    """POST /athletes/onboarding → 201, coaching_mode=tracking_only."""
    resp = e2e_client.post("/athletes/onboarding", json=_onboarding_payload())
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["athlete"]["coaching_mode"] == "tracking_only"
    _state["token"] = body["access_token"]
    _state["athlete_id"] = body["athlete"]["id"]


def test_02_full_mode_plan_creation_blocked(e2e_client):
    """POST workflow/create-plan → 403 when athlete is in tracking_only mode."""
    headers = {"Authorization": f"Bearer {_state['token']}"}
    resp = e2e_client.post(
        f"/athletes/{_state['athlete_id']}/workflow/create-plan",
        json={"start_date": _next_monday(), "weeks": 8},
        headers=headers,
    )
    assert resp.status_code == 403, resp.text


def test_03_create_external_plan(e2e_client):
    """POST /athletes/{id}/external-plan → 201, plan is active with source=manual."""
    headers = {"Authorization": f"Bearer {_state['token']}"}
    resp = e2e_client.post(
        f"/athletes/{_state['athlete_id']}/external-plan",
        json={"title": "Plan coach externe", "start_date": _next_monday()},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["title"] == "Plan coach externe"
    assert body["status"] == "active"
    assert body["source"] == "manual"
    assert body["sessions"] == []
    _state["plan_id"] = body["id"]


def test_04_get_active_external_plan(e2e_client):
    """GET /athletes/{id}/external-plan → 200, returns active plan."""
    headers = {"Authorization": f"Bearer {_state['token']}"}
    resp = e2e_client.get(
        f"/athletes/{_state['athlete_id']}/external-plan",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["id"] == _state["plan_id"]
    assert body["sessions"] == []


def test_05_add_external_session(e2e_client):
    """POST /athletes/{id}/external-plan/sessions → 201, session status=planned."""
    headers = {"Authorization": f"Bearer {_state['token']}"}
    session_date = str(date.today() + timedelta(days=7))
    resp = e2e_client.post(
        f"/athletes/{_state['athlete_id']}/external-plan/sessions",
        json={
            "session_date": session_date,
            "sport": "running",
            "title": "Long run 12km",
            "description": "Easy Z1 pace",
            "duration_min": 75,
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["title"] == "Long run 12km"
    assert body["sport"] == "running"
    assert body["status"] == "planned"
    assert body["plan_id"] == _state["plan_id"]
    _state["session_id"] = body["id"]


def test_06_update_external_session_to_completed(e2e_client):
    """PATCH /athletes/{id}/external-plan/sessions/{id} → 200, status updated."""
    headers = {"Authorization": f"Bearer {_state['token']}"}
    resp = e2e_client.patch(
        f"/athletes/{_state['athlete_id']}/external-plan/sessions/{_state['session_id']}",
        json={"status": "completed"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "completed"
    assert body["id"] == _state["session_id"]


def test_07_checkin_works_in_tracking_mode(e2e_client):
    """POST /athletes/{id}/checkin → 201 (Volet 2 has no mode restriction)."""
    headers = {"Authorization": f"Bearer {_state['token']}"}
    resp = e2e_client.post(
        f"/athletes/{_state['athlete_id']}/checkin",
        json={
            "work_intensity": "heavy",
            "stress_level": "significant",
            "legs_feeling": "heavy",
            "energy_global": "low",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert "traffic_light" in body
    assert body["traffic_light"] in ("green", "yellow", "red")


def test_08_readiness_works_in_tracking_mode(e2e_client):
    """GET /athletes/{id}/readiness → 200 (Volet 2 operates in any mode)."""
    headers = {"Authorization": f"Bearer {_state['token']}"}
    resp = e2e_client.get(
        f"/athletes/{_state['athlete_id']}/readiness",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["traffic_light"] in ("green", "yellow", "red")
    assert 0.0 <= body["final_readiness"] <= 100.0


def test_09_delete_external_session(e2e_client):
    """DELETE /athletes/{id}/external-plan/sessions/{id} → 204, session removed."""
    headers = {"Authorization": f"Bearer {_state['token']}"}
    resp = e2e_client.delete(
        f"/athletes/{_state['athlete_id']}/external-plan/sessions/{_state['session_id']}",
        headers=headers,
    )
    assert resp.status_code == 204, resp.text

    # Verify session is gone from the plan
    get_resp = e2e_client.get(
        f"/athletes/{_state['athlete_id']}/external-plan",
        headers=headers,
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["sessions"] == []
