"""Contract tests — POST /athletes/{id}/workouts (off-plan manual log)."""
from datetime import date


def test_post_workout_requires_auth(api_client, auth_state):
    resp = api_client.post(
        f"/athletes/{auth_state['athlete_id']}/workouts",
        json={
            "sport": "running",
            "workout_type": "Easy run",
            "date": str(date.today()),
            "actual_duration_min": 45,
        },
    )
    assert resp.status_code == 401


def test_post_workout_creates_201(api_client, auth_state):
    resp = api_client.post(
        f"/athletes/{auth_state['athlete_id']}/workouts",
        headers=auth_state["headers"],
        json={
            "sport": "running",
            "workout_type": "Easy run",
            "date": str(date.today()),
            "actual_duration_min": 45,
            "rpe": 6,
            "notes": "Bonus jog",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["session_id"].startswith("manual-")
    assert body["sport"] == "running"
    assert body["actual_duration_min"] == 45
    assert body["rpe"] == 6
    assert "logged_at" in body


def test_post_workout_session_id_is_unique(api_client, auth_state):
    """Two separate manual workouts get distinct session_ids."""
    payload = {
        "sport": "lifting",
        "workout_type": "Upper body",
        "date": str(date.today()),
        "actual_duration_min": 60,
    }
    r1 = api_client.post(
        f"/athletes/{auth_state['athlete_id']}/workouts",
        headers=auth_state["headers"],
        json=payload,
    )
    r2 = api_client.post(
        f"/athletes/{auth_state['athlete_id']}/workouts",
        headers=auth_state["headers"],
        json=payload,
    )
    assert r1.json()["session_id"] != r2.json()["session_id"]


def test_post_workout_invalid_duration_zero(api_client, auth_state):
    resp = api_client.post(
        f"/athletes/{auth_state['athlete_id']}/workouts",
        headers=auth_state["headers"],
        json={
            "sport": "running",
            "workout_type": "Easy",
            "date": str(date.today()),
            "actual_duration_min": 0,
        },
    )
    assert resp.status_code == 422


def test_post_workout_invalid_sport(api_client, auth_state):
    resp = api_client.post(
        f"/athletes/{auth_state['athlete_id']}/workouts",
        headers=auth_state["headers"],
        json={
            "sport": "hockey",
            "workout_type": "Easy",
            "date": str(date.today()),
            "actual_duration_min": 45,
        },
    )
    assert resp.status_code == 422


def test_post_workout_actual_data_stored(api_client, auth_state):
    """actual_data dict preserved in response, sport injected."""
    resp = api_client.post(
        f"/athletes/{auth_state['athlete_id']}/workouts",
        headers=auth_state["headers"],
        json={
            "sport": "running",
            "workout_type": "Long run",
            "date": str(date.today()),
            "actual_duration_min": 90,
            "actual_data": {"distance_km": 15.0},
        },
    )
    body = resp.json()
    assert body["actual_data"]["distance_km"] == 15.0
    assert body["actual_data"]["sport"] == "running"
