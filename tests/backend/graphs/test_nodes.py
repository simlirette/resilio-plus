"""Unit tests for coaching graph node functions."""
import dataclasses
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

# Pre-import via the 'app.' path to avoid SQLAlchemy double-table-registration.
# The pytest pythonpath config adds 'backend/' so 'app.' is the correct root.
# The nodes.py uses a lazy relative import which resolves to 'backend.app.services…'
# — a different module key. By importing here first via 'app.' we ensure the
# models are registered once; the lazy import in the node then reuses sys.modules.
import app.services.energy_cycle_service  # noqa: F401

from backend.app.graphs.nodes import (
    analyze_profile,
    apply_energy_snapshot,
    build_proposed_plan,
    compute_acwr,
    delegate_specialists,
    detect_conflicts_node,
    finalize_plan,
    merge_recommendations,
    present_to_athlete,
    resolve_conflicts_node,
    revise_plan,
)
from backend.app.graphs.state import AthleteCoachingState
from backend.app.schemas.athlete import AthleteProfile, Sport


def _base_state() -> AthleteCoachingState:
    athlete = AthleteProfile(
        name="Test Athlete",
        age=30,
        sex="M",
        weight_kg=70.0,
        height_cm=175.0,
        sports=[Sport.RUNNING],
        primary_sport=Sport.RUNNING,
        goals=["run 10k"],
        available_days=[0, 2, 4],
        hours_per_week=6.0,
    )
    athlete_id = str(athlete.id)
    return {
        "athlete_id": athlete_id,
        "athlete_dict": athlete.model_dump(mode="json"),
        "load_history": [5.0, 6.0, 5.5, 7.0],
        "budgets": {},
        "recommendations_dicts": [],
        "acwr_dict": None,
        "conflicts_dicts": [],
        "proposed_plan_dict": None,
        "energy_snapshot_dict": None,
        "human_approved": False,
        "human_feedback": None,
        "final_plan_dict": None,
        "messages": [],
    }


def test_analyze_profile_populates_budgets():
    state = _base_state()
    result = analyze_profile(state, config={"configurable": {}})
    assert "budgets" in result
    budgets = result["budgets"]
    assert "running" in budgets
    assert abs(sum(budgets.values()) - 6.0) < 0.01


def test_compute_acwr_populates_acwr_dict():
    state = _base_state()
    state["recommendations_dicts"] = [
        {
            "agent_name": "running",
            "weekly_load": 6.0,
            "fatigue_score": {"local_muscular": 30.0, "cns_load": 20.0, "metabolic_cost": 25.0, "recovery_hours": 24.0, "affected_muscles": []},
            "suggested_sessions": [],
            "readiness_modifier": 1.0,
            "notes": "",
        }
    ]
    result = compute_acwr(state, config={"configurable": {}})
    assert result["acwr_dict"] is not None
    assert "ratio" in result["acwr_dict"]
    assert "status" in result["acwr_dict"]


def test_delegate_specialists_returns_recommendations():
    state = _base_state()
    state["budgets"] = {"running": 6.0}
    result = delegate_specialists(state, config={"configurable": {}})
    assert "recommendations_dicts" in result
    assert isinstance(result["recommendations_dicts"], list)
    assert len(result["recommendations_dicts"]) >= 1
    rec = result["recommendations_dicts"][0]
    assert "agent_name" in rec
    assert "weekly_load" in rec


def test_merge_recommendations_is_passthrough():
    state = _base_state()
    result = merge_recommendations(state, config={"configurable": {}})
    # No-op: just returns empty dict or messages
    assert isinstance(result, dict)


def test_detect_conflicts_node_returns_conflicts_dicts():
    state = _base_state()
    state["recommendations_dicts"] = []
    result = detect_conflicts_node(state, config={"configurable": {}})
    assert "conflicts_dicts" in result
    assert isinstance(result["conflicts_dicts"], list)


def test_resolve_conflicts_node_drops_shorter_session():
    """resolve_conflicts_node drops the shorter session from a CRITICAL conflict pair."""
    from datetime import date
    state = _base_state()
    today = str(date.today())
    fatigue = {"local_muscular": 30.0, "cns_load": 20.0, "metabolic_cost": 25.0, "recovery_hours": 24.0, "affected_muscles": []}
    # Two recommendations with HIIT sessions on the same day — triggers CRITICAL conflict
    state["recommendations_dicts"] = [
        {
            "agent_name": "running",
            "weekly_load": 6.0,
            "fatigue_score": fatigue,
            "suggested_sessions": [
                {"id": "s1", "date": today, "sport": "running", "workout_type": "hiit_interval", "duration_min": 60, "fatigue_score": fatigue, "notes": ""}
            ],
            "readiness_modifier": 1.0,
            "notes": "",
        },
        {
            "agent_name": "lifting",
            "weekly_load": 3.0,
            "fatigue_score": fatigue,
            "suggested_sessions": [
                {"id": "s2", "date": today, "sport": "lifting", "workout_type": "hiit_strength", "duration_min": 45, "fatigue_score": fatigue, "notes": ""}
            ],
            "readiness_modifier": 1.0,
            "notes": "",
        },
    ]
    # Set a CRITICAL conflict between running and lifting on this day
    state["conflicts_dicts"] = [
        {"severity": "critical", "rule": "dual_hiit", "agents": ["running", "lifting"], "message": "Two HIIT sessions on same day"}
    ]
    result = resolve_conflicts_node(state, config={"configurable": {}})
    assert "recommendations_dicts" in result
    # Collect all sessions from result
    all_sessions = []
    for rec in result["recommendations_dicts"]:
        all_sessions.extend(rec.get("suggested_sessions", []))
    # The 45-min lifting session (shorter) should be dropped; the 60-min running session should remain
    session_ids = [s["id"] for s in all_sessions]
    assert "s1" in session_ids, "Longer session (60 min) should be kept"
    assert "s2" not in session_ids, "Shorter session (45 min) should be dropped"
    # conflicts_dicts should be cleared
    assert result.get("conflicts_dicts") == []


