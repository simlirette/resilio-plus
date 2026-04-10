"""Tests unitaires pour backend/app/core/allostatic.py.

Couvre :
- calculate_allostatic_score() — formule pondérée, composantes, cas limites
- intensity_cap_from_score() — seuils d'action par plage de score
"""
from __future__ import annotations

import pytest

from app.core.allostatic import calculate_allostatic_score, intensity_cap_from_score


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _score(
    hrv_deviation: float = 0.0,
    sleep_quality: float = 100.0,
    work_intensity: str = "light",
    stress_level: str = "none",
    cycle_phase: str | None = None,
    ea_status: str = "optimal",
) -> float:
    return calculate_allostatic_score(
        hrv_deviation=hrv_deviation,
        sleep_quality=sleep_quality,
        work_intensity=work_intensity,
        stress_level=stress_level,
        cycle_phase=cycle_phase,
        ea_status=ea_status,
    )


# ---------------------------------------------------------------------------
# calculate_allostatic_score — composantes
# ---------------------------------------------------------------------------

class TestAllostaticScoreComponents:

    def test_all_optimal_returns_minimal_score(self):
        """hrv=0, sleep=100, light, none, follicular, optimal → très bas."""
        score = _score(
            hrv_deviation=0.0,
            sleep_quality=100.0,
            work_intensity="light",
            stress_level="none",
            cycle_phase="follicular",
            ea_status="optimal",
        )
        # sleep=100 → sleep_score=0; hrv=0 → hrv_score=0; light→10; none→0; follicular→10; optimal→0
        # weighted: 0.30*0 + 0.25*0 + 0.20*10 + 0.15*0 + 0.05*10 + 0.05*0 = 2.5
        assert pytest.approx(score, abs=0.01) == 2.5

    def test_hrv_negative_15_percent_contributes_30(self):
        """hrv_deviation = -15 → hrv_score = max(0, 15*2) = 30."""
        score = _score(hrv_deviation=-15.0, sleep_quality=100.0, work_intensity="light",
                       stress_level="none", ea_status="optimal")
        # hrv contribution = 0.30 * 30 = 9.0; other components = 2.0 (light=10, no cycle default=20)
        # 0.30*30 + 0.25*0 + 0.20*10 + 0.15*0 + 0.05*20 + 0.05*0 = 9+0+2+0+1+0 = 12.0
        assert pytest.approx(score, abs=0.01) == 12.0

    def test_hrv_positive_deviation_contributes_zero(self):
        """hrv_deviation > 0 (meilleur que baseline) → hrv_score = 0."""
        score = _score(hrv_deviation=10.0, sleep_quality=100.0, work_intensity="light",
                       stress_level="none", ea_status="optimal")
        # hrv_score = max(0, -10*2) = 0 — positive deviation = no load
        assert score < 5.0  # only light work + default cycle contribute

    def test_sleep_quality_zero_contributes_maximum(self):
        """sleep_quality = 0 → sleep_score = 100."""
        score = _score(sleep_quality=0.0, work_intensity="light",
                       stress_level="none", ea_status="optimal")
        # sleep component alone = 0.25 * 100 = 25
        assert score >= 25.0

    def test_sleep_quality_100_contributes_zero(self):
        """sleep_quality = 100 → sleep_score = 0."""
        # With perfect sleep, score is only driven by other components
        score = _score(sleep_quality=100.0, work_intensity="light",
                       stress_level="none", ea_status="optimal")
        assert score < 10.0  # minimal contribution from light work only

    def test_work_intensity_scores_mapping(self):
        """Vérifie que chaque niveau de travail produit le bon score."""
        scores_by_work = {
            "light": _score(work_intensity="light"),
            "normal": _score(work_intensity="normal"),
            "heavy": _score(work_intensity="heavy"),
            "exhausting": _score(work_intensity="exhausting"),
        }
        assert scores_by_work["light"] < scores_by_work["normal"]
        assert scores_by_work["normal"] < scores_by_work["heavy"]
        assert scores_by_work["heavy"] < scores_by_work["exhausting"]

    def test_work_exhausting_contributes_90_times_weight(self):
        """work_intensity='exhausting' → work_score=90, contribution=0.20*90=18."""
        score = _score(sleep_quality=100.0, work_intensity="exhausting",
                       stress_level="none", ea_status="optimal")
        # 0.20*90 = 18, + 0.05*20 (default cycle) = 1 → 19
        assert pytest.approx(score, abs=0.01) == 19.0

    def test_stress_significant_score_70(self):
        """stress_level='significant' → stress_score=70, contribution=0.15*70=10.5."""
        score = _score(sleep_quality=100.0, work_intensity="light",
                       stress_level="significant", ea_status="optimal")
        # 0.20*10 + 0.15*70 + 0.05*20 = 2 + 10.5 + 1 = 13.5
        assert pytest.approx(score, abs=0.01) == 13.5

    def test_cycle_menstrual_score_40(self):
        """cycle_phase='menstrual' → cycle_score=40, contribution=0.05*40=2."""
        score_menstrual = _score(sleep_quality=100.0, work_intensity="light",
                                  stress_level="none", cycle_phase="menstrual", ea_status="optimal")
        score_follicular = _score(sleep_quality=100.0, work_intensity="light",
                                   stress_level="none", cycle_phase="follicular", ea_status="optimal")
        # menstrual contributes more than follicular
        assert score_menstrual > score_follicular

    def test_cycle_none_defaults_to_score_20(self):
        """cycle_phase=None → default score=20, contribution=0.05*20=1."""
        score_none = _score(sleep_quality=100.0, work_intensity="light",
                            stress_level="none", cycle_phase=None, ea_status="optimal")
        score_follicular = _score(sleep_quality=100.0, work_intensity="light",
                                   stress_level="none", cycle_phase="follicular", ea_status="optimal")
        # None (default 20) should be higher than follicular (10)
        assert score_none > score_follicular

    def test_ea_critical_contributes_80_times_weight(self):
        """ea_status='critical' → ea_score=80, contribution=0.05*80=4."""
        score_crit = _score(sleep_quality=100.0, work_intensity="light",
                             stress_level="none", ea_status="critical")
        score_opt = _score(sleep_quality=100.0, work_intensity="light",
                            stress_level="none", ea_status="optimal")
        # difference should be exactly 0.05*(80-0) = 4
        assert pytest.approx(score_crit - score_opt, abs=0.01) == 4.0

    def test_ea_suboptimal_contributes_40_times_weight(self):
        """ea_status='suboptimal' → ea_score=40, contribution=0.05*40=2."""
        score_sub = _score(sleep_quality=100.0, work_intensity="light",
                            stress_level="none", ea_status="suboptimal")
        score_opt = _score(sleep_quality=100.0, work_intensity="light",
                            stress_level="none", ea_status="optimal")
        assert pytest.approx(score_sub - score_opt, abs=0.01) == 2.0


