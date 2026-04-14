# tests/e2e/test_scenario_03_conflict_resolution.py
"""S3 — Running + Lifting conflict on same day → HeadCoach resolution.

Simon available only on Monday (available_days=[0]). Both RunningCoach and
LiftingCoach schedule on Monday. detect_conflicts finds CRITICAL conflict
(high-CNS sessions same day). resolve_conflicts + HeadCoach._arbitrate
drops the shorter session.
"""
from __future__ import annotations

import random

import pytest
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db import models as _db_models   # noqa: F401
from app.models import schemas as _v3     # noqa: F401
from app.services.coaching_service import CoachingService
from tests.fixtures.athlete_states import (
    make_scenario_engine,
    seed_athlete,
    simon_single_day_profile,
    STABLE_LOAD,
)

random.seed(42)

ATHLETE_ID = "e2e-s03-simon"
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


def test_01_create_plan_produces_sessions(scenario_db):
    """create_plan with single available day returns a valid proposed plan."""
    svc = CoachingService()
    _state["svc"] = svc

    thread_id, proposed = svc.create_plan(
        athlete_id=ATHLETE_ID,
        athlete_dict=simon_single_day_profile(),
        load_history=STABLE_LOAD,
        db=scenario_db,
    )

    assert proposed is not None
    assert len(proposed["sessions"]) > 0
    _state["thread_id"] = thread_id
    _state["proposed"] = proposed


def test_02_conflicts_detected(scenario_db):
    """Both sports land on the same date (only 1 slot available) — conflict detection ran.

    available_days=[0] means a single slot (offset 0 from week_start).
    Both RunningCoach and LiftingCoach assign their sessions to the same date.

    Per §1.2 of the interference rules, Z1/Z2 easy running + lifting on the
    same day is explicitly NOT a conflict (MICT exception). The detect_conflicts
    node therefore returns an empty list when the running session is easy_z1/z2.
    We verify the structural invariants instead:
    - The proposed dict has the 'conflicts' key (graph node ran)
    - All sessions are on the same date (single available slot)
    - If any HIIT/interval running session exists, at least 1 conflict is logged
    """
    proposed = _state["proposed"]
    assert "conflicts" in proposed, "proposed_plan_dict must contain 'conflicts' key"

    sessions = proposed["sessions"]
    # With available_days=[0], all sessions must share the same date
    dates = {s["date"] for s in sessions}
    assert len(dates) == 1, (
        f"Expected all sessions on same date (single available day), "
        f"got {dates}. Sessions: {sessions}"
    )

    # If a HIIT/interval running session was generated, conflicts must exist
    hiit_keywords = ("hiit", "interval", "vo2max", "repetition", "speed")
    has_hiit_running = any(
        s["sport"] == "running" and any(k in s.get("workout_type", "").lower() for k in hiit_keywords)
        for s in sessions
    )
    conflicts = proposed.get("conflicts", [])
    if has_hiit_running:
        assert len(conflicts) > 0, (
            f"HIIT running + lifting same day must trigger conflict. "
            f"Sessions: {sessions}"
        )


def test_03_no_two_hard_sessions_same_day(scenario_db):
    """After resolution: no date has two sessions both with cns_load > 40."""
    from collections import defaultdict
    sessions_by_date: dict[str, list[dict]] = defaultdict(list)
    for s in _state["proposed"]["sessions"]:
        sessions_by_date[s["date"]].append(s)

    for session_date, day_sessions in sessions_by_date.items():
        if len(day_sessions) < 2:
            continue
        high_cns = [
            s for s in day_sessions
            if s.get("fatigue_score", {}).get("cns_load", 0) > 40
        ]
        assert len(high_cns) < 2, (
            f"Two high-CNS sessions on {session_date}: {high_cns}"
        )


def test_04_approve_persists(scenario_db):
    """resume_plan(approved=True) persists without error."""
    svc = _state["svc"]
    final = svc.resume_plan(
        thread_id=_state["thread_id"],
        approved=True,
        feedback=None,
        db=scenario_db,
    )
    assert final is not None
    assert final.get("db_plan_id") is not None
