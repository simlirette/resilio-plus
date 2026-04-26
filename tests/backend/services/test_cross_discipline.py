"""D5 TDD — CrossDisciplineInterferenceService (DEP-C4-004)."""
from __future__ import annotations

import pytest


class TestCrossDisciplineInterferenceService:
    def test_all_zero_when_no_active_plan(self):
        from app.services.cross_discipline_interference import compute_cross_discipline_load_v1

        result = compute_cross_discipline_load_v1(active_plan=None)
        assert result.weekly_running_sessions == 0
        assert result.weekly_biking_sessions == 0
        assert result.weekly_swimming_sessions == 0

    def test_counts_running_sessions(self):
        from app.services.cross_discipline_interference import compute_cross_discipline_load_v1

        plan = {
            "sessions": [
                {"sport": "running"},
                {"sport": "running"},
                {"sport": "lifting"},
            ]
        }
        result = compute_cross_discipline_load_v1(active_plan=plan)
        assert result.weekly_running_sessions == 2
        assert result.weekly_biking_sessions == 0

    def test_counts_all_disciplines(self):
        from app.services.cross_discipline_interference import compute_cross_discipline_load_v1

        plan = {
            "sessions": [
                {"sport": "running"},
                {"sport": "cycling"},
                {"sport": "cycling"},
                {"sport": "swimming"},
                {"sport": "lifting"},
            ]
        }
        result = compute_cross_discipline_load_v1(active_plan=plan)
        assert result.weekly_running_sessions == 1
        assert result.weekly_biking_sessions == 2
        assert result.weekly_swimming_sessions == 1

    def test_cycling_alias_biking(self):
        """'cycling' and 'biking' both map to weekly_biking_sessions."""
        from app.services.cross_discipline_interference import compute_cross_discipline_load_v1

        plan = {"sessions": [{"sport": "cycling"}, {"sport": "biking"}]}
        result = compute_cross_discipline_load_v1(active_plan=plan)
        assert result.weekly_biking_sessions == 2

    def test_empty_sessions_list(self):
        from app.services.cross_discipline_interference import compute_cross_discipline_load_v1

        result = compute_cross_discipline_load_v1(active_plan={"sessions": []})
        assert result.weekly_running_sessions == 0
