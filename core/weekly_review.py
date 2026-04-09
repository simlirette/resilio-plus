"""
WeeklyAnalyzer  — planned vs actual session analysis + TRIMP calculation.
WeeklyAdjuster  — ACWR recalculation + adjustment rule engine.
"""
from __future__ import annotations

from datetime import datetime

from models.weekly_review import ActualWorkout

# ── TRIMP intensity factors ───────────────────────────────────────────────────
# Running: Z1=easy(1.0), Z2=tempo(1.5), Z3=interval(2.5), unknown(1.2)
# Lifting: hypertrophy(0.8), strength/power(1.2), default(1.0)

_RUN_TYPE_FACTOR: dict[str, float] = {
    "easy": 1.0,
    "tempo": 1.5,
    "interval": 2.5,
}
_LIFT_TYPE_FACTOR: dict[str, float] = {
    "hypertrophy": 0.8,
    "strength": 1.2,
    "power": 1.2,
}

# HRmax thresholds for avg_hr zone detection (assuming max_hr ≈ 185 bpm for V1)
_HR_Z1_MAX = 138   # < 75% of 185
_HR_Z2_MAX = 162   # < 88% of 185


def _running_factor(actual_data: dict) -> float:
    """Return TRIMP intensity factor for a running workout."""
    avg_hr = actual_data.get("avg_hr")
    if avg_hr is not None:
        if avg_hr < _HR_Z1_MAX:
            return 1.0
        if avg_hr <= _HR_Z2_MAX:
            return 1.5
        return 2.5
    workout_type = actual_data.get("type", "")
    return _RUN_TYPE_FACTOR.get(workout_type, 1.2)


def _lifting_factor(actual_data: dict) -> float:
    """Return TRIMP intensity factor for a lifting workout."""
    session_type = actual_data.get("session_type", "")
    return _LIFT_TYPE_FACTOR.get(session_type, 1.0)


def _trimp(workout: ActualWorkout) -> float:
    """Compute TRIMP for a single completed workout."""
    duration = workout.actual_data.get("duration_min", 60)
    if workout.sport == "running":
        return duration * _running_factor(workout.actual_data)
    return duration * _lifting_factor(workout.actual_data)


def _day_index(date_str: str) -> int:
    """Return 0-based weekday index (0=Monday) for a 'YYYY-MM-DD' string."""
    return datetime.strptime(date_str, "%Y-%m-%d").weekday()


class WeeklyAnalyzer:
    def analyze(
        self,
        planned_sessions: list[dict],
        actual_workouts: list[ActualWorkout],
    ) -> dict:
        """
        Compare planned sessions against actuals.

        Returns:
            {
              "completion_rate": float,
              "sessions_planned": int,
              "sessions_completed": int,
              "trimp_total": float,
              "trimp_by_sport": {"running": float, "lifting": float},
              "week_loads": list[float],   # 7 daily TRIMP values (Mon–Sun)
            }
        """
        sessions_planned = len(planned_sessions) if planned_sessions else len(actual_workouts)
        sessions_completed = sum(1 for w in actual_workouts if w.completed)
        completion_rate = (
            sessions_completed / sessions_planned if sessions_planned > 0 else 0.0
        )

        trimp_by_sport: dict[str, float] = {"running": 0.0, "lifting": 0.0}
        week_loads = [0.0] * 7

        for workout in actual_workouts:
            if not workout.completed:
                continue
            t = _trimp(workout)
            trimp_by_sport[workout.sport] = trimp_by_sport.get(workout.sport, 0.0) + t
            day_idx = _day_index(workout.date)
            week_loads[day_idx] += t

        trimp_total = sum(trimp_by_sport.values())

        return {
            "completion_rate": completion_rate,
            "sessions_planned": sessions_planned,
            "sessions_completed": sessions_completed,
            "trimp_total": trimp_total,
            "trimp_by_sport": trimp_by_sport,
            "week_loads": week_loads,
        }
