from __future__ import annotations

from datetime import timedelta

from ..agents.base import AgentContext, AgentRecommendation, BaseAgent
from ..core.swimming_logic import (
    compute_swimming_fatigue, estimate_css, generate_swimming_sessions,
)
from ..core.periodization import get_current_phase
from ..core.readiness import compute_readiness


class SwimmingCoach(BaseAgent):
    """Specialist agent for swimming: CSS-based zones, technique focus."""

    @property
    def name(self) -> str:
        return "swimming"

    def analyze(self, context: AgentContext) -> AgentRecommendation:
        prior_swims = [
            a for a in context.strava_activities
            if a.sport_type == "Swim"
            and context.date_range[0] - timedelta(days=7) <= a.date < context.date_range[0]
        ]

        css = estimate_css(context.athlete)
        readiness_modifier = compute_readiness(context.terra_health)
        fatigue_score = compute_swimming_fatigue(prior_swims)
        phase = get_current_phase(context.athlete.target_race_date, context.date_range[0])
        hours_budget = context.sport_budgets.get("swimming", 0.0)

        sessions = generate_swimming_sessions(
            css_per_100m=css,
            week_number=context.week_number,
            phase=phase.phase.value,
            available_days=context.athlete.available_days,
            hours_budget=hours_budget,
            volume_modifier=phase.volume_modifier,
            week_start=context.date_range[0],
        )

        _INTENSITY = {
            "Z1_technique": 0.8, "Z2_endurance_swim": 1.0, "Z3_threshold_set": 1.5,
        }
        weekly_load = sum(
            s.duration_min * _INTENSITY.get(s.workout_type, 1.0) for s in sessions
        )

        return AgentRecommendation(
            agent_name=self.name,
            fatigue_score=fatigue_score,
            weekly_load=weekly_load,
            suggested_sessions=sessions,
            readiness_modifier=readiness_modifier,
            notes=f"CSS {css:.0f}s/100m | Phase: {phase.phase.value}",
        )
