"""The weekly cycle looks back before it looks forward.

Step 5 of the goal document: "Once a week, coach AI is doing a follow up,
taking the data from the last completed week and making a short statement for
the athlete."

The cycle synced providers, computed a snapshot and generated a new week. It
never compared the week that just ended to what had been planned, so the
athlete got a fresh plan with no acknowledgement that they had missed two
sessions or run 14 km when the plan said 8. That is a scheduler, not a coach.

The statement is written by the coach from adherence facts. It is not a
template: a real coach says something different to an athlete who did every
session than to one who did none, and neither sentence can be pre-written.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.db.models import AthleteModel, TrainingPlanModel

ATHLETE = "review-1"
LAST_MONDAY = date.today() - timedelta(days=7)


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


@pytest.fixture
def athlete(db_session) -> AthleteModel:
    row = AthleteModel(
        id=ATHLETE,
        name="Simon",
        age=24,
        sex="M",
        weight_kg=77.1,
        height_cm=182.9,
        hours_per_week=8.0,
        primary_sport="running",
        sports_json='["running"]',
        goals_json='["semi"]',
        available_days_json="[]",
        equipment_json="[]",
    )
    db_session.add(row)
    db_session.commit()
    return row


def _plan(db_session, slots: list[dict]) -> None:
    db_session.add(
        TrainingPlanModel(
            id="p1",
            athlete_id=ATHLETE,
            start_date=LAST_MONDAY,
            end_date=LAST_MONDAY + timedelta(days=6),
            phase="competition",
            total_weekly_hours=8.0,
            acwr=1.0,
            weekly_slots_json=json.dumps(slots),
        )
    )
    db_session.commit()


def _slot(offset: int, sport: str = "running", minutes: int = 45) -> dict:
    return {
        "date": (LAST_MONDAY + timedelta(days=offset)).isoformat(),
        "sport": sport,
        "workout_type": "easy_z1",
        "duration_min": minutes,
    }


class TestTheFactsAreGathered:
    def test_the_completed_week_is_compared_to_the_plan(
        self, db_session, athlete
    ) -> None:
        from app.jobs.weekly_review import gather_week

        _plan(db_session, [_slot(0), _slot(2)])

        with patch(
            "app.jobs.weekly_review._completed", return_value=[]
        ):
            comparison = gather_week(ATHLETE, db_session)

        assert comparison is not None
        assert comparison.missed == 2

    def test_no_plan_means_nothing_to_review(self, db_session, athlete) -> None:
        from app.jobs.weekly_review import gather_week

        assert gather_week(ATHLETE, db_session) is None

    def test_only_the_week_that_ended_is_considered(
        self, db_session, athlete
    ) -> None:
        """A slot for the week ahead has not happened yet."""
        from app.jobs.weekly_review import gather_week

        _plan(db_session, [_slot(0), _slot(20)])

        with patch("app.jobs.weekly_review._completed", return_value=[]):
            comparison = gather_week(ATHLETE, db_session)

        assert comparison is not None
        assert len(comparison.outcomes) == 1


class TestTheStatement:
    def test_it_is_written_by_the_coach_not_templated(
        self, db_session, athlete
    ) -> None:
        from app.jobs.weekly_review import write_statement

        _plan(db_session, [_slot(0)])

        turn = MagicMock()
        turn.reply = "Deux séances manquées mardi et jeudi."
        turn.ok = True
        turn.tools_used = []

        with (
            patch("app.jobs.weekly_review._completed", return_value=[]),
            patch("app.jobs.weekly_review.run_coach_turn", return_value=turn) as coach,
        ):
            statement = write_statement(ATHLETE, db_session)

        assert coach.called
        assert statement == "Deux séances manquées mardi et jeudi."

    def test_the_facts_reach_the_coach(self, db_session, athlete) -> None:
        from app.jobs.weekly_review import write_statement

        _plan(db_session, [_slot(0)])
        turn = MagicMock(reply="ok", ok=True, tools_used=[])

        with (
            patch("app.jobs.weekly_review._completed", return_value=[]),
            patch("app.jobs.weekly_review.run_coach_turn", return_value=turn) as coach,
        ):
            write_statement(ATHLETE, db_session)

        sent = coach.call_args.kwargs["user_message"]
        assert "non faite" in sent

    def test_a_week_that_went_to_plan_says_nothing(
        self, db_session, athlete
    ) -> None:
        """Silence beats a weekly "well done" nobody reads."""
        from app.jobs.weekly_review import write_statement

        _plan(db_session, [_slot(0)])
        done = [
            {
                "date": LAST_MONDAY,
                "sport": "running",
                "duration_min": 45,
            }
        ]

        with (
            patch("app.jobs.weekly_review._completed", return_value=done),
            patch("app.jobs.weekly_review.run_coach_turn") as coach,
        ):
            statement = write_statement(ATHLETE, db_session)

        assert statement is None
        assert not coach.called

    def test_nothing_to_review_says_nothing(self, db_session, athlete) -> None:
        from app.jobs.weekly_review import write_statement

        assert write_statement(ATHLETE, db_session) is None

    def test_a_coach_failure_does_not_sink_the_cycle(
        self, db_session, athlete
    ) -> None:
        """The plan still has to go out even if the statement cannot be written."""
        from app.jobs.weekly_review import write_statement

        _plan(db_session, [_slot(0)])

        with (
            patch("app.jobs.weekly_review._completed", return_value=[]),
            patch(
                "app.jobs.weekly_review.run_coach_turn",
                side_effect=RuntimeError("api down"),
            ),
        ):
            assert write_statement(ATHLETE, db_session) is None


class TestItRunsBeforeTheNewWeek:
    def test_the_cycle_reviews_then_plans(self) -> None:
        """Order matters: the athlete reads what happened, then what is next."""
        import inspect

        from app.jobs import weekly_jobs

        source = inspect.getsource(weekly_jobs.run_weekly_cycle_now)
        assert "write_statement" in source

        review_at = source.index("write_statement")
        generate_at = source.index("_generate_week")
        assert review_at < generate_at, "the plan is built before the look back"
