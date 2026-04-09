import time
from datetime import date, timedelta
from unittest.mock import ANY, patch

PLAN_BODY = {"start_date": "2026-03-30", "end_date": "2026-04-05"}


def test_generate_plan_returns_201_with_sessions(authed_client):
    c, athlete_id = authed_client
    resp = c.post(f"/athletes/{athlete_id}/plan", json=PLAN_BODY)
    assert resp.status_code == 201
    body = resp.json()
    assert len(body["sessions"]) > 0
    assert body["acwr"] >= 0


def test_generate_plan_wrong_athlete_returns_403(authed_client):
    c, _ = authed_client
    resp = c.post("/athletes/does-not-exist/plan", json=PLAN_BODY)
    assert resp.status_code == 403


def test_get_plan_returns_200_after_onboarding(authed_client):
    c, athlete_id = authed_client
    resp = c.get(f"/athletes/{athlete_id}/plan")
    assert resp.status_code == 200


def test_get_plan_returns_latest(authed_client):
    c, athlete_id = authed_client
    first_id = c.get(f"/athletes/{athlete_id}/plan").json()["id"]

    time.sleep(0.01)
    resp2 = c.post(
        f"/athletes/{athlete_id}/plan",
        json={"start_date": "2026-04-07", "end_date": "2026-04-13"},
    )
    assert resp2.status_code == 201
    second_id = resp2.json()["id"]
    assert first_id != second_id

    get_resp = c.get(f"/athletes/{athlete_id}/plan")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == second_id


def test_plan_phase_matches_periodization(authed_client):
    from app.core.periodization import get_current_phase

    c, athlete_id = authed_client
    target_race = (date(2026, 3, 30) + timedelta(weeks=30)).isoformat()
    c.put(f"/athletes/{athlete_id}", json={"target_race_date": target_race})

    resp = c.post(f"/athletes/{athlete_id}/plan", json=PLAN_BODY)
    assert resp.status_code == 201

    start_date = date.fromisoformat("2026-03-30")
    expected_phase = get_current_phase(
        date.fromisoformat(target_race), start_date
    ).phase.value
    assert resp.json()["phase"] == expected_phase


def test_plan_total_weekly_hours_positive(authed_client):
    c, athlete_id = authed_client
    resp = c.post(f"/athletes/{athlete_id}/plan", json=PLAN_BODY)
    assert resp.status_code == 201
    assert resp.json()["total_weekly_hours"] > 0


def test_plan_sessions_have_valid_dates(authed_client):
    c, athlete_id = authed_client
    resp = c.post(f"/athletes/{athlete_id}/plan", json=PLAN_BODY)
    assert resp.status_code == 201
    start = date.fromisoformat("2026-03-30")
    end = date.fromisoformat("2026-04-05")
    for session in resp.json()["sessions"]:
        session_date = date.fromisoformat(session["date"])
        assert start <= session_date <= end


def test_plan_persisted_in_db(authed_client):
    c, athlete_id = authed_client
    post_resp = c.post(f"/athletes/{athlete_id}/plan", json=PLAN_BODY)
    assert post_resp.status_code == 201
    plan_id = post_resp.json()["id"]

    get_resp = c.get(f"/athletes/{athlete_id}/plan")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == plan_id


def test_plan_route_calls_connector_service(authed_client):
    c, athlete_id = authed_client

    with patch("app.routes.plans.fetch_connector_data") as mock_fetch:
        mock_fetch.return_value = {"strava_activities": [], "hevy_workouts": []}
        resp = c.post(
            f"/athletes/{athlete_id}/plan",
            json={"start_date": "2026-04-07", "end_date": "2026-04-13"},
        )
        assert resp.status_code == 201
        mock_fetch.assert_called_once_with(athlete_id, ANY)


def test_plan_without_token_returns_401(client):
    from tests.backend.api.conftest import athlete_payload
    create_resp = client.post("/athletes/", json=athlete_payload())
    athlete_id = create_resp.json()["id"]
    resp = client.post(f"/athletes/{athlete_id}/plan", json=PLAN_BODY)
    assert resp.status_code == 401
