# tests/e2e/test_mode_switch.py
"""
E2E: Mode switching.

Scenario 1 (full → tracking_only):
  - Active training plan is archived on switch
  - Full-mode routes become 403
  - Tracking-only routes become accessible

Scenario 2 (tracking_only → full):
  - Full-mode routes become accessible again
  - Tracking-only routes become 403

All tests share the module-scoped `e2e_client` fixture.
"""
from datetime import date, timedelta

_state: dict = {}


def _next_monday() -> str:
    today = date.today()
    days_ahead = (7 - today.weekday()) % 7 or 7
    return str(today + timedelta(days=days_ahead))


def _onboarding_payload() -> dict:
    return {
        "email": "switch@resilio.test",
        "password": "switchpass123",
        "plan_start_date": _next_monday(),
        "name": "Switch Athlete",
        "age": 35,
        "sex": "M",
        "weight_kg": 80.0,
        "height_cm": 178.0,
        "primary_sport": "running",
        "sports": ["running"],
        "goals": ["improve speed"],
        "available_days": [0, 2, 4, 6],
        "hours_per_week": 10.0,
        "coaching_mode": "full",
    }


def test_01_onboarding_full_mode(e2e_client):
    """Register athlete in full mode — plan is created by onboarding."""
    resp = e2e_client.post("/athletes/onboarding", json=_onboarding_payload())
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["athlete"]["coaching_mode"] == "full"
    _state["token"] = body["access_token"]
    _state["athlete_id"] = body["athlete"]["id"]


def test_02_active_plan_exists_before_switch(e2e_client):
    """GET /athletes/{id}/plans → at least one active plan exists in full mode."""
    headers = {"Authorization": f"Bearer {_state['token']}"}
    resp = e2e_client.get(f"/athletes/{_state['athlete_id']}/plans", headers=headers)
    assert resp.status_code == 200, resp.text
    plans = resp.json()
    assert len(plans) >= 1
    active_plans = [p for p in plans if p["status"] == "active"]
    assert len(active_plans) >= 1, "Expected at least one active plan before switch"


def test_03_switch_to_tracking_only(e2e_client):
    """PATCH /athletes/{id}/mode → tracking_only, response confirms new mode."""
    headers = {"Authorization": f"Bearer {_state['token']}"}
    resp = e2e_client.patch(
        f"/athletes/{_state['athlete_id']}/mode",
        json={"coaching_mode": "tracking_only"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["coaching_mode"] == "tracking_only"
    assert body["athlete_id"] == _state["athlete_id"]


def test_04_training_plans_archived_after_switch(e2e_client):
    """GET /athletes/{id}/plans → all training plans are now archived."""
    headers = {"Authorization": f"Bearer {_state['token']}"}
    resp = e2e_client.get(f"/athletes/{_state['athlete_id']}/plans", headers=headers)
    assert resp.status_code == 200, resp.text
    plans = resp.json()
    assert len(plans) >= 1, "Plans should still exist (never deleted, only archived)"
    for plan in plans:
        assert plan["status"] == "archived", (
            f"Plan {plan['id']} expected status=archived, got {plan['status']}"
        )


def test_05_full_mode_route_blocked_after_switch(e2e_client):
    """POST workflow/create-plan → 403 once athlete is in tracking_only mode."""
    headers = {"Authorization": f"Bearer {_state['token']}"}
    resp = e2e_client.post(
        f"/athletes/{_state['athlete_id']}/workflow/create-plan",
        json={"start_date": _next_monday(), "weeks": 8},
        headers=headers,
    )
    assert resp.status_code == 403, resp.text


def test_06_tracking_route_accessible_after_switch(e2e_client):
    """POST external-plan → 201 after switching to tracking_only."""
    headers = {"Authorization": f"Bearer {_state['token']}"}
    resp = e2e_client.post(
        f"/athletes/{_state['athlete_id']}/external-plan",
        json={"title": "Plan coach externe post-switch"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "active"


def test_07_volet2_still_works_after_switch(e2e_client):
    """POST /checkin → 201 (Volet 2 has no mode restriction, works in any mode)."""
    headers = {"Authorization": f"Bearer {_state['token']}"}
    resp = e2e_client.post(
        f"/athletes/{_state['athlete_id']}/checkin",
        json={
            "work_intensity": "normal",
            "stress_level": "none",
            "legs_feeling": "normal",
            "energy_global": "ok",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text


def test_08_switch_back_to_full(e2e_client):
    """PATCH /athletes/{id}/mode → full, confirms bidirectional switching."""
    headers = {"Authorization": f"Bearer {_state['token']}"}
    resp = e2e_client.patch(
        f"/athletes/{_state['athlete_id']}/mode",
        json={"coaching_mode": "full"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["coaching_mode"] == "full"


def test_09_tracking_route_blocked_after_switch_back(e2e_client):
    """POST external-plan → 403 once back in full mode."""
    headers = {"Authorization": f"Bearer {_state['token']}"}
    resp = e2e_client.post(
        f"/athletes/{_state['athlete_id']}/external-plan",
        json={"title": "Should fail"},
        headers=headers,
    )
    assert resp.status_code == 403, resp.text
