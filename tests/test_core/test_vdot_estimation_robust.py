"""Estimating VDOT from training runs must not be inflated by one fast day.

`estimate_vdot` took the **maximum** VDOT across every run in the window, and
looked each run's average pace up in a table keyed on *easy* pace. Two
compounding errors: a threshold or interval session gets read as though the
athlete jogs that fast, and taking the max means the single hardest day sets
the number.

Measured on the live account 2026-08-20: runs ranged 5:19/km to 8:14/km and the
estimate came out at 53.0 -- taken entirely from the fastest, shortest run. Every
prescribed pace for the block would have been derived from it.

Over-prescribing is the more harmful failure, so the estimate is now the median
of qualifying runs, and runs too short to establish an aerobic pace do not
qualify at all. This is still an estimate; a declared race time replaces it.
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest
from app.core.running_logic import estimate_vdot

TODAY = date(2026, 8, 20)
BEGINNER_FLOOR = 35.0


def _run(km: float, min_per_km: float, days_ago: int = 3) -> object:
    from app.schemas.connector import StravaActivity

    return StravaActivity(
        id=f"a{days_ago}-{km}-{min_per_km}",
        name="Run",
        sport_type="Run",
        date=TODAY - timedelta(days=days_ago),
        duration_seconds=int(km * min_per_km * 60),
        distance_meters=km * 1000,
    )


class TestOneFastDayDoesNotSetTheNumber:
    def test_a_single_hard_session_does_not_dominate(self) -> None:
        easy = [_run(8.0, 7.5, d) for d in (2, 4, 6, 8, 10)]
        hard = _run(5.0, 4.5, days_ago=3)

        with_hard = estimate_vdot([*easy, hard], reference_date=TODAY)
        without = estimate_vdot(easy, reference_date=TODAY)

        assert with_hard == without, "the hard day moved the estimate"

    def test_the_estimate_tracks_the_typical_run_not_the_best(self) -> None:
        runs = [
            _run(8.0, 7.5, 2),
            _run(8.0, 7.5, 4),
            _run(8.0, 7.5, 6),
            _run(6.0, 5.0, 8),  # one much faster
        ]
        typical_only = [_run(8.0, 7.5, d) for d in (2, 4, 6)]

        assert estimate_vdot(runs, reference_date=TODAY) == estimate_vdot(
            typical_only, reference_date=TODAY
        )

    def test_getting_genuinely_faster_does_move_it(self) -> None:
        """Robust, not inert."""
        slow = [_run(8.0, 7.5, d) for d in (2, 4, 6, 8, 10)]
        fast = [_run(8.0, 5.0, d) for d in (2, 4, 6, 8, 10)]

        assert estimate_vdot(fast, reference_date=TODAY) > estimate_vdot(
            slow, reference_date=TODAY
        )


class TestShortRunsDoNotQualify:
    @pytest.mark.parametrize("km", [0.4, 1.0, 2.0, 2.9])
    def test_a_run_too_short_to_establish_a_pace_is_excluded(self, km: float) -> None:
        assert estimate_vdot([_run(km, 4.0)], reference_date=TODAY) == BEGINNER_FLOOR

    def test_a_short_sprint_cannot_inflate_a_week_of_easy_running(self) -> None:
        easy = [_run(8.0, 7.5, d) for d in (2, 4, 6, 8, 10)]
        sprint = _run(1.0, 3.5, days_ago=1)

        assert estimate_vdot([*easy, sprint], reference_date=TODAY) == estimate_vdot(
            easy, reference_date=TODAY
        )

    def test_a_long_run_qualifies(self) -> None:
        assert estimate_vdot([_run(10.0, 5.5)], reference_date=TODAY) > BEGINNER_FLOOR


class TestWindowAndFallback:
    def test_runs_outside_thirty_days_are_ignored(self) -> None:
        assert (
            estimate_vdot([_run(10.0, 5.0, days_ago=45)], reference_date=TODAY)
            == BEGINNER_FLOOR
        )

    def test_no_runs_at_all_returns_the_floor(self) -> None:
        assert estimate_vdot([], reference_date=TODAY) == BEGINNER_FLOOR

    def test_non_runs_are_ignored(self) -> None:
        from app.schemas.connector import StravaActivity

        ride = StravaActivity(
            id="r1",
            name="Ride",
            sport_type="Ride",
            date=TODAY - timedelta(days=2),
            duration_seconds=3600,
            distance_meters=30000.0,
        )
        assert estimate_vdot([ride], reference_date=TODAY) == BEGINNER_FLOOR


class TestQualificationIsSharedNotDuplicated:
    """The view builder must ask the same question the estimator asks.

    `_attach_estimated_vdot` had its own inline copy of the qualification rule
    and drifted from it within a single commit. There is now one predicate.
    """

    def test_the_predicate_agrees_with_the_estimator(self) -> None:
        from app.core.running_logic import qualifies_for_vdot

        short = _run(1.0, 4.0)
        long_enough = _run(8.0, 6.0)

        assert not qualifies_for_vdot(short, reference_date=TODAY)
        assert qualifies_for_vdot(long_enough, reference_date=TODAY)

        assert estimate_vdot([short], reference_date=TODAY) == BEGINNER_FLOOR
        assert estimate_vdot([long_enough], reference_date=TODAY) > BEGINNER_FLOOR

    def test_a_stale_run_does_not_qualify(self) -> None:
        from app.core.running_logic import qualifies_for_vdot

        assert not qualifies_for_vdot(_run(10.0, 5.0, days_ago=60), reference_date=TODAY)
