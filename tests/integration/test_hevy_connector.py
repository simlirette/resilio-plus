"""
Integration tests — Hevy CSV connector.

Tests the parse_hevy_csv() function with realistic mock data
matching the Hevy 2026 CSV export format.
"""
import pytest

from backend.app.connectors.hevy import parse_hevy_csv, _parse_hevy_datetime, _LBS_TO_KG
from backend.app.schemas.connector import HevyWorkout


# ── Mock CSV data ─────────────────────────────────────────────────────────────

# Real Hevy CSV wraps datetime strings in quotes (they contain a comma)
HEVY_CSV_MINIMAL = (
    b'Title,Start Time,End Time,Description,Exercise Name,Superset ID,Exercise Notes,Set Order,Weight (lbs),Reps,RPE,Set Type,Seconds\n'
    b'Leg Day,"2 Apr 2026, 19:23","2 Apr 2026, 20:45",,Back Squat,,,1,225,8,,normal,\n'
    b'Leg Day,"2 Apr 2026, 19:23","2 Apr 2026, 20:45",,Back Squat,,,2,225,6,,normal,\n'
    b'Leg Day,"2 Apr 2026, 19:23","2 Apr 2026, 20:45",,Romanian Deadlift,,,1,185,10,,normal,\n'
)

HEVY_CSV_FULL = (
    b'Title,Start Time,End Time,Description,Exercise Name,Superset ID,Exercise Notes,Set Order,Weight (lbs),Reps,RPE,Set Type,Seconds\n'
    b'Push Day,"9 Apr 2026, 07:00","9 Apr 2026, 08:15",,Bench Press,,,1,155,10,7.0,normal,\n'
    b'Push Day,"9 Apr 2026, 07:00","9 Apr 2026, 08:15",,Bench Press,,,2,165,8,8.0,normal,\n'
    b'Push Day,"9 Apr 2026, 07:00","9 Apr 2026, 08:15",,Bench Press,,,3,175,6,9.0,normal,\n'
    b'Push Day,"9 Apr 2026, 07:00","9 Apr 2026, 08:15",,Overhead Press,,,1,95,12,,normal,\n'
    b'Push Day,"9 Apr 2026, 07:00","9 Apr 2026, 08:15",,Overhead Press,,,2,100,10,,normal,\n'
    b'Push Day,"9 Apr 2026, 07:00","9 Apr 2026, 08:15",,Incline DB Press,,,1,50,12,,normal,\n'
    b'Pull Day,"8 Apr 2026, 17:30","8 Apr 2026, 18:45",,Barbell Row,,,1,135,10,,normal,\n'
    b'Pull Day,"8 Apr 2026, 17:30","8 Apr 2026, 18:45",,Barbell Row,,,2,145,8,,normal,\n'
    b'Pull Day,"8 Apr 2026, 17:30","8 Apr 2026, 18:45",,Pull-Up,,,1,0,8,,normal,\n'
    b'Pull Day,"8 Apr 2026, 17:30","8 Apr 2026, 18:45",,Pull-Up,,,2,0,7,,normal,\n'
)

HEVY_CSV_WITH_BOM = (
    b'\xef\xbb\xbf'
    b'Title,Start Time,End Time,Description,Exercise Name,Superset ID,Exercise Notes,Set Order,Weight (lbs),Reps,RPE,Set Type,Seconds\n'
    b'Chest,"1 Apr 2026, 10:00","1 Apr 2026, 11:00",,Dumbbell Fly,,,1,40,12,,normal,\n'
)

HEVY_CSV_WARMUP_DROPSET = (
    b'Title,Start Time,End Time,Description,Exercise Name,Superset ID,Exercise Notes,Set Order,Weight (lbs),Reps,RPE,Set Type,Seconds\n'
    b'Strength,"3 Apr 2026, 09:00","3 Apr 2026, 10:30",,Deadlift,,,0,135,5,,warmup,\n'
    b'Strength,"3 Apr 2026, 09:00","3 Apr 2026, 10:30",,Deadlift,,,1,315,5,8.0,normal,\n'
    b'Strength,"3 Apr 2026, 09:00","3 Apr 2026, 10:30",,Deadlift,,,2,315,5,8.5,normal,\n'
    b'Strength,"3 Apr 2026, 09:00","3 Apr 2026, 10:30",,Bicep Curl,,,1,50,12,,dropset,\n'
    b'Strength,"3 Apr 2026, 09:00","3 Apr 2026, 10:30",,Bicep Curl,,,2,35,15,,dropset,\n'
)


# ── DateTime parsing ──────────────────────────────────────────────────────────

class TestParseHevyDatetime:
    def test_standard_format(self):
        dt = _parse_hevy_datetime("2 Apr 2026, 19:23")
        assert dt.year == 2026
        assert dt.month == 4
        assert dt.day == 2
        assert dt.hour == 19
        assert dt.minute == 23

    def test_leading_zero_day(self):
        dt = _parse_hevy_datetime("02 Apr 2026, 07:05")
        assert dt.day == 2
        assert dt.hour == 7

    def test_various_months(self):
        assert _parse_hevy_datetime("1 Jan 2026, 00:00").month == 1
        assert _parse_hevy_datetime("31 Dec 2025, 23:59").month == 12
        assert _parse_hevy_datetime("15 Jun 2026, 12:00").month == 6

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError):
            _parse_hevy_datetime("2026-04-02 19:23")


