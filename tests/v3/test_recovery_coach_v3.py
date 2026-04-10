"""Tests V3 — Recovery Coach : veto 5 composantes.

Couvre :
- classify_hrv()       — ratio HRV vs baseline
- classify_acwr()      — charge aiguë/chronique
- classify_ea()        — disponibilité énergétique (seuils par sexe)
- classify_allostatic()— score allostatic
- classify_cycle()     — phase du cycle menstruel
- compute_recovery_veto_v3() — logique de synthèse + cap final
- RecoveryCoachV3.assess() — API publique de l'agent

Référence : docs/resilio-v3-master.md — section 2.2
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import pytest

from app.agents.recovery_coach.prescriber import (
    classify_acwr,
    classify_allostatic,
    classify_cycle,
    classify_ea,
    classify_hrv,
    compute_recovery_veto_v3,
)
from app.agents.recovery_coach.agent import RecoveryCoachV3
from app.models.athlete_state import (
    EnergySnapshot,
    HormonalProfile,
    RecoveryVetoV3,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _snapshot(
    allostatic_score: float = 30.0,
    ea: float = 50.0,
    cycle_phase=None,
) -> EnergySnapshot:
    return EnergySnapshot(
        timestamp=datetime(2026, 4, 10, 8, 0, tzinfo=timezone.utc),
        allostatic_score=allostatic_score,
        cognitive_load=20.0,
        energy_availability=ea,
        cycle_phase=cycle_phase,
        sleep_quality=75.0,
        recommended_intensity_cap=1.0,
        veto_triggered=False,
    )


def _hormonal(phase: str, enabled: bool = True) -> HormonalProfile:
    return HormonalProfile(
        enabled=enabled,
        cycle_length_days=28,
        current_phase=phase,
    )


# ---------------------------------------------------------------------------
# classify_hrv
# ---------------------------------------------------------------------------

class TestClassifyHrv:

    def test_hrv_at_100pct_baseline_is_green(self):
        assert classify_hrv(current_hrv=60.0, baseline_hrv=60.0) == "green"

    def test_hrv_above_baseline_is_green(self):
        assert classify_hrv(current_hrv=70.0, baseline_hrv=60.0) == "green"

    def test_hrv_at_80pct_baseline_is_green(self):
        """Borne basse du vert : ratio = 0.80."""
        assert classify_hrv(current_hrv=48.0, baseline_hrv=60.0) == "green"

    def test_hrv_at_79pct_baseline_is_yellow(self):
        """Juste sous 0.80 → jaune."""
        assert classify_hrv(current_hrv=47.4, baseline_hrv=60.0) == "yellow"

    def test_hrv_at_60pct_baseline_is_yellow(self):
        """Borne basse du jaune : ratio = 0.60."""
        assert classify_hrv(current_hrv=36.0, baseline_hrv=60.0) == "yellow"

    def test_hrv_at_59pct_baseline_is_red(self):
        """Sous 0.60 → rouge."""
        assert classify_hrv(current_hrv=35.4, baseline_hrv=60.0) == "red"

    def test_hrv_no_data_is_green(self):
        """Pas de données HRV = vert par défaut (cold start)."""
        assert classify_hrv(current_hrv=None, baseline_hrv=None) == "green"

    def test_hrv_no_baseline_is_green(self):
        """HRV disponible mais pas de baseline → vert (pas de comparaison possible)."""
        assert classify_hrv(current_hrv=55.0, baseline_hrv=None) == "green"


# ---------------------------------------------------------------------------
# classify_acwr
# ---------------------------------------------------------------------------

class TestClassifyAcwr:

    def test_acwr_in_safe_zone_is_green(self):
        assert classify_acwr(acwr=1.0) == "green"

    def test_acwr_at_lower_bound_080_is_green(self):
        assert classify_acwr(acwr=0.8) == "green"

    def test_acwr_at_upper_bound_130_is_green(self):
        assert classify_acwr(acwr=1.3) == "green"

    def test_acwr_below_safe_zone_is_green(self):
        """ACWR < 0.8 = sous-entraînement — pas un risque → vert."""
        assert classify_acwr(acwr=0.5) == "green"

    def test_acwr_caution_zone_is_yellow(self):
        assert classify_acwr(acwr=1.4) == "yellow"

    def test_acwr_at_150_is_yellow(self):
        """Borne haute du jaune."""
        assert classify_acwr(acwr=1.5) == "yellow"

    def test_acwr_above_150_is_red(self):
        assert classify_acwr(acwr=1.6) == "red"

    def test_acwr_no_data_is_green(self):
        assert classify_acwr(acwr=None) == "green"


# ---------------------------------------------------------------------------
# classify_ea
# ---------------------------------------------------------------------------

class TestClassifyEa:

    # --- femme ---

    def test_ea_optimal_female_is_green(self):
        assert classify_ea(ea=50.0, sex="female") == "green"

    def test_ea_at_45_female_is_green(self):
        """Borne basse de l'optimal."""
        assert classify_ea(ea=45.0, sex="female") == "green"

    def test_ea_suboptimal_female_is_yellow(self):
        assert classify_ea(ea=35.0, sex="female") == "yellow"

    def test_ea_at_30_female_is_yellow(self):
        """EA = seuil critique féminin → encore jaune (non strictement < 30)."""
        assert classify_ea(ea=30.0, sex="female") == "yellow"

    def test_ea_critical_female_is_red(self):
        """EA < 30 kcal/kg FFM chez la femme → rouge immédiat."""
        assert classify_ea(ea=29.9, sex="female") == "red"

    def test_ea_very_low_female_is_red(self):
        assert classify_ea(ea=10.0, sex="female") == "red"

    # --- homme ---

    def test_ea_optimal_male_is_green(self):
        assert classify_ea(ea=50.0, sex="male") == "green"

    def test_ea_suboptimal_male_is_yellow(self):
        """EA 25-45 chez l'homme → jaune."""
        assert classify_ea(ea=30.0, sex="male") == "yellow"

    def test_ea_at_25_male_is_yellow(self):
        """Borne basse du jaune masculin."""
        assert classify_ea(ea=25.0, sex="male") == "yellow"

    def test_ea_critical_male_is_red(self):
        """EA < 25 chez l'homme → rouge."""
        assert classify_ea(ea=24.9, sex="male") == "red"

    def test_ea_no_data_is_green(self):
        assert classify_ea(ea=None, sex="female") == "green"


