"""Apple Health data has to reach readiness, or importing it changes nothing.

The goal document names three data sources: "Strava, Hevy, Apple Health". The
XML parser, the aggregator and the `apple_health_daily` table were all built in
V3-X — and nothing ever read the table. `compute_readiness` takes Terra records
only, so an athlete could import a full export and `readiness` would still be
None, the Recovery Coach still blind.

One rule decides the shape of this: **never mix the two sources.** Terra
reports RMSSD, Apple Health reports SDNN. They are different measurements of
the same phenomenon on different scales, and readiness is a *delta* against a
baseline — so a series that switches between them mid-window produces a swing
that looks like fatigue and is arithmetic. Apple Health is used only when there
is no Terra data at all.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app.db.models import AppleHealthDailyModel, AthleteModel

ATHLETE = "ah-1"


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
        name="Simon",
        age=24,
        sex="M",
        weight_kg=77.1,
        height_cm=182.9,
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


def _days(db_session, count: int, sdnn: float = 60.0, sleep: float = 7.5) -> None:
    for offset in range(count):
        db_session.add(
            AppleHealthDailyModel(
                id=f"ah-{offset}",
                athlete_id=ATHLETE,
                record_date=date.today() - timedelta(days=offset),
                hrv_sdnn_avg=sdnn,
                sleep_hours=sleep,
                rhr_bpm=52.0,
                imported_at=datetime.now(timezone.utc),
            )
        )
    db_session.commit()


class TestItReachesReadiness:
    def test_imported_days_produce_a_readiness(self, db_session) -> None:
        from app.jobs.compute_jobs import snapshot_athlete
        from app.jobs.models import AthleteStateSnapshotModel

        _days(db_session, 7)

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

        snapshot = db_session.query(AthleteStateSnapshotModel).one()
        assert snapshot.readiness_source == "measured"

    def test_the_coach_sees_it(self, db_session, athlete) -> None:
        from app.core.head_coach_view_builder import build_head_coach_view
        from app.jobs.compute_jobs import snapshot_athlete

        _days(db_session, 7)

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

        assert build_head_coach_view(athlete, db_session).readiness is not None

    def test_no_import_leaves_readiness_unmeasured(self, db_session) -> None:
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

        assert db_session.query(AthleteStateSnapshotModel).one().readiness_source is None


class TestTheTwoSourcesAreNeverMixed:
    def test_terra_wins_when_both_exist(self, db_session) -> None:
        """RMSSD and SDNN on one baseline is arithmetic that looks like fatigue."""
        from app.jobs.compute_jobs import _recovery_records
        from app.schemas.connector import TerraHealthData

        _days(db_session, 7)
        terra = TerraHealthData(
            date=date.today(), hrv_rmssd=62.0, sleep_duration_hours=7.0
        )

        records = _recovery_records(ATHLETE, db_session, terra)

        assert len(records) == 1
        assert records[0].hrv_rmssd == 62.0

    def test_apple_health_is_used_only_without_terra(self, db_session) -> None:
        from app.jobs.compute_jobs import _recovery_records

        _days(db_session, 7)

        records = _recovery_records(ATHLETE, db_session, None)

        assert len(records) == 7


class TestWhatItReads:
    def test_only_recent_days_are_used(self, db_session) -> None:
        """A baseline built from last winter says nothing about this week."""
        from app.jobs.compute_jobs import _recovery_records

        db_session.add(
            AppleHealthDailyModel(
                id="old",
                athlete_id=ATHLETE,
                record_date=date.today() - timedelta(days=400),
                hrv_sdnn_avg=60.0,
                imported_at=datetime.now(timezone.utc),
            )
        )
        db_session.commit()

        assert _recovery_records(ATHLETE, db_session, None) == []

    def test_a_day_without_hrv_or_sleep_is_skipped(self, db_session) -> None:
        from app.jobs.compute_jobs import _recovery_records

        db_session.add(
            AppleHealthDailyModel(
                id="empty",
                athlete_id=ATHLETE,
                record_date=date.today(),
                body_mass_kg=77.0,
                imported_at=datetime.now(timezone.utc),
            )
        )
        db_session.commit()

        assert _recovery_records(ATHLETE, db_session, None) == []

    def test_a_broken_read_does_not_stop_the_snapshot(self, db_session) -> None:
        from app.jobs.compute_jobs import _recovery_records

        class Exploding:
            def query(self, *a, **k):
                raise RuntimeError("db gone")

        assert _recovery_records(ATHLETE, Exploding(), None) == []
