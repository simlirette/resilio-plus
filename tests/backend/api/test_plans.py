import time
from datetime import date, timedelta
from unittest.mock import ANY, patch

from tests.backend.api.conftest import athlete_payload

START = "2026-03-30"
END = "2026-04-05"
PLAN_BODY = {"start_date": START, "end_date": END}


def _create_athlete(client, **overrides):
    resp = client.post("/athletes/", json=athlete_payload(**overrides))
    assert resp.status_code == 201
    return resp.json()["id"]


def test_generate_plan_returns_201_with_sessions(client):
    athlete_id = _create_athlete(client)
    resp = client.post(f"/athletes/{athlete_id}/plan", json=PLAN_BODY)
    assert resp.status_code == 201
    body = resp.json()
    assert len(body["sessions"]) > 0
    assert body["acwr"] >= 0


def test_generate_plan_unknown_athlete_returns_404(client):
    resp = client.post("/athletes/does-not-exist/plan", json=PLAN_BODY)
    assert resp.status_code == 404


def test_get_plan_no_plan_returns_404(client):
    athlete_id = _create_athlete(client)
    resp = client.get(f"/athletes/{athlete_id}/plan")
    assert resp.status_code == 404


def test_get_plan_returns_latest(client):
    athlete_id = _create_athlete(client)
    resp1 = client.post(f"/athletes/{athlete_id}/plan", json=PLAN_BODY)
    assert resp1.status_code == 201
    first_id = resp1.json()["id"]

    time.sleep(0.01)  # ensure distinct created_at values

    resp2 = client.post(
        f"/athletes/{athlete_id}/plan",
        json={"start_date": "2026-04-07", "end_date": "2026-04-13"},
    )
    assert resp2.status_code == 201
    second_id = resp2.json()["id"]

    assert first_id != second_id

    get_resp = client.get(f"/athletes/{athlete_id}/plan")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == second_id


def test_plan_phase_matches_periodization(client):
    from app.core.periodization import get_current_phase

    target_race = (date(2026, 3, 30) + timedelta(weeks=30)).isoformat()
    athlete_id = _create_athlete(client, target_race_date=target_race)
    resp = client.post(f"/athletes/{athlete_id}/plan", json=PLAN_BODY)
    assert resp.status_code == 201

    start_date = date.fromisoformat(START)
    expected_phase = get_current_phase(
        date.fromisoformat(target_race), start_date
    ).phase.value  # PeriodizationPhase.phase.value → MacroPhase string
    assert resp.json()["phase"] == expected_phase


def test_plan_total_weekly_hours_positive(client):
    athlete_id = _create_athlete(client)
    resp = client.post(f"/athletes/{athlete_id}/plan", json=PLAN_BODY)
    assert resp.status_code == 201
    assert resp.json()["total_weekly_hours"] > 0


def test_plan_sessions_have_valid_dates(client):
    athlete_id = _create_athlete(client)
    resp = client.post(f"/athletes/{athlete_id}/plan", json=PLAN_BODY)
    assert resp.status_code == 201
    start = date.fromisoformat(START)
    end = date.fromisoformat(END)
    for session in resp.json()["sessions"]:
        session_date = date.fromisoformat(session["date"])
        assert start <= session_date <= end


def test_plan_persisted_in_db(client):
    athlete_id = _create_athlete(client)
    post_resp = client.post(f"/athletes/{athlete_id}/plan", json=PLAN_BODY)
    assert post_resp.status_code == 201
    plan_id = post_resp.json()["id"]

    get_resp = client.get(f"/athletes/{athlete_id}/plan")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == plan_id


def test_plan_route_calls_connector_service(client):
    athlete_id = _create_athlete(client)

    with patch("app.routes.plans.fetch_connector_data") as mock_fetch:
        mock_fetch.return_value = {"strava_activities": [], "hevy_workouts": []}
        resp = client.post(
            f"/athletes/{athlete_id}/plan",
            json={"start_date": "2026-04-07", "end_date": "2026-04-13"},
        )
        assert resp.status_code == 201
        mock_fetch.assert_called_once_with(athlete_id, ANY)
