"""Tests for connector_service.fetch_connector_data — Terra health data."""
import json
import uuid
from datetime import date
from unittest.mock import patch

from app.db.models import AthleteModel, ConnectorCredentialModel
from app.schemas.connector import TerraHealthData
from app.services.connector_service import fetch_connector_data


def _make_athlete(db_session):
    athlete_id = str(uuid.uuid4())
    db_session.add(AthleteModel(
        id=athlete_id, name="Bob", age=28, sex="M",
        weight_kg=75.0, height_cm=180.0, primary_sport="running",
        hours_per_week=8.0,
        sports_json='["running"]', goals_json='["run fast"]',
        available_days_json='[0,2,4]', equipment_json='[]',
    ))
    db_session.commit()
    return athlete_id


def _add_terra_cred(db_session, athlete_id, extra=None):
    cred = ConnectorCredentialModel(
        id=str(uuid.uuid4()),
        athlete_id=athlete_id,
        provider="terra",
        extra_json=json.dumps(extra or {"terra_user_id": "uid-abc",
                                        "last_hrv_rmssd": 52.0,
                                        "last_sleep_hours": 7.5,
                                        "last_sleep_score": 80}),
    )
    db_session.add(cred)
    db_session.commit()
    return cred


def test_fetch_connector_data_includes_terra_health_key(db_session):
    """fetch_connector_data must return terra_health key."""
    athlete_id = _make_athlete(db_session)
    result = fetch_connector_data(athlete_id, db_session)
    assert "terra_health" in result


def test_fetch_connector_data_terra_health_none_when_not_connected(db_session):
    """terra_health is None when no Terra credential exists."""
    athlete_id = _make_athlete(db_session)
    result = fetch_connector_data(athlete_id, db_session)
    assert result["terra_health"] is None


def test_fetch_connector_data_terra_health_from_extra_json(db_session):
    """terra_health reads cached HRV/sleep from extra_json without live API call."""
    athlete_id = _make_athlete(db_session)
    _add_terra_cred(db_session, athlete_id, extra={
        "terra_user_id": "uid-abc",
        "last_hrv_rmssd": 55.0,
        "last_sleep_hours": 8.0,
        "last_sleep_score": 85,
    })

    result = fetch_connector_data(athlete_id, db_session)
    terra = result["terra_health"]
    assert terra is not None
    assert terra.hrv_rmssd == 55.0
    assert terra.sleep_duration_hours == 8.0
    assert terra.sleep_score == 85


def test_fetch_connector_data_terra_health_none_values_when_extra_empty(db_session):
    """terra_health has None fields when extra_json has no cached values."""
    athlete_id = _make_athlete(db_session)
    _add_terra_cred(db_session, athlete_id, extra={"terra_user_id": "uid-abc"})

    result = fetch_connector_data(athlete_id, db_session)
    terra = result["terra_health"]
    assert terra is not None
    assert terra.hrv_rmssd is None
    assert terra.sleep_duration_hours is None
