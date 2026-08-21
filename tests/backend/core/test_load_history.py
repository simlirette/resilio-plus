"""Daily training load, the input ACWR has been missing.

Every caller passed `load_history=[]`, so ACWR was pinned at 0.00
"undertrained" no matter what the athlete actually did. These tests pin the
load formula to the one `core/strain.py` already uses for cardio, so the two
modules cannot drift into disagreeing about what a session costs.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from app.core.load_history import (
    DEFAULT_RPE,
    daily_training_loads,
    session_load,
)


@pytest.fixture
def db_session():
    from app.db import models  # noqa: F401 — registers ORM models
    from app.db.database import Base
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import Session as SASession

    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )

    @event.listens_for(engine, "connect")
    def _fk(dbapi_connection: Any, _record: Any) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    with SASession(engine) as session:
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def athlete_id(db_session: Any) -> str:
    from app.db.models import AthleteModel

    athlete_id = str(uuid.uuid4())
    db_session.add(
        AthleteModel(
            id=athlete_id,
            name="Load Athlete",
            age=24,
            sex="M",
            weight_kg=77.1,
            height_cm=182.9,
            primary_sport="running",
            hours_per_week=8.0,
            sports_json='["running", "lifting"]',
            goals_json="[]",
            available_days_json="[]",
            equipment_json="[]",
        )
    )
    db_session.commit()
    return athlete_id


TODAY = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)


def add_activity(
    db: Any, athlete_id: str, *, days_ago: int, minutes: int, rpe: float | None = 7.0
) -> None:
    from app.db.models import StravaActivityModel

    db.add(
        StravaActivityModel(
            id=f"strava_{uuid.uuid4().hex[:8]}",
            athlete_id=athlete_id,
            strava_id=int(uuid.uuid4().int % 10**12),
            sport_type="running",
            name="run",
            started_at=TODAY - timedelta(days=days_ago),
            duration_s=minutes * 60,
            perceived_exertion=rpe,
        )
    )
    db.commit()


def add_session_log(
    db: Any, athlete_id: str, *, days_ago: int, minutes: int, rpe: int | None = 7,
    skipped: bool = False,
) -> None:
    from app.db.models import SessionLogModel

    db.add(
        SessionLogModel(
            id=str(uuid.uuid4()),
            athlete_id=athlete_id,
            session_id=str(uuid.uuid4()),
            actual_duration_min=minutes,
            rpe=rpe,
            skipped=skipped,
            logged_at=TODAY - timedelta(days=days_ago),
        )
    )
    db.commit()


class TestSessionLoad:
    def test_matches_the_strain_module_cardio_formula(self) -> None:
        # duration_h * (rpe/10)^2 * 100
        assert session_load(60, 10.0) == pytest.approx(100.0)
        assert session_load(60, 5.0) == pytest.approx(25.0)
        assert session_load(30, 10.0) == pytest.approx(50.0)

    def test_missing_rpe_falls_back_to_the_shared_default(self) -> None:
        assert session_load(60, None) == pytest.approx(
            session_load(60, DEFAULT_RPE)
        )

    def test_zero_and_negative_duration_cost_nothing(self) -> None:
        assert session_load(0, 8.0) == 0.0
        assert session_load(-30, 8.0) == 0.0

    def test_load_grows_with_the_square_of_intensity(self) -> None:
        easy = session_load(60, 5.0)
        hard = session_load(60, 10.0)
        assert hard == pytest.approx(easy * 4)


class TestDailyTrainingLoads:
    def test_no_history_is_a_window_of_zeros(
        self, db_session: Any, athlete_id: str
    ) -> None:
        loads = daily_training_loads(
            athlete_id, db_session, days=28, reference_date=TODAY.date()
        )

        assert len(loads) == 28
        assert all(value == 0.0 for value in loads)

    def test_an_activity_lands_on_its_own_day(
        self, db_session: Any, athlete_id: str
    ) -> None:
        add_activity(db_session, athlete_id, days_ago=0, minutes=60, rpe=10.0)

        loads = daily_training_loads(
            athlete_id, db_session, days=28, reference_date=TODAY.date()
        )

        assert loads[-1] == pytest.approx(100.0)
        assert sum(loads[:-1]) == 0.0

    def test_oldest_first_ordering(self, db_session: Any, athlete_id: str) -> None:
        add_activity(db_session, athlete_id, days_ago=27, minutes=60, rpe=10.0)
        add_activity(db_session, athlete_id, days_ago=0, minutes=30, rpe=10.0)

        loads = daily_training_loads(
            athlete_id, db_session, days=28, reference_date=TODAY.date()
        )

        assert loads[0] == pytest.approx(100.0)
        assert loads[-1] == pytest.approx(50.0)

    def test_two_sessions_on_one_day_add_up(
        self, db_session: Any, athlete_id: str
    ) -> None:
        add_activity(db_session, athlete_id, days_ago=3, minutes=60, rpe=10.0)
        add_activity(db_session, athlete_id, days_ago=3, minutes=60, rpe=10.0)

        loads = daily_training_loads(
            athlete_id, db_session, days=28, reference_date=TODAY.date()
        )

        assert loads[-4] == pytest.approx(200.0)

    def test_activity_outside_the_window_is_ignored(
        self, db_session: Any, athlete_id: str
    ) -> None:
        add_activity(db_session, athlete_id, days_ago=40, minutes=90, rpe=10.0)

        loads = daily_training_loads(
            athlete_id, db_session, days=28, reference_date=TODAY.date()
        )

        assert sum(loads) == 0.0

    def test_session_logs_count_too(self, db_session: Any, athlete_id: str) -> None:
        add_session_log(db_session, athlete_id, days_ago=1, minutes=60, rpe=10)

        loads = daily_training_loads(
            athlete_id, db_session, days=28, reference_date=TODAY.date()
        )

        assert loads[-2] == pytest.approx(100.0)

    def test_a_skipped_session_costs_nothing(
        self, db_session: Any, athlete_id: str
    ) -> None:
        add_session_log(
            db_session, athlete_id, days_ago=1, minutes=60, rpe=10, skipped=True
        )

        loads = daily_training_loads(
            athlete_id, db_session, days=28, reference_date=TODAY.date()
        )

        assert sum(loads) == 0.0

    def test_another_athletes_work_is_not_counted(
        self, db_session: Any, athlete_id: str
    ) -> None:
        from app.db.models import AthleteModel

        other = str(uuid.uuid4())
        db_session.add(
            AthleteModel(
                id=other,
                name="Other",
                age=30,
                sex="F",
                weight_kg=60.0,
                height_cm=165.0,
                primary_sport="running",
                hours_per_week=5.0,
                sports_json='["running"]',
                goals_json="[]",
                available_days_json="[]",
                equipment_json="[]",
            )
        )
        db_session.commit()
        add_activity(db_session, other, days_ago=1, minutes=90, rpe=10.0)

        loads = daily_training_loads(
            athlete_id, db_session, days=28, reference_date=TODAY.date()
        )

        assert sum(loads) == 0.0

    def test_it_feeds_acwr_a_usable_ratio(
        self, db_session: Any, athlete_id: str
    ) -> None:
        """The whole point: a real history must produce a non-zero ACWR."""
        from app.core.acwr import compute_acwr

        for days_ago in range(28):
            add_activity(db_session, athlete_id, days_ago=days_ago, minutes=45, rpe=7.0)

        loads = daily_training_loads(
            athlete_id, db_session, days=28, reference_date=TODAY.date()
        )
        result = compute_acwr(loads)

        assert result.chronic_28d > 0
        assert result.ratio > 0
        assert result.max_safe_weekly_load > 0

    def test_a_database_failure_degrades_to_zeros(
        self, athlete_id: str
    ) -> None:
        class Broken:
            def query(self, *args: Any, **kwargs: Any) -> Any:
                raise RuntimeError("db down")

        loads = daily_training_loads(
            athlete_id, Broken(), days=28, reference_date=TODAY.date()
        )

        assert loads == [0.0] * 28
