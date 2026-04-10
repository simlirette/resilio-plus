"""Tests unitaires pour les modèles AthleteState V3.

Couvre : EnergySnapshot, HormonalProfile, AllostaticEntry, RecoveryVetoV3, get_agent_view()
"""
from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from app.models.athlete_state import (
    AllostaticEntry,
    AthleteStateV3,
    EnergySnapshot,
    HormonalProfile,
    RecoveryVetoV3,
    get_agent_view,
)


# ---------------------------------------------------------------------------
# EnergySnapshot
# ---------------------------------------------------------------------------

class TestEnergySnapshot:
    def test_instantiation_with_all_fields(self):
        snap = EnergySnapshot(
            timestamp=datetime(2026, 4, 10, 8, 0, tzinfo=timezone.utc),
            allostatic_score=45.0,
            cognitive_load=50.0,
            energy_availability=40.0,
            cycle_phase="follicular",
            sleep_quality=75.0,
            recommended_intensity_cap=1.0,
            veto_triggered=False,
            veto_reason=None,
        )
        assert snap.allostatic_score == 45.0
        assert snap.cognitive_load == 50.0
        assert snap.energy_availability == 40.0
        assert snap.cycle_phase == "follicular"
        assert snap.veto_triggered is False

    def test_instantiation_without_optional_fields(self):
        snap = EnergySnapshot(
            timestamp=datetime(2026, 4, 10, 8, 0, tzinfo=timezone.utc),
            allostatic_score=20.0,
            cognitive_load=30.0,
            energy_availability=50.0,
            sleep_quality=85.0,
            recommended_intensity_cap=1.0,
            veto_triggered=False,
        )
        assert snap.cycle_phase is None
        assert snap.veto_reason is None

    def test_veto_triggered_when_ea_below_30(self):
        snap = EnergySnapshot(
            timestamp=datetime(2026, 4, 10, 8, 0, tzinfo=timezone.utc),
            allostatic_score=40.0,
            cognitive_load=40.0,
            energy_availability=25.0,   # < 30 → veto
            sleep_quality=70.0,
            recommended_intensity_cap=0.0,
            veto_triggered=True,
            veto_reason="Energy availability critically low (25.0 kcal/kg FFM)",
        )
        assert snap.veto_triggered is True
        assert snap.veto_reason is not None

    def test_veto_triggered_when_allostatic_above_80(self):
        snap = EnergySnapshot(
            timestamp=datetime(2026, 4, 10, 8, 0, tzinfo=timezone.utc),
            allostatic_score=85.0,   # > 80 → veto
            cognitive_load=80.0,
            energy_availability=40.0,
            sleep_quality=30.0,
            recommended_intensity_cap=0.0,
            veto_triggered=True,
            veto_reason="Allostatic score critical (85.0)",
        )
        assert snap.veto_triggered is True

    def test_score_bounds_are_accepted(self):
        """allostatic_score, cognitive_load, sleep_quality must be 0–100."""
        snap = EnergySnapshot(
            timestamp=datetime(2026, 4, 10, tzinfo=timezone.utc),
            allostatic_score=0.0,
            cognitive_load=100.0,
            energy_availability=45.0,
            sleep_quality=0.0,
            recommended_intensity_cap=1.0,
            veto_triggered=False,
        )
        assert snap.allostatic_score == 0.0

    def test_invalid_score_above_100_raises(self):
        with pytest.raises(ValidationError):
            EnergySnapshot(
                timestamp=datetime(2026, 4, 10, tzinfo=timezone.utc),
                allostatic_score=101.0,  # invalid
                cognitive_load=50.0,
                energy_availability=40.0,
                sleep_quality=75.0,
                recommended_intensity_cap=1.0,
                veto_triggered=False,
            )

    def test_invalid_score_below_0_raises(self):
        with pytest.raises(ValidationError):
            EnergySnapshot(
                timestamp=datetime(2026, 4, 10, tzinfo=timezone.utc),
                allostatic_score=20.0,
                cognitive_load=-1.0,  # invalid
                energy_availability=40.0,
                sleep_quality=75.0,
                recommended_intensity_cap=1.0,
                veto_triggered=False,
            )

    def test_valid_cycle_phases_accepted(self):
        for phase in ("menstrual", "follicular", "ovulation", "luteal"):
            snap = EnergySnapshot(
                timestamp=datetime(2026, 4, 10, tzinfo=timezone.utc),
                allostatic_score=20.0,
                cognitive_load=20.0,
                energy_availability=45.0,
                cycle_phase=phase,
                sleep_quality=80.0,
                recommended_intensity_cap=1.0,
                veto_triggered=False,
            )
            assert snap.cycle_phase == phase

    def test_invalid_cycle_phase_raises(self):
        with pytest.raises(ValidationError):
            EnergySnapshot(
                timestamp=datetime(2026, 4, 10, tzinfo=timezone.utc),
                allostatic_score=20.0,
                cognitive_load=20.0,
                energy_availability=45.0,
                cycle_phase="unknown_phase",  # invalid
                sleep_quality=80.0,
                recommended_intensity_cap=1.0,
                veto_triggered=False,
            )


