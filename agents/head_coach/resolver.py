"""
Conflict Resolver — agents/head_coach/resolver.py
Resolves scheduling and load conflicts between partial agent plans.
"""
from __future__ import annotations

from models.athlete_state import AthleteState

_DAY_ORDER = [
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
]


class ConflictResolver:
    """Applies ACWR-based and overlap-based modifications to partial plans."""

    MAX_ITERATIONS = 2

    def resolve(
        self, state: AthleteState, partial_plans: dict
    ) -> tuple[dict, list[str]]:
        """
        Detect and resolve conflicts between partial plans.

        Reads state.acwr_computed (or state.fatigue.acwr) and
        state.constraint_matrix.schedule for muscle overlap detection.

        Returns:
            (resolved_plans, conflict_log)
            - resolved_plans: shallow copies of partial_plans with modification keys added
            - conflict_log: list of strings describing each resolution
        """
        resolved = {sport: dict(plan) for sport, plan in partial_plans.items()}
        log: list[str] = []

        acwr = state.acwr_computed or state.fatigue.acwr or 0.0

        if acwr > 1.5:
            for sport in resolved:
                resolved[sport]["intensity_reduction_pct"] = 30
                resolved[sport]["tier_max"] = 1
            log.append(f"acwr_danger:{acwr:.2f} → intensity_reduction_pct=30, tier_max=1")

        elif acwr > 1.3:
            for sport in resolved:
                resolved[sport]["volume_reduction_pct"] = 20
            log.append(f"acwr_overload:{acwr:.2f} → volume_reduction_pct=20")

        overlap_log = self._detect_muscle_overlap(state)
        log.extend(overlap_log)

        return resolved, log

    def _detect_muscle_overlap(self, state: AthleteState) -> list[str]:
        """
        Detect days where running and leg-heavy lifting overlap in the
        constraint matrix schedule. Flags only (no structural plan change).
        """
        log: list[str] = []
        schedule = state.constraint_matrix.schedule

        for day in _DAY_ORDER:
            day_info = schedule.get(day, {})
            if not isinstance(day_info, dict):
                continue
            sessions = day_info.get("sessions", [])
            sports = {s.get("sport") for s in sessions if isinstance(s, dict)}
            if "running" in sports and "lifting" in sports:
                log.append(f"muscle_overlap:{day} → running+lifting same day flagged")

        return log