# ── Weight conversion ─────────────────────────────────────────────────────────

class TestWeightConversion:
    def test_lbs_to_kg_225(self):
        kg = round(225 * _LBS_TO_KG, 3)
        assert abs(kg - 102.058) < 0.01

    def test_lbs_to_kg_135(self):
        kg = round(135 * _LBS_TO_KG, 3)
        assert abs(kg - 61.235) < 0.01

    def test_bodyweight_zero(self):
        # 0 lbs → 0 kg (pull-up bodyweight)
        assert round(0 * _LBS_TO_KG, 3) == 0.0


# ── CSV parsing ───────────────────────────────────────────────────────────────

class TestParseHevyCsv:
    def test_returns_list_of_workouts(self):
        workouts = parse_hevy_csv(HEVY_CSV_MINIMAL)
        assert isinstance(workouts, list)
        assert len(workouts) == 1

    def test_workout_title(self):
        workouts = parse_hevy_csv(HEVY_CSV_MINIMAL)
        assert workouts[0].title == "Leg Day"

    def test_workout_date(self):
        from datetime import date
        workouts = parse_hevy_csv(HEVY_CSV_MINIMAL)
        assert workouts[0].date == date(2026, 4, 2)

    def test_workout_duration(self):
        workouts = parse_hevy_csv(HEVY_CSV_MINIMAL)
        # 19:23 → 20:45 = 82 minutes = 4920 seconds
        assert workouts[0].duration_seconds == 4920

    def test_workout_exercises_count(self):
        workouts = parse_hevy_csv(HEVY_CSV_MINIMAL)
        assert len(workouts[0].exercises) == 2  # Back Squat + Romanian Deadlift

    def test_exercise_sets(self):
        workouts = parse_hevy_csv(HEVY_CSV_MINIMAL)
        squat = next(e for e in workouts[0].exercises if e.name == "Back Squat")
        assert len(squat.sets) == 2
        assert squat.sets[0].reps == 8
        assert squat.sets[1].reps == 6

    def test_weight_converted_to_kg(self):
        workouts = parse_hevy_csv(HEVY_CSV_MINIMAL)
        squat = next(e for e in workouts[0].exercises if e.name == "Back Squat")
        # 225 lbs ≈ 102.058 kg
        assert squat.sets[0].weight_kg is not None
        assert abs(squat.sets[0].weight_kg - 102.058) < 0.01

    def test_multiple_workouts(self):
        workouts = parse_hevy_csv(HEVY_CSV_FULL)
        assert len(workouts) == 2
        titles = {w.title for w in workouts}
        assert titles == {"Push Day", "Pull Day"}

    def test_rpe_parsed(self):
        workouts = parse_hevy_csv(HEVY_CSV_FULL)
        push = next(w for w in workouts if w.title == "Push Day")
        bench = next(e for e in push.exercises if e.name == "Bench Press")
        assert bench.sets[0].rpe == 7.0
        assert bench.sets[1].rpe == 8.0

    def test_set_types(self):
        workouts = parse_hevy_csv(HEVY_CSV_WARMUP_DROPSET)
        dl = next(e for e in workouts[0].exercises if e.name == "Deadlift")
        assert dl.sets[0].set_type == "warmup"
        assert dl.sets[1].set_type == "normal"
        curl = next(e for e in workouts[0].exercises if e.name == "Bicep Curl")
        assert curl.sets[0].set_type == "dropset"

    def test_bom_handling(self):
        workouts = parse_hevy_csv(HEVY_CSV_WITH_BOM)
        assert len(workouts) == 1
        assert workouts[0].title == "Chest"

    def test_empty_csv_returns_empty_list(self):
        result = parse_hevy_csv(b"Title,Start Time,End Time,Description,Exercise Name,Superset ID,Exercise Notes,Set Order,Weight (lbs),Reps,RPE,Set Type,Seconds\n")
        assert result == []

    def test_workout_id_is_string(self):
        workouts = parse_hevy_csv(HEVY_CSV_MINIMAL)
        assert isinstance(workouts[0].id, str)
        assert len(workouts[0].id) == 36  # UUID format

    def test_zero_weight_bodyweight_exercise(self):
        workouts = parse_hevy_csv(HEVY_CSV_FULL)
        pull = next(w for w in workouts if w.title == "Pull Day")
        pullup = next(e for e in pull.exercises if e.name == "Pull-Up")
        assert pullup.sets[0].weight_kg is not None
        assert pullup.sets[0].weight_kg == 0.0

    def test_returns_hevyworkout_instances(self):
        workouts = parse_hevy_csv(HEVY_CSV_MINIMAL)
        assert all(isinstance(w, HevyWorkout) for w in workouts)

    def test_model_serializable(self):
        workouts = parse_hevy_csv(HEVY_CSV_FULL)
        for w in workouts:
            data = w.model_dump(mode="json")
            assert "id" in data
            assert "title" in data
            assert "date" in data
            assert "exercises" in data
