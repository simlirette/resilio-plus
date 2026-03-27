from datetime import date, timedelta
from app.core.lifting_logic import (
    StrengthLevel, estimate_strength_level,
    compute_lifting_fatigue, generate_lifting_sessions,
)
from app.schemas.connector import HevyWorkout, HevyExercise, HevySet


def _set(reps=8, kg=60.0, rpe=7.0) -> HevySet:
    return HevySet(reps=reps, weight_kg=kg, rpe=rpe, set_type="normal")


def _exercise(name: str, sets=3) -> HevyExercise:
    return HevyExercise(name=name, sets=[_set() for _ in range(sets)])


def _workout(exercises: list[HevyExercise], days_ago=1) -> HevyWorkout:
    return HevyWorkout(
        id="h1", title="Workout",
        date=date(2026, 4, 7) - timedelta(days=days_ago),
        duration_seconds=3600,
        exercises=exercises,
    )


# estimate_strength_level

def test_estimate_strength_level_no_data_returns_beginner():
    assert estimate_strength_level([]) == StrengthLevel.BEGINNER


def test_estimate_strength_level_advanced():
    # 14 workouts with high RPE -> ADVANCED
    workouts = [_workout([_exercise("Bench Press", 4)], days_ago=i*2) for i in range(14)]
    for w in workouts:
        for ex in w.exercises:
            ex.sets = [HevySet(reps=5, weight_kg=100, rpe=9.0, set_type="normal")]
    assert estimate_strength_level(workouts) == StrengthLevel.ADVANCED


# compute_lifting_fatigue

def test_fatigue_empty_workouts_returns_zeros():
    f = compute_lifting_fatigue([])
    assert f.local_muscular == 0
    assert f.cns_load == 0
    assert f.recovery_hours == 0
    assert f.affected_muscles == []


def test_fatigue_tier3_increases_cns_load():
    # "Barbell Back Squat" is Tier 3 -> cns_load = 25
    workout = _workout([_exercise("Barbell Back Squat", 4)])
    f = compute_lifting_fatigue([workout])
    assert f.cns_load == 25.0


def test_fatigue_squat_sets_recovery_48h():
    workout = _workout([_exercise("Barbell Back Squat", 3)])
    f = compute_lifting_fatigue([workout])
    assert f.recovery_hours == 48.0


def test_fatigue_upper_body_only_sets_recovery_24h():
    workout = _workout([_exercise("Lat Pulldown", 3), _exercise("Dumbbell Bench Press", 3)])
    f = compute_lifting_fatigue([workout])
    assert f.recovery_hours == 24.0


# generate_lifting_sessions

_WEEK_START = date(2026, 4, 7)


def _gen(week_number=1, available_days=None, phase="general_prep",
         running_ratio=0.4, weeks_remaining=10):
    return generate_lifting_sessions(
        strength_level=StrengthLevel.INTERMEDIATE,
        phase=phase,
        week_number=week_number,
        weeks_remaining=weeks_remaining,
        available_days=available_days or [1, 3, 5, 6],
        hours_budget=4.0,
        volume_modifier=1.0,
        running_load_ratio=running_ratio,
        week_start=_WEEK_START,
    )


def test_generate_sessions_dup_rotation_week_0_hypertrophy():
    # week 3 -> 3 % 3 == 0 -> hypertrophy priority
    sessions = _gen(week_number=3)
    types = {s.workout_type for s in sessions}
    assert "upper_hypertrophy" in types


def test_generate_sessions_dup_rotation_week_1_strength():
    # week 1 -> 1 % 3 == 1 -> strength priority
    sessions = _gen(week_number=1)
    types = {s.workout_type for s in sessions}
    assert "upper_strength" in types


def test_generate_sessions_dup_rotation_week_2_endurance():
    # week 2 -> 2 % 3 == 2 -> endurance priority
    sessions = _gen(week_number=2)
    types = {s.workout_type for s in sessions}
    assert "full_body_endurance" in types


def test_generate_sessions_hybrid_reduction_applied_when_running_high():
    # running_ratio > 0.5 -> lower_strength shorter than default 60 min
    normal = _gen(running_ratio=0.3)
    hybrid = _gen(running_ratio=0.7)
    normal_lower = [s for s in normal if s.workout_type == "lower_strength"]
    hybrid_lower = [s for s in hybrid if s.workout_type == "lower_strength"]
    if normal_lower and hybrid_lower:
        assert hybrid_lower[0].duration_min < normal_lower[0].duration_min


def test_generate_sessions_deload_week_reduces_duration():
    normal = _gen(week_number=1)
    deload = _gen(week_number=4)  # 4 % 4 == 0 -> deload
    total_normal = sum(s.duration_min for s in normal)
    total_deload = sum(s.duration_min for s in deload)
    assert total_deload < total_normal


def test_generate_sessions_arms_hypertrophy_included():
    # week 3 (dup=0) + 4 available days -> arms_hypertrophy included
    sessions = _gen(week_number=3, available_days=[0, 2, 4, 6])
    types = {s.workout_type for s in sessions}
    assert "arms_hypertrophy" in types


def test_generate_sessions_tier1_only_in_general_prep():
    # general_prep -> upper_strength notes should mention "Tier 1"
    sessions = _gen(week_number=1, phase="general_prep")
    upper = [s for s in sessions if s.workout_type == "upper_strength"]
    if upper:
        assert "Tier 1" in upper[0].notes


def test_generate_sessions_workout_slots_have_positive_duration():
    sessions = _gen()
    assert all(s.duration_min > 0 for s in sessions)
