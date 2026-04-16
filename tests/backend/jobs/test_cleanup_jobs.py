import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

import pytest
from freezegun import freeze_time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db import models as _models  # noqa: F401
from app.jobs import models as _job_models  # noqa: F401
from app.jobs.models import JobRunModel
from app.jobs.cleanup_jobs import _cleanup_old_runs, RETENTION_DAYS


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(engine)
    with Session() as session:
        yield session
    Base.metadata.drop_all(engine)


def _add_run(db, days_ago: int):
    ts = datetime.now(timezone.utc) - timedelta(days=days_ago)
    db.add(JobRunModel(
        id=str(uuid.uuid4()),
        job_id="test_job",
        job_type="strava_sync",
        status="ok",
        started_at=ts,
        duration_ms=100,
        created_at=ts,
    ))
    db.commit()


def test_cleanup_deletes_old_runs(db_session):
    _add_run(db_session, days_ago=31)  # should be deleted
    _add_run(db_session, days_ago=35)  # should be deleted
    _add_run(db_session, days_ago=5)   # should be kept

    deleted = _cleanup_old_runs(db_session)

    assert deleted == 2
    remaining = db_session.query(JobRunModel).count()
    assert remaining == 1


def test_cleanup_keeps_recent_runs(db_session):
    _add_run(db_session, days_ago=1)
    _add_run(db_session, days_ago=15)
    _add_run(db_session, days_ago=29)

    deleted = _cleanup_old_runs(db_session)

    assert deleted == 0
    remaining = db_session.query(JobRunModel).count()
    assert remaining == 3
