from datetime import date
import pytest
from app.core.biking_logic import (
    estimate_ftp, compute_biking_fatigue, generate_biking_sessions,
)
from app.schemas.athlete import AthleteProfile, Sport
from app.schemas.connector import StravaActivity
from app.schemas.plan import WorkoutSlot


def _athlete(ftp=None):
    return AthleteProfile(
        name="Bob", age=30, sex="M", weight_kg=75, height_cm=178,
        sports=[Sport.BIKING], primary_sport=Sport.BIKING,
        goals=["improve FTP"], available_days=[1, 3, 5],
        hours_per_week=6.0, ftp_watts=ftp,
    )


def _ride(duration_s=3600, distance_m=40000):
    return StravaActivity(
        id="s1", name="Ride", sport_type="Ride",
        date=date(2026, 4, 1),
        duration_seconds=duration_s,
        distance_meters=distance_m,
    )


def test_estimate_ftp_uses_athlete_value():
    assert estimate_ftp(_athlete(ftp=250)) == 250


def test_estimate_ftp_cold_start():
    assert estimate_ftp(_athlete(ftp=None)) == 200


def test_compute_biking_fatigue_empty():
    f = compute_biking_fatigue([])
    assert f.local_muscular == 0.0
    assert f.cns_load == 0.0


def test_compute_biking_fatigue_with_ride():
    f = compute_biking_fatigue([_ride()])
    assert f.local_muscular > 0
    assert f.recovery_hours > 0


def test_generate_sessions_returns_workout_slots():
    sessions = generate_biking_sessions(
        ftp=200,
        week_number=1,
        phase="general_prep",
        available_days=[1, 3, 5],
        hours_budget=4.0,
        volume_modifier=1.0,
        week_start=date(2026, 4, 7),
    )
    assert len(sessions) >= 1
    for s in sessions:
        assert isinstance(s, WorkoutSlot)
        assert s.sport.value == "biking"


def test_generate_sessions_respects_available_days():
    week_start = date(2026, 4, 7)
    sessions = generate_biking_sessions(
        ftp=200, week_number=1, phase="general_prep",
        available_days=[0, 2], hours_budget=3.0,
        volume_modifier=1.0, week_start=week_start,
    )
    # All sessions must fall on offsets 0 or 2 from week_start
    for s in sessions:
        assert (s.date - week_start).days in [0, 2]


def test_generate_sessions_zero_budget_returns_empty():
    sessions = generate_biking_sessions(
        ftp=200, week_number=1, phase="general_prep",
        available_days=[0, 2, 4], hours_budget=0.0,
        volume_modifier=1.0, week_start=date(2026, 4, 7),
    )
    assert sessions == []
