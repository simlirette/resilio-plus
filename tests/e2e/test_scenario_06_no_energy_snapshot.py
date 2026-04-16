# tests/e2e/test_scenario_06_no_energy_snapshot.py
"""S6 — No EnergySnapshotModel in DB → apply_energy_snapshot returns None gracefully.

Verifies the graceful degradation path: when no check-in exists for today,
apply_energy_snapshot node returns energy_snapshot_dict=None and sessions
are NOT scaled (plan preserved as-is). No exception raised.
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

ATHLETE_ID = "e2e-s06-simon"
_state: dict = {}


@pytest.fixture(scope="module")
def scenario_db():
    """No EnergySnapshotModel seeded — only AthleteModel."""
    engine = make_scenario_engine()
    Base.metadata.create_all(engine)
    Session = sessionmaker(engine)
    with Session() as db:
        seed_athlete(db, ATHLETE_ID)
        # Intentionally no seed_energy_snapshot call
        yield db
    Base.metadata.drop_all(engine)


def test_01_create_plan_no_crash(scenario_db):
    """create_plan with no energy snapshot does not raise an exception."""
    svc = CoachingService(checkpointer=MemorySaver())
    _state["svc"] = svc

    thread_id, proposed = svc.create_plan(
        athlete_id=ATHLETE_ID,
        athlete_dict=simon_fresh_profile(),
        load_history=STABLE_LOAD,
        db=scenario_db,
    )

    assert proposed is not None
    assert len(proposed["sessions"]) > 0
    _state["thread_id"] = thread_id
    _state["proposed"] = proposed


def test_02_approve_no_crash(scenario_db):
    """resume_plan(approved=True) with no energy snapshot does not crash."""
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


def test_03_energy_snapshot_none_in_graph_state(scenario_db):
    """Graph state has energy_snapshot_dict=None when no snapshot in DB."""
    config = {"configurable": {"thread_id": _state["thread_id"], "db": scenario_db}}
    graph_state = _state["svc"]._graph.get_state(config)
    snapshot = graph_state.values.get("energy_snapshot_dict")
    assert snapshot is None, f"Expected None energy_snapshot_dict, got: {snapshot}"


def test_04_sessions_not_scaled(scenario_db):
    """Sessions in final plan have normal durations (no cap applied)."""
    final = _state["final"]
    for s in final.get("sessions", []):
        # Without cap, sessions should have typical durations > 1 minute
        assert s["duration_min"] > 1, f"Session unexpectedly at 1min: {s}"
