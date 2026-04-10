"""Tests unitaires pour backend/app/core/hormonal.py.

Couvre :
- compute_cycle_day()  — calcul du jour de cycle depuis la date des dernières regles
- detect_cycle_phase() — mapping jour -> phase (menstrual/follicular/ovulation/luteal)
- get_lifting_adjustments()  — ajustements de force par phase
- get_running_adjustments()  — ajustements de course par phase
- get_nutrition_adjustments() — ajustements nutritionnels par phase
"""
from __future__ import annotations

from datetime import date

import pytest

from app.core.hormonal import (
    compute_cycle_day,
    detect_cycle_phase,
    get_lifting_adjustments,
    get_nutrition_adjustments,
    get_running_adjustments,
)


# ---------------------------------------------------------------------------
# compute_cycle_day
# ---------------------------------------------------------------------------

class TestComputeCycleDay:
    def test_today_is_start_date_returns_day_1(self):
        start = date(2026, 4, 1)
        assert compute_cycle_day(start, start) == 1

    def test_five_days_later_returns_day_6(self):
        start = date(2026, 4, 1)
        today = date(2026, 4, 6)
        assert compute_cycle_day(start, today) == 6

    def test_wraps_at_cycle_length_default_28(self):
        start = date(2026, 4, 1)
        today = date(2026, 4, 29)  # 28 days later -> wraps to day 1
        assert compute_cycle_day(start, today) == 1

    def test_cycle_length_30_wraps_correctly(self):
        start = date(2026, 4, 1)
        today = date(2026, 5, 1)  # 30 days later
        assert compute_cycle_day(start, today, cycle_length=30) == 1

    def test_day_27_returns_27(self):
        start = date(2026, 4, 1)
        today = date(2026, 4, 27)  # 26 days later -> day 27
        assert compute_cycle_day(start, today) == 27

    def test_last_day_of_cycle_returns_cycle_length(self):
        start = date(2026, 4, 1)
        today = date(2026, 4, 28)  # 27 days later -> day 28
        assert compute_cycle_day(start, today) == 28


# ---------------------------------------------------------------------------
# detect_cycle_phase
# ---------------------------------------------------------------------------

class TestDetectCyclePhase:
    @pytest.mark.parametrize("day", [1, 2, 3, 4, 5])
    def test_days_1_to_5_are_menstrual(self, day):
        assert detect_cycle_phase(day) == "menstrual"

    @pytest.mark.parametrize("day", [6, 7, 8, 10, 12, 13])
    def test_days_6_to_13_are_follicular(self, day):
        assert detect_cycle_phase(day) == "follicular"

    @pytest.mark.parametrize("day", [14, 15])
    def test_days_14_to_15_are_ovulation(self, day):
        assert detect_cycle_phase(day) == "ovulation"

    @pytest.mark.parametrize("day", [16, 20, 24, 28])
    def test_days_16_to_28_are_luteal(self, day):
        assert detect_cycle_phase(day) == "luteal"

    def test_boundary_day_1(self):
        assert detect_cycle_phase(1) == "menstrual"

    def test_boundary_day_28(self):
        assert detect_cycle_phase(28) == "luteal"

    def test_custom_cycle_length_day_30_is_luteal(self):
        assert detect_cycle_phase(30, cycle_length=35) == "luteal"

    def test_custom_cycle_length_day_35_is_luteal(self):
        assert detect_cycle_phase(35, cycle_length=35) == "luteal"


# ---------------------------------------------------------------------------
# get_lifting_adjustments
# ---------------------------------------------------------------------------

class TestGetLiftingAdjustments:
    def test_menstrual_rpe_offset_is_minus_1(self):
        adj = get_lifting_adjustments("menstrual")
        assert adj["rpe_offset"] == -1

    def test_menstrual_no_1rm_is_true(self):
        adj = get_lifting_adjustments("menstrual")
        assert adj["no_1rm"] is True

    def test_follicular_rpe_offset_is_zero(self):
        adj = get_lifting_adjustments("follicular")
        assert adj["rpe_offset"] == 0

    def test_follicular_1rm_allowed(self):
        adj = get_lifting_adjustments("follicular")
        assert adj["no_1rm"] is False

    def test_follicular_pr_week_flag(self):
        adj = get_lifting_adjustments("follicular")
        assert adj.get("pr_week") is True

    def test_ovulation_rpe_offset_is_zero(self):
        adj = get_lifting_adjustments("ovulation")
        assert adj["rpe_offset"] == 0

    def test_ovulation_ligament_risk_flag(self):
        adj = get_lifting_adjustments("ovulation")
        assert adj.get("ligament_risk_note") is True

    def test_luteal_rpe_offset_is_minus_1(self):
        adj = get_lifting_adjustments("luteal")
        assert adj["rpe_offset"] == -1

    def test_luteal_1rm_allowed(self):
        adj = get_lifting_adjustments("luteal")
        assert adj["no_1rm"] is False

    def test_all_phases_have_notes(self):
        for phase in ("menstrual", "follicular", "ovulation", "luteal"):
            adj = get_lifting_adjustments(phase)
            assert "notes" in adj
            assert len(adj["notes"]) > 0


