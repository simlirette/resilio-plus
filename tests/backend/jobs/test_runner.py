import time
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db import models as _models  # noqa: F401
from app.jobs import models as _job_models  # noqa: F401
from app.jobs.models import JobRunModel
from app.jobs.runner import run_job


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(engine)
    with Session() as session:
        yield session
    Base.metadata.drop_all(engine)


def test_run_job_success(db_session):
    fn = MagicMock(return_value={"synced": 3})

    run_job(
        job_id="strava_sync_abc",
        job_type="strava_sync",
        athlete_id="abc",
        fn=fn,
        db=db_session,
        timeout_s=60,
    )

    fn.assert_called_once()
    row = db_session.query(JobRunModel).first()
    assert row is not None
    assert row.status == "ok"
    assert row.duration_ms >= 0
    assert row.error_message is None


def test_run_job_error(db_session):
    fn = MagicMock(side_effect=ValueError("something broke"))

    run_job(
        job_id="strava_sync_abc",
        job_type="strava_sync",
        athlete_id="abc",
        fn=fn,
        db=db_session,
        timeout_s=60,
    )

    row = db_session.query(JobRunModel).first()
    assert row is not None
    assert row.status == "error"
    assert "something broke" in row.error_message


def test_run_job_timeout(db_session):
    def slow_fn():
        time.sleep(5)

    run_job(
        job_id="strava_sync_abc",
        job_type="strava_sync",
        athlete_id="abc",
        fn=slow_fn,
        db=db_session,
        timeout_s=0.2,
    )

    row = db_session.query(JobRunModel).first()
    assert row is not None
    assert row.status == "timeout"
    assert row.error_message is not None
    assert "timed out" in row.error_message


def test_run_job_truncates_long_error(db_session):
    fn = MagicMock(side_effect=ValueError("x" * 5000))

    run_job(
        job_id="test_job",
        job_type="strava_sync",
        athlete_id=None,
        fn=fn,
        db=db_session,
        timeout_s=60,
    )

    row = db_session.query(JobRunModel).first()
    assert len(row.error_message) <= 2000
