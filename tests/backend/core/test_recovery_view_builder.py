"""D6 TDD — recovery_view_builder."""
from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest


def _make_athlete(athlete_id: str = "a1") -> MagicMock:
    m = MagicMock()
    m.id = athlete_id
    m.sports_json = '["running"]'
    m.primary_sport = "running"
    m.hours_per_week = 8.0
    m.coaching_mode = "full"
    m.journey_phase = "steady_state"
    return m


class TestBuildRecoveryView:
    def test_basic_view_shape(self):
        from app.core.recovery_view_builder import build_recovery_view

        athlete = _make_athlete()
        view = build_recovery_view(athlete=athlete, db=MagicMock())
        assert view.athlete_id == "a1"
        assert hasattr(view, "mean_vs_prescribed_delta_7d")

    def test_delta_null_when_no_logs(self):
        """mean_vs_prescribed_delta_7d is None when no session logs exist."""
        from app.core.recovery_view_builder import build_recovery_view

        athlete = _make_athlete()
        db = MagicMock()
        db.query.return_value.filter.return_value.filter.return_value.all.return_value = []
        view = build_recovery_view(athlete=athlete, db=db)
        assert view.mean_vs_prescribed_delta_7d is None

    def test_delta_computed_when_logs_exist(self):
        """mean_vs_prescribed_delta_7d computed as mean(actual - prescribed) over last 7 days."""
        from app.core.recovery_view_builder import build_recovery_view

        athlete = _make_athlete()
        db = MagicMock()

        # Two logs: actual 60min vs prescribed 45min → delta = +15; 30 vs 60 → -30
        log1 = MagicMock()
        log1.actual_duration_min = 60
        log1.prescribed_duration_min = 45
        log2 = MagicMock()
        log2.actual_duration_min = 30
        log2.prescribed_duration_min = 60

        db.query.return_value.filter.return_value.filter.return_value.all.return_value = [
            log1, log2
        ]
        view = build_recovery_view(athlete=athlete, db=db)
        # mean delta = (15 + (-30)) / 2 = -7.5
        assert view.mean_vs_prescribed_delta_7d == pytest.approx(-7.5, abs=0.1)


class TestBuildEnergyView:
    def test_energy_view_shape(self):
        from app.core.energy_view_builder import build_energy_view

        athlete = _make_athlete()
        db = MagicMock()
        db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        view = build_energy_view(athlete=athlete, db=db)
        assert view.athlete_id == "a1"
        assert isinstance(view.discipline_loads, list)
        assert isinstance(view.recent_checkins, list)

    def test_energy_view_graceful_with_no_data(self):
        """No data → all optional fields None, lists empty, no exception."""
        from app.core.energy_view_builder import build_energy_view

        athlete = _make_athlete()
        db = MagicMock()
        db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        view = build_energy_view(athlete=athlete, db=db)
        assert view.current_energy_availability is None
        assert view.allostatic_score is None
        assert view.intensity_cap is None
        assert view.recent_checkins == []
