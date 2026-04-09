"""
Plan Merger — agents/head_coach/merger.py
Combines partial agent plans into a unified weekly plan.
"""
from __future__ import annotations

from models.athlete_state import AthleteState

_DAY_ORDER = [
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
]


class PlanMerger:
    """Merges running and lifting partial plans into a single unified weekly plan."""

    def merge(
        self,
        state: AthleteState,
        partial_plans: dict,
        conflict_log: list[str],
    ) -> dict:
        """
        Combine partial agent plans into a unified weekly plan.

        Args:
            state: current AthleteState (reads current_phase, fatigue, constraint_matrix)
            partial_plans: {"running": dict, "lifting": dict} from agent runs
            conflict_log: resolution strings from ConflictResolver

        Returns unified plan dict.
        """
        schedule = state.constraint_matrix.schedule

        running_days = self._days_for_sport(schedule, "running")
        lifting_days = self._days_for_sport(schedule, "lifting")

        sessions: list[dict] = []

        running_sessions = partial_plans.get("running", {}).get("sessions", [])
        for i, session in enumerate(running_sessions):
            day = running_days[i] if i < len(running_days) else f"day_r{i + 1}"
            sessions.append({"day": day, "sport": "running", "workout": session})

        lifting_sessions = partial_plans.get("lifting", {}).get("sessions", [])
        for i, session in enumerate(lifting_sessions):
            day = lifting_days[i] if i < len(lifting_days) else f"day_l{i + 1}"
            sessions.append({"day": day, "sport": "lifting", "workout": session})

        # Sort by day-of-week order (unknown/fallback days go last)
        day_idx = {day: i for i, day in enumerate(_DAY_ORDER)}
        sessions.sort(key=lambda s: day_idx.get(s["day"], 99))

        return {
            "agent": "head_coach",
            "week": state.current_phase.mesocycle_week,
            "phase": state.current_phase.macrocycle,
            "sessions": sessions,
            "acwr": state.fatigue.acwr,
            "conflicts_resolved": conflict_log,
            "coaching_summary": "",
        }

    def _days_for_sport(self, schedule: dict, sport: str) -> list[str]:
        """Return days assigned to a given sport, in day-of-week order."""
        return [
            day for day in _DAY_ORDER
            if isinstance(schedule.get(day), dict)
            and any(
                s.get("sport") == sport
                for s in schedule[day].get("sessions", [])
            )
        ]