# ---------------------------------------------------------------------------
# get_running_adjustments
# ---------------------------------------------------------------------------

class TestGetRunningAdjustments:
    def test_menstrual_replaces_intervals_with_z2(self):
        adj = get_running_adjustments("menstrual")
        assert adj["replace_intervals_with_z2"] is True

    def test_menstrual_no_direction_change_avoidance(self):
        adj = get_running_adjustments("menstrual")
        assert adj["avoid_direction_changes"] is False

    def test_follicular_does_not_replace_intervals(self):
        adj = get_running_adjustments("follicular")
        assert adj["replace_intervals_with_z2"] is False

    def test_follicular_high_intensity_optimal(self):
        adj = get_running_adjustments("follicular")
        assert adj.get("high_intensity_optimal") is True

    def test_ovulation_avoid_direction_changes(self):
        adj = get_running_adjustments("ovulation")
        assert adj["avoid_direction_changes"] is True

    def test_ovulation_does_not_replace_intervals(self):
        adj = get_running_adjustments("ovulation")
        assert adj["replace_intervals_with_z2"] is False

    def test_luteal_increase_hydration(self):
        adj = get_running_adjustments("luteal")
        assert adj["increase_hydration"] is True

    def test_luteal_avoid_heat(self):
        adj = get_running_adjustments("luteal")
        assert adj["avoid_heat"] is True

    def test_all_phases_have_notes(self):
        for phase in ("menstrual", "follicular", "ovulation", "luteal"):
            adj = get_running_adjustments(phase)
            assert "notes" in adj
            assert len(adj["notes"]) > 0


# ---------------------------------------------------------------------------
# get_nutrition_adjustments
# ---------------------------------------------------------------------------

class TestGetNutritionAdjustments:
    def test_menstrual_supplements_include_iron(self):
        adj = get_nutrition_adjustments("menstrual")
        assert "iron" in adj["supplements"]

    def test_menstrual_supplements_include_magnesium(self):
        adj = get_nutrition_adjustments("menstrual")
        assert "magnesium" in adj["supplements"]

    def test_menstrual_supplements_include_omega3(self):
        adj = get_nutrition_adjustments("menstrual")
        assert "omega3" in adj["supplements"]

    def test_menstrual_no_extra_protein(self):
        adj = get_nutrition_adjustments("menstrual")
        assert adj["protein_extra_g_per_kg"] == 0.0

    def test_menstrual_no_extra_calories(self):
        adj = get_nutrition_adjustments("menstrual")
        assert adj["calories_extra"] == 0

    def test_follicular_no_supplements(self):
        adj = get_nutrition_adjustments("follicular")
        assert adj["supplements"] == []

    def test_follicular_no_extra_protein(self):
        adj = get_nutrition_adjustments("follicular")
        assert adj["protein_extra_g_per_kg"] == 0.0

    def test_ovulation_no_extra_protein(self):
        adj = get_nutrition_adjustments("ovulation")
        assert adj["protein_extra_g_per_kg"] == 0.0

    def test_luteal_protein_extra_is_0_2(self):
        adj = get_nutrition_adjustments("luteal")
        assert adj["protein_extra_g_per_kg"] == pytest.approx(0.2)

    def test_luteal_calories_extra_is_200(self):
        adj = get_nutrition_adjustments("luteal")
        assert adj["calories_extra"] == 200

    def test_luteal_supplements_include_iron_and_magnesium(self):
        adj = get_nutrition_adjustments("luteal")
        assert "iron" in adj["supplements"]
        assert "magnesium" in adj["supplements"]

    def test_all_phases_have_notes(self):
        for phase in ("menstrual", "follicular", "ovulation", "luteal"):
            adj = get_nutrition_adjustments(phase)
            assert "notes" in adj
            assert len(adj["notes"]) > 0
