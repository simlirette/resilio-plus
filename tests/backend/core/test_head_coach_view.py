"""What the coach knows about you when you text it.

Before this, `HeadCoachView` carried six fields — id, phase, sports,
primary_sport, hours_per_week, coaching_mode — and `active_plan_summary` was
hardcoded `None` behind a "D6: populated from active plan" comment that was
never done. So the Head Coach answered "my legs are wrecked" knowing you run
and lift eight hours a week, and nothing else: not your age, not your VDOT, not
your race, not this week's plan, not what you actually did.

These tests pin the context that makes it a coach instead of a persona.
"""
from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

import pytest
from app.core.head_coach_view_builder import build_head_coach_view

NOW = datetime.now(timezone.utc)


@pytest.fixture
def db_session():
    from app.db import models  # noqa: F401
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
def athlete(db_session: Any):
    from app.db.models import AthleteModel

    row = AthleteModel(
        id=str(uuid.uuid4()),
        name="Simon",
        age=24,
        sex="M",
        weight_kg=77.1,
        height_cm=182.9,
        primary_sport="running",
        hours_per_week=8.0,
        sports_json='["running", "lifting"]',
        goals_json='["half marathon Usti nad Labem"]',
        available_days_json="[]",
        equipment_json="[]",
        journey_phase="steady_state",
        vdot=48.0,
        resting_hr=48,
        target_race_date=date(2026, 9, 19),
    )
    db_session.add(row)
    db_session.commit()
    return row


class TestBackwardsCompatibility:
    def test_it_still_works_without_a_database(self, athlete: Any) -> None:
        view = build_head_coach_view(athlete)

        assert view.athlete_id == athlete.id
        assert view.sports == ["running", "lifting"]
        assert view.primary_sport == "running"
        assert view.coaching_mode == "full"

    def test_without_a_database_the_state_fields_stay_empty(
        self, athlete: Any
    ) -> None:
        view = build_head_coach_view(athlete)

        assert view.active_plan_summary is None
        assert view.acwr_ratio is None
        assert view.recent_sessions == []


class TestPhysiologyAndGoal:
    """The numbers a coach would ask for in the first five minutes."""

    def test_the_profile_is_carried(self, athlete: Any) -> None:
        view = build_head_coach_view(athlete)

        assert view.age == 24
        assert view.sex == "M"
        assert view.weight_kg == 77.1
        assert view.height_cm == 182.9

    def test_the_fitness_markers_are_carried(self, athlete: Any) -> None:
        view = build_head_coach_view(athlete)

        assert view.vdot == 48.0
        assert view.resting_hr == 48

    def test_the_goal_and_race_are_carried(self, athlete: Any) -> None:
        view = build_head_coach_view(athlete)

        assert view.goals == ["half marathon Usti nad Labem"]
        assert view.target_race_date == date(2026, 9, 19)

    def test_weeks_to_race_is_derived(self, athlete: Any) -> None:
        athlete.target_race_date = NOW.date() + timedelta(days=28)
        view = build_head_coach_view(athlete)

        assert view.weeks_to_race == 4

    def test_no_race_means_no_countdown(self, athlete: Any) -> None:
        athlete.target_race_date = None
        assert build_head_coach_view(athlete).weeks_to_race is None


class TestActivePlan:
    """The D6 TODO: the coach could not see the plan it had just written."""

    def _plan(self, db: Any, athlete_id: str, when: date) -> None:
        from app.db.models import TrainingPlanModel

        db.add(
            TrainingPlanModel(
                id=str(uuid.uuid4()),
                athlete_id=athlete_id,
                start_date=when,
                end_date=when + timedelta(days=6),
                phase="competition",
                total_weekly_hours=6.5,
                acwr=1.05,
                weekly_slots_json=json.dumps(
                    [
                        {
                            "id": "s1",
                            "date": when.isoformat(),
                            "sport": "running",
                            "workout_type": "tempo",
                            "duration_min": 50,
                            "notes": "8 km @ 4:35/km",
                        },
                        {
                            "id": "s2",
                            "date": (when + timedelta(days=2)).isoformat(),
                            "sport": "lifting",
                            "workout_type": "lower_strength",
                            "duration_min": 60,
                            "notes": "",
                        },
                    ]
                ),
                status="active",
                created_at=NOW,
            )
        )
        db.commit()

    def test_the_plan_summary_is_populated(
        self, db_session: Any, athlete: Any
    ) -> None:
        self._plan(db_session, athlete.id, NOW.date())

        view = build_head_coach_view(athlete, db_session)

        assert view.active_plan_summary is not None
        assert view.active_plan_summary["phase"] == "competition"
        assert view.active_plan_summary["sessions_total"] == 2

    def test_the_sessions_are_listed_so_the_coach_can_talk_about_them(
        self, db_session: Any, athlete: Any
    ) -> None:
        self._plan(db_session, athlete.id, NOW.date())

        summary = build_head_coach_view(athlete, db_session).active_plan_summary

        assert summary is not None
        types = [s["workout_type"] for s in summary["sessions"]]
        assert types == ["tempo", "lower_strength"]

    def test_no_plan_leaves_the_summary_none(
        self, db_session: Any, athlete: Any
    ) -> None:
        assert build_head_coach_view(athlete, db_session).active_plan_summary is None


