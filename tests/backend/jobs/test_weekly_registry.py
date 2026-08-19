from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import MagicMock

import pytest
from app.db.models import AthleteModel
from app.jobs.registry import (
    WEEKLY_CYCLE_MISFIRE_GRACE_S,
    daily_reminder_job_id,
    register_weekly_cycle,
    restore_weekly_cycles,
    unregister_weekly_cycle,
    weekly_cycle_job_id,
)
from apscheduler.jobstores.base import JobLookupError
from sqlalchemy.orm import Session


@pytest.fixture
def db_session():
    """Local SQLite session — tests/backend/jobs has no conftest of its own."""
    from app.db import models  # noqa: F401 — registers ORM models with Base
    from app.db.database import Base
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import Session as SASession

    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )

    @event.listens_for(engine, "connect")
    def _enable_fk(dbapi_connection, _record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    with SASession(engine) as session:
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


def make_athlete(db_session: Session, **overrides: Any) -> str:
    athlete_id = str(uuid.uuid4())
    db_session.add(
        AthleteModel(
            id=athlete_id,
            name="Scheduled Athlete",
            age=30,
            sex="F",
            weight_kg=60.0,
            height_cm=168.0,
            primary_sport="running",
            hours_per_week=6.0,
            sports_json='["running"]',
            goals_json="[]",
            available_days_json="[]",
            equipment_json="[]",
            **overrides,
        )
    )
    db_session.commit()
    return athlete_id


def _kwargs_for(scheduler: MagicMock, job_id: str) -> dict[str, Any]:
    for call in scheduler.add_job.call_args_list:
        if call.kwargs.get("id") == job_id:
            return dict(call.kwargs)
    raise AssertionError(f"no job registered with id {job_id!r}")


class TestRegisterWeeklyCycle:
    def test_defaults_to_sunday_evening_in_the_athlete_timezone(
        self, db_session: Session
    ) -> None:
        athlete_id = make_athlete(db_session)
        scheduler = MagicMock()

        register_weekly_cycle(athlete_id, scheduler, db_session)

        kwargs = _kwargs_for(scheduler, weekly_cycle_job_id(athlete_id))
        assert kwargs["trigger"] == "cron"
        assert kwargs["day_of_week"] == 6
        assert kwargs["hour"] == 18
        assert kwargs["timezone"] == "America/Montreal"
        assert kwargs["kwargs"] == {"athlete_id": athlete_id}

    def test_honours_the_athletes_own_schedule_and_zone(
        self, db_session: Session
    ) -> None:
        athlete_id = make_athlete(
            db_session,
            weekly_cycle_day=2,
            weekly_cycle_hour=7,
            timezone="Europe/Paris",
        )
        scheduler = MagicMock()

        register_weekly_cycle(athlete_id, scheduler, db_session)

        kwargs = _kwargs_for(scheduler, weekly_cycle_job_id(athlete_id))
        assert (kwargs["day_of_week"], kwargs["hour"]) == (2, 7)
        assert kwargs["timezone"] == "Europe/Paris"

    def test_misfire_grace_survives_a_redeploy(self, db_session: Session) -> None:
        athlete_id = make_athlete(db_session)
        scheduler = MagicMock()

        register_weekly_cycle(athlete_id, scheduler, db_session)

        kwargs = _kwargs_for(scheduler, weekly_cycle_job_id(athlete_id))
        assert kwargs["misfire_grace_time"] == WEEKLY_CYCLE_MISFIRE_GRACE_S
        assert WEEKLY_CYCLE_MISFIRE_GRACE_S >= 7200

    def test_daily_reminder_is_registered_alongside(
        self, db_session: Session
    ) -> None:
        athlete_id = make_athlete(db_session)
        scheduler = MagicMock()

        register_weekly_cycle(athlete_id, scheduler, db_session)

        kwargs = _kwargs_for(scheduler, daily_reminder_job_id(athlete_id))
        assert (kwargs["hour"], kwargs["minute"]) == (6, 30)

    def test_re_registering_replaces_instead_of_duplicating(
        self, db_session: Session
    ) -> None:
        athlete_id = make_athlete(db_session)
        scheduler = MagicMock()

        register_weekly_cycle(athlete_id, scheduler, db_session)

        assert _kwargs_for(scheduler, weekly_cycle_job_id(athlete_id))[
            "replace_existing"
        ]

    def test_unknown_athlete_registers_nothing(self, db_session: Session) -> None:
        scheduler = MagicMock()

        register_weekly_cycle("ghost", scheduler, db_session)

        assert scheduler.add_job.call_count == 0


class TestUnregister:
    def test_removes_both_jobs(self, db_session: Session) -> None:
        athlete_id = make_athlete(db_session)
        scheduler = MagicMock()

        unregister_weekly_cycle(athlete_id, scheduler)

        removed = [call.args[0] for call in scheduler.remove_job.call_args_list]
        assert removed == [
            weekly_cycle_job_id(athlete_id),
            daily_reminder_job_id(athlete_id),
        ]

    def test_missing_job_is_not_an_error(self, db_session: Session) -> None:
        athlete_id = make_athlete(db_session)
        scheduler = MagicMock()
        scheduler.remove_job.side_effect = JobLookupError("gone")

        unregister_weekly_cycle(athlete_id, scheduler)  # must not raise


class TestRestore:
    def test_registers_every_athlete_even_without_connectors(
        self, db_session: Session
    ) -> None:
        first = make_athlete(db_session)
        second = make_athlete(db_session)
        scheduler = MagicMock()

        restore_weekly_cycles(scheduler, db_session)

        ids = {call.kwargs.get("id") for call in scheduler.add_job.call_args_list}
        assert weekly_cycle_job_id(first) in ids
        assert weekly_cycle_job_id(second) in ids

    def test_no_athletes_registers_nothing(self, db_session: Session) -> None:
        scheduler = MagicMock()
        restore_weekly_cycles(scheduler, db_session)
        assert scheduler.add_job.call_count == 0


@pytest.mark.parametrize("day", [0, 3, 6])
def test_every_weekday_is_accepted(db_session: Session, day: int) -> None:
    athlete_id = make_athlete(db_session, weekly_cycle_day=day)
    scheduler = MagicMock()

    register_weekly_cycle(athlete_id, scheduler, db_session)

    assert _kwargs_for(scheduler, weekly_cycle_job_id(athlete_id))["day_of_week"] == day
