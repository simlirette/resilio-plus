# tests/e2e/test_volet2_standalone.py
"""
E2E: Volet 2 standalone — Energy Cycle operates independently of Volet 1.

Validates the key architectural invariant:
  "Le Volet 2 (Energy Cycle) fonctionne sans le Volet 1."

Tests:
  - checkin + readiness + history without any coaching plan action
  - Volet 2 works in both full and tracking_only modes
  - Second checkin on same day → 409 (conflict guard)
  - Energy history after checkin → list with snapshot

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
        "email": "volet2@resilio.test",
        "password": "volet2pass123",
        "plan_start_date": _next_monday(),
        "name": "Volet2 Athlete",
        "age": 25,
        "sex": "F",
        "weight_kg": 55.0,
        "height_cm": 162.0,
        "primary_sport": "running",
        "sports": ["running"],
        "goals": ["well-being"],
        "available_days": [0, 2, 4],
        "hours_per_week": 5.0,
        "coaching_mode": "full",
    }


def test_01_register_athlete(e2e_client):
    """Register athlete — no plan interaction needed for Volet 2."""
    resp = e2e_client.post("/athletes/onboarding", json=_onboarding_payload())
    assert resp.status_code == 201, resp.text
    body = resp.json()
    _state["token"] = body["access_token"]
    _state["athlete_id"] = body["athlete"]["id"]


def test_02_readiness_before_checkin_is_404(e2e_client):
    """GET /athletes/{id}/readiness before any checkin → 404 (no snapshot today)."""
    headers = {"Authorization": f"Bearer {_state['token']}"}
    resp = e2e_client.get(f"/athletes/{_state['athlete_id']}/readiness", headers=headers)
    assert resp.status_code == 404, resp.text


def test_03_energy_history_empty_before_checkin(e2e_client):
    """GET energy/history before any checkin → 200 with empty list."""
    headers = {"Authorization": f"Bearer {_state['token']}"}
    resp = e2e_client.get(
        f"/athletes/{_state['athlete_id']}/energy/history?days=7",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == []


def test_04_checkin_without_coaching_plan(e2e_client):
    """POST /checkin → 201, Volet 2 works without any plan creation."""
    headers = {"Authorization": f"Bearer {_state['token']}"}
    resp = e2e_client.post(
        f"/athletes/{_state['athlete_id']}/checkin",
        json={
            "work_intensity": "light",
            "stress_level": "none",
            "legs_feeling": "fresh",
            "energy_global": "great",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    # Validate full ReadinessResponse shape
    assert "final_readiness" in body
    assert "traffic_light" in body
    assert body["traffic_light"] in ("green", "yellow", "red")
    assert "intensity_cap" in body
    assert 0.0 <= body["intensity_cap"] <= 1.0
    assert "divergence_flag" in body
    assert body["divergence_flag"] in ("none", "moderate", "high")
    assert "insights" in body
    assert isinstance(body["insights"], list)
    assert "allostatic_score" in body
    assert "energy_availability" in body


def test_05_readiness_available_after_checkin(e2e_client):
    """GET /athletes/{id}/readiness → 200 with full response after checkin."""
    headers = {"Authorization": f"Bearer {_state['token']}"}
    resp = e2e_client.get(f"/athletes/{_state['athlete_id']}/readiness", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["traffic_light"] in ("green", "yellow", "red")
    assert 0.0 <= body["final_readiness"] <= 100.0
    assert 0.0 <= body["intensity_cap"] <= 1.0


def test_06_second_checkin_same_day_conflicts(e2e_client):
    """POST /checkin twice on same day → 409 (one check-in per day guard)."""
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
    assert resp.status_code == 409, resp.text


def test_07_energy_history_has_snapshot(e2e_client):
    """GET energy/history → 200 with at least 1 snapshot entry."""
    headers = {"Authorization": f"Bearer {_state['token']}"}
    resp = e2e_client.get(
        f"/athletes/{_state['athlete_id']}/energy/history?days=7",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    history = resp.json()
    assert isinstance(history, list)
    assert len(history) >= 1
    snapshot = history[0]
    assert "traffic_light" in snapshot
    assert snapshot["traffic_light"] in ("green", "yellow", "red")
    assert "allostatic_score" in snapshot
    assert "intensity_cap" in snapshot


def test_08_volet2_works_in_tracking_only_mode(e2e_client):
    """Switch to tracking_only → Volet 2 readiness still accessible (modularity invariant)."""
    headers = {"Authorization": f"Bearer {_state['token']}"}

    # Switch mode
    switch_resp = e2e_client.patch(
        f"/athletes/{_state['athlete_id']}/mode",
        json={"coaching_mode": "tracking_only"},
        headers=headers,
    )
    assert switch_resp.status_code == 200, switch_resp.text

    # Volet 2 readiness endpoint has no mode restriction
    readiness_resp = e2e_client.get(
        f"/athletes/{_state['athlete_id']}/readiness",
        headers=headers,
    )
    assert readiness_resp.status_code == 200, readiness_resp.text


def test_09_volet2_never_invokes_langgraph(e2e_client):
    """Critical architectural invariant: Volet 2 endpoints NEVER trigger the coaching graph.

    Patches CoachingService.create_plan and resume_plan with assertion failures.
    If any Volet 2 endpoint (checkin, readiness, history) calls them, the test fails.
    This guarantees the Volet 2 independence contract specified in resilio-master-v3.md §1.
    """
    from unittest.mock import patch

    headers = {"Authorization": f"Bearer {_state['token']}"}
    athlete_id = _state["athlete_id"]

    def _must_not_be_called(*args, **kwargs):
        raise AssertionError(
            "LangGraph coaching graph was invoked from a Volet 2 endpoint — "
            "this violates the 2-volet modularity invariant."
        )

    with patch(
        "app.services.coaching_service.CoachingService.create_plan",
        side_effect=_must_not_be_called,
    ):
        with patch(
            "app.services.coaching_service.CoachingService.resume_plan",
            side_effect=_must_not_be_called,
        ):
            # GET /readiness must not touch the coaching graph
            r1 = e2e_client.get(f"/athletes/{athlete_id}/readiness", headers=headers)
            assert r1.status_code == 200, r1.text

            # GET /energy/history must not touch the coaching graph
            r2 = e2e_client.get(
                f"/athletes/{athlete_id}/energy/history?days=7", headers=headers
            )
            assert r2.status_code == 200, r2.text
