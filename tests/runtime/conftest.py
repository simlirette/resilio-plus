# tests/runtime/conftest.py
"""Shared fixtures for runtime tests — mock agents, canned responses, DB setup."""
from __future__ import annotations

import json
import random
import uuid
from datetime import date, timedelta
from unittest.mock import patch

import pytest
from langgraph.checkpoint.memory import MemorySaver
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.db import models as _db_models  # noqa: F401
from app.models import schemas as _v3  # noqa: F401
from app.agents.base import AgentContext, AgentRecommendation
from app.schemas.fatigue import FatigueScore
from app.schemas.plan import WorkoutSlot
from app.services.coaching_service import CoachingService

random.seed(42)

WEEK_START = date(2026, 4, 14)
TARGET_RACE = WEEK_START + timedelta(weeks=27)
STABLE_LOAD = [400.0] * 28


def _canned_recommendation(agent_name: str, sport: str) -> AgentRecommendation:
    """Build a minimal valid AgentRecommendation for testing."""
    today = date.today()
    return AgentRecommendation(
        agent_name=agent_name,
        weekly_load=200.0,
        fatigue_score=FatigueScore(
            local_muscular=30.0,
            cns_load=25.0,
            metabolic_cost=20.0,
            recovery_hours=24.0,
            affected_muscles=["quads"],
        ),
        suggested_sessions=[
            WorkoutSlot(
                id=str(uuid.uuid4()),
                sport=sport,
                date=today.isoformat(),
                workout_type="easy_z1",
                duration_min=45,
                intensity_target="Z1",
                notes=f"Canned {sport} session",
            ),
        ],
        readiness_modifier=1.0,
        notes=f"Canned {agent_name} recommendation",
    )


def _mock_analyze(agent_name: str, sport: str):
    """Return a mock analyze function for a specific agent."""
    def mock_fn(self, context: AgentContext) -> AgentRecommendation:
        return _canned_recommendation(agent_name, sport)
    return mock_fn


@pytest.fixture
def mock_agents():
    """Patch all agent analyze() methods with canned responses."""
    patches = [
        patch("app.agents.running_coach.RunningCoach.analyze",
              _mock_analyze("running", "running")),
        patch("app.agents.lifting_coach.LiftingCoach.analyze",
              _mock_analyze("lifting", "lifting")),
        patch("app.agents.nutrition_coach.NutritionCoach.analyze",
              _mock_analyze("nutrition", "running")),
        patch("app.agents.recovery_coach.RecoveryCoach.analyze",
              _mock_analyze("recovery", "running")),
    ]
    for p in patches:
        p.start()
    yield
    for p in patches:
        p.stop()


@pytest.fixture
def runtime_db():
    """In-memory SQLite DB with all tables created."""
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

    Base.metadata.create_all(engine)
    Session = sessionmaker(engine)
    with Session() as db:
        # Seed a minimal athlete
        from app.db.models import AthleteModel
        athlete = AthleteModel(
            id="rt-simon-001",
            name="Simon",
            age=32,
            sex="M",
            weight_kg=78.5,
            height_cm=178.0,
            primary_sport="running",
            target_race_date=TARGET_RACE,
            hours_per_week=8.0,
            sports_json=json.dumps(["running", "lifting"]),
            goals_json=json.dumps(["run sub-25min 5K"]),
            available_days_json=json.dumps([0, 1, 3, 5, 6]),
            equipment_json=json.dumps([]),
            coaching_mode="full",
            vdot=45.0,
            resting_hr=58,
            max_hr=188,
        )
        db.add(athlete)
        db.commit()
        yield db
    Base.metadata.drop_all(engine)


@pytest.fixture
def runtime_svc():
    """CoachingService with in-memory checkpointer for runtime tests."""
    return CoachingService(checkpointer=MemorySaver())


SIMON_PROFILE = {
    "id": str(uuid.UUID("00000000-0000-0000-0000-000000000001")),
    "name": "Simon",
    "age": 32,
    "sex": "M",
    "weight_kg": 78.5,
    "height_cm": 178.0,
    "sports": ["running", "lifting"],
    "primary_sport": "running",
    "goals": ["run sub-25min 5K"],
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