# ---------------------------------------------------------------------------
# HormonalProfile
# ---------------------------------------------------------------------------

class TestHormonalProfile:
    def test_enabled_profile_full_fields(self):
        profile = HormonalProfile(
            enabled=True,
            cycle_length_days=28,
            current_cycle_day=10,
            current_phase="follicular",
            last_period_start=date(2026, 4, 1),
            tracking_source="manual",
            notes="Cycles réguliers",
        )
        assert profile.enabled is True
        assert profile.cycle_length_days == 28
        assert profile.current_phase == "follicular"

    def test_disabled_profile_minimal_fields(self):
        profile = HormonalProfile(
            enabled=False,
            tracking_source="manual",
        )
        assert profile.enabled is False
        assert profile.cycle_length_days == 28   # default
        assert profile.current_cycle_day is None
        assert profile.current_phase is None
        assert profile.last_period_start is None
        assert profile.notes is None

    def test_valid_tracking_sources(self):
        for src in ("manual", "apple_health"):
            p = HormonalProfile(enabled=True, tracking_source=src)
            assert p.tracking_source == src

    def test_invalid_tracking_source_raises(self):
        with pytest.raises(ValidationError):
            HormonalProfile(enabled=True, tracking_source="garmin")  # invalid

    def test_valid_phases_accepted(self):
        for phase in ("menstrual", "follicular", "ovulation", "luteal"):
            p = HormonalProfile(
                enabled=True,
                tracking_source="manual",
                current_phase=phase,
            )
            assert p.current_phase == phase

    def test_invalid_phase_raises(self):
        with pytest.raises(ValidationError):
            HormonalProfile(
                enabled=True,
                tracking_source="manual",
                current_phase="random",
            )

    def test_cycle_length_default_is_28(self):
        p = HormonalProfile(enabled=True, tracking_source="manual")
        assert p.cycle_length_days == 28

    def test_cycle_length_custom(self):
        p = HormonalProfile(enabled=True, tracking_source="manual", cycle_length_days=30)
        assert p.cycle_length_days == 30


# ---------------------------------------------------------------------------
# AllostaticEntry
# ---------------------------------------------------------------------------

