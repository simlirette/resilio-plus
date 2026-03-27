from __future__ import annotations

from datetime import timedelta

from app.agents.base import AgentContext, AgentRecommendation, BaseAgent
from app.core.periodization import get_current_phase
from app.core.readiness import compute_readiness
from app.core.running_logic import (
    compute_running_fatigue, estimate_vdot, generate_running_sessions,
)
from app.schemas.athlete import Sport


class RunningCoach(BaseAgent):
    """Specialist agent for running: VDOT-aware, 80/20 TID, wave loading."""

    @property
    def name(self) -> str:
        return "running"

    def analyze(self, context: AgentContext) -> AgentRecommendation:
        # 1. Filter Strava activities to the 7 days before this week
        prior_activities = [
            a for a in context.strava_activities
            if context.date_range[0] - timedelta(days=7) <= a.date < context.date_range[0]
        ]

        # 2. VDOT: use athlete's stored value, else estimate from full history
        vdot = context.athlete.vdot or estimate_vdot(context.strava_activities)

        # 3. Readiness modifier from Terra health data
        readiness_modifier = compute_readiness(context.terra_health)

        # 4. Fatigue from last week's runs
        fatigue_score = compute_running_fatigue(prior_activities)

        # 5. Periodization phase
        phase = get_current_phase(context.athlete.target_race_date, context.date_range[0])

        # 6. Budget split: 60% running / 40% lifting; reversed if primary is LIFTING
        run_ratio = 0.4 if context.athlete.primary_sport == Sport.LIFTING else 0.6
        hours_budget = context.athlete.hours_per_week * run_ratio

        # 7. Generate sessions
        sessions = generate_running_sessions(
            vdot=vdot,
            week_number=context.week_number,
            weeks_remaining=context.weeks_remaining,
            available_days=context.athlete.available_days,
            hours_budget=hours_budget,
            volume_modifier=phase.volume_modifier,
            tid_strategy=phase.tid_recommendation,
            week_start=context.date_range[0],
        )

        # 8. Weekly load: sum(duration_min * intensity_weight)
        _INTENSITY = {
            "easy_z1": 1.0, "long_run_z1": 1.0,
            "tempo_z2": 1.5, "vo2max_z3": 2.0, "activation_z3": 2.0,
        }
        weekly_load = sum(
            s.duration_min * _INTENSITY.get(s.workout_type, 1.0)
            for s in sessions
        )

        return AgentRecommendation(
            agent_name=self.name,
            fatigue_score=fatigue_score,
            weekly_load=weekly_load,
            suggested_sessions=sessions,
            readiness_modifier=readiness_modifier,
            notes=(
                f"VDOT {vdot:.0f} | Phase: {phase.phase.value} | "
                f"Week: {context.week_number} | Weeks remaining: {context.weeks_remaining}"
            ),
        )
