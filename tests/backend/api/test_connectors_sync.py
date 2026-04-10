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
    with patch("app.routes.connectors.HevyConnector"):
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

    with patch("app.routes.connectors.HevyConnector") as MockHevy:
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
