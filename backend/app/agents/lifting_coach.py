from __future__ import annotations

from datetime import timedelta

from ..agents.base import AgentContext, AgentRecommendation, BaseAgent
from ..core.hormonal import get_lifting_adjustments
from ..core.lifting_logic import (
    compute_lifting_fatigue, estimate_strength_level, generate_lifting_sessions,
)
from ..core.periodization import get_current_phase
from ..core.readiness import compute_readiness
from ..schemas.athlete import Sport
from .prompts import LIFTING_COACH_PROMPT

_SYSTEM_PROMPT = LIFTING_COACH_PROMPT


class LiftingCoach(BaseAgent):
    """Specialist agent for lifting: DUP rotation, SFR tiers, hybrid reduction."""

    @property
    def name(self) -> str:
        return "lifting"

    def analyze(self, context: AgentContext) -> AgentRecommendation:
        # 1. Filter Hevy workouts to 7 days before this week
        prior_workouts = [
            w for w in context.hevy_workouts
            if context.date_range[0] - timedelta(days=7) <= w.date < context.date_range[0]
        ]

        # 2. Strength level from full history
        strength_level = estimate_strength_level(context.hevy_workouts)

        # 3. Readiness modifier from Terra data
        readiness_modifier = compute_readiness(context.terra_health)

        # 4. Fatigue from last week
        fatigue_score = compute_lifting_fatigue(prior_workouts)

        # 5. Periodization phase
        phase = get_current_phase(context.athlete.target_race_date, context.date_range[0])

        # 6. Budget from goal analysis (injected by HeadCoach)
        hours_budget = context.sport_budgets.get("lifting", context.athlete.hours_per_week * 0.4)

        # 7. Running load ratio derived from sport_budgets
        running_load_ratio = (
            context.sport_budgets.get("running", 0) / context.athlete.hours_per_week
            if context.athlete.hours_per_week > 0
            else 0.6
        )

        # 8. Generate sessions
        sessions = generate_lifting_sessions(
            strength_level=strength_level,
            phase=phase.phase.value,
            week_number=context.week_number,
            weeks_remaining=context.weeks_remaining,
            available_days=context.athlete.available_days,
            hours_budget=hours_budget,
            volume_modifier=phase.volume_modifier,
            running_load_ratio=running_load_ratio,
            week_start=context.date_range[0],
        )

        # 9. Weekly load: sum(duration_min * intensity_weight)
        _LIFT_INTENSITY = {
            "upper_strength": 2.0, "lower_strength": 2.0,
            "upper_hypertrophy": 1.5, "arms_hypertrophy": 1.0,
            "full_body_endurance": 1.0,
        }
        weekly_load = sum(
            s.duration_min * _LIFT_INTENSITY.get(s.workout_type, 1.0)
            for s in sessions
        )

        # V3: apply cycle phase adjustments if hormonal profile is enabled
        cycle_notes = ""
        hp = context.hormonal_profile
        if hp is not None and hp.enabled and hp.current_phase is not None:
            adj = get_lifting_adjustments(hp.current_phase)
            if adj["rpe_offset"] < 0:
                # Approximate RPE -1 as ~10% intensity reduction
                readiness_modifier = max(0.5, readiness_modifier * 0.90)
            cycle_notes = (
                f" | Cycle({hp.current_phase}): RPE{adj['rpe_offset']:+d}"
                + (" NO-1RM" if adj["no_1rm"] else "")
                + f" — {adj['notes']}"
            )

        return AgentRecommendation(
            agent_name=self.name,
            fatigue_score=fatigue_score,
            weekly_load=weekly_load,
            suggested_sessions=sessions,
            readiness_modifier=readiness_modifier,
            notes=(
                f"Level: {strength_level.value} | Phase: {phase.phase.value} | "
                f"DUP block: {context.week_number % 3}{cycle_notes}"
            ),
        )
