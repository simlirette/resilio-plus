"""Approved workouts reach the Garmin watch through intervals.icu.

Step 4 of the goal document: "Once the training plan is approved, it is pushed
to Google Agenda and the workouts that can be on garmin are pushed on
intervals.icu for them to be pushed on garmin."

Google Calendar was built. intervals.icu did not exist at all — the athlete
could see the week on their phone and had nothing on their wrist.

Two things this must get right, because both are silent when wrong:

  - **Idempotence.** A re-approval must update the same event, not create a
    second one. Google Calendar learned this the hard way; the same lesson
    applies here.
  - **Not every session is a workout.** A lifting session has no structure
    intervals.icu can express, and pushing it produces a meaningless entry on
    the watch. Those are skipped, and skipping is reported rather than hidden.
"""
from __future__ import annotations

from datetime import date

import pytest

from app.integrations.intervals_icu.workout_builder import (
    build_workout,
    is_pushable,
)

MONDAY = date(2026, 8, 24)


def _slot(sport: str, workout: str, minutes: int, **extra) -> dict:
    return {
        "date": MONDAY.isoformat(),
        "sport": sport,
        "workout_type": workout,
        "duration_min": minutes,
        **extra,
    }


class TestWhatCanBePushed:
    @pytest.mark.parametrize(
        "workout", ["easy_z1", "tempo_z2", "vo2max_z3", "long_run_z1"]
    )
    def test_a_structured_run_is_pushable(self, workout: str) -> None:
        assert is_pushable(_slot("running", workout, 45))

    @pytest.mark.parametrize(
        "workout", ["upper_hypertrophy", "lower_strength", "full_body_endurance"]
    )
    def test_a_lifting_session_is_not(self, workout: str) -> None:
        """A watch cannot run a hypertrophy block; the entry would be noise."""
        assert not is_pushable(_slot("lifting", workout, 60))

    def test_a_session_with_no_duration_is_not_pushable(self) -> None:
        assert not is_pushable(_slot("running", "easy_z1", 0))

    def test_an_unknown_sport_is_not_pushable(self) -> None:
        assert not is_pushable(_slot("dek_hockey", "game", 60))


class TestTheWorkoutItBuilds:
    def test_it_carries_the_date_and_name(self) -> None:
        workout = build_workout(_slot("running", "tempo_z2", 45))

        assert workout is not None
        assert workout["start_date_local"].startswith("2026-08-24")
        assert "tempo" in workout["name"].lower()

    def test_the_duration_reaches_the_watch(self) -> None:
        workout = build_workout(_slot("running", "easy_z1", 50))

        assert workout is not None
        assert "50" in str(workout["description"]) or workout["moving_time"] == 3000

    def test_the_prescribed_pace_is_carried_when_present(self) -> None:
        """The pace is the whole point of pushing it to the watch."""
        workout = build_workout(
            _slot("running", "tempo_z2", 45, notes="8 km @ 5:10/km")
        )

        assert workout is not None
        assert "5:10" in str(workout["description"])

    def test_a_session_that_cannot_be_pushed_builds_nothing(self) -> None:
        assert build_workout(_slot("lifting", "lower_strength", 60)) is None

    def test_the_slot_id_travels_so_it_can_be_updated(self) -> None:
        """Without it a re-approval creates a duplicate instead of updating."""
        workout = build_workout(
            _slot("running", "easy_z1", 45, id="slot-42")
        )

        assert workout is not None
        assert "slot-42" in str(workout.get("external_id", ""))


class TestTheWeek:
    def test_only_pushable_sessions_come_back(self) -> None:
        from app.integrations.intervals_icu.workout_builder import build_week

        workouts, skipped = build_week(
            [
                _slot("running", "easy_z1", 45),
                _slot("lifting", "lower_strength", 60),
                _slot("running", "tempo_z2", 40),
            ]
        )

        assert len(workouts) == 2
        assert skipped == 1

    def test_an_empty_week_is_not_an_error(self) -> None:
        from app.integrations.intervals_icu.workout_builder import build_week

        assert build_week([]) == ([], 0)

    def test_a_malformed_slot_is_skipped_not_raised(self) -> None:
        """One bad slot must not stop the rest of the week reaching the watch."""
        from app.integrations.intervals_icu.workout_builder import build_week

        workouts, skipped = build_week(
            [{"nonsense": True}, _slot("running", "easy_z1", 45)]
        )

        assert len(workouts) == 1
        assert skipped == 1
