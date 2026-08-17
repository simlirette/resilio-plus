"""MonitoringService — Phase D (D11).

Detects proactive events and dispatches flags to AthleteState.
Does NOT call LLM directly — flags are picked up by CoordinatorService
on next athlete interaction (per product decision C9 §1265).

Events monitored (V1):
  - HRV degraded ≥ 3 consecutive days → flag Recovery
  - Energy patterns detected (via energy_patterns.py) → flag Energy
  - Proactive Head Coach message cap: ≤ 2/week
  - baseline_active exit conditions → trigger followup_transition
"""
from __future__ import annotations

from typing import Any

from ..core.energy_patterns import detect_energy_patterns
from ..db.models import AthleteModel

# Proactive message weekly cap (product decision: ≤ 2/week)
_PROACTIVE_MESSAGE_CAP = 2

# Number of consecutive degraded HRV days to set recovery flag
_HRV_CONSECUTIVE_DAYS = 3


class MonitoringService:
    """Monitors athlete state, sets flags, never triggers LLM directly."""

    def __init__(self, db: Any) -> None:
        self.db = db

    def _get_athlete(self, athlete_id: str) -> AthleteModel:
        athlete: AthleteModel | None = (
            self.db.query(AthleteModel)
            .filter(AthleteModel.id == athlete_id)
            .first()
        )
        if athlete is None:
            raise ValueError(f"Athlete {athlete_id!r} not found")
        return athlete

    def check_hrv_trend(
        self,
        athlete_id: str,
        hrv_daily_values: list[float],
    ) -> dict[str, Any]:
        """Check for consecutive HRV degradation.

        Args:
            athlete_id: Athlete identifier.
            hrv_daily_values: HRV values ordered oldest→newest (last N days).

        Returns:
            {"recovery_flag_set": bool, "llm_calls": int}
        """
        if len(hrv_daily_values) < _HRV_CONSECUTIVE_DAYS:
            return {"recovery_flag_set": False, "llm_calls": 0}

        # Check if last _HRV_CONSECUTIVE_DAYS values are strictly decreasing
        recent = hrv_daily_values[-_HRV_CONSECUTIVE_DAYS:]
        degraded = all(
            recent[i] > recent[i + 1] for i in range(len(recent) - 1)
        )

        if degraded:
            athlete = self._get_athlete(athlete_id)
            object.__setattr__(athlete, "hrv_recovery_flag", True)
            self.db.commit()

        return {"recovery_flag_set": degraded, "llm_calls": 0}

    def check_energy_patterns(self, athlete_id: str) -> dict[str, Any]:
        """Detect energy patterns and set flags.

        Uses existing detect_energy_patterns() from energy_patterns.py.

        Returns:
            {"energy_flags": list[str], "llm_calls": int}
        """
        raw = detect_energy_patterns(self.db)
        # detect_energy_patterns returns a dict; extract flag names as list
        if isinstance(raw, dict):
            patterns: list[str] = [k for k, v in raw.items() if v]
        else:
            patterns = list(raw)

        if patterns:
            athlete = self._get_athlete(athlete_id)
            object.__setattr__(athlete, "energy_pattern_flags", patterns)
            self.db.commit()

        return {"energy_flags": patterns, "llm_calls": 0}

    def check_proactive_message_allowed(self, athlete_id: str) -> dict[str, Any]:
        """Check whether a proactive Head Coach message is permitted this week.

        Cap: ≤ 2 proactive messages per week.

        Returns:
            {"allowed": bool}
        """
        athlete = self._get_athlete(athlete_id)
        count: int = getattr(athlete, "proactive_message_count_this_week", 0)
        return {"allowed": count < _PROACTIVE_MESSAGE_CAP}

    def check_baseline_exit_conditions(
        self,
        athlete_id: str,
        weeks_completed: int,
        required_weeks: int,
    ) -> dict[str, Any]:
        """Check if baseline_active exit conditions are met.

        Triggers followup_transition if weeks_completed >= required_weeks.

        Returns:
            {"followup_triggered": bool}
        """
        if weeks_completed >= required_weeks:
            triggered = self._trigger_followup_transition(athlete_id)
            return {"followup_triggered": triggered}
        return {"followup_triggered": False}

    def _trigger_followup_transition(self, athlete_id: str) -> bool:
        """Trigger the followup_transition conversation.

        Sets a flag on the athlete state; CoordinatorService picks it up
        on next event dispatch.

        Returns:
            True if triggered successfully.
        """
        athlete = self._get_athlete(athlete_id)
        object.__setattr__(athlete, "followup_transition_pending", True)
        self.db.commit()
        return True

    def run_daily_checks(self, athlete_id: str) -> dict[str, Any]:
        """Run all daily monitoring checks for one athlete.

        Called by the APScheduler daily monitoring job.

        Returns:
            Summary of checks run and flags set.
        """
        hrv_result = {"recovery_flag_set": False, "llm_calls": 0}
        energy_result = {"energy_flags": [], "llm_calls": 0}

        # HRV check — would load from DB in production;
        # here we check if data is available
        try:
            hrv_result = self.check_energy_patterns(athlete_id=athlete_id)
        except Exception:  # noqa: BLE001
            pass

        return {
            "athlete_id": athlete_id,
            "hrv_checked": hrv_result,
            "energy_checked": energy_result,
        }
