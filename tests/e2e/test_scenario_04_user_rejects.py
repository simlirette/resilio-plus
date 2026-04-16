# tests/e2e/test_scenario_04_user_rejects.py
"""S4 — User rejects proposed plan → revise loop → second proposed plan.

Verifies the full reject+revise cycle:
  create_plan → interrupt → resume(approved=False) → revise_plan node →
  delegate_specialists → build_proposed_plan → interrupt again → proposed_v2 returned.

The graph enforces max 1 revision (coaching_graph._after_revise logic).
"""
from __future__ import annotations

import random

import pytest
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db import models as _db_models   # noqa: F401
from app.models import schemas as _v3     # noqa: F401
from langgraph.checkpoint.memory import MemorySaver

from app.services.coaching_service import CoachingService
from tests.fixtures.athlete_states import (
    make_scenario_engine,
    seed_athlete,
    simon_fresh_profile,
    STABLE_LOAD,
)

random.seed(42)

ATHLETE_ID = "e2e-s04-simon"
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


def test_01_create_plan(scenario_db):
    """create_plan returns proposed_v1."""
    svc = CoachingService(checkpointer=MemorySaver())
    _state["svc"] = svc

    thread_id, proposed_v1 = svc.create_plan(
        athlete_id=ATHLETE_ID,
        athlete_dict=simon_fresh_profile(),
        load_history=STABLE_LOAD,
        db=scenario_db,
    )

    assert proposed_v1 is not None
    assert len(proposed_v1["sessions"]) > 0
    _state["thread_id"] = thread_id
    _state["proposed_v1"] = proposed_v1


def test_02_reject_returns_proposed_v2(scenario_db):
    """resume_plan(approved=False) returns second proposed plan (not None, not final)."""
    svc = _state["svc"]

    proposed_v2 = svc.resume_plan(
        thread_id=_state["thread_id"],
        approved=False,
        feedback="Too much volume this week, please reduce.",
        db=scenario_db,
    )

    assert proposed_v2 is not None, "Expected a second proposed plan, got None"
    assert isinstance(proposed_v2.get("sessions"), list)
    assert len(proposed_v2["sessions"]) > 0
    # proposed_v2 is NOT a final plan — it should NOT have db_plan_id
    assert proposed_v2.get("db_plan_id") is None
    _state["proposed_v2"] = proposed_v2
    _state["thread_id_v2"] = _state["thread_id"]  # same thread continues


def test_03_revised_plan_is_structurally_valid(scenario_db):
    """proposed_v2 has all required top-level fields."""
    p = _state["proposed_v2"]
    assert "sessions" in p
    assert "readiness_level" in p
    assert p["readiness_level"] in ("green", "yellow", "red")
    assert "acwr" in p
    assert "phase" in p


def test_04_approve_revised_plan(scenario_db):
    """resume_plan(approved=True) on the same thread after rejection → persists."""
    svc = _state["svc"]

    final = svc.resume_plan(
        thread_id=_state["thread_id_v2"],
        approved=True,
        feedback=None,
        db=scenario_db,
    )

    assert final is not None
    assert final.get("db_plan_id") is not None
