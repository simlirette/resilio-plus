from __future__ import annotations

from datetime import timedelta

from ..agents.base import AgentContext, AgentRecommendation, BaseAgent
from ..core.hormonal import get_running_adjustments
from ..core.periodization import get_current_phase
from ..core.readiness import compute_readiness
from ..core.running_logic import (
    compute_running_fatigue,
    estimate_vdot,
    generate_running_sessions,
)
from .prompts import RUNNING_COACH_PROMPT

_SYSTEM_PROMPT = RUNNING_COACH_PROMPT


class RunningCoach(BaseAgent):
    """Specialist agent for running: VDOT-aware, 80/20 TID, wave loading."""

    @property
    def name(self) -> str:
        return "running"

    def analyze(self, context: AgentContext) -> AgentRecommendation:
        # 1. Filter Strava activities to the 7 days before this week
        prior_activities = [
            a
            for a in context.strava_activities
            if context.date_range[0] - timedelta(days=7) <= a.date < context.date_range[0]
        ]

        # 2. VDOT: use athlete's stored value, else estimate from full history
        vdot = context.athlete.vdot or estimate_vdot(
            context.strava_activities, reference_date=context.date_range[0]
        )

        # 3. Readiness modifier from Terra health data
        readiness_modifier = compute_readiness(context.terra_health)

        # 4. Fatigue from last week's runs
        fatigue_score = compute_running_fatigue(prior_activities)

        # 5. Periodization phase
        phase = get_current_phase(context.athlete.target_race_date, context.date_range[0])

        # 6. Budget from goal analysis (injected by HeadCoach)
        hours_budget = context.sport_budgets.get("running", context.athlete.hours_per_week * 0.6)

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
            "easy_z1": 1.0,
            "long_run_z1": 1.0,
            "tempo_z2": 1.5,
            "vo2max_z3": 2.0,
            "activation_z3": 2.0,
        }
        weekly_load = sum(s.duration_min * _INTENSITY.get(s.workout_type, 1.0) for s in sessions)

        # V3: apply cycle phase adjustments if hormonal profile is enabled
        cycle_notes = ""
        hp = context.hormonal_profile
        if hp is not None and hp.enabled and hp.current_phase is not None:
            adj = get_running_adjustments(hp.current_phase)
            flags = []
            if adj["replace_intervals_with_z2"]:
                flags.append("intervals->Z2")
            if adj["avoid_direction_changes"]:
                flags.append("avoid-dir-changes")
            if adj["increase_hydration"]:
                flags.append("hydration++")
            if adj["avoid_heat"]:
                flags.append("avoid-heat")
            flag_str = " ".join(flags)
            cycle_notes = (
                f" | Cycle({hp.current_phase})"
                + (f": {flag_str}" if flags else "")
                + f" — {adj['notes']}"
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
                f"{cycle_notes}"
            ),
        )
