import json
import uuid
from datetime import date, datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.db.models import AthleteModel, ConnectorCredentialModel, SessionLogModel, TrainingPlanModel
from app.schemas.connector import HevyWorkout, HevyExercise, HevySet


_TODAY = date.today().isoformat()


def test_hevy_sync_no_credential_returns_404(authed_client):
    client, athlete_id = authed_client
    resp = client.post(f"/athletes/{athlete_id}/connectors/hevy/sync")
    assert resp.status_code == 404
    assert "Hevy" in resp.json()["detail"]


def test_hevy_sync_maps_workout_to_session_log(authed_client):
    client, athlete_id = authed_client

    # Connect Hevy first
    client.post(
        f"/athletes/{athlete_id}/connectors/hevy",
        json={"api_key": "test-key-123"},
    )

    mock_workout = HevyWorkout(
        id="hevy-w-1",
        title="Upper A",
        date=date.today(),
        duration_seconds=3600,
        exercises=[
            HevyExercise(
                name="Bench Press",
                sets=[HevySet(reps=8, weight_kg=80.0, rpe=7, set_type="normal")],
            )
        ],
    )

    with patch("app.services.sync_service.HevyConnector") as MockHevy:
        instance = MockHevy.return_value.__enter__.return_value
        instance.fetch_workouts.return_value = [mock_workout]
        resp = client.post(f"/athletes/{athlete_id}/connectors/hevy/sync")

    assert resp.status_code == 200
    body = resp.json()
    assert body["synced"] >= 0


def test_hevy_sync_wrong_athlete_returns_403(authed_client):
    client, _ = authed_client
    other_id = str(uuid.uuid4())
    resp = client.post(f"/athletes/{other_id}/connectors/hevy/sync")
    assert resp.status_code == 403


def test_terra_sync_no_credential_returns_404(authed_client):
    client, athlete_id = authed_client
    resp = client.post(f"/athletes/{athlete_id}/connectors/terra/sync")
    assert resp.status_code == 404
    assert "Terra" in resp.json()["detail"]


def test_terra_sync_with_mock(authed_client):
    client, athlete_id = authed_client

    # Connect Terra first
    client.post(
        f"/athletes/{athlete_id}/connectors/terra",
        json={"terra_user_id": "terra-user-abc"},
    )

    from app.schemas.connector import TerraHealthData
    from datetime import date as _date
    mock_data = TerraHealthData(
        date=_date.today(),
        hrv_rmssd=55.0,
        sleep_duration_hours=7.5,
        sleep_score=82,
        steps=8000,
        active_energy_kcal=450.0,
    )

    with patch("app.services.sync_service.TerraConnector") as MockTerra:
        instance = MockTerra.return_value.__enter__.return_value
        instance.fetch_daily.return_value = mock_data
        resp = client.post(f"/athletes/{athlete_id}/connectors/terra/sync")

    assert resp.status_code == 200
    body = resp.json()
    assert body["synced"] == 1
    assert body["hrv_rmssd"] == 55.0


def test_apple_health_upload(authed_client):
    client, athlete_id = authed_client
    resp = client.post(
        f"/athletes/{athlete_id}/connectors/apple-health/upload",
        json={
            "snapshot_date": "2026-04-10",
            "hrv_rmssd": 52.0,
            "sleep_hours": 7.5,
            "hr_rest": 50,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["uploaded"] is True
    assert body["hrv_rmssd"] == 52.0


def test_apple_health_upload_missing_date_returns_422(authed_client):
    client, athlete_id = authed_client
    resp = client.post(
        f"/athletes/{athlete_id}/connectors/apple-health/upload",
        json={"hrv_rmssd": 52.0},
    )
    assert resp.status_code == 422
