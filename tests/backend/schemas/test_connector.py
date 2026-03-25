import pytest
from datetime import date
from uuid import UUID
from app.schemas.connector import (
    ConnectorCredential,
    StravaLap,
    StravaActivity,
    HevySet,
    HevyExercise,
    HevyWorkout,
    FatSecretMeal,
    FatSecretDay,
    TerraHealthData,
)


def test_connector_credential_defaults():
    cred = ConnectorCredential(
        athlete_id="00000000-0000-0000-0000-000000000001",
        provider="strava",
    )
    assert isinstance(cred.id, UUID)
    assert cred.extra == {}
    assert cred.access_token is None
    assert cred.expires_at is None


def test_connector_credential_full():
    cred = ConnectorCredential(
        athlete_id="00000000-0000-0000-0000-000000000001",
        provider="strava",
        access_token="tok",
        refresh_token="ref",
        expires_at=9999999999,
        extra={"scope": "read_all"},
    )
    assert cred.access_token == "tok"
    assert cred.expires_at == 9999999999
    assert cred.extra == {"scope": "read_all"}


def test_strava_lap_round_trip():
    lap = StravaLap(
        lap_index=1,
        elapsed_time_seconds=300,
        distance_meters=1000.0,
        average_hr=142.0,
        pace_per_km="5:00",
    )
    assert lap.lap_index == 1
    assert lap.pace_per_km == "5:00"


def test_strava_activity_with_laps():
    lap = StravaLap(
        lap_index=1,
        elapsed_time_seconds=300,
        distance_meters=1000.0,
        average_hr=None,
        pace_per_km=None,
    )
    activity = StravaActivity(
        id="strava_12345",
        name="Morning Run",
        sport_type="Run",
        date=date(2026, 3, 20),
        duration_seconds=3600,
        distance_meters=10000.0,
        elevation_gain_meters=50.0,
        average_hr=145.0,
        max_hr=165.0,
        perceived_exertion=6,
        laps=[lap],
    )
    assert activity.id == "strava_12345"
    assert len(activity.laps) == 1


def test_strava_activity_optional_fields_default_none():
    activity = StravaActivity(
        id="strava_1",
        name="Test",
        sport_type="Run",
        date=date(2026, 3, 20),
        duration_seconds=1800,
        distance_meters=None,
        elevation_gain_meters=None,
        average_hr=None,
        max_hr=None,
        perceived_exertion=None,
    )
    assert activity.distance_meters is None
    assert activity.laps == []


def test_hevy_set_bodyweight_exercise():
    s = HevySet(reps=8, weight_kg=None, rpe=7.0, set_type="normal")
    assert s.weight_kg is None


def test_hevy_workout_round_trip():
    workout = HevyWorkout(
        id="w1",
        title="Push Day",
        date=date(2026, 3, 20),
        duration_seconds=3900,
        exercises=[
            HevyExercise(
                name="Bench Press",
                sets=[HevySet(reps=10, weight_kg=60.0, rpe=7.0, set_type="normal")],
            )
        ],
    )
    assert workout.title == "Push Day"
    assert workout.exercises[0].name == "Bench Press"


def test_fatsecret_day_aggregates():
    day = FatSecretDay(
        date=date(2026, 3, 20),
        calories_total=1800.0,
        carbs_g=220.0,
        protein_g=130.0,
        fat_g=60.0,
        meals=[
            FatSecretMeal(name="Breakfast", calories=600.0, carbs_g=80.0, protein_g=30.0, fat_g=20.0),
            FatSecretMeal(name="Lunch", calories=700.0, carbs_g=80.0, protein_g=50.0, fat_g=20.0),
        ],
    )
    assert day.calories_total == 1800.0
    assert len(day.meals) == 2


def test_terra_health_data_none_hrv():
    data = TerraHealthData(
        date=date(2026, 3, 20),
        hrv_rmssd=None,
        sleep_duration_hours=7.5,
        sleep_score=78.0,
        steps=8500,
        active_energy_kcal=450.0,
    )
    assert data.hrv_rmssd is None
    assert data.steps == 8500
