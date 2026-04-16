# tests/e2e/test_scenario_07_reds_veto.py
"""S7 — RED-S energy veto: EnergySnapshot(cap=0.0, veto=True) → sessions all 1min.

EnergySnapshotModel pre-seeded with:
  energy_availability=18.0 kcal/kg FFM (< 25 male threshold = critical)
  recommended_intensity_cap=0.0
  veto_triggered=True

apply_energy_snapshot node (runs AFTER approval) reads the snapshot and scales:
  new_duration = max(1, int(duration_min * 0.0)) = 1 for all sessions.

The veto is non-overridable — sessions are already scaled before finalize_plan.
Approving persists the plan with all sessions at 1min.
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
    seed_energy_snapshot,
    simon_fresh_profile,
    STABLE_LOAD,
)

random.seed(42)

ATHLETE_ID = "e2e-s07-simon"
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
            intensity_cap=0.0,
            veto_triggered=True,
            allostatic_score=88.0,
            energy_availability=18.0,
            veto_reason="EA critique (18.0 < 25 kcal/kg FFM)",
        )
        yield db
    Base.metadata.drop_all(engine)


def test_01_create_plan_does_not_crash(scenario_db):
    """create_plan with RED-S veto snapshot completes without exception."""
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


def test_02_approve_does_not_crash(scenario_db):
    """resume_plan(approved=True) with RED-S veto completes without exception."""
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


def test_03_veto_flag_in_graph_state(scenario_db):
    """Graph state has energy_snapshot_dict with veto_triggered=True after approval."""
    config = {"configurable": {"thread_id": _state["thread_id"], "db": scenario_db}}
    graph_state = _state["svc"]._graph.get_state(config)
    snapshot = graph_state.values.get("energy_snapshot_dict")
    assert snapshot is not None
    assert snapshot["veto_triggered"] is True
    assert abs(snapshot["intensity_cap"]) < 0.01  # ~0.0


def test_04_all_sessions_at_1_minute(scenario_db):
    """All final sessions have duration_min == 1 (max(1, int(d * 0.0)) = 1)."""
    final = _state["final"]
    sessions = final.get("sessions", [])
    assert len(sessions) > 0
    for s in sessions:
        assert s["duration_min"] == 1, (
            f"Expected 1min (RED-S cap=0), got {s['duration_min']}min "
            f"for session: {s.get('workout_type')}"
        )


def test_05_db_sessions_at_1_minute(scenario_db):
    """Persisted TrainingPlanModel has sessions all at 1min in weekly_slots_json."""
    import json
    import importlib
    _m = importlib.import_module("app.db.models")
    TrainingPlanModel = _m.TrainingPlanModel

    plan = (
        scenario_db.query(TrainingPlanModel)
        .filter(TrainingPlanModel.athlete_id == ATHLETE_ID)
        .first()
    )
    assert plan is not None
    slots = json.loads(plan.weekly_slots_json)
    assert len(slots) > 0
    for slot in slots:
        assert slot["duration_min"] == 1, (
            f"DB slot has duration_min={slot['duration_min']}, expected 1"
        )
