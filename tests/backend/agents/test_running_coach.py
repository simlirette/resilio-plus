from datetime import date, timedelta
import pytest
from app.agents.base import AgentContext, AgentRecommendation
from app.agents.running_coach import RunningCoach
from app.schemas.athlete import AthleteProfile, Sport
from app.schemas.connector import StravaActivity, TerraHealthData
from app.schemas.plan import WorkoutSlot


def _athlete(primary=Sport.RUNNING, hours=8.0, days=None):
    return AthleteProfile(
        name="Alice", age=28, sex="F", weight_kg=58, height_cm=165,
        sports=[Sport.RUNNING, Sport.LIFTING], primary_sport=primary,
        goals=["sub-4h marathon"], target_race_date=date(2026, 10, 15),
        available_days=days or [0, 2, 4, 5, 6],
        hours_per_week=hours,
    )


def _context(athlete=None, week_number=1, weeks_remaining=28,
             strava=None, terra=None):
    a = athlete or _athlete()
    return AgentContext(
        athlete=a,
        date_range=(date(2026, 4, 7), date(2026, 4, 13)),
        phase="general_prep",
        strava_activities=strava or [],
        terra_health=terra or [],
        week_number=week_number,
        weeks_remaining=weeks_remaining,
    )


def test_analyze_returns_agent_recommendation():
    coach = RunningCoach()
    result = coach.analyze(_context())
    assert isinstance(result, AgentRecommendation)


def test_analyze_name_is_running():
    assert RunningCoach().name == "running"


def test_analyze_readiness_modifier_propagated_from_terra():
    # Good HRV + good sleep -> modifier = 1.1
    terra = [
        TerraHealthData(date=date(2026, 4, 7) - timedelta(days=i),
                        hrv_rmssd=60.0, sleep_duration_hours=7.5, sleep_score=80.0)
        for i in range(7)
    ]
    result = RunningCoach().analyze(_context(terra=terra))
    assert result.readiness_modifier > 1.0


def test_analyze_sessions_are_workout_slots():
    result = RunningCoach().analyze(_context())
    assert all(isinstance(s, WorkoutSlot) for s in result.suggested_sessions)


def test_analyze_weekly_load_positive():
    result = RunningCoach().analyze(_context())
    assert result.weekly_load > 0


def test_analyze_cold_start_no_strava_data():
    # No data -> VDOT defaults to 35.0, still returns valid recommendation
    result = RunningCoach().analyze(_context(strava=[]))
    assert result.agent_name == "running"
    assert result.weekly_load >= 0


def test_analyze_week_number_deload_less_load():
    # Week 4 (deload) should produce less weekly_load than week 3
    regular = RunningCoach().analyze(_context(week_number=3, weeks_remaining=28))
    deload = RunningCoach().analyze(_context(week_number=4, weeks_remaining=28))
    assert deload.weekly_load < regular.weekly_load


def test_analyze_near_race_only_z1_sessions():
    result = RunningCoach().analyze(_context(weeks_remaining=1))
    types = {s.workout_type for s in result.suggested_sessions}
    assert "tempo_z2" not in types
