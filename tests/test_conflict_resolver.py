"""Tests for agents/head_coach/resolver.py — ConflictResolver."""
import pytest


def _make_minimal_state(acwr: float):
    """Create a minimal AthleteState with given ACWR."""
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
            "training_split": "upper_lower", "sessions_per_week": 3,
            "progression_model": "double_progression", "rir_target_range": [1, 3],
        },
        nutrition_profile={
            "tdee_estimated": 2600,
            "macros_target": {"protein_g": 150, "carbs_g": 280, "fat_g": 70},
        },
    )
    state.acwr_computed = acwr
    state.fatigue.acwr = acwr
    return state


_MOCK_PLANS = {
    "running": {"agent": "running_coach", "sessions": [], "coaching_notes": []},
    "lifting": {"agent": "lifting_coach", "sessions": [], "coaching_notes": []},
}


def test_no_conflicts_returns_unchanged_plans():
    """ACWR = 1.0 (safe zone) → plans unchanged, log is empty."""
    from agents.head_coach.resolver import ConflictResolver

    state = _make_minimal_state(acwr=1.0)
    resolver = ConflictResolver()
    resolved, log = resolver.resolve(state, _MOCK_PLANS)

    assert "intensity_reduction_pct" not in resolved.get("running", {})
    assert "volume_reduction_pct" not in resolved.get("running", {})
    assert log == []


def test_acwr_overload_adds_volume_reduction():
    """ACWR = 1.4 (1.3–1.5 caution zone) → volume_reduction_pct=20 in both plans."""
    from agents.head_coach.resolver import ConflictResolver

    state = _make_minimal_state(acwr=1.4)
    resolver = ConflictResolver()
    resolved, log = resolver.resolve(state, _MOCK_PLANS)

    assert resolved["running"]["volume_reduction_pct"] == 20
    assert resolved["lifting"]["volume_reduction_pct"] == 20
    assert len(log) == 1
    assert "acwr_overload" in log[0]


def test_acwr_danger_adds_intensity_reduction():
    """ACWR = 1.6 (>1.5 danger zone) → intensity_reduction_pct=30, tier_max=1 in both plans."""
    from agents.head_coach.resolver import ConflictResolver

    state = _make_minimal_state(acwr=1.6)
    resolver = ConflictResolver()
    resolved, log = resolver.resolve(state, _MOCK_PLANS)

    assert resolved["running"]["intensity_reduction_pct"] == 30
    assert resolved["running"]["tier_max"] == 1
    assert resolved["lifting"]["intensity_reduction_pct"] == 30
    assert resolved["lifting"]["tier_max"] == 1
    assert len(log) == 1
    assert "acwr_danger" in log[0]


def test_resolve_returns_tuple_of_dict_and_list():
    """resolve() always returns (dict, list[str]) even with no conflicts."""
    from agents.head_coach.resolver import ConflictResolver

    state = _make_minimal_state(acwr=0.9)
    resolver = ConflictResolver()
    result = resolver.resolve(state, {})

    assert isinstance(result, tuple)
    assert len(result) == 2
    resolved, log = result
    assert isinstance(resolved, dict)
    assert isinstance(log, list)
