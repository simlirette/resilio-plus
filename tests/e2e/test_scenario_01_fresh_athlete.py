# tests/e2e/test_scenario_01_fresh_athlete.py
"""S1 — Fresh athlete: create_plan → approve → TrainingPlanModel persisted.

Tests the happy path through the full CoachingService flow with no
energy snapshot (cap=1.0 by default), STABLE_LOAD, ACWR in safe zone.
"""
from __future__ import annotations

import random

import pytest
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db import models as _db_models   # noqa: F401 — registers ORM
from app.models import schemas as _v3     # noqa: F401 — registers V3 models
from app.services.coaching_service import CoachingService
from tests.fixtures.athlete_states import (
    make_scenario_engine,
    seed_athlete,
    simon_fresh_profile,
    STABLE_LOAD,
)

random.seed(42)

ATHLETE_ID = "e2e-s01-simon"
_state: dict = {}


@pytest.fixture(scope="module")
def scenario_db():
    engine = make_scenario_engine()
    Base.metadata.create_all(engine)
    Session = sessionmaker(engine)
    with Session() as db:
        seed_athlete(db, ATHLETE_ID)
        yield db
    Base.metadata.drop_all(engine)


def test_01_create_plan_returns_proposed(scenario_db):
    """create_plan() returns non-None proposed_plan_dict with sessions."""
    svc = CoachingService()
    _state["svc"] = svc

    thread_id, proposed = svc.create_plan(
        athlete_id=ATHLETE_ID,
        athlete_dict=simon_fresh_profile(),
        load_history=STABLE_LOAD,
        db=scenario_db,
    )

    assert thread_id is not None
    assert proposed is not None
    assert isinstance(proposed.get("sessions"), list)
    assert len(proposed["sessions"]) > 0

    _state["thread_id"] = thread_id
    _state["proposed"] = proposed


def test_02_proposed_plan_is_green(scenario_db):
    """Fresh athlete with STABLE_LOAD → readiness_level == 'green'."""
    proposed = _state["proposed"]
    assert proposed["readiness_level"] == "green"


def test_03_proposed_acwr_safe(scenario_db):
    """STABLE_LOAD produces ACWR in safe zone."""
    acwr = _state["proposed"]["acwr"]
    assert acwr["status"] in ("safe", "undertrained")


def test_04_sessions_have_valid_duration(scenario_db):
    """All proposed sessions have duration_min > 0."""
    for s in _state["proposed"]["sessions"]:
        assert s["duration_min"] > 0, f"Session with zero duration: {s}"


def test_05_approve_returns_final_with_db_plan_id(scenario_db):
    """resume_plan(approved=True) → final dict with db_plan_id."""
    svc = _state["svc"]
    final = svc.resume_plan(
        thread_id=_state["thread_id"],
        approved=True,
        feedback=None,
        db=scenario_db,
    )

    assert final is not None
    assert final.get("db_plan_id") is not None
    _state["final"] = final


def test_06_plan_persisted_in_db(scenario_db):
    """TrainingPlanModel row exists in DB after approval."""
    import importlib
    _m = importlib.import_module("app.db.models")
    TrainingPlanModel = _m.TrainingPlanModel

    db_plan_id = _state["final"]["db_plan_id"]
    plan = scenario_db.get(TrainingPlanModel, db_plan_id)
    assert plan is not None
    assert plan.athlete_id == ATHLETE_ID
    assert plan.status == "active"
