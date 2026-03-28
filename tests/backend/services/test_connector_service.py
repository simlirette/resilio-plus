import json
import time
import uuid

import httpx
import pytest
import respx

from app.db.models import AthleteModel, ConnectorCredentialModel
from app.services.connector_service import fetch_connector_data


# ─── helpers ───────────────────────────────────────────────────────────────────

def _make_athlete(db_session):
    athlete_id = str(uuid.uuid4())
    db_session.add(AthleteModel(
        id=athlete_id, name="Alice", age=30, sex="F",
        weight_kg=60.0, height_cm=168.0, primary_sport="running",
        hours_per_week=10.0,
        sports_json='["running"]', goals_json='["run fast"]',
        available_days_json='[0,2,4]', equipment_json='[]',
    ))
    db_session.commit()
    return athlete_id


def _add_strava_cred(db_session, athlete_id, expires_at=9999999999):
    db_session.add(ConnectorCredentialModel(
        id=str(uuid.uuid4()), athlete_id=athlete_id, provider="strava",
        access_token="test_access", refresh_token="test_refresh",
        expires_at=expires_at, extra_json="{}",
    ))
    db_session.commit()


def _add_hevy_cred(db_session, athlete_id):
    db_session.add(ConnectorCredentialModel(
        id=str(uuid.uuid4()), athlete_id=athlete_id, provider="hevy",
        access_token=None, refresh_token=None, expires_at=None,
        extra_json=json.dumps({"api_key": "hevy_test_key"}),
    ))
    db_session.commit()


# ─── tests ─────────────────────────────────────────────────────────────────────

def test_fetch_no_credentials_returns_empty_lists(db_session):
    athlete_id = _make_athlete(db_session)
    result = fetch_connector_data(athlete_id, db_session)
    assert result == {"strava_activities": [], "hevy_workouts": []}


@respx.mock
def test_fetch_strava_activities_maps_to_schema(db_session):
    athlete_id = _make_athlete(db_session)
    _add_strava_cred(db_session, athlete_id)

    respx.get("https://www.strava.com/api/v3/athlete/activities").mock(
        return_value=httpx.Response(200, json=[{
            "id": 111,
            "name": "Morning Run",
            "sport_type": "Run",
            "start_date_local": "2026-03-25T07:00:00Z",
            "elapsed_time": 3600,
            "distance": 10000.0,
            "total_elevation_gain": 50.0,
            "average_heartrate": 145.0,
            "max_heartrate": 170.0,
        }])
    )

    result = fetch_connector_data(athlete_id, db_session)
    assert len(result["strava_activities"]) == 1
    act = result["strava_activities"][0]
    assert act.id == "strava_111"
    assert act.name == "Morning Run"
    assert act.duration_seconds == 3600


@respx.mock
def test_fetch_hevy_workouts_maps_to_schema(db_session):
    athlete_id = _make_athlete(db_session)
    _add_hevy_cred(db_session, athlete_id)

    respx.get("https://api.hevyapp.com/v1/workouts").mock(
        return_value=httpx.Response(200, json={
            "page": 1, "page_count": 1,
            "workouts": [{
                "id": "w1",
                "title": "Push Day",
                "start_time": "2026-03-25T08:00:00Z",
                "end_time": "2026-03-25T09:00:00Z",
                "exercises": [],
            }]
        })
    )

    result = fetch_connector_data(athlete_id, db_session)
    assert len(result["hevy_workouts"]) == 1
    w = result["hevy_workouts"][0]
    assert w.id == "w1"
    assert w.title == "Push Day"
    assert w.duration_seconds == 3600


@respx.mock
def test_strava_token_refresh_on_expiry_persisted_to_db(db_session):
    athlete_id = _make_athlete(db_session)
    expired_at = int(time.time()) - 10
    _add_strava_cred(db_session, athlete_id, expires_at=expired_at)

    respx.post("https://www.strava.com/oauth/token").mock(
        return_value=httpx.Response(200, json={
            "access_token": "new_access", "refresh_token": "new_refresh",
            "expires_at": 9999999999,
        })
    )
    respx.get("https://www.strava.com/api/v3/athlete/activities").mock(
        return_value=httpx.Response(200, json=[])
    )

    fetch_connector_data(athlete_id, db_session)

    db_session.expire_all()
    cred = db_session.query(ConnectorCredentialModel).filter_by(
        athlete_id=athlete_id, provider="strava"
    ).first()
    assert cred.access_token == "new_access"
    assert cred.expires_at == 9999999999


def test_fetch_strava_network_error_returns_empty(db_session):
    """A ConnectorError during fetch returns [] without raising."""
    athlete_id = _make_athlete(db_session)
    _add_strava_cred(db_session, athlete_id)

    with respx.mock:
        respx.get("https://www.strava.com/api/v3/athlete/activities").mock(
            side_effect=httpx.ConnectError("timeout")
        )
        result = fetch_connector_data(athlete_id, db_session)

    assert result["strava_activities"] == []
    assert result["hevy_workouts"] == []  # Hevy had no cred, also empty


def test_fetch_hevy_network_error_returns_empty(db_session):
    """A network error during Hevy fetch returns [] without raising."""
    athlete_id = _make_athlete(db_session)
    _add_hevy_cred(db_session, athlete_id)

    with respx.mock:
        respx.get("https://api.hevyapp.com/v1/workouts").mock(
            side_effect=httpx.ConnectError("timeout")
        )
        result = fetch_connector_data(athlete_id, db_session)

    assert result["hevy_workouts"] == []
    assert result["strava_activities"] == []  # no Strava cred, also empty
