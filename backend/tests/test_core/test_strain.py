"""Tests for compute_muscle_strain() — synthetic data, no network.

Each test verifies a specific aspect of the formula using minimal data:
  - One workout/activity in the last 7 days (acute window)
  - No chronic history → EWMA_28d converges to a small value
    so normalized score > 0 for the tested muscles.

The EWMA formula: if all 28 days have load=0 except the last day,
EWMA_7d > EWMA_28d, so score = min(100, EWMA_7d/EWMA_28d * 100) == 100.0.
When EWMA_28d == 0 (no history at all), score == 0.0.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

import pytest


def _make_hevy_workout(
    exercise_name: str,
    weight_kg: float,
    reps: int,
    rpe: float | None,
    workout_date: date,
) -> object:
    from app.schemas.connector import HevyExercise, HevySet, HevyWorkout
    s = HevySet(reps=reps, weight_kg=weight_kg, rpe=rpe, set_type="normal")
    ex = HevyExercise(name=exercise_name, sets=[s])
    return HevyWorkout(
        id="test-1",
        title="Test Workout",
        date=workout_date,
        duration_seconds=3600,
        exercises=[ex],
    )


def _make_strava_run(duration_seconds: int, rpe: int, run_date: date) -> object:
    from app.schemas.connector import StravaActivity
    return StravaActivity(
        id="strava-1",
        name="Morning Run",
        sport_type="Run",
        date=run_date,
        duration_seconds=duration_seconds,
        perceived_exertion=rpe,
    )


TODAY = date(2026, 4, 13)


def test_import():
    from app.core.strain import compute_muscle_strain  # noqa: F401


def test_squat_targets_quads_glutes_posterior():
    from app.core.strain import compute_muscle_strain
    workout = _make_hevy_workout("Squat", weight_kg=100.0, reps=5, rpe=8.0, workout_date=TODAY)
    result = compute_muscle_strain([], [workout], reference_date=TODAY)
    assert result.quads > 0.0
    assert result.glutes > 0.0
    assert result.posterior_chain > 0.0
    assert result.chest == 0.0
    assert result.upper_pull == 0.0


def test_pullup_targets_upper_pull_biceps_not_quads():
    from app.core.strain import compute_muscle_strain
    workout = _make_hevy_workout("Pull-up", weight_kg=0.0, reps=8, rpe=7.0, workout_date=TODAY)
    result = compute_muscle_strain([], [workout], reference_date=TODAY)
    assert result.upper_pull > 0.0
    assert result.biceps > 0.0
    assert result.quads == 0.0
    assert result.calves == 0.0


def test_run_targets_quads_calves_not_chest():
    from app.core.strain import compute_muscle_strain
    activity = _make_strava_run(duration_seconds=3600, rpe=6, run_date=TODAY)
    result = compute_muscle_strain([activity], [], reference_date=TODAY)
    assert result.quads > 0.0
    assert result.calves > 0.0
    assert result.chest == 0.0
    assert result.biceps == 0.0


def test_hevy_set_without_rpe_uses_fallback():
    """Set with rpe=None falls back to RPE 7 → result non-zero."""
    from app.core.strain import compute_muscle_strain
    workout = _make_hevy_workout("Squat", weight_kg=80.0, reps=5, rpe=None, workout_date=TODAY)
    result = compute_muscle_strain([], [workout], reference_date=TODAY)
    assert result.quads > 0.0


def test_unknown_exercise_hits_core_fallback():
    from app.core.strain import compute_muscle_strain
    workout = _make_hevy_workout(
        "Some Weird Machine Exercise XYZ",
        weight_kg=50.0, reps=10, rpe=7.0,
        workout_date=TODAY,
    )
    result = compute_muscle_strain([], [workout], reference_date=TODAY)
    assert result.core > 0.0


def test_no_history_returns_all_zeros():
    """No activities → EWMA_28d == 0 → all scores == 0.0."""
    from app.core.strain import compute_muscle_strain
    result = compute_muscle_strain([], [], reference_date=TODAY)
    assert result.quads == 0.0
    assert result.posterior_chain == 0.0
    assert result.core == 0.0


def test_score_is_bounded_0_to_100():
    from app.core.strain import compute_muscle_strain
    # Many heavy squats today — score must not exceed 100
    workouts = [
        _make_hevy_workout("Squat", weight_kg=200.0, reps=10, rpe=10.0, workout_date=TODAY)
        for _ in range(10)
    ]
    result = compute_muscle_strain([], workouts, reference_date=TODAY)
    for field in ["quads", "posterior_chain", "glutes", "calves",
                  "chest", "upper_pull", "shoulders", "triceps", "biceps", "core"]:
        assert 0.0 <= getattr(result, field) <= 100.0, f"{field} out of bounds"


def test_activity_outside_28d_window_ignored():
    from app.core.strain import compute_muscle_strain
    old_date = date(2026, 3, 1)  # > 28 days before TODAY (2026-04-13)
    activity = _make_strava_run(duration_seconds=3600, rpe=8, run_date=old_date)
    result = compute_muscle_strain([activity], [], reference_date=TODAY)
    assert result.quads == 0.0


def test_result_has_computed_at():
    from app.core.strain import compute_muscle_strain
    result = compute_muscle_strain([], [], reference_date=TODAY)
    assert isinstance(result.computed_at, datetime)


def test_repeated_sessions_accumulate():
    """Two squat sessions score higher on quads than one."""
    from app.core.strain import compute_muscle_strain
    w1 = _make_hevy_workout("Squat", weight_kg=100.0, reps=5, rpe=8.0, workout_date=TODAY)
    result_one = compute_muscle_strain([], [w1], reference_date=TODAY)
    w2 = _make_hevy_workout("Squat", weight_kg=100.0, reps=5, rpe=8.0,
                             workout_date=date(2026, 4, 12))
    result_two = compute_muscle_strain([], [w1, w2], reference_date=TODAY)
    assert result_two.quads > result_one.quads
