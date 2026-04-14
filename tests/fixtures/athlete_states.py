# tests/fixtures/athlete_states.py
"""Shared athlete profile factories and DB helpers for E2E scenario tests.

Usage:
    from tests.fixtures.athlete_states import (
        simon_fresh_profile, layla_luteal_context,
        seed_athlete, seed_energy_snapshot,
        make_scenario_engine, STABLE_LOAD, ELEVATED_LOAD, FRESH_LOAD,
    )
"""
from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


# ---------------------------------------------------------------------------
# Load constants
# ---------------------------------------------------------------------------

STABLE_LOAD: list[float] = [400.0] * 28    # ACWR safe (~1.0)
ELEVATED_LOAD: list[float] = [600.0] * 28  # ACWR caution (~1.3)
FRESH_LOAD: list[float] = [50.0] * 28      # new athlete, low load

# Fixed reference dates (deterministic)
WEEK_START = date(2026, 4, 14)
TARGET_RACE = WEEK_START + timedelta(weeks=27)


# ---------------------------------------------------------------------------
# Engine factory (mirrors e2e/conftest._make_e2e_engine)
# ---------------------------------------------------------------------------

def make_scenario_engine():
    """SQLite in-memory engine with FK enforcement."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_pragma(dbapi_conn, _record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


# ---------------------------------------------------------------------------
# AthleteModel seeding
# ---------------------------------------------------------------------------

def seed_athlete(db, athlete_id: str = "e2e-simon-001") -> None:
    """Insert minimal AthleteModel row. Imports deferred to avoid SA conflicts."""
    import importlib
    importlib.import_module("app.models.schemas")   # V3 models first
    _m = importlib.import_module("app.db.models")
    AthleteModel = _m.AthleteModel

    athlete = AthleteModel(
        id=athlete_id,
        name="Simon",
        age=32,
        sex="M",
        weight_kg=78.5,
        height_cm=178.0,
        primary_sport="running",
        target_race_date=TARGET_RACE,
        hours_per_week=8.0,
        sports_json=json.dumps(["running", "lifting"]),
        goals_json=json.dumps(["run sub-25min 5K", "maintain muscle mass"]),
        available_days_json=json.dumps([0, 1, 3, 5, 6]),
        equipment_json=json.dumps([]),
        coaching_mode="full",
        vdot=45.0,
        resting_hr=58,
        max_hr=188,
    )
    db.add(athlete)
    db.commit()


def seed_athlete_layla(db, athlete_id: str = "e2e-layla-001") -> None:
    """Insert Layla (female, VDOT 40) for hormonal cycle tests."""
    import importlib
    importlib.import_module("app.models.schemas")
    _m = importlib.import_module("app.db.models")
    AthleteModel = _m.AthleteModel

    athlete = AthleteModel(
        id=athlete_id,
        name="Layla",
        age=28,
        sex="F",
        weight_kg=62.0,
        height_cm=168.0,
        primary_sport="running",
        target_race_date=TARGET_RACE,
        hours_per_week=7.0,
        sports_json=json.dumps(["running", "lifting"]),
        goals_json=json.dumps(["sub-30min 5K", "stay healthy"]),
        available_days_json=json.dumps([0, 2, 4, 6]),
        equipment_json=json.dumps([]),
        coaching_mode="full",
        vdot=40.0,
        resting_hr=62,
        max_hr=192,
    )
    db.add(athlete)
    db.commit()


# ---------------------------------------------------------------------------
# EnergySnapshotModel seeding
# ---------------------------------------------------------------------------

def seed_energy_snapshot(
    db,
    athlete_id: str = "e2e-simon-001",
    intensity_cap: float = 1.0,
    veto_triggered: bool = False,
    allostatic_score: float = 40.0,
    energy_availability: float = 45.0,
    veto_reason: str | None = None,
) -> None:
    """Insert today's EnergySnapshotModel (timestamp=now UTC) for apply_energy_snapshot node."""
    import importlib
    importlib.import_module("app.models.schemas")
    _schemas = importlib.import_module("app.models.schemas")
    EnergySnapshotModel = _schemas.EnergySnapshotModel

    snapshot = EnergySnapshotModel(
        id=str(uuid.uuid4()),
        athlete_id=athlete_id,
        timestamp=datetime.now(timezone.utc),
        allostatic_score=allostatic_score,
        energy_availability=energy_availability,
        cognitive_load=4.0,
        sleep_quality=7.0,
        recommended_intensity_cap=intensity_cap,
        veto_triggered=veto_triggered,
        veto_reason=veto_reason,
        objective_score=None,
        subjective_score=None,
    )
    db.add(snapshot)
    db.commit()


# ---------------------------------------------------------------------------
# AthleteProfile dicts (for CoachingService.create_plan athlete_dict param)
# ---------------------------------------------------------------------------

def simon_fresh_profile() -> dict[str, Any]:
    """AthleteProfile.model_dump(mode='json') for Simon — normal training state."""
    return {
        "id": str(uuid.UUID("00000000-0000-0000-0000-000000000001")),
        "name": "Simon",
        "age": 32,
        "sex": "M",
        "weight_kg": 78.5,
        "height_cm": 178.0,
        "sports": ["running", "lifting"],
        "primary_sport": "running",
        "goals": ["run sub-25min 5K", "maintain muscle mass"],
        "target_race_date": TARGET_RACE.isoformat(),
        "available_days": [0, 1, 3, 5, 6],
        "hours_per_week": 8.0,
        "equipment": [],
        "vdot": 45.0,
        "resting_hr": 58,
        "max_hr": 188,
        "sleep_hours_typical": 7.5,
        "stress_level": 4,
        "job_physical": False,
        "coaching_mode": "full",
        "ftp_watts": None,
        "css_per_100m": None,
    }


def simon_single_day_profile() -> dict[str, Any]:
    """Simon with available_days=[0] only — forces both sports on Monday (conflict scenario)."""
    profile = simon_fresh_profile()
    profile["available_days"] = [0]
    return profile


# ---------------------------------------------------------------------------
# AgentContext factory for HeadCoach.build_week() (used in S8 — bypasses CoachingService)
# ---------------------------------------------------------------------------

def layla_luteal_context():
    """Returns (athlete, terra, hormonal_profile) tuple for S8."""
    from app.schemas.athlete import AthleteProfile, Sport
    from app.schemas.connector import TerraHealthData
    from app.models.athlete_state import HormonalProfile

    athlete = AthleteProfile(
        name="Layla",
        age=28,
        sex="F",
        weight_kg=62.0,
        height_cm=168.0,
        sports=[Sport.RUNNING, Sport.LIFTING],
        primary_sport=Sport.RUNNING,
        goals=["sub-30min 5K", "stay healthy"],
        target_race_date=TARGET_RACE,
        available_days=[0, 2, 4, 6],
        hours_per_week=7.0,
        vdot=40.0,
        resting_hr=62,
        max_hr=192,
    )

    # Terra: moderate HRV (not pathological, but cycle-adjusted)
    terra = [
        TerraHealthData(
            date=WEEK_START - timedelta(days=i),
            hrv_rmssd=38.0,
            sleep_duration_hours=6.8,
            sleep_score=65.0,
        )
        for i in range(7)
    ]

    # Luteal phase — day 20/28, higher fatigue baseline
    hormonal = HormonalProfile(
        enabled=True,
        current_phase="luteal",
        current_cycle_day=20,
        cycle_length_days=28,
    )

    return athlete, terra, hormonal
