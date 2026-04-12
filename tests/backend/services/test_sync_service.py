"""Tests for SyncService — centralized sync logic for all connectors."""
import json
import uuid
from datetime import date
from unittest.mock import patch

import pytest

from app.db.models import ConnectorCredentialModel, SessionLogModel, TrainingPlanModel
from app.db.models import AthleteModel
from app.services.sync_service import ConnectorNotFoundError, SyncService
from app.schemas.connector import HevyExercise, HevySet, HevyWorkout, StravaActivity, TerraHealthData

_ATHLETE_ID = str(uuid.uuid4())


def _make_athlete(db):
    a = AthleteModel(
        id=_ATHLETE_ID, name="Test", age=30, sex="M", weight_kg=70.0, height_cm=175.0,
        primary_sport="running", hours_per_week=6.0,
        sports_json='["running"]', goals_json='["run 10k"]',
        available_days_json='["monday"]', equipment_json='[]',
    )
    db.add(a)
    db.commit()
    return a


def _make_plan(db, sessions_json: str = "[]"):
    p = TrainingPlanModel(
        id=str(uuid.uuid4()), athlete_id=_ATHLETE_ID,
        start_date=date.today(), end_date=date.today(),
        phase="base", total_weekly_hours=6.0, acwr=1.0,
        weekly_slots_json=sessions_json,
    )
    db.add(p)
    db.commit()
    return p


def _make_cred(db, provider: str, extra: dict | None = None):
    c = ConnectorCredentialModel(
        id=str(uuid.uuid4()), athlete_id=_ATHLETE_ID, provider=provider,
        extra_json=json.dumps(extra or {}),
    )
    db.add(c)
    db.commit()
    return c


# ── sync_strava ────────────────────────────────────────────────────────────────

def test_sync_strava_raises_if_not_connected(db_session):
    _make_athlete(db_session)
    with pytest.raises(ConnectorNotFoundError):
        SyncService.sync_strava(_ATHLETE_ID, db_session)


def test_sync_strava_maps_activity_to_session_log(db_session):
    _make_athlete(db_session)
    today = date.today().isoformat()
    _make_plan(db_session, json.dumps([
        {"id": "s1", "date": today, "sport": "running", "workout_type": "easy_z1", "duration_min": 60}
    ]))
    cred = _make_cred(db_session, "strava")
    cred.access_token = "tok"
    cred.refresh_token = "ref"
    db_session.commit()

    mock_activity = StravaActivity(
        id="strava_123", name="Morning Run", sport_type="Run",
        date=date.today(), duration_seconds=3600,
        distance_meters=10000.0, elevation_gain_meters=50.0,
        average_hr=145.0, max_hr=165.0, perceived_exertion=None,
    )

    with patch("app.services.sync_service.StravaConnector") as MockStrava:
        instance = MockStrava.return_value.__enter__.return_value
        instance.fetch_activities.return_value = [mock_activity]
        instance.credential.access_token = "tok"
        result = SyncService.sync_strava(_ATHLETE_ID, db_session)

    assert result["synced"] == 1
    assert result["skipped"] == 0
    log = db_session.query(SessionLogModel).filter_by(athlete_id=_ATHLETE_ID, session_id="s1").first()
    assert log is not None
    assert log.actual_duration_min == 60
    data = json.loads(log.actual_data_json)
    assert data["source"] == "strava"
    assert data["strava_activity_id"] == "strava_123"


def test_sync_strava_updates_last_sync(db_session):
    _make_athlete(db_session)
    _make_plan(db_session)
    cred = _make_cred(db_session, "strava")
    cred.access_token = "tok"
    cred.refresh_token = "ref"
    db_session.commit()

    with patch("app.services.sync_service.StravaConnector") as MockStrava:
        instance = MockStrava.return_value.__enter__.return_value
        instance.fetch_activities.return_value = []
        instance.credential.access_token = "tok"
        SyncService.sync_strava(_ATHLETE_ID, db_session)

    db_session.refresh(cred)
    extra = json.loads(cred.extra_json)
    assert "last_sync" in extra


def test_sync_strava_persists_refreshed_token(db_session):
    _make_athlete(db_session)
    _make_plan(db_session)
    cred = _make_cred(db_session, "strava")
    cred.access_token = "old_tok"
    cred.refresh_token = "old_ref"
    db_session.commit()

    with patch("app.services.sync_service.StravaConnector") as MockStrava:
        instance = MockStrava.return_value.__enter__.return_value
        instance.fetch_activities.return_value = []
        instance.credential.access_token = "new_tok"
        instance.credential.refresh_token = "new_ref"
        instance.credential.expires_at = 9999999999
        SyncService.sync_strava(_ATHLETE_ID, db_session)

    db_session.refresh(cred)
    assert cred.access_token == "new_tok"
    assert cred.refresh_token == "new_ref"


