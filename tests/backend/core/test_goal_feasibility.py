"""The coach must say whether the goal is reachable, and offer the alternative.

The first live plan accepted "sub-2h au semi" without a word and generated a
1h30 week. That silence is the substance of "ce n'est pas un vrai coach" -- not
the tone. An athlete whose 10 km projects 2h20 deserves to hear it, four weeks
out, from something calling itself a coach.

Operator decision, 2026-08-21: when the goal is ambitious the coach presents
**both** weeks -- the one built for the stated target and what would change for
a realistic one -- and the athlete chooses. It never revises the target on its
own.

Daniels' table, checked: VDOT 30 -> 2h24, VDOT 35 -> 2h00, VDOT 40 -> 1h42.
Sub-2h therefore needs VDOT 35, not the 36-37 estimated by interpolation.
"""
from __future__ import annotations

import pytest
from app.core.goal_feasibility import (
    Verdict,
    assess_goal,
    describe_assessment,
    parse_goal_time,
)


class TestParsingTheStatedGoal:
    @pytest.mark.parametrize(
        "text,seconds",
        [
            ("compléter en 2h ou moins", 7200),
            ("sous 2h", 7200),
            ("sub-2h half marathon", 7200),
            ("objectif 1h45", 6300),
            ("2h05", 7500),
            ("finir en 2:00", 7200),
            ("semi en 1h50 si possible", 6600),
        ],
    )
    def test_a_target_time_is_read(self, text: str, seconds: int) -> None:
        assert parse_goal_time(text) == seconds

    @pytest.mark.parametrize(
        "text",
        [
            "compléter le semi",
            "finir sans marcher",
            "demi-marathon Usti nad Labem",
            "",
        ],
    )
    def test_a_goal_without_a_time_yields_nothing(self, text: str) -> None:
        """"Finish it" is a real goal and must not become a fabricated time."""
        assert parse_goal_time(text) is None

    def test_a_race_date_is_not_read_as_a_time(self) -> None:
        assert parse_goal_time("semi le 19 septembre 2026") is None


class TestTheVerdict:
    def test_a_goal_within_reach_is_on_track(self) -> None:
        result = assess_goal(vdot=40.0, distance="half_marathon", goal_seconds=7200)

        assert result.verdict is Verdict.ON_TRACK

    def test_a_goal_just_beyond_current_fitness_is_ambitious(self) -> None:
        """Simon: VDOT 31 projects 2h20-ish, goal 2h00."""
        result = assess_goal(vdot=31.0, distance="half_marathon", goal_seconds=7200)

        assert result.verdict is Verdict.AMBITIOUS

    def test_a_goal_far_beyond_current_fitness_says_so(self) -> None:
        result = assess_goal(vdot=30.0, distance="half_marathon", goal_seconds=5400)

        assert result.verdict is Verdict.OUT_OF_REACH

    def test_no_vdot_means_no_verdict(self) -> None:
        """Guessing without a measured fitness would be worse than silence."""
        result = assess_goal(vdot=None, distance="half_marathon", goal_seconds=7200)

        assert result.verdict is Verdict.UNKNOWN

    def test_no_goal_time_means_no_verdict(self) -> None:
        result = assess_goal(vdot=31.0, distance="half_marathon", goal_seconds=None)

        assert result.verdict is Verdict.UNKNOWN


class TestTheNumbersItReports:
    def test_it_projects_from_the_current_vdot(self) -> None:
        result = assess_goal(vdot=30.0, distance="half_marathon", goal_seconds=7200)

        assert result.projected_seconds == 2 * 3600 + 24 * 60

    def test_it_names_the_vdot_the_goal_requires(self) -> None:
        result = assess_goal(vdot=31.0, distance="half_marathon", goal_seconds=7200)

        assert result.required_vdot == 35

    def test_it_offers_a_realistic_alternative(self) -> None:
        """The operator's choice: present both, let the athlete pick."""
        result = assess_goal(vdot=31.0, distance="half_marathon", goal_seconds=7200)

        assert result.realistic_seconds is not None
        assert result.realistic_seconds > 7200

    def test_an_on_track_goal_needs_no_alternative(self) -> None:
        result = assess_goal(vdot=40.0, distance="half_marathon", goal_seconds=7200)

        assert result.realistic_seconds is None


class TestWhatTheCoachIsTold:
    def test_an_ambitious_goal_asks_for_both_weeks(self) -> None:
        result = assess_goal(vdot=31.0, distance="half_marathon", goal_seconds=7200)
        text = describe_assessment(result)

        assert "2h" in text
        assert "deux" in text.lower() or "alternative" in text.lower()

    def test_it_says_the_signal_once(self) -> None:
        """Operator decision: flag it, then follow. Not a weekly lecture."""
        text = describe_assessment(
            assess_goal(vdot=31.0, distance="half_marathon", goal_seconds=7200)
        )

        assert "une seule fois" in text.lower() or "ne reviens pas" in text.lower()

    def test_an_unknown_verdict_says_nothing_to_the_athlete(self) -> None:
        text = describe_assessment(
            assess_goal(vdot=None, distance="half_marathon", goal_seconds=7200)
        )

        assert text == ""

    def test_an_on_track_goal_is_confirmed_not_hedged(self) -> None:
        text = describe_assessment(
            assess_goal(vdot=40.0, distance="half_marathon", goal_seconds=7200)
        )

        assert text
        assert "alternative" not in text.lower()
