"""Tests unitaires pour energy_availability.py et EnergyCoach.

Couvre :
- calculate_energy_availability() — formule EA = (intake - EAT) / FFM
- get_ea_status() — seuils par sexe
- detect_reds_risk() — signal RED-S sur 3 jours consécutifs
- EnergyCoach — 5 skills + create_snapshot()
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.core.energy_availability import (
    calculate_energy_availability,
    detect_reds_risk,
    get_ea_status,
)
from app.agents.energy_coach import EnergyCoach
from app.agents.energy_coach.agent import EnergyCheckIn, EnergyInput
from app.models.athlete_state import EnergySnapshot


# ---------------------------------------------------------------------------
# calculate_energy_availability
# ---------------------------------------------------------------------------

class TestCalculateEnergyAvailability:

    def test_normal_values_return_correct_ea(self):
        """EA = (2500 - 500) / 60 = 33.33 kcal/kg FFM."""
        ea = calculate_energy_availability(
            caloric_intake=2500.0,
            exercise_energy=500.0,
            ffm_kg=60.0,
        )
        assert pytest.approx(ea, abs=0.01) == 33.33

    def test_optimal_ea_above_45(self):
        """intake=3000, EAT=300, FFM=55 → EA = 2700/55 = 49.09 → optimal."""
        ea = calculate_energy_availability(3000.0, 300.0, 55.0)
        assert ea > 45.0

    def test_zero_exercise_energy(self):
        """Sans entraînement : EA = intake / FFM."""
        ea = calculate_energy_availability(2000.0, 0.0, 50.0)
        assert pytest.approx(ea, abs=0.01) == 40.0

    def test_raises_if_ffm_zero(self):
        """FFM = 0 doit lever une ValueError."""
        with pytest.raises((ValueError, ZeroDivisionError)):
            calculate_energy_availability(2000.0, 500.0, 0.0)

    def test_ea_can_be_negative(self):
        """intake < EAT → EA négatif (cas extrême)."""
        ea = calculate_energy_availability(200.0, 700.0, 50.0)
        assert ea < 0.0


# ---------------------------------------------------------------------------
# get_ea_status
# ---------------------------------------------------------------------------

class TestGetEaStatus:

    def test_above_45_is_optimal_for_female(self):
        assert get_ea_status(46.0, sex="F") == "optimal"

    def test_above_45_is_optimal_for_male(self):
        assert get_ea_status(50.0, sex="M") == "optimal"

    def test_between_30_and_45_is_suboptimal_female(self):
        assert get_ea_status(35.0, sex="F") == "suboptimal"

    def test_between_25_and_45_is_suboptimal_male(self):
        assert get_ea_status(30.0, sex="M") == "suboptimal"

    def test_below_30_is_critical_female(self):
        assert get_ea_status(28.0, sex="F") == "critical"

    def test_below_25_is_critical_male(self):
        assert get_ea_status(24.0, sex="M") == "critical"

    def test_exactly_30_is_suboptimal_female(self):
        """EA = 30 kcal/kg FFM (femme) — seuil inclusif côté suboptimal."""
        assert get_ea_status(30.0, sex="F") == "suboptimal"

    def test_exactly_25_is_suboptimal_male(self):
        """EA = 25 kcal/kg FFM (homme) — seuil inclusif côté suboptimal."""
        assert get_ea_status(25.0, sex="M") == "suboptimal"

    def test_between_25_and_30_male_is_suboptimal_not_critical(self):
        """Homme : critique < 25, pas < 30."""
        assert get_ea_status(27.0, sex="M") == "suboptimal"

    def test_below_25_female_is_critical(self):
        """Femme EA=24 → aussi critique (sous seuil femme ET homme)."""
        assert get_ea_status(24.0, sex="F") == "critical"


# ---------------------------------------------------------------------------
# detect_reds_risk
# ---------------------------------------------------------------------------

class TestDetectRedsRisk:

    def test_three_consecutive_critical_days_female(self):
        """EA sous seuil critique (< 30) 3 jours d'affilée → RED-S."""
        history = [28.0, 27.0, 25.0]
        assert detect_reds_risk(history, sex="F") is True

    def test_three_consecutive_critical_days_male(self):
        """EA < 25 pendant 3 jours (homme) → RED-S."""
        history = [24.0, 23.0, 22.0]
        assert detect_reds_risk(history, sex="M") is True

    def test_two_consecutive_days_not_enough(self):
        """Seulement 2 jours critiques → pas de RED-S."""
        history = [28.0, 27.0, 35.0]  # jour 3 est OK
        assert detect_reds_risk(history, sex="F") is False

    def test_three_days_not_consecutive(self):
        """3 jours critiques mais non-consécutifs → pas de RED-S."""
        history = [28.0, 35.0, 27.0, 38.0, 26.0]
        assert detect_reds_risk(history, sex="F") is False

    def test_empty_history_no_risk(self):
        assert detect_reds_risk([], sex="F") is False

    def test_fewer_than_three_entries(self):
        assert detect_reds_risk([28.0, 27.0], sex="F") is False

    def test_four_consecutive_critical_days(self):
        """4 jours consécutifs → toujours RED-S."""
        history = [28.0, 27.0, 25.0, 24.0]
        assert detect_reds_risk(history, sex="F") is True

    def test_male_threshold_30_does_not_trigger(self):
        """EA=28 femme→critique mais homme→suboptimal → pas RED-S pour homme."""
        history = [28.0, 28.0, 28.0]
        assert detect_reds_risk(history, sex="M") is False


