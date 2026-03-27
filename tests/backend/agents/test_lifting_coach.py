from datetime import date, timedelta
import pytest
from app.agents.base import AgentContext, AgentRecommendation
from app.agents.lifting_coach import LiftingCoach
from app.schemas.athlete import AthleteProfile, Sport
from app.schemas.connector import HevyWorkout, HevyExercise, HevySet, TerraHealthData
from app.schemas.plan import WorkoutSlot


def _athlete(primary=Sport.RUNNING, hours=8.0, days=None):
    return AthleteProfile(
        name="Bob", age=32, sex="M", weight_kg=80, height_cm=180,
        sports=[Sport.RUNNING, Sport.LIFTING], primary_sport=primary,
        goals=["strength + run hybrid"], target_race_date=None,
        available_days=days or [1, 3, 5, 6],
        hours_per_week=hours,
    )


def _context(athlete=None, week_number=1, weeks_remaining=20,
             hevy=None, terra=None):
    a = athlete or _athlete()
    return AgentContext(
        athlete=a,
        date_range=(date(2026, 4, 7), date(2026, 4, 13)),
        phase="general_prep",
        hevy_workouts=hevy or [],
        terra_health=terra or [],
        week_number=week_number,
        weeks_remaining=weeks_remaining,
    )


def test_analyze_returns_agent_recommendation():
    result = LiftingCoach().analyze(_context())
    assert isinstance(result, AgentRecommendation)


def test_analyze_name_is_lifting():
    assert LiftingCoach().name == "lifting"


def test_analyze_readiness_modifier_propagated_from_terra():
    terra = [
        TerraHealthData(date=date(2026, 4, 7) - timedelta(days=i),
                        hrv_rmssd=60.0, sleep_duration_hours=7.5, sleep_score=80.0)
        for i in range(7)
    ]
    result = LiftingCoach().analyze(_context(terra=terra))
    assert result.readiness_modifier > 1.0


def test_analyze_sessions_are_workout_slots():
    result = LiftingCoach().analyze(_context())
    assert all(isinstance(s, WorkoutSlot) for s in result.suggested_sessions)


def test_analyze_weekly_load_positive():
    result = LiftingCoach().analyze(_context())
    assert result.weekly_load > 0


def test_analyze_cold_start_no_hevy_data():
    result = LiftingCoach().analyze(_context(hevy=[]))
    assert result.agent_name == "lifting"
    assert result.weekly_load >= 0


def test_analyze_week_number_affects_dup_rotation():
    # week_number=3 -> dup=0 -> hypertrophy; week_number=1 -> dup=1 -> strength
    hypertrophy_week = LiftingCoach().analyze(_context(week_number=3))
    strength_week = LiftingCoach().analyze(_context(week_number=1))
    hyper_types = {s.workout_type for s in hypertrophy_week.suggested_sessions}
    strength_types = {s.workout_type for s in strength_week.suggested_sessions}
    assert "upper_hypertrophy" in hyper_types
    assert "upper_strength" in strength_types


def test_analyze_deload_week_reduces_load():
    normal = LiftingCoach().analyze(_context(week_number=1))
    deload = LiftingCoach().analyze(_context(week_number=4))
    assert deload.weekly_load < normal.weekly_load
