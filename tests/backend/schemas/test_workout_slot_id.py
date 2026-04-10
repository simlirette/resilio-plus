import json
from app.schemas.plan import WorkoutSlot
from app.schemas.fatigue import FatigueScore
from datetime import date


def _slot(**overrides):
    base = dict(
        date=date(2026, 4, 7),
        sport="running",
        workout_type="easy_z1",
        duration_min=45,
        fatigue_score=FatigueScore(
            local_muscular=20.0, cns_load=10.0, metabolic_cost=30.0,
            recovery_hours=12.0, affected_muscles=[],
        ),
    )
    return WorkoutSlot(**{**base, **overrides})


def test_workout_slot_has_id_by_default():
    slot = _slot()
    assert slot.id is not None
    assert isinstance(slot.id, str)
    assert len(slot.id) == 36  # UUID format


def test_two_slots_have_different_ids():
    a = _slot()
    b = _slot()
    assert a.id != b.id


def test_slot_id_roundtrips_through_json():
    slot = _slot()
    dumped = slot.model_dump(mode="json")
    restored = WorkoutSlot.model_validate(dumped)
    assert restored.id == slot.id


def test_slot_without_id_in_json_gets_new_id():
    """Backward compat: old JSON without 'id' field still deserializes."""
    raw = {
        "date": "2026-04-07",
        "sport": "running",
        "workout_type": "easy_z1",
        "duration_min": 45,
        "fatigue_score": {
            "local_muscular": 20.0, "cns_load": 10.0, "metabolic_cost": 30.0,
            "recovery_hours": 12.0, "affected_muscles": [],
        },
    }
    slot = WorkoutSlot.model_validate(raw)
    assert slot.id is not None  # gets a new UUID
