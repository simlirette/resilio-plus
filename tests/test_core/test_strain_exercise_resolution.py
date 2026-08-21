"""Hevy exercise names must resolve to the right muscles.

`EXERCISE_MUSCLE_MAP` was keyed on clean canonical names ("Bench Press",
"Pull-up"). Hevy emits equipment-qualified names: "Incline Bench Press
(Dumbbell)", "Pull Up (Weighted)", "Triceps Extension (Cable)". Measured
against a real account on 2026-08-20, **11 of 11 exercises missed**, so every
lifting session fell through to `__unknown__` — which charges `core: 0.3` and
nothing else. The strain radar showed `core: 100` for an arms-and-chest week.

The bug is silent by construction: the fallback is a valid map, so nothing
raises and no log line fires. These tests pin resolution itself rather than the
downstream score.
"""
from __future__ import annotations

from datetime import date

import pytest
from app.core.strain import EXERCISE_MUSCLE_MAP, resolve_exercise

UNKNOWN = EXERCISE_MUSCLE_MAP["__unknown__"]


def _dominant(name: str) -> str:
    """Return the muscle carrying the highest coefficient for `name`."""
    weights = resolve_exercise(name)
    return max(weights, key=lambda m: weights[m])


class TestExactNamesStillWin:
    """The existing map keeps working byte-for-byte."""

    @pytest.mark.parametrize("name", sorted(EXERCISE_MUSCLE_MAP))
    def test_every_canonical_key_resolves_to_itself(self, name: str) -> None:
        assert resolve_exercise(name) == EXERCISE_MUSCLE_MAP[name]


class TestEquipmentQualifiers:
    """Hevy appends the equipment in parentheses; it never changes the muscles."""

    @pytest.mark.parametrize(
        "name,canonical",
        [
            ("Incline Bench Press (Dumbbell)", "Incline Bench Press"),
            ("Bench Press (Barbell)", "Bench Press"),
            ("Squat (Smith Machine)", "Squat"),
            ("Lateral Raise (Cable)", "Lateral Raise"),
            ("Leg Press (Machine)", "Leg Press"),
            ("Romanian Deadlift (Dumbbell)", "Romanian Deadlift"),
        ],
    )
    def test_qualifier_is_stripped(self, name: str, canonical: str) -> None:
        assert resolve_exercise(name) == EXERCISE_MUSCLE_MAP[canonical]


class TestSeparatorAndCase:
    @pytest.mark.parametrize(
        "name,canonical",
        [
            ("Pull Up (Weighted)", "Pull-up"),
            ("pull-up", "Pull-up"),
            ("PULL UP", "Pull-up"),
            ("Push Up", "Push-up"),
            ("  Bench   Press  ", "Bench Press"),
        ],
    )
    def test_spacing_hyphens_and_case_do_not_matter(
        self, name: str, canonical: str
    ) -> None:
        assert resolve_exercise(name) == EXERCISE_MUSCLE_MAP[canonical]


class TestRealAccountNames:
    """The 11 names that missed, taken verbatim from the live Hevy account."""

    @pytest.mark.parametrize(
        "name,expected_muscle",
        [
            ("Shoulder Press (Dumbbell)", "shoulders"),
            ("Triceps Extension (Cable)", "triceps"),
            ("Preacher Curl (Machine)", "biceps"),
            ("Triceps Dip", "triceps"),
            ("Hammer Curl (Cable)", "biceps"),
            ("Seated Lateral Raise (Dumbbell)", "shoulders"),
            ("Pull Up (Weighted)", "upper_pull"),
            ("Incline Bench Press (Dumbbell)", "chest"),
            ("T Bar Row", "upper_pull"),
            ("Rear Delt Reverse Fly (Cable)", "shoulders"),
            ("Chest Press (Machine)", "chest"),
        ],
    )
    def test_each_resolves_to_the_right_dominant_muscle(
        self, name: str, expected_muscle: str
    ) -> None:
        assert resolve_exercise(name) != UNKNOWN, f"{name!r} still falls through"
        assert _dominant(name) == expected_muscle


class TestGenuinelyUnknown:
    """A name nothing can match must still degrade, not raise."""

    @pytest.mark.parametrize("name", ["Jefferson Curl", "", "   ", "(Cable)", "???"])
    def test_falls_back_without_raising(self, name: str) -> None:
        assert resolve_exercise(name) == UNKNOWN


class TestScoreOnRealWorkout:
    """End to end: an arms session must not read as core."""

    def test_an_arms_session_loads_arms_not_core(self) -> None:
        from app.core.strain import compute_muscle_strain
        from app.schemas.connector import HevyExercise, HevySet, HevyWorkout

        day = date(2026, 8, 20)
        workout = HevyWorkout(
            id="w1",
            title="Arms 2",
            date=day,
            duration_seconds=3600,
            exercises=[
                HevyExercise(
                    name=name,
                    sets=[HevySet(reps=10, weight_kg=30.0, rpe=8.0, set_type="normal")],
                )
                for name in (
                    "Triceps Extension (Cable)",
                    "Preacher Curl (Machine)",
                    "Hammer Curl (Cable)",
                )
            ],
        )

        scores = compute_muscle_strain([], [workout], reference_date=day)
        assert scores is not None
        assert scores.triceps > 0, "triceps unloaded by a triceps session"
        assert scores.biceps > 0, "biceps unloaded by a curl session"