# ---------------------------------------------------------------------------
# classify_allostatic
# ---------------------------------------------------------------------------

class TestClassifyAllostatic:

    def test_allostatic_low_is_green(self):
        assert classify_allostatic(score=30.0) == "green"

    def test_allostatic_at_zero_is_green(self):
        assert classify_allostatic(score=0.0) == "green"

    def test_allostatic_below_60_is_green(self):
        assert classify_allostatic(score=59.9) == "green"

    def test_allostatic_at_60_is_yellow(self):
        """Seuil : >= 60 → jaune."""
        assert classify_allostatic(score=60.0) == "yellow"

    def test_allostatic_elevated_is_yellow(self):
        assert classify_allostatic(score=70.0) == "yellow"

    def test_allostatic_at_80_is_yellow(self):
        """Borne haute du jaune."""
        assert classify_allostatic(score=80.0) == "yellow"

    def test_allostatic_above_80_is_red(self):
        assert classify_allostatic(score=85.0) == "red"

    def test_allostatic_critical_is_red(self):
        assert classify_allostatic(score=100.0) == "red"

    def test_allostatic_no_data_is_green(self):
        assert classify_allostatic(score=None) == "green"


# ---------------------------------------------------------------------------
# classify_cycle
# ---------------------------------------------------------------------------

class TestClassifyCycle:

    def test_follicular_is_green(self):
        assert classify_cycle(_hormonal("follicular")) == "green"

    def test_menstrual_is_yellow(self):
        assert classify_cycle(_hormonal("menstrual")) == "yellow"

    def test_ovulation_is_yellow(self):
        assert classify_cycle(_hormonal("ovulation")) == "yellow"

    def test_luteal_is_yellow(self):
        assert classify_cycle(_hormonal("luteal")) == "yellow"

    def test_disabled_profile_returns_none(self):
        """Si le suivi de cycle est désactivé → None (non comptabilisé)."""
        assert classify_cycle(_hormonal("luteal", enabled=False)) is None

    def test_no_profile_returns_none(self):
        assert classify_cycle(None) is None

    def test_no_phase_set_returns_none(self):
        profile = HormonalProfile(enabled=True, cycle_length_days=28, current_phase=None)
        assert classify_cycle(profile) is None


