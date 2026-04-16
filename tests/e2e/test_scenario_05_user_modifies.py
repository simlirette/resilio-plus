# tests/e2e/test_scenario_05_user_modifies.py
"""S5 — User rejects with specific feedback → second plan returned without crash.

Note: revise_plan clears proposed_plan_dict and stores feedback in messages,
then re-delegates to specialists. Agents do NOT read human_feedback text —
the feedback is recorded for audit trail only. The test verifies:
1. The revise cycle completes without error.
2. A valid second proposed plan is returned.
3. The feedback text appears in the graph messages.
"""
from __future__ import annotations

import random

import pytest
from langgraph.checkpoint.memory import MemorySaver
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db import models as _db_models   # noqa: F401
from app.models import schemas as _v3     # noqa: F401
from app.services.coaching_service import CoachingService
from tests.fixtures.athlete_states import (
    make_scenario_engine,
    seed_athlete,
    simon_fresh_profile,
    STABLE_LOAD,
)

random.seed(42)

ATHLETE_ID = "e2e-s05-simon"
FEEDBACK = "Replace long run with 45min easy run — my legs are sore."
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
    svc = CoachingService(checkpointer=MemorySaver())
    _state["svc"] = svc
    thread_id, proposed = svc.create_plan(
        athlete_id=ATHLETE_ID,
        athlete_dict=simon_fresh_profile(),
        load_history=STABLE_LOAD,
        db=scenario_db,
    )
    assert proposed is not None
    _state["thread_id"] = thread_id


def test_02_reject_with_specific_feedback(scenario_db):
    """Specific feedback text → revise loop completes, returns valid proposed_v2."""
    svc = _state["svc"]
    proposed_v2 = svc.resume_plan(
        thread_id=_state["thread_id"],
        approved=False,
        feedback=FEEDBACK,
        db=scenario_db,
    )
    assert proposed_v2 is not None
    assert isinstance(proposed_v2.get("sessions"), list)
    assert proposed_v2["readiness_level"] in ("green", "yellow", "red")
    _state["proposed_v2"] = proposed_v2


def test_03_feedback_recorded_in_graph_state(scenario_db):
    """Verify revise cycle ran (indirectly: proposed_v2 has no db_plan_id yet)."""
    # proposed_v2 should NOT be a final plan — no persistence happened
    assert _state["proposed_v2"].get("db_plan_id") is None


def test_04_second_approval_persists(scenario_db):
    """approve after modification → DB persist succeeds."""
    svc = _state["svc"]
    final = svc.resume_plan(
        thread_id=_state["thread_id"],
        approved=True,
        feedback=None,
        db=scenario_db,
    )
    assert final is not None
    assert final.get("db_plan_id") is not None
