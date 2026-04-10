from datetime import date
import pytest
from app.core.swimming_logic import (
    estimate_css, compute_swimming_fatigue, generate_swimming_sessions,
)
from app.schemas.athlete import AthleteProfile, Sport
from app.schemas.connector import StravaActivity
from app.schemas.plan import WorkoutSlot


def _athlete(css=None):
    return AthleteProfile(
        name="Marie", age=26, sex="F", weight_kg=60, height_cm=165,
        sports=[Sport.SWIMMING], primary_sport=Sport.SWIMMING,
        goals=["triathlon"], available_days=[1, 3, 6],
        hours_per_week=5.0, css_per_100m=css,
    )


def _swim(duration_s=1800, distance_m=1500):
    return StravaActivity(
        id="sw1", name="Swim", sport_type="Swim",
        date=date(2026, 4, 1),
        duration_seconds=duration_s,
        distance_meters=distance_m,
    )


def test_estimate_css_uses_athlete_value():
    assert estimate_css(_athlete(css=90.0)) == 90.0


def test_estimate_css_cold_start():
    # Cold start = 1:45/100m = 105 seconds/100m
    assert estimate_css(_athlete(css=None)) == 105.0


def test_compute_swimming_fatigue_empty():
    f = compute_swimming_fatigue([])
    assert f.local_muscular == 0.0


def test_compute_swimming_fatigue_with_swim():
    f = compute_swimming_fatigue([_swim()])
    assert f.local_muscular > 0
    assert "shoulders" in f.affected_muscles


def test_generate_sessions_returns_workout_slots():
    sessions = generate_swimming_sessions(
        css_per_100m=105.0,
        week_number=1,
        phase="general_prep",
        available_days=[1, 3, 6],
        hours_budget=3.0,
        volume_modifier=1.0,
        week_start=date(2026, 4, 7),
    )
    assert len(sessions) >= 1
    for s in sessions:
        assert isinstance(s, WorkoutSlot)
        assert s.sport.value == "swimming"


def test_generate_sessions_zero_budget():
    sessions = generate_swimming_sessions(
        css_per_100m=105.0, week_number=1, phase="general_prep",
        available_days=[1, 3], hours_budget=0.0,
        volume_modifier=1.0, week_start=date(2026, 4, 7),
    )
    assert sessions == []
