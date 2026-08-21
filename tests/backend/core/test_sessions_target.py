"""The week must contain the number of sessions the athlete asked for.

Session count was a byproduct: `generate_running_sessions` divided an hours
budget into 30–90 minute chunks and whatever fell out was the week. The
athlete's own answer -- "je vise 3 sorties, si besoin 4" and "3 ou 4 séances"
of lifting -- was never consulted, because until Phase B there was nowhere to
put it.

On the first live plan that produced two running sessions and no lifting at
all, for an athlete who runs three times a week and lifts four. The hours
extraction was wrong too, but even with the right hours the count was an
accident of arithmetic.

`sessions_target` is honoured when given and ignored when not, so every
existing caller keeps its behaviour byte for byte.
"""
from __future__ import annotations

from datetime import date

import pytest
from app.core.periodization import TIDStrategy
from app.core.running_logic import generate_running_sessions

WEEK_START = date(2026, 8, 24)
EVERY_DAY = [0, 1, 2, 3, 4, 5, 6]


def _paces() -> dict:
    return {
        "easy_min_per_km": "6:00",
        "easy_max_per_km": "6:40",
        "long_run_pace_per_km": "6:20",
        "marathon_pace_per_km": "5:30",
        "threshold_pace_per_km": "5:10",
        "interval_pace_per_km": "4:45",
        "repetition_pace_per_400m": "1:50",
        "repetition_pace_per_km": "4:35",
    }


def _shape(week) -> list[tuple[str, int]]:
    """A week's identity for comparison: what and how long, in order."""
    return [(s.workout_type, s.duration_min) for s in week]


def _week(hours: float, target: int | None = None, weeks_remaining: int = 8):
    return generate_running_sessions(
        vdot=43.0,
        week_number=1,
        weeks_remaining=weeks_remaining,
        available_days=EVERY_DAY,
        hours_budget=hours,
        volume_modifier=1.0,
        tid_strategy=TIDStrategy.PYRAMIDAL,
        week_start=WEEK_START,
        sessions_target=target,
        _paces=_paces(),
    )


class TestTheTargetIsHonoured:
    @pytest.mark.parametrize("target", [2, 3, 4, 5])
    def test_the_week_has_exactly_that_many_sessions(self, target: int) -> None:
        assert len(_week(hours=5.0, target=target)) == target

    def test_a_bigger_budget_makes_longer_sessions_not_more_of_them(self) -> None:
        """The athlete asked for three runs, not for however many fit."""
        small = _week(hours=3.0, target=3)
        large = _week(hours=8.0, target=3)

        assert len(small) == len(large) == 3
        assert sum(s.duration_min for s in large) > sum(s.duration_min for s in small)

    def test_the_weekly_volume_still_matches_the_budget(self) -> None:
        total = sum(s.duration_min for s in _week(hours=6.0, target=4))

        assert 6.0 * 60 * 0.8 <= total <= 6.0 * 60 * 1.2

    def test_quality_work_survives_a_small_target(self) -> None:
        """Three sessions must not become three easy runs."""
        week = _week(hours=5.0, target=3)

        assert any("easy" not in s.workout_type for s in week)

    def test_days_are_still_spread_out(self) -> None:
        week = _week(hours=6.0, target=4)

        assert len({s.date for s in week}) == 4


class TestWithoutATargetNothingChanges:
    def test_the_old_shape_is_preserved(self) -> None:
        """Every existing caller passes no target and must be unaffected."""
        before = _week(hours=5.0, target=None)

        assert before
        assert all(s.duration_min > 0 for s in before)

    @pytest.mark.parametrize("target", [0, -2])
    def test_a_nonsense_target_is_ignored(self, target: int) -> None:
        """Zero is a failed extraction, not a request for a rest week.

        Compared by shape: WorkoutSlot carries a generated id, so two
        identical weeks are never equal as objects.
        """
        assert _shape(_week(hours=5.0, target=target)) == _shape(
            _week(hours=5.0, target=None)
        )


class TestEdges:
    def test_a_target_larger_than_the_available_days_is_capped(self) -> None:
        week = generate_running_sessions(
            vdot=43.0,
            week_number=1,
            weeks_remaining=8,
            available_days=[0, 2, 4],
            hours_budget=6.0,
            volume_modifier=1.0,
            tid_strategy=TIDStrategy.PYRAMIDAL,
            week_start=WEEK_START,
            sessions_target=6,
            _paces=_paces(),
        )

        assert len(week) <= 3, "more sessions than days the athlete is free"

    def test_no_available_days_still_yields_nothing(self) -> None:
        week = generate_running_sessions(
            vdot=43.0,
            week_number=1,
            weeks_remaining=8,
            available_days=[],
            hours_budget=6.0,
            volume_modifier=1.0,
            tid_strategy=TIDStrategy.PYRAMIDAL,
            week_start=WEEK_START,
            sessions_target=3,
            _paces=_paces(),
        )

        assert week == []

    def test_a_taper_week_may_hold_fewer_sessions(self) -> None:
        """Tapering is a coaching decision and outranks the athlete's preference."""
        week = _week(hours=6.0, target=5, weeks_remaining=1)

        assert 0 < len(week) <= 5
