"""The coach must be told what day it is.

`HeadCoachView` carried `target_race_date` and `weeks_to_race` but never
today's date, and no prompt supplied it either. A language model with no
anchor falls back to its training prior, which is exactly what happened on the
first live conversation:

    "19 septembre 2026, soit environ 4 semaines calendaires déclarées — ce
     chiffre sera à vérifier : la date à 4 semaines de l'onboarding correspond
     à mi-octobre, non septembre 2026"
    "septembre 2026 représente environ 60+ semaines, pas 4"

It argued with a correct number because it had no way to check it. Every
temporal judgement a coach makes -- taper timing, block length, whether a goal
is still reachable -- rests on this.

`weeks_to_race` alone is not enough: it rounds, so a race 3 days out and one
27 days out can both read as a number of weeks that hides the urgency.
`days_to_race` is exact.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pytest
from app.core.head_coach_view_builder import build_head_coach_view
from app.db.models import AthleteModel


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


def _athlete(db_session, race_date: date | None, tz: str | None = "America/Montreal"):
    row = AthleteModel(
        id="today-1",
        name="Simon",
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
        target_race_date=race_date,
        timezone=tz,
    )
    db_session.add(row)
    db_session.commit()
    return row


class TestTodayIsPresent:
    def test_the_view_carries_todays_date(self, db_session) -> None:
        athlete = _athlete(db_session, None)

        view = build_head_coach_view(athlete, db_session)

        assert view.today is not None

    def test_it_is_the_athletes_day_not_utc(self, db_session) -> None:
        """00:33 UTC on the 21st is still the 20th in Montreal."""
        from datetime import datetime, timezone

        import app.core.head_coach_view_builder as module

        athlete = _athlete(db_session, None)
        monkey = datetime(2026, 8, 21, 0, 33, tzinfo=timezone.utc)

        original = module._utcnow
        try:
            module._utcnow = lambda: monkey  # type: ignore[assignment]
            view = build_head_coach_view(athlete, db_session)
        finally:
            module._utcnow = original  # type: ignore[assignment]

        assert view.today == date(2026, 8, 20)

    def test_it_survives_without_a_database(self, db_session) -> None:
        """The profile-only view still needs a date."""
        athlete = _athlete(db_session, None)

        view = build_head_coach_view(athlete, None)

        assert view.today is not None


class TestDaysToRace:
    def test_an_exact_day_count_is_reported(self, db_session) -> None:
        athlete = _athlete(db_session, date.today() + timedelta(days=30))

        view = build_head_coach_view(athlete, db_session)

        assert view.days_to_race == 30

    def test_no_race_means_no_count(self, db_session) -> None:
        athlete = _athlete(db_session, None)

        view = build_head_coach_view(athlete, db_session)

        assert view.days_to_race is None

    def test_a_race_already_past_is_negative_not_clamped(self, db_session) -> None:
        """A stale goal should be visibly stale, not silently read as today."""
        athlete = _athlete(db_session, date.today() - timedelta(days=5))

        view = build_head_coach_view(athlete, db_session)

        assert view.days_to_race == -5

    def test_days_and_weeks_agree(self, db_session) -> None:
        athlete = _athlete(db_session, date.today() + timedelta(days=28))

        view = build_head_coach_view(athlete, db_session)

        assert view.days_to_race == 28
        assert view.weeks_to_race == 4


class TestItReachesTheModel:
    """Carrying the date is worth nothing if the prompt does not include it."""

    def test_the_serialised_view_contains_today(self, db_session) -> None:
        athlete = _athlete(db_session, date.today() + timedelta(days=30))

        payload = build_head_coach_view(athlete, db_session).model_dump_json(
            exclude_none=True
        )

        assert "today" in payload
        assert "days_to_race" in payload

    @pytest.mark.parametrize(
        "builder,module_name",
        [
            ("_format_head_coach_user_content", "app.graphs.chat_turn"),
            ("_block_question", "app.graphs.onboarding"),
        ],
    )
    def test_every_prompt_builder_passes_the_whole_view(
        self, builder: str, module_name: str
    ) -> None:
        """Hand-picking fields is how the date went missing in the first place."""
        import importlib
        import inspect

        module: Any = importlib.import_module(module_name)
        source = inspect.getsource(getattr(module, builder))

        assert "model_dump_json" in source, (
            f"{module_name}.{builder} builds its context from selected fields"
        )
