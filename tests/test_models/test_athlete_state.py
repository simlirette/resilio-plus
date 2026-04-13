"""Tests for AthleteState V1 sub-models and root model."""
from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from app.models.athlete_state import AllostaticComponents, AllostaticEntry, AthleteMetrics, EnergyCheckIn, SyncSource
from app.schemas.fatigue import FatigueScore


class TestEnergyCheckIn:
    def test_valid_full(self):
        ci = EnergyCheckIn(
            work_intensity="heavy",
            stress_level="mild",
            cycle_phase="follicular",
        )
        assert ci.work_intensity == "heavy"
        assert ci.stress_level == "mild"
        assert ci.cycle_phase == "follicular"

    def test_valid_no_cycle(self):
        ci = EnergyCheckIn(work_intensity="normal", stress_level="none")
        assert ci.cycle_phase is None

    def test_invalid_work_intensity_raises(self):
        with pytest.raises(ValidationError):
            EnergyCheckIn(work_intensity="extreme", stress_level="none")

    def test_invalid_stress_level_raises(self):
        with pytest.raises(ValidationError):
            EnergyCheckIn(work_intensity="normal", stress_level="high")

    def test_invalid_cycle_phase_raises(self):
        with pytest.raises(ValidationError):
            EnergyCheckIn(work_intensity="normal", stress_level="none", cycle_phase="unknown")


class TestAllostaticComponents:
    def test_full_components(self):
        c = AllostaticComponents(hrv=30.0, sleep=40.0, work=65.0, stress=30.0, cycle=10.0, ea=0.0)
        assert c.hrv == 30.0
        assert c.ea == 0.0

    def test_empty_components(self):
        c = AllostaticComponents()
        assert c.hrv is None
        assert c.sleep is None

    def test_component_above_100_raises(self):
        with pytest.raises(ValidationError):
            AllostaticComponents(hrv=101.0)

    def test_component_below_0_raises(self):
        with pytest.raises(ValidationError):
            AllostaticComponents(sleep=-1.0)

    def test_unknown_fields_are_ignored(self):
        # Pydantic v2 default: extra fields are ignored, not rejected.
        c = AllostaticComponents(hrv=50.0, unknown_key=99.0)
        assert not hasattr(c, "unknown_key")

    def test_allostatic_entry_accepts_components_model(self):
        entry = AllostaticEntry(
            date=date(2026, 4, 10),
            allostatic_score=55.0,
            components=AllostaticComponents(hrv=30.0, sleep=40.0),
            intensity_cap_applied=0.85,
        )
        assert entry.components.hrv == 30.0

    def test_allostatic_entry_accepts_dict_coercion(self):
        """Pydantic v2 coerces dict → AllostaticComponents automatically."""
        entry = AllostaticEntry(
            date=date(2026, 4, 10),
            allostatic_score=55.0,
            components={"hrv": 30.0, "sleep": 40.0},
            intensity_cap_applied=0.85,
        )
        assert entry.components.hrv == 30.0

    def test_allostatic_entry_accepts_empty_dict(self):
        entry = AllostaticEntry(
            date=date(2026, 4, 10),
            allostatic_score=0.0,
            components={},
            intensity_cap_applied=1.0,
        )
        assert entry.components.hrv is None


class TestSyncSource:
    def test_valid_ok(self):
        s = SyncSource(
            name="strava",
            last_synced_at=datetime(2026, 4, 13, 8, 0, tzinfo=timezone.utc),
            status="ok",
        )
        assert s.name == "strava"
        assert s.status == "ok"

    def test_invalid_name_raises(self):
        with pytest.raises(ValidationError):
            SyncSource(
                name="garmin",
                last_synced_at=datetime(2026, 4, 13, tzinfo=timezone.utc),
                status="ok",
            )

    def test_invalid_status_raises(self):
        with pytest.raises(ValidationError):
            SyncSource(
                name="terra",
                last_synced_at=datetime(2026, 4, 13, tzinfo=timezone.utc),
                status="pending",
            )


class TestAthleteMetrics:
    def test_minimal(self):
        m = AthleteMetrics(date=date(2026, 4, 13))
        assert m.hrv_rmssd is None
        assert m.acwr is None
        assert m.hrv_history_7d == []

    def test_full(self):
        m = AthleteMetrics(
            date=date(2026, 4, 13),
            hrv_rmssd=65.4,
            hrv_history_7d=[60.0, 62.0, 65.4, 58.0, 70.0, 64.0, 65.4],
            sleep_hours=7.5,
            sleep_quality_score=82.0,
            resting_hr=48.0,
            acwr=1.1,
            acwr_status="safe",
            readiness_score=87.0,
            fatigue_score=FatigueScore(
                local_muscular=20.0, cns_load=15.0,
                metabolic_cost=18.0, recovery_hours=24.0, affected_muscles=[],
            ),
        )
        assert m.hrv_rmssd == 65.4
        assert m.acwr_status == "safe"
        assert len(m.hrv_history_7d) == 7

    def test_invalid_acwr_status_raises(self):
        with pytest.raises(ValidationError):
            AthleteMetrics(date=date(2026, 4, 13), acwr_status="warning")