class TestTrainingState:
    def test_acwr_comes_from_real_history(
        self, db_session: Any, athlete: Any
    ) -> None:
        from app.db.models import StravaActivityModel

        for days_ago in range(14):
            db_session.add(
                StravaActivityModel(
                    id=f"strava_{uuid.uuid4().hex[:8]}",
                    athlete_id=athlete.id,
                    strava_id=int(uuid.uuid4().int % 10**12),
                    sport_type="running",
                    name="run",
                    started_at=NOW - timedelta(days=days_ago),
                    duration_s=45 * 60,
                    perceived_exertion=7.0,
                )
            )
        db_session.commit()

        view = build_head_coach_view(athlete, db_session)

        assert view.acwr_ratio is not None
        assert view.acwr_ratio > 0
        assert view.acwr_status in {"safe", "caution", "danger", "undertrained"}

    def test_recent_sessions_describe_what_was_actually_done(
        self, db_session: Any, athlete: Any
    ) -> None:
        from app.db.models import StravaActivityModel

        db_session.add(
            StravaActivityModel(
                id="strava_recent",
                athlete_id=athlete.id,
                strava_id=987654321,
                sport_type="running",
                name="long run",
                started_at=NOW - timedelta(days=2),
                duration_s=90 * 60,
                distance_m=18000.0,
                perceived_exertion=6.0,
            )
        )
        db_session.commit()

        view = build_head_coach_view(athlete, db_session)

        assert len(view.recent_sessions) == 1
        session = view.recent_sessions[0]
        assert session["sport"] == "running"
        assert session["duration_min"] == 90
        assert session["distance_km"] == pytest.approx(18.0)

    def test_readiness_comes_from_the_latest_snapshot(
        self, db_session: Any, athlete: Any
    ) -> None:
        from app.jobs.models import AthleteStateSnapshotModel

        db_session.add(
            AthleteStateSnapshotModel(
                id=str(uuid.uuid4()),
                athlete_id=athlete.id,
                snapshot_date=NOW.date(),
                readiness=0.82,
                # Only a measured readiness reaches the view; an unmeasured
                # neutral 1.0 is the absence of a signal, not a good one.
                readiness_source="measured",
                strain_json=json.dumps({"quads": 74.0, "calves": 31.0}),
            )
        )
        db_session.commit()

        view = build_head_coach_view(athlete, db_session)

        assert view.readiness == pytest.approx(0.82)
        assert view.muscle_strain["quads"] == pytest.approx(74.0)

    def test_recent_sessions_are_capped(
        self, db_session: Any, athlete: Any
    ) -> None:
        from app.db.models import StravaActivityModel

        for index in range(40):
            db_session.add(
                StravaActivityModel(
                    id=f"strava_{index}",
                    athlete_id=athlete.id,
                    strava_id=100000 + index,
                    sport_type="running",
                    name="run",
                    started_at=NOW - timedelta(hours=index),
                    duration_s=1800,
                )
            )
        db_session.commit()

        view = build_head_coach_view(athlete, db_session)

        assert len(view.recent_sessions) <= 10


class TestDegradation:
    def test_a_broken_database_still_yields_the_base_view(
        self, athlete: Any
    ) -> None:
        class Broken:
            def query(self, *args: Any, **kwargs: Any) -> Any:
                raise RuntimeError("db down")

            def get(self, *args: Any, **kwargs: Any) -> Any:
                raise RuntimeError("db down")

        view = build_head_coach_view(athlete, Broken())

        assert view.athlete_id == athlete.id
        assert view.age == 24
        assert view.active_plan_summary is None
        assert view.recent_sessions == []
