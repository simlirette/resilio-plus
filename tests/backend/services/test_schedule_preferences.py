"""The athlete's schedule reaches the calendar.

Step 1 of the goal document asks for "how many sessions, which days, hour of
the day, flexible or fixed". Sessions and days landed in Phase B.

`preferred_session_hour_json` existed and `calendar_sync_service` reads it to
place each event — but nothing ever wrote it, so every session in every week
landed at the default hour regardless of what the athlete said. Flexibility had
nowhere to live at all, and it is what decides whether the coach may move a
session when the week goes wrong.
"""
from __future__ import annotations

import json

import pytest

from app.db.models import AthleteModel
from app.services.onboarding_extraction import apply_extraction

ATHLETE = "sched-1"


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
        sports_json='["running", "lifting"]',
        goals_json="[]",
        available_days_json="[]",
        equipment_json="[]",
    )
    db_session.add(row)
    db_session.commit()
    return row


class TestSessionHours:
    def test_an_hour_per_sport_is_stored(self, db_session, athlete) -> None:
        changed = apply_extraction(
            athlete,
            {"preferred_session_hour": {"running": 7, "lifting": 18}},
            db_session,
        )

        assert "preferred_session_hour" in changed
        stored = json.loads(athlete.preferred_session_hour_json)
        assert stored == {"running": 7, "lifting": 18}

    def test_an_impossible_hour_is_refused(self, db_session, athlete) -> None:
        apply_extraction(
            athlete, {"preferred_session_hour": {"running": 26}}, db_session
        )

        assert json.loads(athlete.preferred_session_hour_json or "{}") == {}

    def test_an_unknown_sport_is_dropped(self, db_session, athlete) -> None:
        apply_extraction(
            athlete,
            {"preferred_session_hour": {"running": 7, "quidditch": 9}},
            db_session,
        )

        stored = json.loads(athlete.preferred_session_hour_json)
        assert "quidditch" not in stored
        assert stored["running"] == 7

    def test_midnight_is_a_real_hour(self, db_session, athlete) -> None:
        """Zero is a valid hour and must not be read as absent."""
        apply_extraction(
            athlete, {"preferred_session_hour": {"running": 0}}, db_session
        )

        assert json.loads(athlete.preferred_session_hour_json)["running"] == 0


class TestFlexibility:
    @pytest.mark.parametrize("value", ["fixed", "flexible"])
    def test_it_is_stored(self, db_session, athlete, value: str) -> None:
        changed = apply_extraction(
            athlete, {"schedule_flexibility": value}, db_session
        )

        assert "schedule_flexibility" in changed
        assert athlete.schedule_flexibility == value

    def test_anything_else_is_refused(self, db_session, athlete) -> None:
        """A free-text value would mean nothing to the code that reads it."""
        apply_extraction(
            athlete, {"schedule_flexibility": "quand je peux"}, db_session
        )

        assert athlete.schedule_flexibility is None

    def test_the_french_words_are_understood(self, db_session, athlete) -> None:
        apply_extraction(athlete, {"schedule_flexibility": "Flexible"}, db_session)

        assert athlete.schedule_flexibility == "flexible"


class TestItReachesTheCoachAndTheCalendar:
    def test_the_tool_accepts_both(self) -> None:
        from app.services.coach_tools import TOOL_SCHEMAS

        profile = next(s for s in TOOL_SCHEMAS if s["name"] == "update_profile")
        properties = profile["input_schema"]["properties"]

        assert "preferred_session_hour" in properties
        assert "schedule_flexibility" in properties

    def test_the_calendar_reads_the_hour_that_was_written(
        self, db_session, athlete
    ) -> None:
        """The column was read all along; nothing wrote it."""
        from app.integrations.google_calendar.calendar_sync_service import (
            _preferences_of,
        )

        apply_extraction(
            athlete, {"preferred_session_hour": {"running": 6}}, db_session
        )

        assert _preferences_of(athlete).get("running") == 6