# ---------------------------------------------------------------------------
# compute_recovery_veto_v3 — logique de synthèse
# ---------------------------------------------------------------------------

class TestComputeRecoveryVetoV3:

    def test_all_green_returns_green_no_veto(self):
        """Toutes composantes vertes → statut vert, cap 1.0, pas de veto."""
        veto = compute_recovery_veto_v3(
            current_hrv=60.0,
            baseline_hrv=60.0,
            acwr=1.0,
            energy_snapshot=_snapshot(allostatic_score=30.0, ea=50.0),
            hormonal_profile=None,
        )
        assert veto.status == "green"
        assert veto.final_intensity_cap == pytest.approx(1.0)
        assert veto.veto_triggered is False
        assert veto.veto_reasons == []

    def test_one_yellow_returns_yellow_cap_085(self):
        """Un seul indicateur hors zone → jaune, cap −15%."""
        veto = compute_recovery_veto_v3(
            current_hrv=47.0,      # ratio ~0.78 → yellow
            baseline_hrv=60.0,
            acwr=1.0,
            energy_snapshot=_snapshot(allostatic_score=30.0, ea=50.0),
            hormonal_profile=None,
        )
        assert veto.status == "yellow"
        assert veto.final_intensity_cap == pytest.approx(0.85)
        assert veto.veto_triggered is False
        assert len(veto.veto_reasons) == 1

    def test_two_yellow_returns_red_veto(self):
        """Deux indicateurs hors zone → rouge, veto déclenché."""
        veto = compute_recovery_veto_v3(
            current_hrv=47.0,       # yellow
            baseline_hrv=60.0,
            acwr=1.4,               # yellow
            energy_snapshot=_snapshot(allostatic_score=30.0, ea=50.0),
            hormonal_profile=None,
        )
        assert veto.status == "red"
        assert veto.veto_triggered is True
        assert veto.final_intensity_cap == pytest.approx(0.0)

    def test_single_red_ea_triggers_veto_immediately(self):
        """EA < 30 (femme) seul suffit pour déclencher le veto."""
        veto = compute_recovery_veto_v3(
            current_hrv=60.0,
            baseline_hrv=60.0,
            acwr=1.0,
            energy_snapshot=_snapshot(ea=25.0),   # < 30 → red
            hormonal_profile=None,
            sex="female",
        )
        assert veto.status == "red"
        assert veto.ea_component == "red"
        assert veto.veto_triggered is True

    def test_single_red_hrv_triggers_veto_immediately(self):
        """HRV < 60 % de la baseline → rouge seul suffit."""
        veto = compute_recovery_veto_v3(
            current_hrv=30.0,       # ratio 0.5 → red
            baseline_hrv=60.0,
            acwr=1.0,
            energy_snapshot=_snapshot(),
            hormonal_profile=None,
        )
        assert veto.status == "red"
        assert veto.veto_triggered is True

    def test_allostatic_red_triggers_veto(self):
        veto = compute_recovery_veto_v3(
            current_hrv=60.0,
            baseline_hrv=60.0,
            acwr=1.0,
            energy_snapshot=_snapshot(allostatic_score=90.0),
            hormonal_profile=None,
        )
        assert veto.allostatic_component == "red"
        assert veto.status == "red"
        assert veto.veto_triggered is True

    def test_cycle_yellow_plus_hrv_yellow_triggers_red(self):
        """Phase cycle jaune + HRV jaune = 2 indicateurs → rouge."""
        veto = compute_recovery_veto_v3(
            current_hrv=47.0,       # yellow
            baseline_hrv=60.0,
            acwr=1.0,
            energy_snapshot=_snapshot(),
            hormonal_profile=_hormonal("luteal"),  # yellow
        )
        assert veto.cycle_component == "yellow"
        assert veto.hrv_component == "yellow"
        assert veto.status == "red"
        assert veto.veto_triggered is True

    def test_cycle_green_does_not_increase_count(self):
        """Phase folliculaire (verte) ne dégrade pas un statut vert global."""
        veto = compute_recovery_veto_v3(
            current_hrv=60.0,
            baseline_hrv=60.0,
            acwr=1.0,
            energy_snapshot=_snapshot(),
            hormonal_profile=_hormonal("follicular"),
        )
        assert veto.status == "green"
        assert veto.cycle_component == "green"

    def test_no_snapshot_no_hormonal_all_green(self):
        """Sans snapshot ni profil hormonal → composantes EA/allostatic/cycle vertes par défaut."""
        veto = compute_recovery_veto_v3(
            current_hrv=60.0,
            baseline_hrv=60.0,
            acwr=1.0,
            energy_snapshot=None,
            hormonal_profile=None,
        )
        assert veto.ea_component == "green"
        assert veto.allostatic_component == "green"
        assert veto.cycle_component is None
        assert veto.status == "green"

    def test_veto_reasons_contain_component_names(self):
        """Les raisons de veto décrivent les composantes hors zone."""
        veto = compute_recovery_veto_v3(
            current_hrv=47.0,
            baseline_hrv=60.0,
            acwr=1.4,
            energy_snapshot=_snapshot(),
            hormonal_profile=None,
        )
        assert any("hrv" in r.lower() for r in veto.veto_reasons)
        assert any("acwr" in r.lower() for r in veto.veto_reasons)

    def test_cap_is_085_for_single_yellow_component(self):
        """ACWR seul en caution → cap 0.85."""
        veto = compute_recovery_veto_v3(
            current_hrv=60.0,
            baseline_hrv=60.0,
            acwr=1.4,
            energy_snapshot=_snapshot(),
            hormonal_profile=None,
        )
        assert veto.status == "yellow"
        assert veto.final_intensity_cap == pytest.approx(0.85)

    def test_ea_male_25_is_yellow_not_red(self):
        """EA = 25 chez l'homme → jaune (non rouge)."""
        veto = compute_recovery_veto_v3(
            current_hrv=60.0,
            baseline_hrv=60.0,
            acwr=1.0,
            energy_snapshot=_snapshot(ea=25.0),
            hormonal_profile=None,
            sex="male",
        )
        assert veto.ea_component == "yellow"
        assert veto.status == "yellow"
        assert veto.veto_triggered is False

    def test_output_is_recovery_veto_v3_type(self):
        veto = compute_recovery_veto_v3(
            current_hrv=60.0,
            baseline_hrv=60.0,
            acwr=1.0,
            energy_snapshot=None,
            hormonal_profile=None,
        )
        assert isinstance(veto, RecoveryVetoV3)


