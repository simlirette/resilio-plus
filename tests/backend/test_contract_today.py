"""Contract tests — GET /athletes/{id}/today."""
from datetime import date, timedelta


def test_today_requires_auth(api_client, auth_state):
    resp = api_client.get(f"/athletes/{auth_state['athlete_id']}/today")
    assert resp.status_code == 401


def test_today_returns_200(api_client, auth_state):
    resp = api_client.get(
        f"/athletes/{auth_state['athlete_id']}/today",
        headers=auth_state["headers"],
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "date" in body
    assert "is_rest_day" in body
    assert "sessions" in body
    assert isinstance(body["sessions"], list)


def test_today_past_date_is_rest_day(api_client, auth_state):
    """A date with no plan sessions → is_rest_day=True, empty list."""
    resp = api_client.get(
        f"/athletes/{auth_state['athlete_id']}/today",
        headers=auth_state["headers"],
        params={"target_date": "2020-01-01"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_rest_day"] is True
    assert body["sessions"] == []
    assert body["date"] == "2020-01-01"


def test_today_session_fields(api_client, auth_state):
    """Sessions in response have all required schema fields."""
    # Use plan start date — guaranteed to have sessions
    plan = auth_state["plan"]
    start_date = plan["start_date"]
    resp = api_client.get(
        f"/athletes/{auth_state['athlete_id']}/today",
        headers=auth_state["headers"],
        params={"target_date": start_date},
    )
    body = resp.json()
    for session in body["sessions"]:
        assert "session_id" in session
        assert "plan_id" in session
        assert "sport" in session
        assert "workout_type" in session
        assert "duration_min" in session
        assert "fatigue_score" in session
        assert "log" in session  # None when not logged


def test_today_403_for_other_athlete(api_client, auth_state):
    resp = api_client.get(
        "/athletes/00000000-0000-0000-0000-000000000000/today",
        headers=auth_state["headers"],
    )
    assert resp.status_code == 403
