import json
import uuid
from datetime import date, datetime, timezone
from unittest.mock import patch, MagicMock

import pytest
from freezegun import freeze_time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.db import models as _models  # noqa: F401
from app.jobs import models as _job_models  # noqa: F401
from app.db.models import AthleteModel, ConnectorCredentialModel
from app.jobs.models import AthleteStateSnapshotModel, JobRunModel
from app.jobs.compute_jobs import run_daily_snapshot, run_energy_patterns


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(engine)
    with Session() as session:
        yield session
    Base.metadata.drop_all(engine)


def _make_athlete(db, athlete_id=None):
    aid = athlete_id or str(uuid.uuid4())
    db.add(AthleteModel(
        id=aid, name="Alice", age=30, sex="F",
        weight_kg=60.0, height_cm=168.0,
        sports_json='["running"]', primary_sport="running",
        goals_json='["run fast"]', available_days_json="[0]",
        hours_per_week=10.0, equipment_json="[]",
    ))
    db.commit()
    return aid


@patch("app.jobs.compute_jobs.fetch_connector_data")
@patch("app.jobs.compute_jobs.compute_readiness")
@patch("app.jobs.compute_jobs.compute_muscle_strain")
@patch("app.jobs.compute_jobs.SessionLocal")
def test_daily_snapshot_creates_snapshot(mock_sl, mock_strain, mock_readiness, mock_fetch, db_session):
    aid = _make_athlete(db_session)
    mock_sl.return_value.__enter__ = MagicMock(return_value=db_session)
    mock_sl.return_value.__exit__ = MagicMock(return_value=False)
    mock_fetch.return_value = {
        "strava_activities": [],
        "hevy_workouts": [],
        "terra_health": None,
    }
    mock_readiness.return_value = 1.05
    mock_strain.return_value = MagicMock()
    mock_strain.return_value.model_dump.return_value = {"quads": 45, "posterior_chain": 30}

    run_daily_snapshot()

    snap = db_session.query(AthleteStateSnapshotModel).filter_by(athlete_id=aid).first()
    assert snap is not None
    assert snap.readiness == 1.05
    assert "quads" in snap.strain_json


@patch("app.jobs.compute_jobs.fetch_connector_data")
@patch("app.jobs.compute_jobs.compute_readiness")
@patch("app.jobs.compute_jobs.compute_muscle_strain")
@patch("app.jobs.compute_jobs.SessionLocal")
def test_daily_snapshot_idempotent(mock_sl, mock_strain, mock_readiness, mock_fetch, db_session):
    aid = _make_athlete(db_session)
    mock_sl.return_value.__enter__ = MagicMock(return_value=db_session)
    mock_sl.return_value.__exit__ = MagicMock(return_value=False)
    mock_fetch.return_value = {"strava_activities": [], "hevy_workouts": [], "terra_health": None}
    mock_readiness.return_value = 1.0
    mock_strain.return_value = MagicMock()
    mock_strain.return_value.model_dump.return_value = {}

    run_daily_snapshot()
    # Second run updates, doesn't duplicate
    mock_readiness.return_value = 1.1
    run_daily_snapshot()

    snaps = db_session.query(AthleteStateSnapshotModel).filter_by(athlete_id=aid).all()
    assert len(snaps) == 1
    assert snaps[0].readiness == 1.1


@patch("app.jobs.compute_jobs.detect_energy_patterns")
@patch("app.jobs.compute_jobs.SessionLocal")
def test_energy_patterns_job_calls_detect(mock_sl, mock_detect):
    mock_db = MagicMock()
    mock_sl.return_value.__enter__ = MagicMock(return_value=mock_db)
    mock_sl.return_value.__exit__ = MagicMock(return_value=False)
    mock_detect.return_value = {"athletes_scanned": 5, "messages_created": 2}

    run_energy_patterns()

    mock_detect.assert_called_once_with(mock_db)
