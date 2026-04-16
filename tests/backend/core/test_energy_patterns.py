"""Tests for S-4 energy pattern detection."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.db import models as _db_models  # noqa — registers all ORM models


def _make_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine


def _make_session(engine):
    Session = sessionmaker(bind=engine)
    return Session()


def _make_athlete(session):
    from app.db.models import AthleteModel
    a = AthleteModel(
        id=str(uuid.uuid4()),
        name="PatternTester",
        age=30,
        sex="F",
        weight_kg=60.0,
        height_cm=165.0,
        primary_sport="running",
        hours_per_week=8.0,
        sports_json='["running"]',
        goals_json='[]',
        available_days_json='[0,2,4]',
        equipment_json='[]',
    )
    session.add(a)
    session.commit()
    return a


# ---------------------------------------------------------------------------
# Task 1 — ORM columns + table existence
# ---------------------------------------------------------------------------

def test_energy_snapshots_has_legs_feeling_column():
    engine = _make_engine()
    inspector = inspect(engine)
    cols = {c["name"] for c in inspector.get_columns("energy_snapshots")}
    assert "legs_feeling" in cols


def test_energy_snapshots_has_stress_level_column():
    engine = _make_engine()
    inspector = inspect(engine)
    cols = {c["name"] for c in inspector.get_columns("energy_snapshots")}
    assert "stress_level" in cols


def test_head_coach_messages_table_exists():
    engine = _make_engine()
    inspector = inspect(engine)
    assert "head_coach_messages" in inspector.get_table_names()


def test_head_coach_messages_has_required_columns():
    engine = _make_engine()
    inspector = inspect(engine)
    cols = {c["name"] for c in inspector.get_columns("head_coach_messages")}
    assert {"id", "athlete_id", "pattern_type", "message", "created_at", "is_read"} <= cols


# ---------------------------------------------------------------------------
# Task 2 — submit_checkin() persists raw fields
# ---------------------------------------------------------------------------

def test_submit_checkin_persists_legs_feeling():
    from app.services.energy_cycle_service import EnergyCycleService
    from app.schemas.checkin import CheckInInput
    from app.models.schemas import EnergySnapshotModel

    engine = _make_engine()
    session = _make_session(engine)
    athlete = _make_athlete(session)

    svc = EnergyCycleService()
    checkin = CheckInInput(
        work_intensity="heavy",
        stress_level="significant",
        legs_feeling="heavy",
        energy_global="low",
    )
    svc.submit_checkin(athlete.id, session, checkin)

    snap = session.query(EnergySnapshotModel).filter_by(athlete_id=athlete.id).first()
    assert snap.legs_feeling == "heavy"
    session.close()


def test_submit_checkin_persists_stress_level():
    from app.services.energy_cycle_service import EnergyCycleService
    from app.schemas.checkin import CheckInInput
    from app.models.schemas import EnergySnapshotModel

    engine = _make_engine()
    session = _make_session(engine)
    athlete = _make_athlete(session)

    svc = EnergyCycleService()
    checkin = CheckInInput(
        work_intensity="normal",
        stress_level="significant",
        legs_feeling="normal",
        energy_global="ok",
    )
    svc.submit_checkin(athlete.id, session, checkin)

    snap = session.query(EnergySnapshotModel).filter_by(athlete_id=athlete.id).first()
    assert snap.stress_level == "significant"
    session.close()


# ---------------------------------------------------------------------------
# Helpers for pattern tests
# ---------------------------------------------------------------------------

def _make_snapshot(
    session,
    athlete_id: str,
    days_ago: int,
    legs_feeling: str = "normal",
    stress_level: str = "none",
    objective_score: float = 70.0,
    subjective_score: float = 70.0,
    energy_availability: float = 45.0,
):
    from app.models.schemas import EnergySnapshotModel
    snap = EnergySnapshotModel(
        id=str(uuid.uuid4()),
        athlete_id=athlete_id,
        timestamp=datetime.now(timezone.utc) - timedelta(days=days_ago),
        allostatic_score=30.0,
        cognitive_load=20.0,
        energy_availability=energy_availability,
        sleep_quality=70.0,
        recommended_intensity_cap=1.0,
        veto_triggered=False,
        objective_score=objective_score,
        subjective_score=subjective_score,
        legs_feeling=legs_feeling,
        stress_level=stress_level,
    )
    session.add(snap)
    session.commit()
    return snap


# ---------------------------------------------------------------------------
# Pattern 1: Heavy legs ≥3/7 days
# ---------------------------------------------------------------------------

def test_detect_heavy_legs_triggers_at_3_days():
    from app.core.energy_patterns import detect_heavy_legs
    from app.models.schemas import EnergySnapshotModel

    engine = _make_engine()
    session = _make_session(engine)
    athlete = _make_athlete(session)

    # 3 heavy-legs days in last 7
    _make_snapshot(session, athlete.id, days_ago=1, legs_feeling="heavy")
    _make_snapshot(session, athlete.id, days_ago=2, legs_feeling="dead")
    _make_snapshot(session, athlete.id, days_ago=3, legs_feeling="heavy")
    _make_snapshot(session, athlete.id, days_ago=4, legs_feeling="normal")

    snaps = session.query(EnergySnapshotModel).filter_by(athlete_id=athlete.id).all()
    assert detect_heavy_legs(snaps) is True
    session.close()


def test_detect_heavy_legs_no_trigger_below_3_days():
    from app.core.energy_patterns import detect_heavy_legs
    from app.models.schemas import EnergySnapshotModel

    engine = _make_engine()
    session = _make_session(engine)
    athlete = _make_athlete(session)

    # Only 2 heavy-legs days
    _make_snapshot(session, athlete.id, days_ago=1, legs_feeling="heavy")
    _make_snapshot(session, athlete.id, days_ago=2, legs_feeling="normal")
    _make_snapshot(session, athlete.id, days_ago=3, legs_feeling="dead")
    _make_snapshot(session, athlete.id, days_ago=4, legs_feeling="fresh")

    snaps = session.query(EnergySnapshotModel).filter_by(athlete_id=athlete.id).all()
    assert detect_heavy_legs(snaps) is False
    session.close()


def test_detect_heavy_legs_ignores_snapshots_older_than_7_days():
    from app.core.energy_patterns import detect_heavy_legs
    from app.models.schemas import EnergySnapshotModel

    engine = _make_engine()
    session = _make_session(engine)
    athlete = _make_athlete(session)

    # 3 heavy days BUT all older than 7 days — must not trigger
    _make_snapshot(session, athlete.id, days_ago=8, legs_feeling="heavy")
    _make_snapshot(session, athlete.id, days_ago=9, legs_feeling="dead")
    _make_snapshot(session, athlete.id, days_ago=10, legs_feeling="heavy")

    snaps = session.query(EnergySnapshotModel).filter_by(athlete_id=athlete.id).all()
    assert detect_heavy_legs(snaps) is False
    session.close()


# ---------------------------------------------------------------------------
# Pattern 2: Chronic stress ≥4/7 days
# ---------------------------------------------------------------------------

def test_detect_chronic_stress_triggers_at_4_days():
    from app.core.energy_patterns import detect_chronic_stress
    from app.models.schemas import EnergySnapshotModel

    engine = _make_engine()
    session = _make_session(engine)
    athlete = _make_athlete(session)

    for i in range(1, 5):  # 4 "significant" days
        _make_snapshot(session, athlete.id, days_ago=i, stress_level="significant")
    _make_snapshot(session, athlete.id, days_ago=5, stress_level="none")

    snaps = session.query(EnergySnapshotModel).filter_by(athlete_id=athlete.id).all()
    assert detect_chronic_stress(snaps) is True
    session.close()


def test_detect_chronic_stress_no_trigger_below_4_days():
    from app.core.energy_patterns import detect_chronic_stress
    from app.models.schemas import EnergySnapshotModel

    engine = _make_engine()
    session = _make_session(engine)
    athlete = _make_athlete(session)

    # Only 3 significant stress days
    for i in range(1, 4):
        _make_snapshot(session, athlete.id, days_ago=i, stress_level="significant")
    _make_snapshot(session, athlete.id, days_ago=4, stress_level="mild")

    snaps = session.query(EnergySnapshotModel).filter_by(athlete_id=athlete.id).all()
    assert detect_chronic_stress(snaps) is False
    session.close()


# ---------------------------------------------------------------------------
# Pattern 3: Persistent divergence ≥3 consecutive days (high divergence = >30 pts)
# ---------------------------------------------------------------------------

def test_detect_persistent_divergence_triggers_at_3_consecutive():
    from app.core.energy_patterns import detect_persistent_divergence
    from app.models.schemas import EnergySnapshotModel

    engine = _make_engine()
    session = _make_session(engine)
    athlete = _make_athlete(session)

    # 3 consecutive days with divergence >30
    _make_snapshot(session, athlete.id, days_ago=1, objective_score=80.0, subjective_score=40.0)
    _make_snapshot(session, athlete.id, days_ago=2, objective_score=75.0, subjective_score=35.0)
    _make_snapshot(session, athlete.id, days_ago=3, objective_score=70.0, subjective_score=30.0)
    _make_snapshot(session, athlete.id, days_ago=4, objective_score=65.0, subjective_score=60.0)  # divergence=5

    snaps = session.query(EnergySnapshotModel).filter_by(athlete_id=athlete.id).all()
    assert detect_persistent_divergence(snaps) is True
    session.close()


def test_detect_persistent_divergence_no_trigger_if_gap_breaks_streak():
    from app.core.energy_patterns import detect_persistent_divergence
    from app.models.schemas import EnergySnapshotModel

    engine = _make_engine()
    session = _make_session(engine)
    athlete = _make_athlete(session)

    # Day 1 + Day 3 have high divergence, but day 2 breaks the streak
    _make_snapshot(session, athlete.id, days_ago=1, objective_score=80.0, subjective_score=40.0)
    _make_snapshot(session, athlete.id, days_ago=2, objective_score=70.0, subjective_score=68.0)  # divergence=2
    _make_snapshot(session, athlete.id, days_ago=3, objective_score=75.0, subjective_score=35.0)

    snaps = session.query(EnergySnapshotModel).filter_by(athlete_id=athlete.id).all()
    assert detect_persistent_divergence(snaps) is False
    session.close()


# ---------------------------------------------------------------------------
# Pattern 4: RED-S signal — energy_availability < 30 for ≥3/7 days
# ---------------------------------------------------------------------------

def test_detect_reds_signal_triggers_at_3_days():
    from app.core.energy_patterns import detect_reds_signal
    from app.models.schemas import EnergySnapshotModel

    engine = _make_engine()
    session = _make_session(engine)
    athlete = _make_athlete(session)

    _make_snapshot(session, athlete.id, days_ago=1, energy_availability=20.0)
    _make_snapshot(session, athlete.id, days_ago=2, energy_availability=25.0)
    _make_snapshot(session, athlete.id, days_ago=3, energy_availability=28.0)
    _make_snapshot(session, athlete.id, days_ago=4, energy_availability=45.0)

    snaps = session.query(EnergySnapshotModel).filter_by(athlete_id=athlete.id).all()
    assert detect_reds_signal(snaps) is True
    session.close()


def test_detect_reds_signal_no_trigger_below_3_days():
    from app.core.energy_patterns import detect_reds_signal
    from app.models.schemas import EnergySnapshotModel

    engine = _make_engine()
    session = _make_session(engine)
    athlete = _make_athlete(session)

    _make_snapshot(session, athlete.id, days_ago=1, energy_availability=20.0)
    _make_snapshot(session, athlete.id, days_ago=2, energy_availability=45.0)
    _make_snapshot(session, athlete.id, days_ago=3, energy_availability=50.0)

    snaps = session.query(EnergySnapshotModel).filter_by(athlete_id=athlete.id).all()
    assert detect_reds_signal(snaps) is False
    session.close()


# ---------------------------------------------------------------------------
# detect_energy_patterns() integration tests
# ---------------------------------------------------------------------------

def test_detect_energy_patterns_creates_heavy_legs_message():
    from app.core.energy_patterns import detect_energy_patterns
    from app.models.schemas import HeadCoachMessageModel

    engine = _make_engine()
    session = _make_session(engine)
    athlete = _make_athlete(session)

    # 3 heavy-legs days
    for i in range(1, 4):
        _make_snapshot(session, athlete.id, days_ago=i, legs_feeling="heavy")

    detect_energy_patterns(session)

    msgs = session.query(HeadCoachMessageModel).filter_by(
        athlete_id=athlete.id, pattern_type="heavy_legs"
    ).all()
    assert len(msgs) == 1
    assert msgs[0].is_read is False
    session.close()


def test_detect_energy_patterns_creates_chronic_stress_message():
    from app.core.energy_patterns import detect_energy_patterns
    from app.models.schemas import HeadCoachMessageModel

    engine = _make_engine()
    session = _make_session(engine)
    athlete = _make_athlete(session)

    for i in range(1, 5):
        _make_snapshot(session, athlete.id, days_ago=i, stress_level="significant")

    detect_energy_patterns(session)

    msgs = session.query(HeadCoachMessageModel).filter_by(
        athlete_id=athlete.id, pattern_type="chronic_stress"
    ).all()
    assert len(msgs) == 1
    session.close()


def test_detect_energy_patterns_no_duplicate_message_within_7_days():
    from app.core.energy_patterns import detect_energy_patterns
    from app.models.schemas import HeadCoachMessageModel

    engine = _make_engine()
    session = _make_session(engine)
    athlete = _make_athlete(session)

    # 3 heavy-legs days
    for i in range(1, 4):
        _make_snapshot(session, athlete.id, days_ago=i, legs_feeling="heavy")

    # Run detect twice — should still produce only 1 message
    detect_energy_patterns(session)
    detect_energy_patterns(session)

    msgs = session.query(HeadCoachMessageModel).filter_by(
        athlete_id=athlete.id, pattern_type="heavy_legs"
    ).all()
    assert len(msgs) == 1
    session.close()


def test_detect_energy_patterns_no_message_when_no_pattern():
    from app.core.energy_patterns import detect_energy_patterns
    from app.models.schemas import HeadCoachMessageModel

    engine = _make_engine()
    session = _make_session(engine)
    athlete = _make_athlete(session)

    # Only 1 heavy day — no pattern
    _make_snapshot(session, athlete.id, days_ago=1, legs_feeling="heavy")
    _make_snapshot(session, athlete.id, days_ago=2, legs_feeling="normal")

    detect_energy_patterns(session)

    msgs = session.query(HeadCoachMessageModel).filter_by(athlete_id=athlete.id).all()
    assert len(msgs) == 0
    session.close()


def test_detect_energy_patterns_creates_reds_message():
    from app.core.energy_patterns import detect_energy_patterns
    from app.models.schemas import HeadCoachMessageModel

    engine = _make_engine()
    session = _make_session(engine)
    athlete = _make_athlete(session)

    for i in range(1, 4):
        _make_snapshot(session, athlete.id, days_ago=i, energy_availability=20.0)

    detect_energy_patterns(session)

    msgs = session.query(HeadCoachMessageModel).filter_by(
        athlete_id=athlete.id, pattern_type="reds_signal"
    ).all()
    assert len(msgs) == 1
    session.close()


# ---------------------------------------------------------------------------
# APScheduler weekly job — now uses app.jobs.scheduler
# Note: old "energy_patterns_weekly" job id was renamed to "energy_patterns"
# ---------------------------------------------------------------------------

def test_setup_scheduler_has_energy_patterns_job():
    from app.jobs.scheduler import setup_scheduler
    from apscheduler.schedulers.background import BackgroundScheduler

    scheduler = setup_scheduler()
    try:
        job_ids = [job.id for job in scheduler.get_jobs()]
        assert "energy_patterns" in job_ids
    finally:
        scheduler.shutdown(wait=False)


def test_energy_patterns_job_runs_weekly_on_monday():
    from app.jobs.scheduler import setup_scheduler

    scheduler = setup_scheduler()
    try:
        job = next(j for j in scheduler.get_jobs() if j.id == "energy_patterns")
        trigger = job.trigger
        assert trigger.__class__.__name__ == "CronTrigger"
        field_names = [f.name for f in trigger.fields]
        assert "day_of_week" in field_names
    finally:
        scheduler.shutdown(wait=False)