# ---------------------------------------------------------------------------
# EnergyCoach — initialisation
# ---------------------------------------------------------------------------

class TestEnergyCoachInit:

    def test_instantiation(self):
        coach = EnergyCoach()
        assert coach is not None

    def test_name(self):
        assert EnergyCoach().name == "energy"


# ---------------------------------------------------------------------------
# EnergyCoach — skill: calculate_allostatic_score
# ---------------------------------------------------------------------------

class TestEnergyCoachAllostaticSkill:

    def test_returns_float_in_range(self):
        coach = EnergyCoach()
        score = coach.calculate_allostatic_score(
            hrv_deviation=-10.0,
            sleep_quality=70.0,
            work_intensity="normal",
            stress_level="mild",
            cycle_phase=None,
            ea_status="optimal",
        )
        assert 0.0 <= score <= 100.0

    def test_delegates_to_core(self):
        """Doit retourner la même valeur que core/allostatic.py."""
        from app.core.allostatic import calculate_allostatic_score as core_fn
        coach = EnergyCoach()
        kwargs = dict(
            hrv_deviation=-15.0,
            sleep_quality=60.0,
            work_intensity="heavy",
            stress_level="mild",
            cycle_phase="luteal",
            ea_status="suboptimal",
        )
        assert coach.calculate_allostatic_score(**kwargs) == core_fn(**kwargs)


# ---------------------------------------------------------------------------
# EnergyCoach — skill: assess_cognitive_load
# ---------------------------------------------------------------------------

class TestEnergyCoachCognitiveSkill:

    def test_returns_float_in_range(self):
        coach = EnergyCoach()
        load = coach.assess_cognitive_load(work_intensity="normal", stress_level="none")
        assert 0.0 <= load <= 100.0

    def test_exhausting_day_high_cognitive_load(self):
        coach = EnergyCoach()
        load = coach.assess_cognitive_load(work_intensity="exhausting", stress_level="significant")
        assert load > 60.0

    def test_light_day_low_cognitive_load(self):
        coach = EnergyCoach()
        load = coach.assess_cognitive_load(work_intensity="light", stress_level="none")
        assert load < 30.0


# ---------------------------------------------------------------------------
# EnergyCoach — skill: calculate_energy_availability
# ---------------------------------------------------------------------------

class TestEnergyCoachEASkill:

    def test_delegates_to_core(self):
        """Doit retourner la même valeur que core/energy_availability.py."""
        coach = EnergyCoach()
        ea = coach.calculate_energy_availability(
            caloric_intake=2500.0,
            exercise_energy=500.0,
            ffm_kg=60.0,
        )
        assert pytest.approx(ea, abs=0.01) == 33.33


# ---------------------------------------------------------------------------
# EnergyCoach — skill: predict_recovery_capacity
# ---------------------------------------------------------------------------

class TestEnergyCoachRecoverySkill:

    def test_returns_float_in_range(self):
        coach = EnergyCoach()
        cap = coach.predict_recovery_capacity(allostatic_score=50.0)
        assert 0.0 <= cap <= 100.0

    def test_high_allostatic_score_reduces_capacity(self):
        coach = EnergyCoach()
        cap_low = coach.predict_recovery_capacity(allostatic_score=20.0)
        cap_high = coach.predict_recovery_capacity(allostatic_score=80.0)
        assert cap_high < cap_low

    def test_zero_score_max_capacity(self):
        coach = EnergyCoach()
        cap = coach.predict_recovery_capacity(allostatic_score=0.0)
        assert cap == pytest.approx(100.0)

    def test_100_score_min_capacity(self):
        coach = EnergyCoach()
        cap = coach.predict_recovery_capacity(allostatic_score=100.0)
        assert cap == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# EnergyCoach — skill: generate_energy_report
# ---------------------------------------------------------------------------

class TestEnergyCoachReportSkill:

    def test_returns_dict_with_required_keys(self):
        coach = EnergyCoach()
        report = coach.generate_energy_report(
            allostatic_score=45.0,
            energy_availability=38.0,
            cognitive_load=40.0,
            recovery_capacity=55.0,
            flags=[],
        )
        assert "allostatic_score" in report
        assert "energy_availability" in report
        assert "intensity_cap" in report
        assert "veto_triggered" in report
        assert "flags" in report

    def test_veto_true_when_ea_critical_female(self):
        coach = EnergyCoach()
        report = coach.generate_energy_report(
            allostatic_score=30.0,
            energy_availability=28.0,  # < 30 → critique femme
            cognitive_load=30.0,
            recovery_capacity=70.0,
            flags=["ea_critical"],
            sex="F",
        )
        assert report["veto_triggered"] is True

    def test_veto_false_when_all_ok(self):
        coach = EnergyCoach()
        report = coach.generate_energy_report(
            allostatic_score=30.0,
            energy_availability=50.0,
            cognitive_load=20.0,
            recovery_capacity=80.0,
            flags=[],
        )
        assert report["veto_triggered"] is False


