"""D11 TDD — MonitoringService (proactive events, APScheduler integration)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch


def _make_athlete(
    athlete_id: str = "a1",
    journey_phase: str = "steady_state",
) -> MagicMock:
    m = MagicMock()
    m.id = athlete_id
    m.journey_phase = journey_phase
    m.sports_json = '["running"]'
    m.primary_sport = "running"
    m.hours_per_week = 8.0
    m.coaching_mode = "full"
    m.clinical_context_flag = None
    m.recovery_takeover_active = False
    m.proactive_message_count_this_week = 0
    return m


def _make_db(athlete: MagicMock) -> MagicMock:
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = athlete
    return db


class TestMonitoringHRV:
    def test_hrv_degraded_3_days_sets_recovery_flag(self):
        """HRV degraded 3 consecutive days → recovery_flag set, no LLM call."""
        from app.services.monitoring_service import MonitoringService

        athlete = _make_athlete()
        db = _make_db(athlete)

        service = MonitoringService(db=db)
        result = service.check_hrv_trend(
            athlete_id="a1",
            hrv_daily_values=[45.0, 42.0, 38.0],  # 3 days degrading
        )

        assert result["recovery_flag_set"] is True
        assert result["llm_calls"] == 0

    def test_hrv_stable_does_not_set_flag(self):
        """HRV stable → no recovery flag set."""
        from app.services.monitoring_service import MonitoringService

        athlete = _make_athlete()
        db = _make_db(athlete)

        service = MonitoringService(db=db)
        result = service.check_hrv_trend(
            athlete_id="a1",
            hrv_daily_values=[50.0, 51.0, 49.0],  # stable
        )

        assert result["recovery_flag_set"] is False

    def test_hrv_only_2_days_does_not_set_flag(self):
        """HRV degraded only 2 days → no flag (need 3 consecutive)."""
        from app.services.monitoring_service import MonitoringService

        athlete = _make_athlete()
        db = _make_db(athlete)

        service = MonitoringService(db=db)
        result = service.check_hrv_trend(
            athlete_id="a1",
            hrv_daily_values=[50.0, 45.0],  # only 2 values
        )

        assert result["recovery_flag_set"] is False


class TestMonitoringEnergyPatterns:
    def test_energy_patterns_detected_sets_flag_no_llm(self):
        """Energy patterns detected → flag set in AthleteState, no LLM call."""
        from app.services.monitoring_service import MonitoringService

        athlete = _make_athlete()
        db = _make_db(athlete)

        service = MonitoringService(db=db)

        with patch("app.services.monitoring_service.detect_energy_patterns") as mock_detect:
            mock_detect.return_value = ["heavy_legs", "chronic_stress"]
            result = service.check_energy_patterns(athlete_id="a1")

        assert result["energy_flags"] == ["heavy_legs", "chronic_stress"]
        assert result["llm_calls"] == 0

    def test_no_energy_patterns_returns_empty(self):
        """No patterns → empty list, no flags."""
        from app.services.monitoring_service import MonitoringService

        athlete = _make_athlete()
        db = _make_db(athlete)

        service = MonitoringService(db=db)

        with patch("app.services.monitoring_service.detect_energy_patterns") as mock_detect:
            mock_detect.return_value = []
            result = service.check_energy_patterns(athlete_id="a1")

        assert result["energy_flags"] == []


class TestMonitoringProactiveMessages:
    def test_first_proactive_message_allowed(self):
        """First proactive message this week → allowed (count < 2)."""
        from app.services.monitoring_service import MonitoringService

        athlete = _make_athlete()
        athlete.proactive_message_count_this_week = 0
        db = _make_db(athlete)

        service = MonitoringService(db=db)
        result = service.check_proactive_message_allowed(athlete_id="a1")

        assert result["allowed"] is True

    def test_second_proactive_message_allowed(self):
        """Second message this week → still allowed."""
        from app.services.monitoring_service import MonitoringService

        athlete = _make_athlete()
        athlete.proactive_message_count_this_week = 1
        db = _make_db(athlete)

        service = MonitoringService(db=db)
        result = service.check_proactive_message_allowed(athlete_id="a1")

        assert result["allowed"] is True

    def test_third_proactive_message_blocked(self):
        """Third message this week → blocked (cap = 2)."""
        from app.services.monitoring_service import MonitoringService

        athlete = _make_athlete()
        athlete.proactive_message_count_this_week = 2
        db = _make_db(athlete)

        service = MonitoringService(db=db)
        result = service.check_proactive_message_allowed(athlete_id="a1")

        assert result["allowed"] is False


class TestMonitoringBaselineExitConditions:
    def test_baseline_exit_conditions_met_triggers_followup(self):
        """baseline_active exit conditions met → followup_transition triggered."""
        from app.services.monitoring_service import MonitoringService

        athlete = _make_athlete(journey_phase="baseline_active")
        db = _make_db(athlete)

        service = MonitoringService(db=db)

        with patch.object(service, "_trigger_followup_transition") as mock_trigger:
            mock_trigger.return_value = True
            result = service.check_baseline_exit_conditions(
                athlete_id="a1",
                weeks_completed=4,
                required_weeks=4,
            )

        assert result["followup_triggered"] is True
        mock_trigger.assert_called_once_with("a1")

    def test_baseline_exit_conditions_not_met_no_trigger(self):
        """baseline_active exit conditions not met → no trigger."""
        from app.services.monitoring_service import MonitoringService

        athlete = _make_athlete(journey_phase="baseline_active")
        db = _make_db(athlete)

        service = MonitoringService(db=db)

        result = service.check_baseline_exit_conditions(
            athlete_id="a1",
            weeks_completed=2,
            required_weeks=4,
        )

        assert result["followup_triggered"] is False
