# tests/e2e/test_scenario_02_energy_cap.py
"""S2 — Energy snapshot intensity cap (0.6): sessions scaled to 60% duration.

EnergySnapshotModel pre-seeded with recommended_intensity_cap=0.6 (moderate
allostatic load, no veto). Verifies that apply_energy_snapshot node scales
all session durations by cap before persisting the final plan.

Graph flow (with interrupt=True):
  ... -> build_proposed_plan -> [INTERRUPT: present_to_athlete]
  resume(approved=True) -> apply_energy_snapshot -> finalize_plan -> END

The apply_energy_snapshot node runs AFTER human approval, not before the
interrupt. Therefore energy_snapshot_dict is checked on the final graph state
and the final_plan_dict contains the scaled sessions.
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
    seed_energy_snapshot,
    simon_fresh_profile,
    STABLE_LOAD,
)

random.seed(42)

ATHLETE_ID = "e2e-s02-simon"
CAP = 0.6
_state: dict = {}


@pytest.fixture(scope="module")
def scenario_db():
    engine = make_scenario_engine()
    Base.metadata.create_all(engine)
    Session = sessionmaker(engine)
    with Session() as db:
        seed_athlete(db, ATHLETE_ID)
        seed_energy_snapshot(
            db,
            athlete_id=ATHLETE_ID,
            intensity_cap=CAP,
            veto_triggered=False,
            allostatic_score=65.0,
            energy_availability=32.0,
        )
        yield db
    Base.metadata.drop_all(engine)


def test_01_create_plan_no_cap_yet(scenario_db):
    """create_plan runs until interrupt — proposed plan exists, energy_snapshot_dict not yet set."""
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
    # Store unscaled durations for comparison after approval
    _state["original_durations"] = [s["duration_min"] for s in proposed["sessions"]]


def test_02_energy_snapshot_present(scenario_db):
    """After approval, graph state carries energy_snapshot_dict with correct cap."""
    svc = _state["svc"]
    thread_id = _state["thread_id"]

    final = svc.resume_plan(
        thread_id=thread_id,
        approved=True,
        feedback=None,
        db=scenario_db,
    )
    _state["final"] = final

    # Retrieve graph state — apply_energy_snapshot has now run
    config = {"configurable": {"thread_id": thread_id, "db": scenario_db}}
    graph_state = svc._graph.get_state(config)
    _state["graph_state_values"] = graph_state.values

    snapshot = graph_state.values.get("energy_snapshot_dict")
    assert snapshot is not None, (
        "energy_snapshot_dict not found in graph state after approval — "
        "apply_energy_snapshot node may not have run or key name changed"
    )
    assert abs(snapshot["intensity_cap"] - CAP) < 0.01


def test_03_sessions_scaled_to_cap(scenario_db):
    """All sessions have duration_min reflecting intensity_cap=0.6 reduction."""
    # The apply_energy_snapshot node scales: new_duration = max(1, int(original * cap))
    # We can't know original durations without a baseline run, but we verify:
    # 1. All durations > 0 (no crash)
    # 2. energy_snapshot["veto_triggered"] is False
    snapshot = _state["graph_state_values"]["energy_snapshot_dict"]
    assert snapshot["veto_triggered"] is False

    final = _state["final"]
    assert final is not None
    for s in final.get("sessions", []):
        assert s["duration_min"] >= 1

    # Verify scaling: each final duration should be <= original (cap=0.6 reduces)
    original_durations = _state["original_durations"]
    final_sessions = final.get("sessions", [])
    if original_durations and final_sessions:
        for orig, sess in zip(original_durations, final_sessions):
            expected = max(1, int(orig * CAP))
            assert sess["duration_min"] == expected, (
                f"Expected {expected} (= max(1, int({orig} * {CAP}))), got {sess['duration_min']}"
            )


def test_04_approve_persists_scaled_plan(scenario_db):
    """resume_plan(approved=True) already ran in test_02 — final has db_plan_id."""
    final = _state["final"]
    assert final is not None
    assert final.get("db_plan_id") is not None
