import pytest
from datetime import date
from pydantic import ValidationError


def make_valid_athlete(**overrides):
    defaults = {
        "name": "Alice",
        "age": 30,
        "sex": "F",
        "weight_kg": 60.0,
        "height_cm": 168.0,
        "sports": ["running", "lifting"],
        "primary_sport": "running",
        "goals": ["run a marathon sub-4h"],
        "available_days": [0, 2, 4, 6],
        "hours_per_week": 10.0,
    }
    defaults.update(overrides)
    return defaults


# --- Sport enum ---

def test_sport_valid_values():
    from app.schemas.athlete import Sport
    assert Sport("running") == Sport.RUNNING
    assert Sport("lifting") == Sport.LIFTING
    assert Sport("swimming") == Sport.SWIMMING
    assert Sport("biking") == Sport.BIKING


def test_sport_invalid_value_raises():
    from app.schemas.athlete import Sport
    with pytest.raises(ValueError):
        Sport("cycling")


# --- DayType enum ---

def test_daytype_valid_values():
    from app.schemas.athlete import DayType
    assert DayType("rest") == DayType.REST
    assert DayType("strength") == DayType.STRENGTH
    assert DayType("endurance_short") == DayType.ENDURANCE_SHORT
    assert DayType("endurance_long") == DayType.ENDURANCE_LONG
    assert DayType("race") == DayType.RACE


def test_daytype_invalid_value_raises():
    from app.schemas.athlete import DayType
    with pytest.raises(ValueError):
        DayType("cardio")


# --- AthleteProfile ---

def test_athlete_valid_minimal():
    from app.schemas.athlete import AthleteProfile
    athlete = AthleteProfile(**make_valid_athlete())
    assert athlete.name == "Alice"
    assert athlete.age == 30
    assert athlete.sex == "F"
    assert athlete.weight_kg == 60.0
    assert athlete.vdot is None
    assert athlete.ftp_watts is None
    assert athlete.sleep_hours_typical == 7.0
    assert athlete.stress_level == 5
    assert athlete.job_physical is False
    assert athlete.equipment == []
    assert athlete.target_race_date is None


def test_athlete_id_generated_automatically():
    from app.schemas.athlete import AthleteProfile
    a1 = AthleteProfile(**make_valid_athlete())
    a2 = AthleteProfile(**make_valid_athlete())
    assert a1.id != a2.id


def test_athlete_age_too_young_raises():
    from app.schemas.athlete import AthleteProfile
    with pytest.raises(ValidationError):
        AthleteProfile(**make_valid_athlete(age=13))


def test_athlete_age_too_old_raises():
    from app.schemas.athlete import AthleteProfile
    with pytest.raises(ValidationError):
        AthleteProfile(**make_valid_athlete(age=101))


def test_athlete_negative_weight_raises():
    from app.schemas.athlete import AthleteProfile
    with pytest.raises(ValidationError):
        AthleteProfile(**make_valid_athlete(weight_kg=-1.0))


def test_athlete_zero_weight_raises():
    from app.schemas.athlete import AthleteProfile
    with pytest.raises(ValidationError):
        AthleteProfile(**make_valid_athlete(weight_kg=0.0))


def test_athlete_stress_level_out_of_range_raises():
    from app.schemas.athlete import AthleteProfile
    with pytest.raises(ValidationError):
        AthleteProfile(**make_valid_athlete(stress_level=11))
    with pytest.raises(ValidationError):
        AthleteProfile(**make_valid_athlete(stress_level=0))


def test_athlete_sex_invalid_raises():
    from app.schemas.athlete import AthleteProfile
    with pytest.raises(ValidationError):
        AthleteProfile(**make_valid_athlete(sex="X"))


def test_athlete_with_fitness_markers():
    from app.schemas.athlete import AthleteProfile
    athlete = AthleteProfile(**make_valid_athlete(
        vdot=52.3,
        ftp_watts=280,
        css_per_100m=95.0,
        max_hr=185,
        resting_hr=48,
    ))
    assert athlete.vdot == 52.3
    assert athlete.ftp_watts == 280
    assert athlete.css_per_100m == 95.0


def test_athlete_with_target_race_date():
    from app.schemas.athlete import AthleteProfile
    athlete = AthleteProfile(**make_valid_athlete(
        target_race_date=date(2026, 10, 18)
    ))
    assert athlete.target_race_date == date(2026, 10, 18)


def test_athlete_sport_enum_parsed_from_string():
    from app.schemas.athlete import AthleteProfile, Sport
    athlete = AthleteProfile(**make_valid_athlete(primary_sport="swimming"))
    assert athlete.primary_sport == Sport.SWIMMING


def test_athlete_json_round_trip():
    from app.schemas.athlete import AthleteProfile
    athlete = AthleteProfile(**make_valid_athlete())
    json_str = athlete.model_dump_json()
    athlete2 = AthleteProfile.model_validate_json(json_str)
    assert athlete == athlete2
