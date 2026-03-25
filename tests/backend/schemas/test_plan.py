import pytest
from datetime import date
from pydantic import ValidationError


def make_fatigue(**overrides):
    defaults = {
        "local_muscular": 40.0,
        "cns_load": 30.0,
        "metabolic_cost": 35.0,
        "recovery_hours": 12.0,
    }
    defaults.update(overrides)
    return defaults


def make_slot(**overrides):
    defaults = {
        "date": date(2026, 4, 7),
        "sport": "running",
        "workout_type": "easy_run",
        "duration_min": 60,
        "fatigue_score": make_fatigue(),
    }
    defaults.update(overrides)
    return defaults


def make_plan(**overrides):
    defaults = {
        "athlete_id": "00000000-0000-0000-0000-000000000001",
        "start_date": date(2026, 4, 7),
        "end_date": date(2026, 5, 4),
        "phase": "base",
        "total_weekly_hours": 8.0,
        "acwr": 1.0,
    }
    defaults.update(overrides)
    return defaults


def test_workout_slot_valid():
    from app.schemas.plan import WorkoutSlot
    slot = WorkoutSlot(**make_slot())
    assert slot.sport.value == "running"
    assert slot.workout_type == "easy_run"
    assert slot.duration_min == 60
    assert slot.notes == ""
    assert slot.fatigue_score.local_muscular == 40.0


def test_workout_slot_duration_zero_raises():
    from app.schemas.plan import WorkoutSlot
    with pytest.raises(ValidationError):
        WorkoutSlot(**make_slot(duration_min=0))


def test_workout_slot_negative_duration_raises():
    from app.schemas.plan import WorkoutSlot
    with pytest.raises(ValidationError):
        WorkoutSlot(**make_slot(duration_min=-10))


def test_workout_slot_invalid_sport_raises():
    from app.schemas.plan import WorkoutSlot
    with pytest.raises(ValidationError):
        WorkoutSlot(**make_slot(sport="yoga"))


def test_workout_slot_notes_defaults_to_empty():
    from app.schemas.plan import WorkoutSlot
    slot = WorkoutSlot(**make_slot())
    assert slot.notes == ""


def test_workout_slot_with_notes():
    from app.schemas.plan import WorkoutSlot
    slot = WorkoutSlot(**make_slot(notes="Feel good, pushed the pace."))
    assert slot.notes == "Feel good, pushed the pace."


def test_training_plan_valid_empty_slots():
    from app.schemas.plan import TrainingPlan
    plan = TrainingPlan(**make_plan())
    assert plan.phase == "base"
    assert plan.weekly_slots == {}
    assert plan.acwr == 1.0


def test_training_plan_id_generated():
    from app.schemas.plan import TrainingPlan
    p1 = TrainingPlan(**make_plan())
    p2 = TrainingPlan(**make_plan())
    assert p1.id != p2.id


def test_training_plan_invalid_phase_raises():
    from app.schemas.plan import TrainingPlan
    with pytest.raises(ValidationError):
        TrainingPlan(**make_plan(phase="maintenance"))


def test_training_plan_negative_acwr_raises():
    from app.schemas.plan import TrainingPlan
    with pytest.raises(ValidationError):
        TrainingPlan(**make_plan(acwr=-0.1))


def test_training_plan_with_weekly_slots():
    from app.schemas.plan import TrainingPlan
    plan = TrainingPlan(**make_plan(
        weekly_slots={"2026-W15": [make_slot()]}
    ))
    assert len(plan.weekly_slots["2026-W15"]) == 1
    assert plan.weekly_slots["2026-W15"][0].workout_type == "easy_run"


def test_training_plan_json_round_trip_with_slots():
    from app.schemas.plan import TrainingPlan
    plan = TrainingPlan(**make_plan(
        weekly_slots={"2026-W15": [make_slot()]}
    ))
    json_str = plan.model_dump_json()
    plan2 = TrainingPlan.model_validate_json(json_str)
    assert plan == plan2
    assert plan2.weekly_slots["2026-W15"][0].fatigue_score.local_muscular == 40.0
