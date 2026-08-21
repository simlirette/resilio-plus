"""A race that has happened is not still the goal.

Step 6 of the goal document: "When the objective is reach, the athlete can set
up a new objective."

Nothing noticed. `target_race_date` sat in the past and the coach kept
periodising toward it — `weeks_to_race` clamps at 0, so every week after the
race read as race week forever. The athlete would have had to say "that race is
done" for anything to change.

Detection is deterministic here; what to *do* about it is the coach's call and
the athlete's decision. This only reports that the date has passed and how long
ago, which is what a coach notices on their own.
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.core.objective import ObjectiveStatus, describe_objective, objective_status

TODAY = date(2026, 8, 21)


class _Athlete:
    def __init__(self, race_date: date | None, goals: str = '["semi sous 2h"]') -> None:
        self.target_race_date = race_date
        self.goals_json = goals


class TestStatus:
    def test_a_future_race_is_active(self) -> None:
        athlete = _Athlete(TODAY + timedelta(days=30))

        assert objective_status(athlete, TODAY) is ObjectiveStatus.ACTIVE

    def test_the_race_day_itself_is_still_active(self) -> None:
        """The athlete has not run it yet at breakfast."""
        athlete = _Athlete(TODAY)

        assert objective_status(athlete, TODAY) is ObjectiveStatus.ACTIVE

    def test_a_race_yesterday_has_passed(self) -> None:
        athlete = _Athlete(TODAY - timedelta(days=1))

        assert objective_status(athlete, TODAY) is ObjectiveStatus.PASSED

    def test_no_race_date_is_undated(self) -> None:
        """"Get fitter" is a real goal with no finish line."""
        athlete = _Athlete(None)

        assert objective_status(athlete, TODAY) is ObjectiveStatus.UNDATED

    def test_no_goal_at_all_is_none(self) -> None:
        athlete = _Athlete(None, goals="[]")

        assert objective_status(athlete, TODAY) is ObjectiveStatus.NONE


class TestStaleness:
    def test_a_race_long_past_is_still_reported(self) -> None:
        """Silence would leave the athlete periodising toward a date in 2026."""
        athlete = _Athlete(TODAY - timedelta(days=200))

        assert objective_status(athlete, TODAY) is ObjectiveStatus.PASSED

    @pytest.mark.parametrize("days", [1, 7, 45])
    def test_the_description_says_how_long_ago(self, days: int) -> None:
        athlete = _Athlete(TODAY - timedelta(days=days))

        assert str(days) in describe_objective(athlete, TODAY)


class TestWhatTheCoachIsTold:
    def test_a_passed_race_invites_the_next_objective(self) -> None:
        athlete = _Athlete(TODAY - timedelta(days=2))
        text = describe_objective(athlete, TODAY)

        assert "passée" in text.lower()
        assert "objectif" in text.lower()

    def test_it_does_not_dictate_the_next_goal(self) -> None:
        """The athlete decides; the coach reports and asks."""
        athlete = _Athlete(TODAY - timedelta(days=2))
        text = describe_objective(athlete, TODAY)

        assert "je fixe" not in text.lower()
        assert "nouvel objectif :" not in text.lower()

    def test_an_active_race_says_nothing(self) -> None:
        """Only a state worth acting on produces a line."""
        athlete = _Athlete(TODAY + timedelta(days=30))

        assert describe_objective(athlete, TODAY) == ""

    def test_no_goal_asks_for_one(self) -> None:
        athlete = _Athlete(None, goals="[]")

        assert describe_objective(athlete, TODAY)


class TestItReachesTheCoach:
    def test_the_facts_block_carries_it(self) -> None:
        import inspect

        from app.services import profile_provenance

        source = inspect.getsource(profile_provenance)
        assert "describe_objective" in source
