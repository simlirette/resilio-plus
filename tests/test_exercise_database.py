"""Tests de structure pour data/exercise_database.json."""

import json
from pathlib import Path

EXERCISE_DB_PATH = Path(__file__).parent.parent / "data" / "exercise_database.json"
REQUIRED_FIELDS = {
    "exercise_id", "name", "tier", "muscle_primary",
    "muscle_secondary", "equipment", "movement_pattern",
    "sfr_score", "form_cues_fr", "hevy_exercise_id",
}
VALID_TIERS = {1, 2, 3}
VALID_MOVEMENT_PATTERNS = {
    "horizontal_push", "horizontal_pull", "vertical_push", "vertical_pull",
    "squat", "hinge", "lunge", "isolation_push", "isolation_pull",
    "isolation_fly", "isolation_curl", "isolation_extension",
    "isolation_raise", "core", "prevention",
}


def load_db() -> list[dict]:
    with open(EXERCISE_DB_PATH, encoding="utf-8") as f:
        return json.load(f)


def test_exercise_database_exists():
    assert EXERCISE_DB_PATH.exists(), "data/exercise_database.json is missing"


def test_exercise_database_has_exercises():
    db = load_db()
    assert len(db) >= 20, f"Expected at least 20 exercises, got {len(db)}"


def test_all_exercises_have_required_fields():
    db = load_db()
    for ex in db:
        missing = REQUIRED_FIELDS - set(ex.keys())
        assert not missing, f"Exercise '{ex.get('name')}' missing fields: {missing}"


def test_all_exercise_ids_are_unique():
    db = load_db()
    ids = [ex["exercise_id"] for ex in db]
    assert len(ids) == len(set(ids)), "Duplicate exercise_ids found"


def test_all_tiers_are_valid():
    db = load_db()
    for ex in db:
        assert ex["tier"] in VALID_TIERS, (
            f"Exercise '{ex['name']}' has invalid tier: {ex['tier']}"
        )


def test_all_movement_patterns_are_valid():
    db = load_db()
    for ex in db:
        assert ex["movement_pattern"] in VALID_MOVEMENT_PATTERNS, (
            f"Exercise '{ex['name']}' has unknown pattern: {ex['movement_pattern']}"
        )


def test_sfr_score_in_range():
    db = load_db()
    for ex in db:
        assert 1 <= ex["sfr_score"] <= 10, (
            f"Exercise '{ex['name']}' sfr_score {ex['sfr_score']} out of range [1, 10]"
        )


def test_master_doc_exercises_present():
    """Les 6 exercices avec Hevy IDs connus (master doc §6.3) sont présents."""
    db = load_db()
    known_ids = {
        "D04AC939",  # Barbell Bench Press
        "85ADE148",  # Barbell Row
        "3A72B1D0",  # Incline Dumbbell Press
        "F198B2A3",  # Cable Row Seated
        "B5C12E87",  # Cable Lateral Raise
        "A1D3F456",  # Overhead Cable Tricep Extension
    }
    present_ids = {ex["exercise_id"] for ex in db}
    missing = known_ids - present_ids
    assert not missing, f"Master doc exercises missing from DB: {missing}"
