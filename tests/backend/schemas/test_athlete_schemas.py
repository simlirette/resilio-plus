

def test_athlete_create_requires_name():
    import pytest
    from app.schemas.athlete import AthleteCreate
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        AthleteCreate(
            age=30, sex="F", weight_kg=60.0, height_cm=168.0,
            sports=["running"], primary_sport="running",
            goals=[], available_days=[0, 2, 4], hours_per_week=10.0,
        )


def test_athlete_update_all_optional():
    from app.schemas.athlete import AthleteUpdate
    update = AthleteUpdate()  # no fields — must not raise
    assert update.name is None


def test_athlete_response_is_athlete_profile():
    from app.schemas.athlete import AthleteProfile, AthleteResponse
    assert AthleteResponse is AthleteProfile