class TestAllostaticEntry:
    def test_instantiation(self):
        entry = AllostaticEntry(
            date=date(2026, 4, 10),
            allostatic_score=55.0,
            components={
                "hrv": 30.0,
                "sleep": 40.0,
                "work": 65.0,
                "stress": 30.0,
                "cycle": 10.0,
                "ea": 0.0,
            },
            intensity_cap_applied=0.85,
        )
        assert entry.allostatic_score == 55.0
        assert entry.components["work"] == 65.0
        assert entry.intensity_cap_applied == 0.85

    def test_score_bounds(self):
        entry = AllostaticEntry(
            date=date(2026, 4, 10),
            allostatic_score=0.0,
            components={},
            intensity_cap_applied=1.0,
        )
        assert entry.allostatic_score == 0.0

    def test_score_above_100_raises(self):
        with pytest.raises(ValidationError):
            AllostaticEntry(
                date=date(2026, 4, 10),
                allostatic_score=101.0,
                components={},
                intensity_cap_applied=1.0,
            )

    def test_intensity_cap_bounds(self):
        """intensity_cap_applied doit être entre 0 et 1."""
        with pytest.raises(ValidationError):
            AllostaticEntry(
                date=date(2026, 4, 10),
                allostatic_score=50.0,
                components={},
                intensity_cap_applied=1.5,  # > 1
            )


# ---------------------------------------------------------------------------
# RecoveryVetoV3
# ---------------------------------------------------------------------------

class TestRecoveryVetoV3:
    def test_green_status_no_veto(self):
        veto = RecoveryVetoV3(
            status="green",
            hrv_component="green",
            acwr_component="green",
            ea_component="green",
            allostatic_component="green",
            cycle_component=None,
            final_intensity_cap=1.0,
            veto_triggered=False,
            veto_reasons=[],
        )
        assert veto.status == "green"
        assert veto.veto_triggered is False
        assert veto.veto_reasons == []

    def test_red_status_with_veto_and_reasons(self):
        veto = RecoveryVetoV3(
            status="red",
            hrv_component="red",
            acwr_component="yellow",
            ea_component="red",
            allostatic_component="red",
            cycle_component="red",
            final_intensity_cap=0.0,
            veto_triggered=True,
            veto_reasons=["HRV critically low", "Energy availability critical"],
        )
        assert veto.veto_triggered is True
        assert len(veto.veto_reasons) == 2
        assert veto.final_intensity_cap == 0.0

    def test_yellow_reduces_intensity(self):
        veto = RecoveryVetoV3(
            status="yellow",
            hrv_component="yellow",
            acwr_component="green",
            ea_component="green",
            allostatic_component="yellow",
            cycle_component=None,
            final_intensity_cap=0.85,
            veto_triggered=False,
            veto_reasons=[],
        )
        assert veto.status == "yellow"
        assert veto.final_intensity_cap == 0.85

    def test_invalid_status_raises(self):
        with pytest.raises(ValidationError):
            RecoveryVetoV3(
                status="purple",  # invalid
                hrv_component="green",
                acwr_component="green",
                ea_component="green",
                allostatic_component="green",
                final_intensity_cap=1.0,
                veto_triggered=False,
                veto_reasons=[],
            )

    def test_invalid_component_status_raises(self):
        with pytest.raises(ValidationError):
            RecoveryVetoV3(
                status="green",
                hrv_component="optimal",  # invalid
                acwr_component="green",
                ea_component="green",
                allostatic_component="green",
                final_intensity_cap=1.0,
                veto_triggered=False,
                veto_reasons=[],
            )


# ---------------------------------------------------------------------------
# AthleteStateV3
# ---------------------------------------------------------------------------

