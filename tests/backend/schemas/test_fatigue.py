import pytest
from pydantic import ValidationError


def make_valid_fatigue(**overrides):
    defaults = {
        "local_muscular": 40.0,
        "cns_load": 55.0,
        "metabolic_cost": 30.0,
        "recovery_hours": 24.0,
        "affected_muscles": ["quads", "glutes"],
    }
    defaults.update(overrides)
    return defaults


def test_valid_construction():
    from app.schemas.fatigue import FatigueScore
    fs = FatigueScore(**make_valid_fatigue())
    assert fs.local_muscular == 40.0
    assert fs.cns_load == 55.0
    assert fs.metabolic_cost == 30.0
    assert fs.recovery_hours == 24.0
    assert fs.affected_muscles == ["quads", "glutes"]


def test_affected_muscles_defaults_to_empty_list():
    from app.schemas.fatigue import FatigueScore
    data = make_valid_fatigue()
    del data["affected_muscles"]
    fs = FatigueScore(**data)
    assert fs.affected_muscles == []


def test_local_muscular_above_100_raises():
    from app.schemas.fatigue import FatigueScore
    with pytest.raises(ValidationError):
        FatigueScore(**make_valid_fatigue(local_muscular=101.0))


def test_local_muscular_below_0_raises():
    from app.schemas.fatigue import FatigueScore
    with pytest.raises(ValidationError):
        FatigueScore(**make_valid_fatigue(local_muscular=-1.0))


def test_cns_load_above_100_raises():
    from app.schemas.fatigue import FatigueScore
    with pytest.raises(ValidationError):
        FatigueScore(**make_valid_fatigue(cns_load=150.0))


def test_metabolic_cost_above_100_raises():
    from app.schemas.fatigue import FatigueScore
    with pytest.raises(ValidationError):
        FatigueScore(**make_valid_fatigue(metabolic_cost=100.1))


def test_recovery_hours_negative_raises():
    from app.schemas.fatigue import FatigueScore
    with pytest.raises(ValidationError):
        FatigueScore(**make_valid_fatigue(recovery_hours=-0.1))


def test_recovery_hours_zero_is_valid():
    from app.schemas.fatigue import FatigueScore
    fs = FatigueScore(**make_valid_fatigue(recovery_hours=0.0))
    assert fs.recovery_hours == 0.0


def test_json_round_trip():
    from app.schemas.fatigue import FatigueScore
    fs = FatigueScore(**make_valid_fatigue())
    json_str = fs.model_dump_json()
    fs2 = FatigueScore.model_validate_json(json_str)
    assert fs == fs2
