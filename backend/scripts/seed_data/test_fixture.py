"""Minimal deterministic test fixture.

Inserts one user, one athlete, one training plan, three session logs,
one energy snapshot, and one allostatic entry. Idempotent.
"""
from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone

from app.db.models import (
    AthleteModel,
    SessionLogModel,
    TrainingPlanModel,
    UserModel,
)
from app.models.schemas import AllostaticEntryModel, EnergySnapshotModel
from passlib.context import CryptContext
from sqlalchemy.orm import Session

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

TEST_USER_EMAIL = "test@resilio.dev"
TEST_ATHLETE_ID = "athlete-test-001"
TEST_PLAN_ID = "plan-test-001"


def _athlete_exists(session: Session) -> bool:
    return session.get(AthleteModel, TEST_ATHLETE_ID) is not None


def insert_test_fixture(session: Session) -> None:
    """Insert minimal test fixture. Safe to call multiple times."""
    if _athlete_exists(session):
        return

    today = date(2026, 4, 13)

    # Athlete
    athlete = AthleteModel(
        id=TEST_ATHLETE_ID,
        name="Test Athlete",
        age=28,
        sex="F",
        weight_kg=60.0,
        height_cm=168.0,
        primary_sport="running",
        hours_per_week=8.0,
        sleep_hours_typical=7.5,
        stress_level=3,
        job_physical=False,
        vdot=42.0,
        coaching_mode="active",
        sports_json=json.dumps(["running", "lifting"]),
        goals_json=json.dumps(["marathon_sub4"]),
        available_days_json=json.dumps([1, 3, 5, 6]),
        equipment_json=json.dumps([]),
    )
    session.add(athlete)

    # User
    user = UserModel(
        id=str(uuid.uuid4()),
        email=TEST_USER_EMAIL,
        hashed_password=_pwd_ctx.hash("testpass"),
        athlete_id=TEST_ATHLETE_ID,
        created_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
    )
    session.add(user)

    # Training plan
    plan = TrainingPlanModel(
        id=TEST_PLAN_ID,
        athlete_id=TEST_ATHLETE_ID,
        start_date=date(2026, 4, 7),
        end_date=date(2026, 4, 13),
        phase="base",
        total_weekly_hours=8.0,
        acwr=1.05,
        weekly_slots_json=json.dumps([
            {"day": 1, "sport": "running", "duration_min": 60, "session_type": "easy"},
            {"day": 3, "sport": "lifting", "duration_min": 60, "session_type": "strength"},
            {"day": 5, "sport": "running", "duration_min": 90, "session_type": "long"},
        ]),
        status="active",
        created_at=datetime(2026, 4, 7, tzinfo=timezone.utc),
    )
    session.add(plan)

    # Session logs (1 completed, 1 skipped, 1 pending)
    session.add(SessionLogModel(
        id=str(uuid.uuid4()),
        athlete_id=TEST_ATHLETE_ID,
        plan_id=TEST_PLAN_ID,
        session_id="slot-mon-easy",
        actual_duration_min=62,
        skipped=False,
        rpe=6,
        notes="Felt good.",
        actual_data_json=json.dumps({}),
        logged_at=datetime(2026, 4, 7, 8, 0, tzinfo=timezone.utc),
    ))
    session.add(SessionLogModel(
        id=str(uuid.uuid4()),
        athlete_id=TEST_ATHLETE_ID,
        plan_id=TEST_PLAN_ID,
        session_id="slot-wed-lift",
        actual_duration_min=None,
        skipped=True,
        rpe=None,
        notes="Sick.",
        actual_data_json=json.dumps({}),
        logged_at=datetime(2026, 4, 9, 8, 0, tzinfo=timezone.utc),
    ))
    session.add(SessionLogModel(
        id=str(uuid.uuid4()),
        athlete_id=TEST_ATHLETE_ID,
        plan_id=TEST_PLAN_ID,
        session_id="slot-fri-long",
        actual_duration_min=None,
        skipped=False,
        rpe=None,
        notes="",
        actual_data_json=json.dumps({}),
        logged_at=datetime(2026, 4, 11, 8, 0, tzinfo=timezone.utc),
    ))

    # Energy snapshot
    session.add(EnergySnapshotModel(
        id=str(uuid.uuid4()),
        athlete_id=TEST_ATHLETE_ID,
        timestamp=datetime(2026, 4, 13, 7, 0, tzinfo=timezone.utc),
        allostatic_score=28.0,
        cognitive_load=20.0,
        energy_availability=42.0,
        sleep_quality=82.0,
        recommended_intensity_cap=1.0,
        veto_triggered=False,
        legs_feeling="normal",
        stress_level="none",
    ))

    # Allostatic entry
    session.add(AllostaticEntryModel(
        id=str(uuid.uuid4()),
        athlete_id=TEST_ATHLETE_ID,
        entry_date=today,
        allostatic_score=28.0,
        components_json=json.dumps({"hrv": 20.0, "sleep": 30.0, "work": 25.0}),
        intensity_cap_applied=1.0,
    ))
