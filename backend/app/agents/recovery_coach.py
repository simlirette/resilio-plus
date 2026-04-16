from __future__ import annotations

from datetime import timedelta

from ..agents.base import AgentContext, AgentRecommendation, BaseAgent
from ..core.recovery_logic import compute_recovery_status
from ..schemas.athlete import Sport
from ..schemas.fatigue import FatigueScore
from ..schemas.plan import WorkoutSlot
from .prompts import RECOVERY_COACH_PROMPT

_SYSTEM_PROMPT = RECOVERY_COACH_PROMPT

_LOW_READINESS_THRESHOLD = 0.7


class RecoveryCoach(BaseAgent):
    """Specialist agent for recovery: HRV-guided readiness, sleep banking.

    Does not consume training budget. Adds a recovery session if readiness is low.
    weekly_load = 0 (recovery sessions do not count as training load).
    """

    @property
    def name(self) -> str:
        return "recovery"

    def analyze(self, context: AgentContext) -> AgentRecommendation:
        status = compute_recovery_status(
            context.terra_health,
            context.athlete.target_race_date,
            context.date_range[0],
        )

        sessions: list[WorkoutSlot] = []

        # Add an active_recovery session if readiness is low
        if status.readiness_modifier < _LOW_READINESS_THRESHOLD:
            if context.athlete.available_days:
                recovery_day = context.date_range[0] + timedelta(
                    days=context.athlete.available_days[0]
                )
                sessions.append(
                    WorkoutSlot(
                        date=recovery_day,
                        sport=Sport.RUNNING,
                        workout_type="active_recovery",
                        duration_min=30,
                        fatigue_score=FatigueScore(
                            local_muscular=5.0,
                            cns_load=2.0,
                            metabolic_cost=5.0,
                            recovery_hours=4.0,
                            affected_muscles=[],
                        ),
                        notes="Active recovery: light walk or yoga. No intensity.",
                    )
                )

        return AgentRecommendation(
            agent_name=self.name,
            fatigue_score=FatigueScore(
                local_muscular=0.0,
                cns_load=0.0,
                metabolic_cost=0.0,
                recovery_hours=0.0,
                affected_muscles=[],
            ),
            weekly_load=0.0,
            suggested_sessions=sessions,
            readiness_modifier=status.readiness_modifier,
            notes=status.recommendation,
        )