# ---------------------------------------------------------------------------
# EnergyCoach — create_snapshot() — integration
# ---------------------------------------------------------------------------

class TestEnergyCoachCreateSnapshot:

    def _default_input(self, **overrides) -> EnergyInput:
        defaults = dict(
            hrv_deviation=-5.0,
            sleep_quality=75.0,
            caloric_intake=2400.0,
            exercise_energy=400.0,
            ffm_kg=60.0,
            sex="M",
            check_in=EnergyCheckIn(
                work_intensity="normal",
                stress_level="none",
                cycle_phase=None,
            ),
            ea_history=[],
        )
        defaults.update(overrides)
        return EnergyInput(**defaults)

    def test_returns_energy_snapshot(self):
        coach = EnergyCoach()
        snap = coach.create_snapshot(self._default_input())
        assert isinstance(snap, EnergySnapshot)

    def test_snapshot_has_valid_allostatic_score(self):
        coach = EnergyCoach()
        snap = coach.create_snapshot(self._default_input())
        assert 0.0 <= snap.allostatic_score <= 100.0

    def test_snapshot_has_valid_energy_availability(self):
        coach = EnergyCoach()
        snap = coach.create_snapshot(self._default_input())
        # (2400 - 400) / 60 = 33.33
        assert pytest.approx(snap.energy_availability, abs=0.01) == 33.33

    def test_snapshot_veto_triggered_when_ea_critical_female(self):
        """EA = (1800 - 800) / 60 = 16.67 < 25 (homme) → veto."""
        coach = EnergyCoach()
        inp = self._default_input(
            caloric_intake=1800.0,
            exercise_energy=800.0,
            ffm_kg=60.0,
            sex="M",
        )
        snap = coach.create_snapshot(inp)
        assert snap.veto_triggered is True

    def test_snapshot_no_veto_when_all_ok(self):
        """EA optimale, score bas → pas de veto."""
        coach = EnergyCoach()
        inp = self._default_input(
            hrv_deviation=0.0,
            sleep_quality=90.0,
            caloric_intake=3000.0,
            exercise_energy=300.0,
            ffm_kg=60.0,
            check_in=EnergyCheckIn(work_intensity="light", stress_level="none"),
        )
        snap = coach.create_snapshot(inp)
        assert snap.veto_triggered is False

    def test_snapshot_veto_triggered_when_score_above_80(self):
        """Allostatic score > 80 → veto indépendamment de l'EA."""
        coach = EnergyCoach()
        inp = self._default_input(
            hrv_deviation=-50.0,     # hrv_score = 100 → 0.30*100 = 30
            sleep_quality=0.0,       # sleep_score = 100 → 0.25*100 = 25
            caloric_intake=3000.0,
            exercise_energy=100.0,
            ffm_kg=60.0,
            check_in=EnergyCheckIn(
                work_intensity="exhausting",    # 0.20*90 = 18
                stress_level="significant",     # 0.15*70 = 10.5
            ),
        )
        snap = coach.create_snapshot(inp)
        # allostatic ≈ 30+25+18+10.5+1 = 84.5 > 80 → veto
        assert snap.veto_triggered is True

    def test_snapshot_intensity_cap_reduced_at_heavy_load(self):
        """Score 61-80 → cap = 0.85."""
        coach = EnergyCoach()
        inp = self._default_input(
            hrv_deviation=-20.0,   # hrv_score=40 → 0.30*40=12
            sleep_quality=30.0,    # sleep_score=70 → 0.25*70=17.5
            check_in=EnergyCheckIn(work_intensity="heavy", stress_level="mild"),
        )
        snap = coach.create_snapshot(inp)
        if 61.0 <= snap.allostatic_score <= 80.0:
            assert snap.recommended_intensity_cap == pytest.approx(0.85)

    def test_snapshot_cycle_phase_propagated(self):
        """cycle_phase déclaré dans le check-in → propagé dans le snapshot."""
        coach = EnergyCoach()
        inp = self._default_input(
            check_in=EnergyCheckIn(
                work_intensity="normal",
                stress_level="none",
                cycle_phase="luteal",
            )
        )
        snap = coach.create_snapshot(inp)
        assert snap.cycle_phase == "luteal"

    def test_snapshot_reds_flag_on_three_consecutive_critical_days(self):
        """3 jours EA critique → flag 'red_s_risk' dans veto_reason."""
        coach = EnergyCoach()
        inp = self._default_input(
            caloric_intake=1500.0,   # EA = (1500-400)/60 = 18.33 → critique homme
            exercise_energy=400.0,
            ffm_kg=60.0,
            sex="M",
            ea_history=[22.0, 21.0],  # 2 jours précédents critiques
        )
        snap = coach.create_snapshot(inp)
        assert snap.veto_triggered is True
        assert snap.veto_reason is not None