# ---------------------------------------------------------------------------
# RecoveryCoachV3 — API publique
# ---------------------------------------------------------------------------

class TestRecoveryCoachV3:

    def test_assess_returns_recovery_veto_v3(self):
        coach = RecoveryCoachV3()
        veto = coach.assess(
            current_hrv=60.0,
            baseline_hrv=60.0,
            acwr=1.0,
            energy_snapshot=_snapshot(),
            hormonal_profile=None,
            sex="female",
        )
        assert isinstance(veto, RecoveryVetoV3)

    def test_assess_all_nominal_returns_green(self):
        coach = RecoveryCoachV3()
        veto = coach.assess(
            current_hrv=65.0,
            baseline_hrv=60.0,
            acwr=1.1,
            energy_snapshot=_snapshot(allostatic_score=25.0, ea=52.0),
            hormonal_profile=_hormonal("follicular"),
            sex="female",
        )
        assert veto.status == "green"
        assert veto.veto_triggered is False

    def test_assess_critical_ea_female_veto(self):
        coach = RecoveryCoachV3()
        veto = coach.assess(
            current_hrv=60.0,
            baseline_hrv=60.0,
            acwr=1.0,
            energy_snapshot=_snapshot(ea=20.0),
            hormonal_profile=None,
            sex="female",
        )
        assert veto.veto_triggered is True
        assert veto.ea_component == "red"

    def test_assess_populates_all_five_components(self):
        coach = RecoveryCoachV3()
        veto = coach.assess(
            current_hrv=60.0,
            baseline_hrv=60.0,
            acwr=1.0,
            energy_snapshot=_snapshot(),
            hormonal_profile=_hormonal("luteal"),
            sex="female",
        )
        assert veto.hrv_component is not None
        assert veto.acwr_component is not None
        assert veto.ea_component is not None
        assert veto.allostatic_component is not None
        assert veto.cycle_component is not None
