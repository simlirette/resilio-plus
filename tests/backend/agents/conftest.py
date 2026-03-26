from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pytest

from app.agents.base import AgentContext, AgentRecommendation, BaseAgent
from app.schemas.athlete import AthleteProfile, Sport
from app.schemas.fatigue import FatigueScore
from app.schemas.plan import WorkoutSlot
from app.schemas.connector import StravaActivity, HevyWorkout, TerraHealthData, FatSecretDay


def make_fatigue(local=10.0, cns=10.0, metabolic=10.0, recovery=8.0, muscles=None):
    return FatigueScore(
        local_muscular=local,
        cns_load=cns,
        metabolic_cost=metabolic,
        recovery_hours=recovery,
        affected_muscles=muscles or [],
    )


def make_recommendation(
    agent_name="running",
    weekly_load=100.0,
    readiness_modifier=1.0,
    sessions=None,
    notes="",
):
    return AgentRecommendation(
        agent_name=agent_name,
        fatigue_score=make_fatigue(),
        weekly_load=weekly_load,
        suggested_sessions=sessions or [],
        readiness_modifier=readiness_modifier,
        notes=notes,
    )


@pytest.fixture
def sample_athlete():
    return AthleteProfile(
        name="Test Athlete",
        age=30,
        sex="M",
        weight_kg=75.0,
        height_cm=178.0,
        sports=[Sport.RUNNING, Sport.LIFTING],
        primary_sport=Sport.RUNNING,
        goals=["run sub-4h marathon"],
        target_race_date=date(2026, 10, 15),
        available_days=[0, 2, 4, 6],
        hours_per_week=8.0,
    )


@pytest.fixture
def sample_context(sample_athlete):
    return AgentContext(
        athlete=sample_athlete,
        date_range=(date(2026, 4, 7), date(2026, 4, 13)),
        phase="general_prep",
        strava_activities=[],
        hevy_workouts=[],
        terra_health=[],
        fatsecret_days=[],
    )


class MockAgent(BaseAgent):
    def __init__(self, name: str, recommendation: AgentRecommendation):
        self._name = name
        self._recommendation = recommendation

    @property
    def name(self) -> str:
        return self._name

    def analyze(self, context: AgentContext) -> AgentRecommendation:
        return self._recommendation
