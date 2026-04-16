from __future__ import annotations

from datetime import timedelta

from ..agents.base import AgentContext, AgentRecommendation, BaseAgent
from ..core.biking_logic import (
    compute_biking_fatigue,
    estimate_ftp,
    generate_biking_sessions,
)
from ..core.periodization import get_current_phase
from ..core.readiness import compute_readiness


class BikingCoach(BaseAgent):
    """Specialist agent for cycling: FTP-aware, Coggan zones, wave loading."""

    @property
    def name(self) -> str:
        return "biking"

    def analyze(self, context: AgentContext) -> AgentRecommendation:
        # 1. Filter Strava rides to 7 days before this week
        prior_rides = [
            a
            for a in context.strava_activities
            if a.sport_type in ("Ride", "VirtualRide")
            and context.date_range[0] - timedelta(days=7) <= a.date < context.date_range[0]
        ]

        # 2. FTP: use athlete's stored value or cold start
        ftp = estimate_ftp(context.athlete)

        # 3. Readiness modifier from Terra data
        readiness_modifier = compute_readiness(context.terra_health)

        # 4. Fatigue from last week's rides
        fatigue_score = compute_biking_fatigue(prior_rides)

        # 5. Periodization phase
        phase = get_current_phase(context.athlete.target_race_date, context.date_range[0])

        # 6. Budget from goal analysis (injected by HeadCoach)
        hours_budget = context.sport_budgets.get("biking", 0.0)

        # 7. Generate sessions
        sessions = generate_biking_sessions(
            ftp=ftp,
            week_number=context.week_number,
            phase=phase.phase.value,
            available_days=context.athlete.available_days,
            hours_budget=hours_budget,
            volume_modifier=phase.volume_modifier,
            week_start=context.date_range[0],
        )

        # 8. Weekly load
        _intensity = {
            "Z2_endurance_ride": 1.0,
            "Z3_tempo_ride": 1.4,
            "Z4_threshold_intervals": 1.8,
        }
        weekly_load = sum(s.duration_min * _intensity.get(s.workout_type, 1.0) for s in sessions)

        return AgentRecommendation(
            agent_name=self.name,
            fatigue_score=fatigue_score,
            weekly_load=weekly_load,
            suggested_sessions=sessions,
            readiness_modifier=readiness_modifier,
            notes=f"FTP {ftp}W | Phase: {phase.phase.value} | Week: {context.week_number}",
        )
