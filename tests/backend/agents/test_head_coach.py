from datetime import date

import pytest

from app.agents.head_coach import HeadCoach, WeeklyPlan
from app.core.acwr import ACWRStatus
from app.core.conflict import ConflictSeverity
from app.schemas.athlete import Sport
from app.schemas.fatigue import FatigueScore
from app.schemas.plan import WorkoutSlot
from tests.backend.agents.conftest import (
    MockAgent,
    make_recommendation,
    make_fatigue,
    sample_context,
    sample_athlete,
)


def _slot(sport: Sport, workout_type: str, duration: int = 60) -> WorkoutSlot:
    return WorkoutSlot(
        date=date(2026, 4, 7),
        sport=sport,
        workout_type=workout_type,
        duration_min=duration,
        fatigue_score=make_fatigue(),
    )


def test_empty_agents_returns_empty_plan(sample_context):
    hc = HeadCoach([])
    plan = hc.build_week(sample_context, [])
    assert plan.sessions == []
    assert plan.readiness_level == "green"
    assert plan.notes == []


def test_single_agent_sessions_pass_through(sample_context):
    session = _slot(Sport.RUNNING, "easy_z1")
    rec = make_recommendation("running", sessions=[session], weekly_load=80.0)
    hc = HeadCoach([MockAgent("running", rec)])
    plan = hc.build_week(sample_context, [50.0] * 28)
    assert len(plan.sessions) == 1


def test_readiness_green_when_modifier_above_0_9(sample_context):
    rec = make_recommendation("running", readiness_modifier=1.0)
    hc = HeadCoach([MockAgent("running", rec)])
    plan = hc.build_week(sample_context, [50.0] * 28)
    assert plan.readiness_level == "green"


def test_readiness_yellow_when_modifier_between_0_6_and_0_9(sample_context):
    rec = make_recommendation("recovery", readiness_modifier=0.75)
    hc = HeadCoach([MockAgent("recovery", rec)])
    plan = hc.build_week(sample_context, [50.0] * 28)
    assert plan.readiness_level == "yellow"


def test_readiness_red_converts_sessions_to_z1(sample_context):
    session = _slot(Sport.RUNNING, "tempo_run")
    rec = make_recommendation("running", readiness_modifier=0.5, sessions=[session])
    hc = HeadCoach([MockAgent("running", rec)])
    plan = hc.build_week(sample_context, [50.0] * 28)
    assert plan.readiness_level == "red"
    assert all(s.workout_type == "easy_z1" for s in plan.sessions)


def test_danger_acwr_scales_sessions_by_75_percent(sample_context):
    session = _slot(Sport.RUNNING, "long_run", duration=120)
    # Very high weekly load to trigger DANGER
    rec = make_recommendation("running", weekly_load=500.0, sessions=[session])
    hc = HeadCoach([MockAgent("running", rec)])
    plan = hc.build_week(sample_context, [10.0] * 28)
    assert plan.acwr.status == ACWRStatus.DANGER
    # Duration should be scaled to 120 * 0.75 = 90
    assert plan.sessions[0].duration_min == 90


def test_notes_collected_from_agents(sample_context):
    rec = make_recommendation("running", notes="Easy week — deload")
    hc = HeadCoach([MockAgent("running", rec)])
    plan = hc.build_week(sample_context, [50.0] * 28)
    assert "Easy week — deload" in plan.notes


def test_acwr_computed_from_load_history(sample_context):
    rec = make_recommendation("running", weekly_load=50.0)
    hc = HeadCoach([MockAgent("running", rec)])
    plan = hc.build_week(sample_context, [50.0] * 28)
    assert plan.acwr.status == ACWRStatus.SAFE