# ---------------------------------------------------------------------------
# calculate_allostatic_score — weighted sum exact
# ---------------------------------------------------------------------------

class TestAllostaticScoreFormula:

    def test_exact_weighted_sum_from_spec(self):
        """Valeur de référence section 5.2 du master doc.

        Reproduit le calcul manuel:
          hrv_deviation=-15 → hrv_score=30
          sleep_quality=60  → sleep_score=40
          work='heavy'      → work_score=65
          stress='mild'     → stress_score=30
          cycle='luteal'    → cycle_score=35
          ea='suboptimal'   → ea_score=40

          total = 0.30*30 + 0.25*40 + 0.20*65 + 0.15*30 + 0.05*35 + 0.05*40
                = 9 + 10 + 13 + 4.5 + 1.75 + 2 = 40.25
        """
        score = calculate_allostatic_score(
            hrv_deviation=-15.0,
            sleep_quality=60.0,
            work_intensity="heavy",
            stress_level="mild",
            cycle_phase="luteal",
            ea_status="suboptimal",
        )
        assert pytest.approx(score, abs=0.01) == 40.25

    def test_all_worst_case_returns_near_100(self):
        """Scénario catastrophe → score élevé."""
        score = calculate_allostatic_score(
            hrv_deviation=-50.0,
            sleep_quality=0.0,
            work_intensity="exhausting",
            stress_level="significant",
            cycle_phase="menstrual",
            ea_status="critical",
        )
        # hrv_score = min(100, 100) = 100; sleep_score=100; work=90; stress=70; cycle=40; ea=80
        # = 0.30*100 + 0.25*100 + 0.20*90 + 0.15*70 + 0.05*40 + 0.05*80
        # = 30 + 25 + 18 + 10.5 + 2 + 4 = 89.5
        assert pytest.approx(score, abs=0.01) == 89.5

    def test_score_is_clamped_to_100(self):
        """hrv_deviation très négatif → hrv_score plafonné à 100."""
        score = calculate_allostatic_score(
            hrv_deviation=-100.0,  # sans plafond = 200, avec plafond = 100
            sleep_quality=0.0,
            work_intensity="exhausting",
            stress_level="significant",
            cycle_phase="menstrual",
            ea_status="critical",
        )
        assert score <= 100.0

    def test_score_is_never_negative(self):
        """Score toujours >= 0 même avec hrv_deviation positif."""
        score = calculate_allostatic_score(
            hrv_deviation=50.0,
            sleep_quality=100.0,
            work_intensity="light",
            stress_level="none",
            cycle_phase="follicular",
            ea_status="optimal",
        )
        assert score >= 0.0


# ---------------------------------------------------------------------------
# intensity_cap_from_score
# ---------------------------------------------------------------------------

class TestIntensityCapFromScore:

    def test_score_0_returns_full_cap(self):
        assert intensity_cap_from_score(0.0) == 1.0

    def test_score_40_returns_full_cap(self):
        assert intensity_cap_from_score(40.0) == 1.0

    def test_score_41_returns_full_cap_with_warning(self):
        # 41-60: cap 1.0 (avertissement mais pas de réduction)
        assert intensity_cap_from_score(41.0) == 1.0

    def test_score_60_returns_full_cap(self):
        assert intensity_cap_from_score(60.0) == 1.0

    def test_score_61_returns_85_percent(self):
        assert intensity_cap_from_score(61.0) == pytest.approx(0.85)

    def test_score_80_returns_85_percent(self):
        assert intensity_cap_from_score(80.0) == pytest.approx(0.85)

    def test_score_81_returns_70_percent(self):
        assert intensity_cap_from_score(81.0) == pytest.approx(0.70)

    def test_score_100_returns_70_percent(self):
        assert intensity_cap_from_score(100.0) == pytest.approx(0.70)
