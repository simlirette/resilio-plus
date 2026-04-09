"""Tests for core/constraint_matrix.py — build_constraint_matrix()."""
import pytest


def _make_state(available_days: dict, lifting_sessions: int):
    """Helper: minimal AthleteState with custom availability."""
    from datetime import UTC, datetime
    from uuid import UUID
    from models.athlete_state import AthleteState

    return AthleteState(
        athlete_id=UUID("00000000-0000-0000-0000-000000000001"),
        updated_at=datetime.now(UTC),
        profile={
            "first_name": "Test",
            "age": 30,
            "sex": "M",
            "weight_kg": 75.0,
            "height_cm": 175,
            "active_sports": ["running", "lifting"],
            "available_days": available_days,
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
        current_phase={"macrocycle": "base_building", "mesocycle_week": 1, "mesocycle_length": 4},
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
            "training_split": "upper_lower",
            "sessions_per_week": lifting_sessions,
            "progression_model": "double_progression",
            "rir_target_range": [1, 3],
        },
        nutrition_profile={
            "tdee_estimated": 2600,
            "macros_target": {"protein_g": 150, "carbs_g": 280, "fat_g": 70},
        },
    )


_SIX_DAYS = {
    "monday":    {"available": True,  "max_hours": 1.5},
    "tuesday":   {"available": True,  "max_hours": 1.5},
    "wednesday": {"available": True,  "max_hours": 1.0},
    "thursday":  {"available": True,  "max_hours": 1.5},
    "friday":    {"available": False, "max_hours": 0},
    "saturday":  {"available": True,  "max_hours": 2.5},
    "sunday":    {"available": True,  "max_hours": 2.0},
}


def test_all_available_days_appear_in_result():
    """Every key in the result is a day name; all 7 days are present."""
    from core.constraint_matrix import build_constraint_matrix

    state = _make_state(_SIX_DAYS, lifting_sessions=2)
    result = build_constraint_matrix(state)

    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for day in days:
        assert day in result, f"Missing day: {day}"


def test_lifting_days_non_consecutive():
    """With 2 lifting sessions, no two lifted days are adjacent."""
    from core.constraint_matrix import build_constraint_matrix

    state = _make_state(_SIX_DAYS, lifting_sessions=2)
    result = build_constraint_matrix(state)

    day_order = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    lifting_days = [
        d for d in day_order
        if any(s["sport"] == "lifting" for s in result[d]["sessions"])
    ]
    assert len(lifting_days) == 2
    for i in range(len(lifting_days) - 1):
        idx_a = day_order.index(lifting_days[i])
        idx_b = day_order.index(lifting_days[i + 1])
        assert abs(idx_b - idx_a) > 1, f"Consecutive lifting days: {lifting_days[i]}, {lifting_days[i+1]}"


def test_running_fills_remaining_available_days():
    """Running sessions fill the available days not taken by lifting."""
    from core.constraint_matrix import build_constraint_matrix

    state = _make_state(_SIX_DAYS, lifting_sessions=2)
    result = build_constraint_matrix(state)

    running_days = [
        d for d in result
        if d not in ("total_sessions", "running_days", "lifting_days")
        and any(s["sport"] == "running" for s in result[d]["sessions"])
    ]
    assert result["running_days"] == len(running_days)
    assert result["lifting_days"] == 2
    assert result["total_sessions"] == result["running_days"] + result["lifting_days"]


def test_empty_available_days_no_crash():
    """No available days → empty schedule, no crash."""
    from core.constraint_matrix import build_constraint_matrix

    no_days = {d: {"available": False, "max_hours": 0} for d in
               ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]}
    state = _make_state(no_days, lifting_sessions=2)
    result = build_constraint_matrix(state)

    assert result["total_sessions"] == 0
    assert result["lifting_days"] == 0
    assert result["running_days"] == 0


def test_unavailable_day_has_no_sessions():
    """Friday (available=False in _SIX_DAYS) must have sessions=[]."""
    from core.constraint_matrix import build_constraint_matrix

    state = _make_state(_SIX_DAYS, lifting_sessions=2)
    result = build_constraint_matrix(state)

    assert result["friday"]["sessions"] == []
    assert result["friday"]["available"] is False
