"""An unmeasured readiness must not read as a good one.

`compute_readiness` returns a *modifier* in [0.5, 1.5] where 1.0 means "no
adjustment". That is the right answer for the agents: with no recovery signal,
do not adjust anything.

The snapshot stored that 1.0 whether the signals were neutral or simply absent,
and `HeadCoachView` handed the number to the conversational coach under the
name `readiness` -- where 1.0 reads as *perfectly fresh*. An athlete with no HRV
device was told, in effect, that they were fully recovered. That is the worst
direction for the error to run: it is the number the coach leans on to decide
whether a hard session goes ahead.

The modifier keeps its meaning for the agents. The view now reports a readiness
only when something was actually measured.
"""
from __future__ import annotations

from datetime import date
from unittest.mock import patch

import pytest
from app.db.models import AthleteModel

ATHLETE = "66666666-6666-6666-6666-666666666666"


@pytest.fixture
def db_session():
    from app.db import models  # noqa: F401 -- registers ORM models with Base
    from app.db.database import Base
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import Session as SASession

    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )

    @event.listens_for(engine, "connect")
    def _fk(conn, _):
        cur = conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    Base.metadata.create_all(engine)
    with SASession(engine) as s:
        yield s
    Base.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def athlete(db_session) -> AthleteModel:
    row = AthleteModel(
        id=ATHLETE,
        name="Test",
        age=24,
        sex="M",
        weight_kg=77.0,
        height_cm=183.0,
        hours_per_week=8.0,
        primary_sport="running",
        sports_json='["running"]',
        goals_json="[]",
        available_days_json="[]",
        equipment_json="[]",
    )
    db_session.add(row)
    db_session.commit()
    return row


def _terra_day():
    from app.schemas.connector import TerraHealthData

    return TerraHealthData(
        date=date.today(),
        hrv_rmssd=62.0,
        sleep_duration_hours=7.5,
        resting_hr=52,
    )


def _fetch(terra):
    return patch(
        "app.jobs.compute_jobs.fetch_connector_data",
        return_value={
            "strava_activities": [],
            "hevy_workouts": [],
            "terra_health": terra,
        },
    )


def _snapshot(db_session, terra=None):
    from app.jobs.compute_jobs import snapshot_athlete

    with _fetch(terra):
        snapshot_athlete(ATHLETE, db_session)
    db_session.commit()


def _view(db_session):
    from app.core.head_coach_view_builder import build_head_coach_view

    return build_head_coach_view(db_session.get(AthleteModel, ATHLETE), db_session)


class TestWithoutRecoveryData:
    def test_the_snapshot_records_that_nothing_was_measured(self, db_session) -> None:
        from app.jobs.models import AthleteStateSnapshotModel

        _snapshot(db_session, terra=None)

        assert db_session.query(AthleteStateSnapshotModel).one().readiness_source is None

    def test_the_coach_is_not_told_the_athlete_is_fresh(self, db_session) -> None:
        _snapshot(db_session, terra=None)

        assert _view(db_session).readiness is None, (
            "an unmeasured neutral modifier was presented as a readiness score"
        )

    def test_the_agents_still_get_a_neutral_modifier(self, db_session) -> None:
        """1.0 means 'do not adjust' and stays correct where it is used as one."""
        from app.core.readiness import compute_readiness

        assert compute_readiness([]) == 1.0


class TestWithRecoveryData:
    def test_the_snapshot_records_that_it_was_measured(self, db_session) -> None:
        from app.jobs.models import AthleteStateSnapshotModel

        _snapshot(db_session, terra=_terra_day())

        assert (
            db_session.query(AthleteStateSnapshotModel).one().readiness_source
            == "measured"
        )

    def test_the_coach_sees_it(self, db_session) -> None:
        _snapshot(db_session, terra=_terra_day())

        readiness = _view(db_session).readiness
        assert readiness is not None
        assert 0.5 <= readiness <= 1.5


class TestTransitions:
    def test_getting_a_device_starts_reporting_readiness(self, db_session) -> None:
        _snapshot(db_session, terra=None)
        assert _view(db_session).readiness is None

        _snapshot(db_session, terra=_terra_day())
        assert _view(db_session).readiness is not None

    def test_losing_the_device_stops_reporting_it(self, db_session) -> None:
        """A stale reading must not be presented as current."""
        _snapshot(db_session, terra=_terra_day())
        assert _view(db_session).readiness is not None

        _snapshot(db_session, terra=None)
        assert _view(db_session).readiness is None


class TestOlderSnapshots:
    def test_a_snapshot_written_before_this_column_existed_is_not_trusted(
        self, db_session
    ) -> None:
        """Existing rows have readiness_source NULL and a 1.0 of unknown origin."""
        import json
        import uuid

        from app.jobs.models import AthleteStateSnapshotModel

        db_session.add(
            AthleteStateSnapshotModel(
                id=str(uuid.uuid4()),
                athlete_id=ATHLETE,
                snapshot_date=date.today(),
                readiness=1.0,
                strain_json=json.dumps({"quads": 10.0}),
            )
        )
        db_session.commit()

        view = _view(db_session)
        assert view.readiness is None
        assert view.muscle_strain, "strain is unaffected and must still come through"
