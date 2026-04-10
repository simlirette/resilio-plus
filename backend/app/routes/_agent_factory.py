from __future__ import annotations

from ..agents.base import BaseAgent
from ..agents.biking_coach import BikingCoach
from ..agents.lifting_coach import LiftingCoach
from ..agents.nutrition_coach import NutritionCoach
from ..agents.recovery_coach import RecoveryCoach
from ..agents.running_coach import RunningCoach
from ..agents.swimming_coach import SwimmingCoach
from ..schemas.athlete import AthleteProfile, Sport


def build_agents(athlete: AthleteProfile) -> list[BaseAgent]:
    """Instantiate specialist agents based on athlete's active sports.

    Sport-specific agents (Running, Lifting, Biking, Swimming) are only
    created if the athlete has that sport in their sports list.
    NutritionCoach and RecoveryCoach are always included.
    """
    agents: list[BaseAgent] = []

    if Sport.RUNNING in athlete.sports:
        agents.append(RunningCoach())
    if Sport.LIFTING in athlete.sports:
        agents.append(LiftingCoach())
    if Sport.BIKING in athlete.sports:
        agents.append(BikingCoach())
    if Sport.SWIMMING in athlete.sports:
        agents.append(SwimmingCoach())

    agents.append(NutritionCoach())
    agents.append(RecoveryCoach())

    return agents