def test_build_proposed_plan_populates_proposed_plan_dict():
    state = _base_state()
    state["budgets"] = {"running": 6.0}
    state["recommendations_dicts"] = [
        {
            "agent_name": "running",
            "weekly_load": 6.0,
            "fatigue_score": {"local_muscular": 30.0, "cns_load": 20.0, "metabolic_cost": 25.0, "recovery_hours": 24.0, "affected_muscles": []},
            "suggested_sessions": [
                {
                    "id": "s1",
                    "date": str(date.today()),
                    "sport": "running",
                    "workout_type": "easy_z1",
                    "duration_min": 60,
                    "fatigue_score": {"local_muscular": 20.0, "cns_load": 10.0, "metabolic_cost": 15.0, "recovery_hours": 12.0, "affected_muscles": []},
                    "notes": "",
                }
            ],
            "readiness_modifier": 1.0,
            "notes": "",
        }
    ]
    state["acwr_dict"] = {
        "ratio": 1.1,
        "status": "safe",
        "acute_7d": 6.0,
        "chronic_28d": 5.5,
        "max_safe_weekly_load": 8.0,
    }
    state["conflicts_dicts"] = []
    result = build_proposed_plan(state, config={"configurable": {}})
    assert result["proposed_plan_dict"] is not None
    assert "sessions" in result["proposed_plan_dict"]
    assert "phase" in result["proposed_plan_dict"]


def test_apply_energy_snapshot_no_snapshot():
    state = _base_state()
    state["proposed_plan_dict"] = {"sessions": [], "phase": "base", "readiness_level": "green"}
    # Patch via app. path (pre-imported above to avoid double-table-registration).
    with patch("app.services.energy_cycle_service.EnergyCycleService.get_today_snapshot", return_value=None):
        result = apply_energy_snapshot(state, config={"configurable": {"db": MagicMock()}})
    assert result.get("energy_snapshot_dict") is None


def test_present_to_athlete_returns_message():
    state = _base_state()
    result = present_to_athlete(state, config={"configurable": {}})
    assert isinstance(result, dict)
    # Should add a message
    assert "messages" in result


def test_revise_plan_clears_proposed_plan():
    state = _base_state()
    state["human_feedback"] = "Trop de volume"
    state["proposed_plan_dict"] = {"sessions": [], "phase": "base"}
    result = revise_plan(state, config={"configurable": {}})
    assert result.get("proposed_plan_dict") is None
    assert result.get("human_approved") is False
    assert result.get("human_feedback") is None


def test_finalize_plan_raises_without_approval():
    state = _base_state()
    state["proposed_plan_dict"] = {"sessions": [], "phase": "base", "readiness_level": "green", "acwr": {"ratio": 1.0, "status": "safe", "acute_7d": 5.0, "chronic_28d": 5.0, "max_safe_weekly_load": 8.0}, "conflicts": [], "global_fatigue": {}, "notes": []}
    state["human_approved"] = False
    db_mock = MagicMock()
    with pytest.raises(ValueError, match="human_approved"):
        finalize_plan(state, config={"configurable": {"db": db_mock}})


def test_finalize_plan_persists_when_approved():
    state = _base_state()
    state["proposed_plan_dict"] = {
        "sessions": [],
        "phase": "base",
        "readiness_level": "green",
        "acwr": {"ratio": 1.0, "status": "safe", "acute_7d": 5.0, "chronic_28d": 5.0, "max_safe_weekly_load": 8.0},
        "conflicts": [],
        "global_fatigue": {},
        "notes": [],
    }
    state["human_approved"] = True
    db_mock = MagicMock()
    db_mock.commit = MagicMock()
    db_mock.refresh = MagicMock()
    db_mock.add = MagicMock()
    result = finalize_plan(state, config={"configurable": {"db": db_mock}})
    assert result["final_plan_dict"] is not None
    db_mock.add.assert_called_once()
    db_mock.commit.assert_called_once()
