"""The daily snapshot must actually be writable.

`snapshot_athlete` did ``json.dumps(strain.model_dump())``. `MuscleStrainScore`
carries a `computed_at: datetime`, and `model_dump()` leaves it as a datetime
object, which stdlib json refuses. So the job raised `TypeError` on every
athlete who had any training data at all -- and silently succeeded for anyone
with none, because `compute_muscle_strain` returns None there and the branch
was never reached.

Measured on the live database on 2026-08-20: `athlete_state_snapshots` held
**zero rows** after weeks of scheduled runs. Downstream, `HeadCoachView.
readiness` and `.muscle_strain` are read off the newest snapshot, so the
conversational coach never saw either.

The reader already skips non-numeric values, so serialising `computed_at` as a
string costs nothing.
"""
from __future__ import annotations

import json
from datetime import date
from unittest.mock import patch

import pytest
from app.schemas.connector import HevyExercise, HevySet, HevyWorkout


@pytest.fixture
def db_session():
    """Local SQLite session -- tests/backend/jobs has no conftest of its own."""
    from app.db import models  # noqa: F401 -- registers ORM models with Base
    from app.db.database import Base
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import Session as SASession

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _enable_fk(dbapi_connection, _record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    with SASession(engine) as session:
        yield session
    Base.metadata.drop_all(engine)


ATHLETE = "55555555-5555-5555-5555-555555555555"


@pytest.fixture(autouse=True)
def _athlete(db_session):
    from app.db.models import AthleteModel

    db_session.add(
        AthleteModel(
            id=ATHLETE,
            name="Test",
            age=24,
            sex="M",
            weight_kg=77.0,
            height_cm=183.0,
            hours_per_week=8.0,
            primary_sport="running",
            sports_json='["running", "lifting"]',
            goals_json="[]",
            available_days_json="[]",
            equipment_json="[]",
        )
    )
    db_session.commit()


def _workout() -> HevyWorkout:
    return HevyWorkout(
        id="w1",
        title="Arms",
        date=date.today(),
        duration_seconds=3600,
        exercises=[
            HevyExercise(
                name="Barbell Curl",
                sets=[HevySet(reps=10, weight_kg=30.0, rpe=8.0, set_type="normal")],
            )
        ],
    )


def _with_data():
    """Patch the connector fetch so strain is non-None."""
    return patch(
        "app.jobs.compute_jobs.fetch_connector_data",
        return_value={
            "strava_activities": [],
            "hevy_workouts": [_workout()],
            "terra_health": None,
        },
    )


class TestSnapshotIsWritable:
    def test_an_athlete_with_training_data_gets_a_row(self, db_session) -> None:
        from app.jobs.compute_jobs import snapshot_athlete
        from app.jobs.models import AthleteStateSnapshotModel

        with _with_data():
            snapshot_athlete(ATHLETE, db_session)
        db_session.commit()

        rows = db_session.query(AthleteStateSnapshotModel).all()
        assert len(rows) == 1, "the daily snapshot wrote nothing"

    def test_the_stored_strain_is_valid_json(self, db_session) -> None:
        from app.jobs.compute_jobs import snapshot_athlete
        from app.jobs.models import AthleteStateSnapshotModel

        with _with_data():
            snapshot_athlete(ATHLETE, db_session)
        db_session.commit()

        row = db_session.query(AthleteStateSnapshotModel).one()
        parsed = json.loads(row.strain_json)
        assert isinstance(parsed, dict)
        assert "biceps" in parsed

    def test_computed_at_survives_as_a_string(self, db_session) -> None:
        from app.jobs.compute_jobs import snapshot_athlete
        from app.jobs.models import AthleteStateSnapshotModel

        with _with_data():
            snapshot_athlete(ATHLETE, db_session)
        db_session.commit()

        parsed = json.loads(db_session.query(AthleteStateSnapshotModel).one().strain_json)
        assert isinstance(parsed.get("computed_at"), str)


class TestTheCoachCanReadItBack:
    def test_muscle_strain_reaches_the_view(self, db_session) -> None:
        from app.core.head_coach_view_builder import build_head_coach_view
        from app.db.models import AthleteModel
        from app.jobs.compute_jobs import snapshot_athlete

        with _with_data():
            snapshot_athlete(ATHLETE, db_session)
        db_session.commit()

        view = build_head_coach_view(db_session.get(AthleteModel, ATHLETE), db_session)

        assert view.muscle_strain, "the coach still sees no strain"
        assert "computed_at" not in view.muscle_strain, "a timestamp leaked in as a muscle"
        assert all(isinstance(v, float) for v in view.muscle_strain.values())


class TestNoDataStillWorks:
    def test_an_athlete_with_nothing_still_gets_a_snapshot(self, db_session) -> None:
        """The path that used to "pass" -- it must keep working."""
        from app.jobs.compute_jobs import snapshot_athlete
        from app.jobs.models import AthleteStateSnapshotModel

        with patch(
            "app.jobs.compute_jobs.fetch_connector_data",
            return_value={
                "strava_activities": [],
                "hevy_workouts": [],
                "terra_health": None,
            },
        ):
            snapshot_athlete(ATHLETE, db_session)
        db_session.commit()

        assert db_session.query(AthleteStateSnapshotModel).count() == 1

    def test_a_second_run_the_same_day_updates_rather_than_duplicates(
        self, db_session
    ) -> None:
        from app.jobs.compute_jobs import snapshot_athlete
        from app.jobs.models import AthleteStateSnapshotModel

        with _with_data():
            snapshot_athlete(ATHLETE, db_session)
            db_session.commit()
            snapshot_athlete(ATHLETE, db_session)
            db_session.commit()

        assert db_session.query(AthleteStateSnapshotModel).count() == 1
