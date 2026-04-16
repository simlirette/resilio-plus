import uuid
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db import models as _models  # noqa: F401
from app.jobs import models as _job_models  # noqa: F401
from app.db.models import AthleteModel, ConnectorCredentialModel
from app.jobs.registry import register_athlete_jobs, unregister_athlete_jobs, restore_all_jobs


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
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


def test_register_athlete_jobs_adds_to_scheduler():
    scheduler = MagicMock()
    register_athlete_jobs("abc-123", "strava", scheduler)
    scheduler.add_job.assert_called_once()
    args, kwargs = scheduler.add_job.call_args
    assert kwargs["id"] == "strava_sync_abc-123"
    assert kwargs["replace_existing"] is True


def test_unregister_athlete_jobs_removes_from_scheduler():
    scheduler = MagicMock()
    unregister_athlete_jobs("abc-123", "strava", scheduler)
    scheduler.remove_job.assert_called_once_with("strava_sync_abc-123")


def test_unregister_ignores_missing_job():
    from apscheduler.jobstores.base import JobLookupError
    scheduler = MagicMock()
    scheduler.remove_job.side_effect = JobLookupError("strava_sync_abc-123")
    # Should not raise
    unregister_athlete_jobs("abc-123", "strava", scheduler)


def test_restore_all_jobs_registers_all_connected(db_session):
    aid1 = _make_athlete(db_session)
    aid2 = _make_athlete(db_session)
    # aid1 has strava + hevy
    db_session.add(ConnectorCredentialModel(
        id=str(uuid.uuid4()), athlete_id=aid1, provider="strava", extra_json="{}",
    ))
    db_session.add(ConnectorCredentialModel(
        id=str(uuid.uuid4()), athlete_id=aid1, provider="hevy", extra_json="{}",
    ))
    # aid2 has terra
    db_session.add(ConnectorCredentialModel(
        id=str(uuid.uuid4()), athlete_id=aid2, provider="terra", extra_json="{}",
    ))
    db_session.commit()

    scheduler = MagicMock()
    restore_all_jobs(scheduler, db_session)

    assert scheduler.add_job.call_count == 3
    job_ids = {c.kwargs["id"] for c in scheduler.add_job.call_args_list}
    assert f"strava_sync_{aid1}" in job_ids
    assert f"hevy_sync_{aid1}" in job_ids
    assert f"terra_sync_{aid2}" in job_ids
