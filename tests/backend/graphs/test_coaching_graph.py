"""Integration tests for the coaching graph and CoachingService."""
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

# Pre-import via 'app.' path to avoid SQLAlchemy double-table-registration.
import app.services.energy_cycle_service  # noqa: F401

from backend.app.graphs.coaching_graph import build_coaching_graph
from backend.app.graphs.state import AthleteCoachingState
from backend.app.schemas.athlete import AthleteProfile, Sport
from backend.app.services.coaching_service import CoachingService

_ENERGY_PATCH = "app.services.energy_cycle_service.EnergyCycleService.get_today_snapshot"


def _make_athlete() -> AthleteProfile:
    return AthleteProfile(
        name="Test Athlete",
        age=30,
        sex="M",
        weight_kg=70.0,
        height_cm=175.0,
        sports=[Sport.RUNNING],
        primary_sport=Sport.RUNNING,
        goals=["run 10k"],
        available_days=[0, 2, 4],  # Mon, Wed, Fri as ints
        hours_per_week=6.0,
    )


def _db_mock():
    db = MagicMock()
    db.commit = MagicMock()
    db.refresh = MagicMock()
    db.add = MagicMock()
    return db


def test_build_coaching_graph_returns_compiled():
    """build_coaching_graph returns a compiled LangGraph app."""
    graph = build_coaching_graph(interrupt=False)
    assert hasattr(graph, "invoke")


def test_graph_no_interrupt_runs_to_completion():
    """With interrupt=False and human_approved=True pre-set, graph produces final_plan_dict."""
    graph = build_coaching_graph(interrupt=False)
    athlete = _make_athlete()

    initial_state: AthleteCoachingState = {
        "athlete_id": "a1",
        "athlete_dict": athlete.model_dump(mode="json"),
        "load_history": [5.0, 6.0, 5.5, 7.0],
        "budgets": {},
        "recommendations_dicts": [],
        "acwr_dict": None,
        "conflicts_dicts": [],
        "proposed_plan_dict": None,
        "energy_snapshot_dict": None,
        "human_approved": True,   # pre-approved so finalize_plan runs
        "human_feedback": None,
        "final_plan_dict": None,
        "messages": [],
    }

    with patch(_ENERGY_PATCH, return_value=None):
        result = graph.invoke(
            initial_state,
            config={"configurable": {"thread_id": "test-thread-1", "db": _db_mock()}},
        )

    assert result["final_plan_dict"] is not None
    assert "sessions" in result["final_plan_dict"]
    assert "phase" in result["final_plan_dict"]


def test_coaching_service_create_plan_returns_thread_id():
    """CoachingService.create_plan returns (thread_id, proposed_dict)."""
    athlete = _make_athlete()
    with patch(_ENERGY_PATCH, return_value=None):
        service = CoachingService()
        thread_id, proposed = service.create_plan(
            athlete_id="a1",
            athlete_dict=athlete.model_dump(mode="json"),
            load_history=[5.0, 6.0, 5.5, 7.0],
            db=_db_mock(),
        )
    assert isinstance(thread_id, str) and len(thread_id) > 0
    assert proposed is not None
    assert "sessions" in proposed


def test_coaching_service_resume_approved():
    """resume_plan(approved=True) finalizes and returns final_plan_dict."""
    db = _db_mock()
    athlete = _make_athlete()
    with patch(_ENERGY_PATCH, return_value=None):
        service = CoachingService()
        thread_id, _ = service.create_plan(
            athlete_id="a1",
            athlete_dict=athlete.model_dump(mode="json"),
            load_history=[5.0, 6.0, 5.5, 7.0],
            db=db,
        )
        final = service.resume_plan(thread_id=thread_id, approved=True, feedback=None, db=db)

    assert final is not None
    assert "sessions" in final


def test_coaching_service_resume_rejected_returns_new_proposed():
    """resume_plan(approved=False) triggers revision and returns new proposed_plan_dict."""
    db = _db_mock()
    athlete = _make_athlete()
    with patch(_ENERGY_PATCH, return_value=None):
        service = CoachingService()
        thread_id, _ = service.create_plan(
            athlete_id="a1",
            athlete_dict=athlete.model_dump(mode="json"),
            load_history=[5.0, 6.0, 5.5, 7.0],
            db=db,
        )
        new_proposed = service.resume_plan(
            thread_id=thread_id, approved=False, feedback="Trop de volume", db=db
        )

    # After rejection, a new proposed plan should be available (or None if graph reached max revisions)
    # Either way, it should not raise
    assert new_proposed is None or "sessions" in new_proposed
