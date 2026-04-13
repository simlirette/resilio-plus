"""Tests for AthleteState V1 sub-models and root model."""
from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from app.models.athlete_state import EnergyCheckIn


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
