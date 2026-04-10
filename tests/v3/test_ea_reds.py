"""Tests unitaires pour la detection EA + RED-S dans backend/app/core/hormonal.py.

Couvre :
- ea_status()   — classification optimal/suboptimal/critical par sexe
- check_reds()  — detection 3 jours consecutifs EA < seuil
"""
from __future__ import annotations

import pytest

from app.core.hormonal import check_reds, ea_status


# ---------------------------------------------------------------------------
# ea_status
# ---------------------------------------------------------------------------

class TestEaStatus:
    # Female thresholds: optimal >= 45, suboptimal 30-44.9, critical < 30
    def test_female_optimal_above_45(self):
        assert ea_status(45.0, "female") == "optimal"

    def test_female_optimal_at_50(self):
        assert ea_status(50.0, "female") == "optimal"

    def test_female_suboptimal_at_35(self):
        assert ea_status(35.0, "female") == "suboptimal"

    def test_female_suboptimal_at_30(self):
        assert ea_status(30.0, "female") == "suboptimal"

    def test_female_critical_below_30(self):
        assert ea_status(29.9, "female") == "critical"

    def test_female_critical_at_20(self):
        assert ea_status(20.0, "female") == "critical"

    # Male thresholds: optimal >= 45, suboptimal 25-44.9, critical < 25
    def test_male_optimal_above_45(self):
        assert ea_status(45.0, "male") == "optimal"

    def test_male_suboptimal_at_30(self):
        assert ea_status(30.0, "male") == "suboptimal"

    def test_male_suboptimal_at_25(self):
        assert ea_status(25.0, "male") == "suboptimal"

    def test_male_critical_below_25(self):
        assert ea_status(24.9, "male") == "critical"

    def test_male_critical_at_20(self):
        assert ea_status(20.0, "male") == "critical"

    # Female critical threshold is lower than male
    def test_female_and_male_differ_at_27(self):
        # 27 kcal/kg FFM: critical for female (< 30), suboptimal for male (>= 25)
        assert ea_status(27.0, "female") == "critical"
        assert ea_status(27.0, "male") == "suboptimal"


# ---------------------------------------------------------------------------
# check_reds
# ---------------------------------------------------------------------------

class TestCheckReds:
    def test_returns_false_when_history_empty(self):
        assert check_reds([], threshold=30.0) is False

    def test_returns_false_when_fewer_than_3_days(self):
        assert check_reds([25.0, 28.0], threshold=30.0) is False

    def test_returns_true_when_3_consecutive_days_below_threshold(self):
        assert check_reds([25.0, 28.0, 29.0], threshold=30.0) is True

    def test_returns_true_when_more_than_3_days_all_below(self):
        assert check_reds([20.0, 22.0, 25.0, 28.0], threshold=30.0) is True

    def test_returns_false_when_last_day_above_threshold(self):
        # [25, 28, 31]: last 3 = [25, 28, 31] -> 31 >= 30, so no RED-S
        assert check_reds([25.0, 28.0, 31.0], threshold=30.0) is False

    def test_returns_false_when_only_2_of_last_3_below(self):
        # [31, 28, 29]: last 3 = [31, 28, 29] -> 31 >= 30, no RED-S
        assert check_reds([31.0, 28.0, 29.0], threshold=30.0) is False

    def test_returns_false_for_non_consecutive_pattern(self):
        # [25, 31, 28]: last 3 = [25, 31, 28] -> 31 >= 30, no RED-S
        assert check_reds([25.0, 31.0, 28.0], threshold=30.0) is False

    def test_exactly_3_days_all_below_returns_true(self):
        history = [20.0, 22.0, 29.9]
        assert check_reds(history, threshold=30.0) is True

    def test_exactly_at_threshold_does_not_trigger(self):
        # EA == threshold is NOT below, so no RED-S
        assert check_reds([30.0, 30.0, 30.0], threshold=30.0) is False

    def test_custom_required_days_2(self):
        # With required_days=2, only need last 2 below threshold
        assert check_reds([31.0, 25.0, 28.0], threshold=30.0, required_days=2) is True

    def test_custom_required_days_5(self):
        # With required_days=5, need 5 consecutive
        history = [25.0, 25.0, 25.0, 25.0, 25.0]
        assert check_reds(history, threshold=30.0, required_days=5) is True

    def test_custom_required_days_5_only_4_days_below(self):
        history = [31.0, 25.0, 25.0, 25.0, 25.0]
        assert check_reds(history, threshold=30.0, required_days=5) is False

    def test_male_threshold_25_triggers_reds(self):
        history = [24.0, 23.0, 22.0]
        assert check_reds(history, threshold=25.0) is True

    def test_male_threshold_25_no_reds_when_above(self):
        history = [26.0, 24.0, 24.0]
        assert check_reds(history, threshold=25.0) is False
