from pathlib import Path
import pytest
from app.integrations.hevy.csv_parser import parse_hevy_csv

FIXTURE = (Path(__file__).parents[2] / "fixtures" / "hevy_export_sample.csv").read_bytes()


def test_parse_returns_two_workouts():
    workouts = parse_hevy_csv(FIXTURE)
    assert len(workouts) == 2


def test_first_workout_title_and_date():
    workouts = parse_hevy_csv(FIXTURE)
    assert workouts[0].title == "Push Day A"
    assert str(workouts[0].date) == "2026-04-01"


def test_first_workout_has_two_exercises():
    workouts = parse_hevy_csv(FIXTURE)
    assert len(workouts[0].exercises) == 2


def test_bench_press_sets_parsed_correctly():
    workouts = parse_hevy_csv(FIXTURE)
    bench = workouts[0].exercises[0]
    assert bench.name == "Bench Press"
    assert len(bench.sets) == 2
    assert bench.sets[0].weight_kg == 80.0
    assert bench.sets[0].reps == 8
    assert bench.sets[0].rpe == 8.0
    assert bench.sets[0].set_type == "normal"


def test_missing_rpe_is_none():
    workouts = parse_hevy_csv(FIXTURE)
    ohp = workouts[0].exercises[1]
    assert ohp.name == "Overhead Press"
    assert ohp.sets[0].rpe is None


def test_bodyweight_set_has_none_weight():
    workouts = parse_hevy_csv(FIXTURE)
    leg_day = workouts[1]
    bw = next(e for e in leg_day.exercises if e.name == "Bodyweight Squat")
    assert bw.sets[0].weight_kg is None
    assert bw.sets[0].reps == 15


def test_lbs_conversion():
    workouts = parse_hevy_csv(FIXTURE, unit="lbs")
    bench = workouts[0].exercises[0]
    assert abs(bench.sets[0].weight_kg - 80 * 0.453592) < 0.001


def test_workout_id_is_slug_of_date_and_title():
    workouts = parse_hevy_csv(FIXTURE)
    assert workouts[0].id == "2026-04-01-push-day-a"
    assert workouts[1].id == "2026-04-03-leg-day"


def test_invalid_unit_raises_value_error():
    with pytest.raises(ValueError, match="Invalid unit"):
        parse_hevy_csv(FIXTURE, unit="stone")


def test_empty_csv_raises_value_error():
    header = b"Date,Workout Name,Exercise Name,Set Order,Weight,Reps,Distance,Seconds,Notes,Workout Notes,RPE\n"
    with pytest.raises(ValueError, match="no workouts found"):
        parse_hevy_csv(header)


def test_missing_required_column_raises_value_error():
    bad = b"Date,Exercise Name\n2026-04-01,Squat\n"
    with pytest.raises(ValueError, match="Missing required columns"):
        parse_hevy_csv(bad)
