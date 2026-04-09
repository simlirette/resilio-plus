"""Tests for agents/head_coach/merger.py — PlanMerger."""


def _make_state_with_schedule():
    """Simon-like state with a pre-built constraint matrix schedule."""
    from datetime import UTC, datetime
    from uuid import UUID
    from models.athlete_state import AthleteState

    state = AthleteState(
        athlete_id=UUID("00000000-0000-0000-0000-000000000001"),
        updated_at=datetime.now(UTC),
        profile={
            "first_name": "Test", "age": 30, "sex": "M",
            "weight_kg": 75.0, "height_cm": 175,
            "active_sports": ["running", "lifting"],
            "available_days": {},
            "training_history": {
                "total_years_training": 3, "years_running": 1, "years_lifting": 2,
                "years_swimming": 0, "current_weekly_volume_hours": 5,
            },
            "lifestyle": {
                "work_type": "desk_sedentary", "work_hours_per_day": 8,
                "commute_active": False, "sleep_avg_hours": 7, "stress_level": "low",
            },
            "goals": {"primary": "get_fit", "timeline_weeks": 12},
            "equipment": {"gym_access": True, "pool_access": False, "outdoor_running": True},
        },
        current_phase={"macrocycle": "base_building", "mesocycle_week": 3, "mesocycle_length": 4},
        running_profile={
            "vdot": 38.2,
            "training_paces": {
                "easy_min_per_km": "6:24", "easy_max_per_km": "7:06",
                "threshold_pace_per_km": "5:18", "interval_pace_per_km": "4:48",
                "repetition_pace_per_km": "4:24", "long_run_pace_per_km": "6:36",
            },
            "weekly_km_current": 20, "weekly_km_target": 30, "max_long_run_km": 10,
        },
        lifting_profile={
            "training_split": "upper_lower", "sessions_per_week": 2,
            "progression_model": "double_progression", "rir_target_range": [1, 3],
        },
        nutrition_profile={
            "tdee_estimated": 2600,
            "macros_target": {"protein_g": 150, "carbs_g": 280, "fat_g": 70},
        },
    )
    # Pre-built schedule: monday=lifting, tuesday=running, thursday=lifting, saturday=running
    state.constraint_matrix.schedule = {
        "monday":    {"available": True,  "sessions": [{"sport": "lifting", "type": "primary"}]},
        "tuesday":   {"available": True,  "sessions": [{"sport": "running", "type": "primary"}]},
        "wednesday": {"available": False, "sessions": []},
        "thursday":  {"available": True,  "sessions": [{"sport": "lifting", "type": "primary"}]},
        "friday":    {"available": False, "sessions": []},
        "saturday":  {"available": True,  "sessions": [{"sport": "running", "type": "primary"}]},
        "sunday":    {"available": False, "sessions": []},
    }
    state.fatigue.acwr = 1.05
    return state


_MOCK_RUNNING_PLAN = {
    "agent": "running_coach",
    "sessions": [
        {"type": "easy", "distance_km": 6.0, "notes": "Easy Z1 run"},
        {"type": "long_run", "distance_km": 12.0, "notes": "Long run Z1"},
    ],
    "coaching_notes": [],
}

_MOCK_LIFTING_PLAN = {
    "agent": "lifting_coach",
    "sessions": [
        {"type": "upper_hypertrophy", "exercises": []},
        {"type": "lower_strength", "exercises": []},
    ],
    "coaching_notes": [],
}


def test_merge_returns_unified_structure():
    """merge() returns dict with all required keys."""
    from agents.head_coach.merger import PlanMerger

    state = _make_state_with_schedule()
    partial = {"running": _MOCK_RUNNING_PLAN, "lifting": _MOCK_LIFTING_PLAN}
    result = PlanMerger().merge(state, partial, conflict_log=[])

    assert result["agent"] == "head_coach"
    assert "week" in result
    assert "phase" in result
    assert "sessions" in result
    assert isinstance(result["sessions"], list)
    assert "acwr" in result
    assert "conflicts_resolved" in result
    assert "coaching_summary" in result


def test_sessions_sorted_by_day():
    """Sessions in the unified plan appear in Monday→Sunday order."""
    from agents.head_coach.merger import PlanMerger

    _DAY_ORDER = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    state = _make_state_with_schedule()
    partial = {"running": _MOCK_RUNNING_PLAN, "lifting": _MOCK_LIFTING_PLAN}
    result = PlanMerger().merge(state, partial, conflict_log=[])

    session_days = [s["day"] for s in result["sessions"] if s["day"] in _DAY_ORDER]
    assert session_days == sorted(session_days, key=lambda d: _DAY_ORDER.index(d))


def test_conflict_log_included():
    """conflict_log passed to merge() appears as conflicts_resolved in the plan."""
    from agents.head_coach.merger import PlanMerger

    state = _make_state_with_schedule()
    log = ["acwr_overload:1.40 → volume_reduction_pct=20"]
    result = PlanMerger().merge(state, {}, conflict_log=log)

    assert result["conflicts_resolved"] == log
