"""Tests for V3-C Energy Cycle Service — schemas, service, routes."""
import pytest
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# Task 1 — Pydantic schemas
# ---------------------------------------------------------------------------

def test_checkin_input_valid():
    from app.schemas.checkin import CheckInInput
    ci = CheckInInput(
        work_intensity="normal",
        stress_level="mild",
        legs_feeling="normal",
        energy_global="ok",
    )
    assert ci.work_intensity == "normal"
    assert ci.legs_feeling == "normal"
    assert ci.cycle_phase is None
    assert ci.comment is None


def test_checkin_input_rejects_invalid_legs():
    from app.schemas.checkin import CheckInInput
    with pytest.raises(ValidationError):
        CheckInInput(
            work_intensity="normal",
            stress_level="none",
            legs_feeling="bad",
            energy_global="ok",
        )


def test_checkin_input_rejects_invalid_energy():
    from app.schemas.checkin import CheckInInput
    with pytest.raises(ValidationError):
        CheckInInput(
            work_intensity="normal",
            stress_level="none",
            legs_feeling="fresh",
            energy_global="meh",
        )


def test_readiness_response_fields():
    from app.schemas.checkin import ReadinessResponse
    from datetime import date
    r = ReadinessResponse(
        date=date.today(),
        objective_score=70.0,
        subjective_score=40.0,
        final_readiness=52.0,
        divergence=30.0,
        divergence_flag="high",
        traffic_light="yellow",
        allostatic_score=30.0,
        energy_availability=45.0,
        intensity_cap=1.0,
        insights=["HRV normale mais jambes à dead. Ton ressenti compte."],
    )
    assert r.divergence_flag == "high"
    assert r.traffic_light == "yellow"


def test_hormonal_profile_update_valid():
    from app.schemas.checkin import HormonalProfileUpdate
    from datetime import date
    h = HormonalProfileUpdate(
        enabled=True,
        cycle_length_days=28,
        last_period_start=date.today(),
    )
    assert h.enabled is True
    assert h.cycle_length_days == 28
