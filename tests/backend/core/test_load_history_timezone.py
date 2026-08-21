"""The training window ends on the athlete's day, not on UTC's.

`daily_training_loads` defaulted its window end to `datetime.now(timezone.utc)
.date()`. For an athlete in America/Montreal that is a different date for four
hours of every evening -- five in winter. During that window the series gains a
day that has not happened yet, every session shifts one bucket further into the
past, and ACWR falls.

Caught live at 00:33 UTC on 2026-08-21, which was 20:33 on the 20th in
Montreal: the same athlete read 1.54 "danger" earlier that day and 0.59
"undertrained" that evening, with no training in between. Whichever number the
coach quotes, one of them is wrong, and an athlete told they are undertrained
while carrying an acute load is told to do more.

The rest of V4 already works in athlete-local time -- the weekly cycle cron,
the calendar events. This brings the load history in line.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest
from app.core.load_history import daily_training_loads
from app.db.models import AthleteModel, StravaActivityModel

ATHLETE = "99999999-9999-9999-9999-999999999999"


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


def _athlete(db_session, tz: str | None) -> AthleteModel:
    row = AthleteModel(
        id=ATHLETE,
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
        timezone=tz,
    )
    db_session.add(row)
    db_session.commit()
    return row


def _run(db_session, when: datetime, minutes: int = 60) -> None:
    db_session.add(
        StravaActivityModel(
            id=f"a-{when.isoformat()}",
            athlete_id=ATHLETE,
            strava_id=f"s-{when.isoformat()}",
            name="Run",
            sport_type="running",
            started_at=when,
            duration_s=minutes * 60,
            distance_m=10000.0,
        )
    )
    db_session.commit()


class TestAnExplicitReferenceDateStillWins:
    def test_the_caller_can_pin_the_window(self, db_session) -> None:
        _athlete(db_session, "America/Montreal")
        _run(db_session, datetime(2026, 8, 19, 12, 0, tzinfo=timezone.utc))

        loads = daily_training_loads(
            ATHLETE, db_session, days=28, reference_date=date(2026, 8, 19)
        )

        assert loads[-1] > 0, "the run did not land on the last day of the window"


class TestTheDefaultFollowsTheAthlete:
    def test_a_montreal_evening_is_still_the_same_day(
        self, db_session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """00:33 UTC on the 21st is 20:33 on the 20th in Montreal."""
        _athlete(db_session, "America/Montreal")
        _run(db_session, datetime(2026, 8, 20, 22, 0, tzinfo=timezone.utc))

        import app.core.load_history as module

        monkeypatch.setattr(
            module,
            "_utcnow",
            lambda: datetime(2026, 8, 21, 0, 33, tzinfo=timezone.utc),
        )

        loads = daily_training_loads(ATHLETE, db_session, days=28)

        assert loads[-1] > 0, (
            "the window ran a day ahead of the athlete, so today was empty"
        )

    def test_an_athlete_east_of_utc_is_handled_too(
        self, db_session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Tokyo is already on the next day while UTC is not."""
        _athlete(db_session, "Asia/Tokyo")
        # A Strava row's `started_at` is a *local date* stored at midnight UTC
        # (activity_mapper reads Strava's `start_date_local`), so a session on
        # the 21st in Tokyo is stored as 2026-08-21 00:00Z.
        _run(db_session, datetime(2026, 8, 21, 0, 0, tzinfo=timezone.utc))

        import app.core.load_history as module

        monkeypatch.setattr(
            module,
            "_utcnow",
            lambda: datetime(2026, 8, 20, 23, 0, tzinfo=timezone.utc),
        )

        loads = daily_training_loads(ATHLETE, db_session, days=28)

        assert loads[-1] > 0, "23:00 UTC is already the 21st in Tokyo"


class TestStravaDatesAreNotConverted:
    """`started_at` is a date in disguise, and must not be shifted.

    The connector parses Strava's `start_date_local` -- already the athlete's
    calendar day -- and `activity_mapper` stores it at midnight UTC. Treating
    that as a real instant and converting it westwards moves every session a
    day into the past, which is how a week of training turned into
    "undertrained".
    """

    def test_a_montreal_athlete_keeps_the_stored_day(self, db_session) -> None:
        _athlete(db_session, "America/Montreal")
        _run(db_session, datetime(2026, 8, 19, 0, 0, tzinfo=timezone.utc))

        loads = daily_training_loads(
            ATHLETE, db_session, days=28, reference_date=date(2026, 8, 19)
        )

        assert loads[-1] > 0, "midnight UTC was read as the previous evening"
        assert not any(loads[:-1]), "the session landed on more than one day"

    def test_the_stored_day_is_independent_of_the_zone(self, db_session) -> None:
        for tz in ("America/Montreal", "Asia/Tokyo", "UTC"):
            db_session.query(AthleteModel).delete()
            db_session.query(StravaActivityModel).delete()
            db_session.commit()
            _athlete(db_session, tz)
            _run(db_session, datetime(2026, 8, 19, 0, 0, tzinfo=timezone.utc))

            loads = daily_training_loads(
                ATHLETE, db_session, days=28, reference_date=date(2026, 8, 19)
            )

            assert loads[-1] > 0, f"{tz} shifted the stored day"


class TestDegradation:
    def test_no_timezone_falls_back_to_utc(
        self, db_session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _athlete(db_session, None)
        _run(db_session, datetime(2026, 8, 21, 6, 0, tzinfo=timezone.utc))

        import app.core.load_history as module

        monkeypatch.setattr(
            module,
            "_utcnow",
            lambda: datetime(2026, 8, 21, 8, 0, tzinfo=timezone.utc),
        )

        assert daily_training_loads(ATHLETE, db_session, days=28)[-1] > 0

    def test_a_nonsense_timezone_falls_back_to_utc(
        self, db_session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A bad value must not take the planning run down."""
        _athlete(db_session, "Mars/Olympus_Mons")
        _run(db_session, datetime(2026, 8, 21, 6, 0, tzinfo=timezone.utc))

        import app.core.load_history as module

        monkeypatch.setattr(
            module,
            "_utcnow",
            lambda: datetime(2026, 8, 21, 8, 0, tzinfo=timezone.utc),
        )

        assert daily_training_loads(ATHLETE, db_session, days=28)[-1] > 0

    def test_an_unknown_athlete_still_returns_a_series(self, db_session) -> None:
        loads = daily_training_loads("nobody", db_session, days=28)

        assert len(loads) == 28
        assert not any(loads)


class TestSeriesShape:
    def test_the_series_is_always_the_requested_length(self, db_session) -> None:
        _athlete(db_session, "America/Montreal")
        _run(db_session, datetime(2026, 8, 19, 12, 0, tzinfo=timezone.utc))

        for days in (7, 28, 42):
            assert len(daily_training_loads(ATHLETE, db_session, days=days)) == days

    def test_a_run_before_the_window_is_excluded(self, db_session) -> None:
        _athlete(db_session, "America/Montreal")
        _run(db_session, datetime(2026, 8, 19, 12, 0, tzinfo=timezone.utc) - timedelta(days=60))

        loads = daily_training_loads(
            ATHLETE, db_session, days=28, reference_date=date(2026, 8, 19)
        )

        assert not any(loads)
