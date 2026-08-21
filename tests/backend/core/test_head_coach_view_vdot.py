"""The chat coach must see the same VDOT the planner uses.

`RunningCoach.analyze` falls back to `estimate_vdot(strava_activities)` when
`athlete.vdot` is unset, and never writes the result back. `HeadCoachView`
read the column directly, so the planner prescribed paces off an estimated
VDOT while the conversational coach was told `vdot: null` and could not
discuss them. Same athlete, same minute, two different answers.

The view now derives the estimate the same way, and labels it so the coach
can hedge: a VDOT inferred from easy runs is not a tested one.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest
from app.core.head_coach_view_builder import build_head_coach_view
from app.db.models import AthleteModel, StravaActivityModel


@pytest.fixture
def db_session():
    """Local SQLite session — tests/backend/core has no conftest of its own.

    The root `db_session` is the live-Postgres one and skips when PG is not up,
    which would make these tests silently vanish rather than run.
    """
    from app.db import models  # noqa: F401 — registers ORM models with Base
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


@pytest.fixture()
def athlete(db_session) -> AthleteModel:
    row = AthleteModel(
        id="vdot-athlete",
        name="Test",
        age=24,
        sex="M",
        weight_kg=77.0,
        height_cm=183.0,
        primary_sport="running",
        sports_json='["running"]',
        goals_json='["half marathon"]',
        available_days_json='["mon","tue","wed","thu","fri","sat","sun"]',
        equipment_json='[]',
        hours_per_week=6,
        journey_phase="steady_state",
        vdot=None,
    )
    db_session.add(row)
    db_session.commit()
    return row


def _run(db_session, athlete_id: str, days_ago: int, km: float, minutes: float) -> None:
    db_session.add(
        StravaActivityModel(
            id=f"act-{days_ago}",
            athlete_id=athlete_id,
            strava_id=f"ext-{days_ago}",
            name="Run",
            sport_type="Run",
            started_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
            duration_s=int(minutes * 60),
            distance_m=km * 1000,
        )
    )
    db_session.commit()


class TestDeclaredVdotWins:
    def test_a_stored_vdot_is_never_overwritten(self, db_session, athlete) -> None:
        athlete.vdot = 52.0
        db_session.commit()
        _run(db_session, athlete.id, days_ago=3, km=10.0, minutes=60.0)

        view = build_head_coach_view(athlete, db_session)

        assert view.vdot == 52.0
        assert view.vdot_source == "declared"


class TestEstimatedFromRuns:
    def test_recent_runs_produce_an_estimate(self, db_session, athlete) -> None:
        _run(db_session, athlete.id, days_ago=3, km=10.0, minutes=50.0)

        view = build_head_coach_view(athlete, db_session)

        assert view.vdot is not None, "planner would have estimated one; view did not"
        assert view.vdot > 0
        assert view.vdot_source == "estimated_from_recent_runs"

    def test_the_estimate_matches_what_the_planner_would_use(
        self, db_session, athlete
    ) -> None:
        from app.core.running_logic import estimate_vdot
        from app.schemas.connector import StravaActivity

        _run(db_session, athlete.id, days_ago=3, km=10.0, minutes=50.0)
        view = build_head_coach_view(athlete, db_session)

        expected = estimate_vdot(
            [
                StravaActivity(
                    id="act-3",
                    name="Run",
                    sport_type="Run",
                    date=date.today() - timedelta(days=3),
                    duration_seconds=3000,
                    distance_meters=10000.0,
                )
            ]
        )
        assert view.vdot == expected


class TestNoData:
    def test_no_runs_leaves_vdot_unset(self, db_session, athlete) -> None:
        view = build_head_coach_view(athlete, db_session)

        assert view.vdot is None
        assert view.vdot_source is None

    def test_only_stale_runs_leave_vdot_unset(self, db_session, athlete) -> None:
        """estimate_vdot only looks at the last 30 days."""
        _run(db_session, athlete.id, days_ago=200, km=10.0, minutes=50.0)

        view = build_head_coach_view(athlete, db_session)

        assert view.vdot is None
        assert view.vdot_source is None

    def test_a_lifting_only_athlete_gets_no_running_estimate(
        self, db_session, athlete
    ) -> None:
        db_session.add(
            StravaActivityModel(
                id="ride-1",
                athlete_id=athlete.id,
                strava_id="ext-ride",
                name="Ride",
                sport_type="Ride",
                started_at=datetime.now(timezone.utc) - timedelta(days=2),
                duration_s=3600,
                distance_m=30000.0,
            )
        )
        db_session.commit()

        view = build_head_coach_view(athlete, db_session)

        assert view.vdot is None


class TestDegradation:
    def test_a_broken_read_does_not_break_the_view(self, db_session, athlete) -> None:
        """A view that raises costs the athlete the whole conversation."""

        class Exploding:
            def query(self, *a, **k):
                raise RuntimeError("db gone")

        view = build_head_coach_view(athlete, Exploding())

        assert view.athlete_id == athlete.id
        assert view.vdot is None