def test_sync_strava_returns_zero_when_no_plan(db_session):
    _make_athlete(db_session)
    cred = _make_cred(db_session, "strava")
    cred.access_token = "tok"
    cred.refresh_token = "ref"
    db_session.commit()

    mock_activity = StravaActivity(
        id="strava_1", name="Run", sport_type="Run", date=date.today(),
        duration_seconds=3600, distance_meters=10000.0,
        elevation_gain_meters=None, average_hr=None, max_hr=None, perceived_exertion=None,
    )

    with patch("app.services.sync_service.StravaConnector") as MockStrava:
        instance = MockStrava.return_value.__enter__.return_value
        instance.fetch_activities.return_value = [mock_activity]
        instance.credential.access_token = "tok"
        result = SyncService.sync_strava(_ATHLETE_ID, db_session)

    assert result["synced"] == 0
    assert "reason" in result


# ── sync_hevy ──────────────────────────────────────────────────────────────────

def test_sync_hevy_raises_if_not_connected(db_session):
    _make_athlete(db_session)
    with pytest.raises(ConnectorNotFoundError):
        SyncService.sync_hevy(_ATHLETE_ID, db_session)


def test_sync_hevy_maps_workout_to_session_log(db_session):
    _make_athlete(db_session)
    today = date.today().isoformat()
    _make_plan(db_session, json.dumps([
        {"id": "s2", "date": today, "sport": "lifting", "workout_type": "strength", "duration_min": 60}
    ]))
    _make_cred(db_session, "hevy", {"api_key": "test-key"})

    mock_workout = HevyWorkout(
        id="hevy-1", title="Upper A", date=date.today(), duration_seconds=3600,
        exercises=[HevyExercise(
            name="Bench Press",
            sets=[HevySet(reps=8, weight_kg=80.0, rpe=7, set_type="normal")]
        )]
    )

    with patch("app.services.sync_service.HevyConnector") as MockHevy:
        instance = MockHevy.return_value.__enter__.return_value
        instance.fetch_workouts.return_value = [mock_workout]
        result = SyncService.sync_hevy(_ATHLETE_ID, db_session)

    assert result["synced"] == 1
    log = db_session.query(SessionLogModel).filter_by(athlete_id=_ATHLETE_ID, session_id="s2").first()
    assert log is not None
    assert log.actual_duration_min == 60
    data = json.loads(log.actual_data_json)
    assert data["source"] == "hevy"
    assert data["exercises"][0]["name"] == "Bench Press"
    assert data["exercises"][0]["sets"][0]["weight_kg"] == 80.0


def test_sync_hevy_updates_last_sync(db_session):
    _make_athlete(db_session)
    _make_plan(db_session)
    cred = _make_cred(db_session, "hevy", {"api_key": "test-key"})

    with patch("app.services.sync_service.HevyConnector") as MockHevy:
        instance = MockHevy.return_value.__enter__.return_value
        instance.fetch_workouts.return_value = []
        SyncService.sync_hevy(_ATHLETE_ID, db_session)

    db_session.refresh(cred)
    extra = json.loads(cred.extra_json)
    assert "last_sync" in extra


# ── sync_terra ─────────────────────────────────────────────────────────────────

def test_sync_terra_raises_if_not_connected(db_session):
    _make_athlete(db_session)
    with pytest.raises(ConnectorNotFoundError):
        SyncService.sync_terra(_ATHLETE_ID, db_session)


def test_sync_terra_stores_hrv_in_extra_json(db_session):
    _make_athlete(db_session)
    cred = _make_cred(db_session, "terra", {"terra_user_id": "uid-abc"})

    mock_data = TerraHealthData(
        date=date.today(), hrv_rmssd=52.0, sleep_duration_hours=7.5,
        sleep_score=80, steps=8000, active_energy_kcal=400.0,
    )

    with patch("app.services.sync_service.TerraConnector") as MockTerra:
        instance = MockTerra.return_value.__enter__.return_value
        instance.fetch_daily.return_value = mock_data
        result = SyncService.sync_terra(_ATHLETE_ID, db_session)

    assert result["synced"] == 1
    assert result["hrv_rmssd"] == 52.0
    assert result["sleep_hours"] == 7.5
    db_session.refresh(cred)
    extra = json.loads(cred.extra_json)
    assert extra["last_hrv_rmssd"] == 52.0
    assert extra["last_sleep_hours"] == 7.5
    assert "last_sync" in extra


def test_sync_terra_updates_last_sync_even_with_null_values(db_session):
    _make_athlete(db_session)
    cred = _make_cred(db_session, "terra", {"terra_user_id": "uid-abc"})

    mock_data = TerraHealthData(
        date=date.today(), hrv_rmssd=None, sleep_duration_hours=None,
        sleep_score=None, steps=None, active_energy_kcal=None,
    )

    with patch("app.services.sync_service.TerraConnector") as MockTerra:
        instance = MockTerra.return_value.__enter__.return_value
        instance.fetch_daily.return_value = mock_data
        SyncService.sync_terra(_ATHLETE_ID, db_session)

    db_session.refresh(cred)
    extra = json.loads(cred.extra_json)
    assert "last_sync" in extra