class TestAthleteStateV3:
    def _make_veto(self) -> RecoveryVetoV3:
        return RecoveryVetoV3(
            status="green",
            hrv_component="green",
            acwr_component="green",
            ea_component="green",
            allostatic_component="green",
            final_intensity_cap=1.0,
            veto_triggered=False,
            veto_reasons=[],
        )

    def test_minimal_instantiation(self):
        state = AthleteStateV3(
            athlete_id="athlete-001",
            recovery_coach_veto=self._make_veto(),
        )
        assert state.athlete_id == "athlete-001"
        assert state.energy_snapshot is None
        assert state.hormonal_profile is None
        assert state.allostatic_history == []

    def test_with_energy_snapshot(self):
        snap = EnergySnapshot(
            timestamp=datetime(2026, 4, 10, tzinfo=timezone.utc),
            allostatic_score=35.0,
            cognitive_load=40.0,
            energy_availability=48.0,
            sleep_quality=80.0,
            recommended_intensity_cap=1.0,
            veto_triggered=False,
        )
        state = AthleteStateV3(
            athlete_id="athlete-002",
            energy_snapshot=snap,
            recovery_coach_veto=self._make_veto(),
        )
        assert state.energy_snapshot is not None
        assert state.energy_snapshot.allostatic_score == 35.0

    def test_with_hormonal_profile(self):
        profile = HormonalProfile(enabled=True, tracking_source="manual", cycle_length_days=28)
        state = AthleteStateV3(
            athlete_id="athlete-003",
            hormonal_profile=profile,
            recovery_coach_veto=self._make_veto(),
        )
        assert state.hormonal_profile.enabled is True

    def test_allostatic_history_list(self):
        entries = [
            AllostaticEntry(
                date=date(2026, 4, i),
                allostatic_score=float(30 + i),
                components={"hrv": 20.0},
                intensity_cap_applied=1.0,
            )
            for i in range(1, 8)
        ]
        state = AthleteStateV3(
            athlete_id="athlete-004",
            allostatic_history=entries,
            recovery_coach_veto=self._make_veto(),
        )
        assert len(state.allostatic_history) == 7

    def test_missing_recovery_veto_raises(self):
        with pytest.raises(ValidationError):
            AthleteStateV3(athlete_id="athlete-005")  # veto required


# ---------------------------------------------------------------------------
# get_agent_view()
# ---------------------------------------------------------------------------

class TestGetAgentView:
    def _make_state(self) -> AthleteStateV3:
        return AthleteStateV3(
            athlete_id="athlete-view-test",
            recovery_coach_veto=RecoveryVetoV3(
                status="green",
                hrv_component="green",
                acwr_component="green",
                ea_component="green",
                allostatic_component="green",
                final_intensity_cap=1.0,
                veto_triggered=False,
                veto_reasons=[],
            ),
            energy_snapshot=EnergySnapshot(
                timestamp=datetime(2026, 4, 10, tzinfo=timezone.utc),
                allostatic_score=20.0,
                cognitive_load=25.0,
                energy_availability=50.0,
                sleep_quality=85.0,
                recommended_intensity_cap=1.0,
                veto_triggered=False,
            ),
            hormonal_profile=HormonalProfile(
                enabled=True,
                tracking_source="manual",
                current_phase="follicular",
            ),
        )

    def test_head_coach_gets_full_access(self):
        state = self._make_state()
        view = get_agent_view(state, "head_coach")
        assert view == "FULL"

    def test_energy_coach_gets_v3_fields(self):
        state = self._make_state()
        view = get_agent_view(state, "energy_coach")
        assert "energy_snapshot" in view
        assert "hormonal_profile" in view
        assert "allostatic_history" in view
        assert "sleep_data" in view
        assert "nutrition_summary" in view

    def test_recovery_coach_gets_extended_v3_fields(self):
        state = self._make_state()
        view = get_agent_view(state, "recovery_coach")
        assert "energy_snapshot" in view       # new V3
        assert "hormonal_profile" in view      # new V3
        assert "hrv_data" in view
        assert "acwr" in view

    def test_nutrition_coach_gets_ea_and_hormones(self):
        state = self._make_state()
        view = get_agent_view(state, "nutrition_coach")
        assert "energy_snapshot" in view       # EA en temps réel
        assert "hormonal_profile" in view      # besoins par phase
        assert "nutrition_profile" in view

    def test_unknown_agent_returns_empty(self):
        state = self._make_state()
        view = get_agent_view(state, "unknown_agent")
        assert view == []
