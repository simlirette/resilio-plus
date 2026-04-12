"""Unit and integration tests for the weekly review graph and WeeklyReviewState."""
import uuid
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest

# Pre-import via 'app.' path to avoid SQLAlchemy double-table-registration.
import app.services.energy_cycle_service  # noqa: F401
import app.db.models  # noqa: F401 — registers all ORM models (EnergySnapshotModel etc.)

from backend.app.graphs.weekly_review_graph import (
    WeeklyReviewState,
    build_weekly_review_graph,
    analyze_actual_vs_planned,
    compute_new_acwr,
    update_athlete_state,
    apply_adjustments,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DEFAULT_LOAD_HISTORY = [3.0, 4.0, 3.5, 4.0, 3.0, 4.0, 3.5]
_SENTINEL = object()


def _make_initial_state(
    athlete_id: str = "a1",
    plan_id: str | None = None,
    load_history=_SENTINEL,
    human_approved: bool = True,
) -> WeeklyReviewState:
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    if load_history is _SENTINEL:
        load_history = _DEFAULT_LOAD_HISTORY
    return {
        "athlete_id": athlete_id,
        "plan_id": plan_id,
        "week_start": week_start.isoformat(),
        "week_number": 3,
        "sessions_planned": 0,
        "sessions_completed": 0,
        "completion_rate": 0.0,
        "actual_hours": 0.0,
        "load_history": list(load_history),
        "acwr_dict": None,
        "review_summary_dict": None,
        "human_approved": human_approved,
        "db_review_id": None,
        "messages": [],
    }


def _db_mock(sessions_completed: int = 3):
    """Create a mock DB session that returns sensible defaults."""
    db = MagicMock()
    db.commit = MagicMock()
    db.refresh = MagicMock()
    db.add = MagicMock()

    mock_query = MagicMock()
    mock_query.filter.return_value = mock_query
    mock_query.count.return_value = sessions_completed
    mock_query.all.return_value = []
    db.query.return_value = mock_query
    db.get.return_value = None  # no plan by default
    return db


# ---------------------------------------------------------------------------
# Build tests
# ---------------------------------------------------------------------------

def test_build_weekly_review_graph_returns_compiled():
    """build_weekly_review_graph returns a compiled LangGraph application."""
    graph = build_weekly_review_graph(interrupt=False)
    assert hasattr(graph, "invoke")


def test_build_weekly_review_graph_with_interrupt():
    """build_weekly_review_graph(interrupt=True) compiles successfully."""
    graph = build_weekly_review_graph(interrupt=True)
    assert hasattr(graph, "invoke")


# ---------------------------------------------------------------------------
# No-interrupt full-run tests
# ---------------------------------------------------------------------------

def test_graph_no_interrupt_runs_to_completion():
    """With interrupt=False and human_approved=True, graph completes without pausing."""
    graph = build_weekly_review_graph(interrupt=False)
    state = _make_initial_state(human_approved=True)
    config = {"configurable": {"thread_id": str(uuid.uuid4()), "db": _db_mock()}}

    result = graph.invoke(state, config=config)

    assert result is not None
    assert "review_summary_dict" in result
    assert result["review_summary_dict"] is not None


def test_graph_no_interrupt_human_approved_false_does_not_write_db():
    """With human_approved=False, apply_adjustments does not commit to DB."""
    graph = build_weekly_review_graph(interrupt=False)
    state = _make_initial_state(human_approved=False)
    db = _db_mock()
    config = {"configurable": {"thread_id": str(uuid.uuid4()), "db": db}}

    result = graph.invoke(state, config=config)

    db.commit.assert_not_called()
    assert result["db_review_id"] is None


def test_graph_no_interrupt_creates_db_review_when_approved():
    """With human_approved=True, apply_adjustments calls db.add and db.commit."""
    graph = build_weekly_review_graph(interrupt=False)
    state = _make_initial_state(human_approved=True)
    db = _db_mock()
    config = {"configurable": {"thread_id": str(uuid.uuid4()), "db": db}}

    result = graph.invoke(state, config=config)

    db.add.assert_called_once()
    db.commit.assert_called_once()
    assert result["db_review_id"] is not None


# ---------------------------------------------------------------------------
# Node unit tests
# ---------------------------------------------------------------------------

def test_analyze_actual_vs_planned_no_plan():
    """analyze_actual_vs_planned with no plan returns 0 sessions_planned."""
    state = _make_initial_state()
    db = _db_mock(sessions_completed=2)
    config = {"configurable": {"thread_id": "t1", "db": db}}

    partial = analyze_actual_vs_planned(state, config)

    assert partial["sessions_planned"] == 0
    assert partial["sessions_completed"] == 2
    assert partial["completion_rate"] == 0.0


def test_analyze_actual_vs_planned_computes_completion_rate():
    """analyze_actual_vs_planned computes correct completion_rate when plan provided."""
    state = _make_initial_state()

    today = date.today()
    week_start = today - timedelta(days=today.weekday())

    mock_plan = MagicMock()
    mock_plan.weekly_slots_json = (
        f'[{{"week_start": "{week_start.isoformat()}", "sessions": [1, 2, 3, 4]}}]'
    )

    db = _db_mock(sessions_completed=3)
    db.get.return_value = mock_plan

    config = {"configurable": {"thread_id": "t1", "db": db}}
    state_with_plan = {**state, "plan_id": "plan-1"}

    partial = analyze_actual_vs_planned(state_with_plan, config)

    assert partial["sessions_planned"] == 4
    assert partial["sessions_completed"] == 3
    assert abs(partial["completion_rate"] - 0.75) < 0.001


def test_compute_new_acwr_with_history():
    """compute_new_acwr produces acwr_dict when load_history is non-empty."""
    state = _make_initial_state(load_history=[3.0, 4.0, 3.5, 4.0, 3.0, 4.0, 3.5, 4.0] * 4)
    config = {"configurable": {"thread_id": "t1", "db": MagicMock()}}

    partial = compute_new_acwr(state, config)

    assert partial["acwr_dict"] is not None
    assert "ratio" in partial["acwr_dict"]
    assert "status" in partial["acwr_dict"]


def test_compute_new_acwr_empty_history():
    """compute_new_acwr with empty load_history returns None acwr_dict."""
    state = _make_initial_state(load_history=[])
    config = {"configurable": {"thread_id": "t1", "db": MagicMock()}}

    partial = compute_new_acwr(state, config)

    assert partial["acwr_dict"] is None


def test_update_athlete_state_builds_summary():
    """update_athlete_state assembles review_summary_dict with all required keys."""
    state = _make_initial_state()
    state = {
        **state,
        "sessions_planned": 4,
        "sessions_completed": 3,
        "completion_rate": 0.75,
        "actual_hours": 3.5,
        "acwr_dict": {
            "ratio": 1.1,
            "status": "safe",
            "acute_7d": 3.5,
            "chronic_28d": 3.2,
            "max_safe_weekly_load": 5.0,
        },
    }
    config = {"configurable": {"thread_id": "t1", "db": MagicMock()}}

    partial = update_athlete_state(state, config)

    summary = partial["review_summary_dict"]
    assert summary is not None
    assert summary["sessions_planned"] == 4
    assert summary["sessions_completed"] == 3
    assert summary["acwr"] == 1.1
    assert summary["readiness"] == "green"
    assert isinstance(summary["recommendations"], list)


def test_apply_adjustments_approved_writes_review():
    """apply_adjustments with human_approved=True writes WeeklyReviewModel to DB."""
    state = _make_initial_state(human_approved=True)
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    state = {
        **state,
        "review_summary_dict": {
            "week_number": 3,
            "week_start": week_start.isoformat(),
            "sessions_planned": 4,
            "sessions_completed": 3,
            "completion_rate": 0.75,
            "actual_hours": 3.5,
            "acwr": 1.1,
            "readiness": "green",
            "recommendations": [],
        },
        "acwr_dict": {
            "ratio": 1.1,
            "status": "safe",
            "acute_7d": 3.5,
            "chronic_28d": 3.2,
            "max_safe_weekly_load": 5.0,
        },
    }
    db = _db_mock()
    config = {"configurable": {"thread_id": "t1", "db": db}}

    partial = apply_adjustments(state, config)

    db.add.assert_called_once()
    db.commit.assert_called_once()
    assert partial["db_review_id"] is not None
    assert len(partial["db_review_id"]) == 36  # UUID format


def test_apply_adjustments_declined_no_db_write():
    """apply_adjustments with human_approved=False skips DB write."""
    state = _make_initial_state(human_approved=False)
    db = _db_mock()
    config = {"configurable": {"thread_id": "t1", "db": db}}

    partial = apply_adjustments(state, config)

    db.add.assert_not_called()
    db.commit.assert_not_called()
    assert partial["db_review_id"] is None


# ---------------------------------------------------------------------------
# Interrupt + resume tests
# ---------------------------------------------------------------------------

def test_graph_with_interrupt_pauses_before_present_review():
    """With interrupt=True, graph pauses before present_review node."""
    graph = build_weekly_review_graph(interrupt=True)
    state = _make_initial_state(human_approved=False)
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id, "db": _db_mock()}}

    result = graph.invoke(state, config=config)

    assert result.get("db_review_id") is None
    assert result.get("review_summary_dict") is not None


def test_graph_interrupt_then_resume_approved():
    """Full interrupt → resume(approved=True) flow creates DB review."""
    graph = build_weekly_review_graph(interrupt=True)
    state = _make_initial_state(human_approved=False)
    thread_id = str(uuid.uuid4())
    db = _db_mock()
    config = {"configurable": {"thread_id": thread_id, "db": db}}

    graph.invoke(state, config=config)
    graph.update_state(config, {"human_approved": True}, as_node="present_review")
    result = graph.invoke(None, config=config)

    db.add.assert_called_once()
    db.commit.assert_called_once()
    assert result.get("db_review_id") is not None


def test_graph_interrupt_then_resume_declined():
    """Full interrupt → resume(approved=False) flow does not write to DB."""
    graph = build_weekly_review_graph(interrupt=True)
    state = _make_initial_state(human_approved=False)
    thread_id = str(uuid.uuid4())
    db = _db_mock()
    config = {"configurable": {"thread_id": thread_id, "db": db}}

    graph.invoke(state, config=config)
    graph.update_state(config, {"human_approved": False}, as_node="present_review")
    result = graph.invoke(None, config=config)

    db.commit.assert_not_called()
    assert result.get("db_review_id") is None
