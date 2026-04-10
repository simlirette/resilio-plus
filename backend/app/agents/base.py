from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date

from ..schemas.athlete import AthleteProfile
from ..schemas.connector import FatSecretDay, HevyWorkout, StravaActivity, TerraHealthData
from ..schemas.fatigue import FatigueScore
from ..schemas.plan import WorkoutSlot


@dataclass
class AgentContext:
    """All data available to specialist agents for a given planning week."""
    athlete: AthleteProfile
    date_range: tuple[date, date]
    phase: str                              # MacroPhase value (string)
    strava_activities: list[StravaActivity] = field(default_factory=list)
    hevy_workouts: list[HevyWorkout] = field(default_factory=list)
    terra_health: list[TerraHealthData] = field(default_factory=list)
    fatsecret_days: list[FatSecretDay] = field(default_factory=list)
    week_number: int = 1                    # 1-based week in multi-week plan
    weeks_remaining: int = 0               # weeks until target_race_date
    sport_budgets: dict[str, float] = field(default_factory=dict)  # sport name → hours


@dataclass
class AgentRecommendation:
    """Output of a specialist agent's analysis for a planning week."""
    agent_name: str
    fatigue_score: FatigueScore
    weekly_load: float
    suggested_sessions: list[WorkoutSlot] = field(default_factory=list)
    readiness_modifier: float = 1.0
    notes: str = ""

    def __post_init__(self) -> None:
        if not (0.5 <= self.readiness_modifier <= 1.5):
            raise ValueError(
                f"readiness_modifier must be in [0.5, 1.5], got {self.readiness_modifier}"
            )


class BaseAgent(ABC):
    """Abstract base class for all specialist coaching agents."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this agent, e.g. 'running', 'lifting'."""

    @abstractmethod
    def analyze(self, context: AgentContext) -> AgentRecommendation:
        """Analyze the context and return a recommendation for the week."""
