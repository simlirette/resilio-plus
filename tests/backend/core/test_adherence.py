"""What was planned against what was actually done.

Nothing in the system compared the two. There is no `skipped`, no compliance,
no adherence logic anywhere — checked. The daily reminder recites today's slots
and never looks at whether yesterday's happened.

That is the whole of "faire le suivi". A real coach notices you missed
Tuesday's intervals, notices you ran 14 km when the plan said 8, and reacts to
both. Neither is currently observable.

Matching is deliberately loose on the numbers and strict on the day. An
athlete who runs 40 minutes instead of 45 did the session. One who ran nothing
did not, and one who ran on Wednesday instead of Tuesday moved it — which is
a different fact from skipping it, and the coach should be able to tell them
apart.
"""
from __future__ import annotations

from datetime import date

import pytest
from app.core.adherence import (
    SessionOutcome,
    Status,
    compare_week,
)

MONDAY = date(2026, 8, 24)
TUESDAY = date(2026, 8, 25)
WEDNESDAY = date(2026, 8, 26)


def _slot(day: date, sport: str, minutes: int, workout: str = "easy_z1") -> dict:
    return {
        "date": day.isoformat(),
        "sport": sport,
        "workout_type": workout,
        "duration_min": minutes,
    }


def _done(day: date, sport: str, minutes: int, km: float | None = None) -> dict:
    return {
        "date": day,
        "sport": sport,
        "duration_min": minutes,
        "distance_km": km,
    }


class TestASessionThatHappened:
    def test_an_exact_match_is_done(self) -> None:
        result = compare_week(
            planned=[_slot(MONDAY, "running", 45)],
            completed=[_done(MONDAY, "running", 45)],
        )

        assert result.outcomes[0].status is Status.DONE

    def test_a_close_duration_still_counts_as_done(self) -> None:
        """40 minutes instead of 45 is the session, not a failure."""
        result = compare_week(
            planned=[_slot(MONDAY, "running", 45)],
            completed=[_done(MONDAY, "running", 40)],
        )

        assert result.outcomes[0].status is Status.DONE

    def test_a_much_longer_session_is_flagged_as_overshot(self) -> None:
        """Doing 90 minutes of a 45 minute easy run is a load event."""
        result = compare_week(
            planned=[_slot(MONDAY, "running", 45)],
            completed=[_done(MONDAY, "running", 90)],
        )

        assert result.outcomes[0].status is Status.OVERSHOT

    def test_a_much_shorter_session_is_flagged_as_cut_short(self) -> None:
        result = compare_week(
            planned=[_slot(MONDAY, "running", 60)],
            completed=[_done(MONDAY, "running", 15)],
        )

        assert result.outcomes[0].status is Status.CUT_SHORT


class TestASessionThatDidNot:
    def test_nothing_on_the_day_is_missed(self) -> None:
        result = compare_week(planned=[_slot(MONDAY, "running", 45)], completed=[])

        assert result.outcomes[0].status is Status.MISSED

    def test_the_wrong_sport_does_not_count(self) -> None:
        result = compare_week(
            planned=[_slot(MONDAY, "running", 45)],
            completed=[_done(MONDAY, "lifting", 45)],
        )

        assert result.outcomes[0].status is Status.MISSED

    def test_a_session_done_a_day_later_is_moved_not_missed(self) -> None:
        """Moving a session is a different fact from skipping it."""
        result = compare_week(
            planned=[_slot(TUESDAY, "running", 45)],
            completed=[_done(WEDNESDAY, "running", 45)],
        )

        assert result.outcomes[0].status is Status.MOVED

    def test_a_session_done_three_days_later_is_missed(self) -> None:
        result = compare_week(
            planned=[_slot(MONDAY, "running", 45)],
            completed=[_done(MONDAY.replace(day=28), "running", 45)],
        )

        assert result.outcomes[0].status is Status.MISSED


class TestUnplannedWork:
    def test_training_that_was_not_planned_is_reported(self) -> None:
        """A coach needs to see the extra load, not only the missing one."""
        result = compare_week(
            planned=[_slot(MONDAY, "running", 45)],
            completed=[_done(MONDAY, "running", 45), _done(WEDNESDAY, "running", 60)],
        )

        assert len(result.unplanned) == 1
        assert result.unplanned[0]["sport"] == "running"

    def test_a_completed_session_is_used_once(self) -> None:
        """Two planned slots must not both claim the same run."""
        result = compare_week(
            planned=[_slot(MONDAY, "running", 45), _slot(MONDAY, "running", 45)],
            completed=[_done(MONDAY, "running", 45)],
        )

        statuses = [o.status for o in result.outcomes]
        assert statuses.count(Status.DONE) == 1
        assert Status.MISSED in statuses


class TestTheSummary:
    def test_it_counts_what_happened(self) -> None:
        result = compare_week(
            planned=[
                _slot(MONDAY, "running", 45),
                _slot(TUESDAY, "lifting", 60),
                _slot(WEDNESDAY, "running", 45),
            ],
            completed=[_done(MONDAY, "running", 45)],
        )

        assert result.done == 1
        assert result.missed == 2

    def test_a_fully_completed_week_needs_no_follow_up(self) -> None:
        result = compare_week(
            planned=[_slot(MONDAY, "running", 45)],
            completed=[_done(MONDAY, "running", 45)],
        )

        assert not result.worth_raising

    def test_a_missed_session_is_worth_raising(self) -> None:
        result = compare_week(planned=[_slot(MONDAY, "running", 45)], completed=[])

        assert result.worth_raising

    def test_an_empty_plan_is_never_worth_raising(self) -> None:
        """Silence beats messaging an athlete about a week that does not exist."""
        result = compare_week(planned=[], completed=[])

        assert not result.worth_raising
        assert result.outcomes == []


class TestTheFactsHandedToTheCoach:
    def test_it_describes_what_happened_without_advice(self) -> None:
        """The coach forms the judgement; this only reports."""
        from app.core.adherence import describe_week

        result = compare_week(
            planned=[_slot(MONDAY, "running", 45, "intervals_z3")],
            completed=[],
        )
        text = describe_week(result)

        assert "intervals_z3" in text or "24" in text
        assert "devrais" not in text.lower()

    def test_a_clean_week_says_so(self) -> None:
        from app.core.adherence import describe_week

        result = compare_week(
            planned=[_slot(MONDAY, "running", 45)],
            completed=[_done(MONDAY, "running", 45)],
        )

        assert describe_week(result)


@pytest.mark.parametrize("status", list(Status))
def test_every_status_has_a_label(status: Status) -> None:
    from app.core.adherence import STATUS_LABELS

    assert status in STATUS_LABELS


def test_outcome_carries_the_slot_it_refers_to() -> None:
    result = compare_week(planned=[_slot(MONDAY, "running", 45)], completed=[])
    outcome: SessionOutcome = result.outcomes[0]

    assert outcome.planned["sport"] == "running"
    assert outcome.date == MONDAY
