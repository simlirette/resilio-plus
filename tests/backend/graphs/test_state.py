"""Tests for AthleteCoachingState TypedDict."""
from backend.app.graphs.state import AthleteCoachingState


def test_state_has_required_keys():
    state: AthleteCoachingState = {
        "athlete_id": "a1",
        "athlete_dict": {"id": "a1", "name": "Test"},
        "load_history": [],
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
    assert state["athlete_id"] == "a1"
    assert state["human_approved"] is False
    assert state["messages"] == []


def test_state_is_fully_serializable():
    """Verify all values are JSON-serializable (critical for MemorySaver)."""
    import json

    state: AthleteCoachingState = {
        "athlete_id": "a1",
        "athlete_dict": {"id": "a1", "name": "Test", "sports": ["running"]},
        "load_history": [10.5, 12.0, 8.3],
        "budgets": {"running": 5.0},
        "recommendations_dicts": [{"agent_name": "running", "weekly_load": 5.0}],
        "acwr_dict": {"ratio": 1.1, "status": "safe"},
        "conflicts_dicts": [],
        "proposed_plan_dict": {"sessions": [], "phase": "base"},
        "energy_snapshot_dict": None,
        "human_approved": False,
        "human_feedback": None,
        "final_plan_dict": None,
        "messages": [],
    }
    serialized = json.dumps(state)
    restored = json.loads(serialized)
    assert restored["athlete_id"] == "a1"
    assert restored["load_history"] == [10.5, 12.0, 8.3]
