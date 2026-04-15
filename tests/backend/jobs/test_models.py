import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db import models as _models  # noqa: F401
from app.jobs import models as _job_models  # noqa: F401
from app.jobs.models import JobRunModel, AthleteStateSnapshotModel


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(engine)
    with Session() as session:
        yield session
    Base.metadata.drop_all(engine)


def test_job_run_model_roundtrip(db_session):
    run = JobRunModel(
        id=str(uuid.uuid4()),
        job_id="strava_sync_abc-123",
        athlete_id=None,
        job_type="strava_sync",
        status="ok",
        started_at=datetime.now(timezone.utc),
        duration_ms=1230,
        error_message=None,
    )
    db_session.add(run)
    db_session.commit()

    fetched = db_session.query(JobRunModel).first()
    assert fetched.job_id == "strava_sync_abc-123"
    assert fetched.status == "ok"
    assert fetched.duration_ms == 1230
    assert fetched.error_message is None
    assert fetched.created_at is not None


def test_athlete_state_snapshot_roundtrip(db_session):
    from app.db.models import AthleteModel
    athlete_id = str(uuid.uuid4())
    db_session.add(AthleteModel(
        id=athlete_id, name="Alice", age=30, sex="F",
        weight_kg=60.0, height_cm=168.0,
        sports_json='["running"]', primary_sport="running",
        goals_json='["run fast"]', available_days_json="[0]",
        hours_per_week=10.0, equipment_json="[]",
    ))
    db_session.commit()

    snap = AthleteStateSnapshotModel(
        id=str(uuid.uuid4()),
        athlete_id=athlete_id,
        snapshot_date=datetime.now(timezone.utc).date(),
        readiness=1.05,
        strain_json='{"quads": 45}',
    )
    db_session.add(snap)
    db_session.commit()

    fetched = db_session.query(AthleteStateSnapshotModel).first()
    assert fetched.athlete_id == athlete_id
    assert fetched.readiness == 1.05
    assert fetched.strain_json == '{"quads": 45}'
    assert fetched.created_at is not None


def test_athlete_state_snapshot_unique_constraint(db_session):
    from app.db.models import AthleteModel
    from sqlalchemy.exc import IntegrityError
    from datetime import date

    athlete_id = str(uuid.uuid4())
    db_session.add(AthleteModel(
        id=athlete_id, name="Alice", age=30, sex="F",
        weight_kg=60.0, height_cm=168.0,
        sports_json='["running"]', primary_sport="running",
        goals_json='["run fast"]', available_days_json="[0]",
        hours_per_week=10.0, equipment_json="[]",
    ))
    db_session.commit()

    today = date.today()
    db_session.add(AthleteStateSnapshotModel(
        id=str(uuid.uuid4()), athlete_id=athlete_id,
        snapshot_date=today, readiness=1.0, strain_json="{}",
    ))
    db_session.commit()

    db_session.add(AthleteStateSnapshotModel(
        id=str(uuid.uuid4()), athlete_id=athlete_id,
        snapshot_date=today, readiness=1.1, strain_json="{}",
    ))
    with pytest.raises(IntegrityError):
        db_session.commit()
