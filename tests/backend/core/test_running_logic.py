from datetime import date, timedelta
from app.core.running_logic import (
    estimate_vdot, compute_running_fatigue, generate_running_sessions,
)
from app.core.periodization import TIDStrategy
from app.schemas.connector import StravaActivity


def _run(distance_m: float, duration_s: int, rpe: int | None = None,
         avg_hr: float | None = None, days_ago: int = 1) -> StravaActivity:
    return StravaActivity(
        id="s1", name="Run", sport_type="Run",
        date=date(2026, 4, 7) - timedelta(days=days_ago),
        duration_seconds=duration_s,
        distance_meters=distance_m,
        perceived_exertion=rpe,
        average_hr=avg_hr,
    )


# estimate_vdot

def test_estimate_vdot_no_activities_returns_default():
    assert estimate_vdot([]) == 35.0


def test_estimate_vdot_from_recent_activity():
    # 10km in 3000s -> pace = 300 s/km -> VDOT table row (53, easy=300) -> VDOT 53
    activity = _run(distance_m=10000, duration_s=3000, days_ago=5)
    assert estimate_vdot([activity], reference_date=date(2026, 4, 7)) == 53


def test_estimate_vdot_ignores_non_run():
    activity = StravaActivity(
        id="s2", name="Ride", sport_type="Ride",
        date=date(2026, 4, 6), duration_seconds=3000, distance_meters=10000,
    )
    assert estimate_vdot([activity]) == 35.0


# compute_running_fatigue

def test_fatigue_empty_activities_returns_zeros():
    f = compute_running_fatigue([])
    assert f.local_muscular == 0
    assert f.cns_load == 0
    assert f.metabolic_cost == 0
    assert f.recovery_hours == 0
    assert f.affected_muscles == []


def test_fatigue_hiit_increases_cns_load():
    # RPE >= 8 -> HIIT -> cns_load = 20
    f = compute_running_fatigue([_run(5000, 1200, rpe=9)])
    assert f.cns_load == 20.0


def test_fatigue_long_distance_increases_local_muscular():
    # 30km -> local_muscular = min(100, 90) = 90
    f = compute_running_fatigue([_run(30000, 7200)])
    assert f.local_muscular == 90.0


def test_fatigue_affected_muscles_are_running_muscles():
    f = compute_running_fatigue([_run(5000, 1500)])
    assert set(f.affected_muscles) == {"quads", "calves", "hamstrings"}


def test_fatigue_hiit_sets_recovery_24h():
    f = compute_running_fatigue([_run(3000, 900, rpe=9)])
    assert f.recovery_hours == 24.0


# generate_running_sessions

_WEEK_START = date(2026, 4, 7)  # Monday


def _gen(week_number=1, weeks_remaining=10, hours=8.0,
         available_days=None, tid=TIDStrategy.PYRAMIDAL, volume_mod=1.0):
    return generate_running_sessions(
        vdot=50.0,
        week_number=week_number,
        weeks_remaining=weeks_remaining,
        available_days=available_days or [0, 2, 4, 5, 6],
        hours_budget=hours,
        volume_modifier=volume_mod,
        tid_strategy=tid,
        week_start=_WEEK_START,
    )


def test_generate_sessions_respects_80_20_ratio():
    sessions = _gen()
    z1_types = ("easy_z1", "long_run_z1")
    z1_total = sum(s.duration_min for s in sessions if s.workout_type in z1_types)
    total = sum(s.duration_min for s in sessions)
    assert total > 0
    assert z1_total / total >= 0.80


def test_generate_sessions_deload_week_reduces_volume():
    regular = _gen(week_number=3)
    deload = _gen(week_number=4)
    total_regular = sum(s.duration_min for s in regular)
    total_deload = sum(s.duration_min for s in deload)
    assert total_deload < total_regular


def test_generate_sessions_tapering_near_race():
    sessions = _gen(weeks_remaining=1)
    types = {s.workout_type for s in sessions}
    assert "tempo_z2" not in types
    assert "vo2max_z3" not in types or "activation_z3" in types


def test_generate_sessions_pyramidal_includes_tempo():
    sessions = _gen(tid=TIDStrategy.PYRAMIDAL)
    types = {s.workout_type for s in sessions}
    assert "tempo_z2" in types


def test_generate_sessions_polarized_avoids_z2():
    sessions = _gen(tid=TIDStrategy.POLARIZED)
    types = {s.workout_type for s in sessions}
    assert "tempo_z2" not in types


def test_generate_sessions_no_long_run_below_6h_budget():
    sessions = _gen(hours=4.0)
    types = {s.workout_type for s in sessions}
    assert "long_run_z1" not in types


def test_generate_sessions_long_run_included_at_6h():
    sessions = _gen(hours=6.0)
    types = {s.workout_type for s in sessions}
    assert "long_run_z1" in types


def test_generate_sessions_workout_slots_have_valid_dates():
    sessions = _gen()
    for s in sessions:
        assert s.date >= _WEEK_START
        assert s.date <= _WEEK_START + timedelta(days=6)
