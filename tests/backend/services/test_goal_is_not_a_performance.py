"""A goal time must never be mistaken for a race result.

Probed against the live extractor on 2026-08-21. Given a transcript where the
athlete says "objectif demi marathon le 19 septembre, sous 2h" and, separately,
"5km: 26min47s, 10km: 1h04min43s", the model returned:

    "race_distance": 21097.5,
    "race_time_seconds": 7200

That is the *target* distance in metres and the *goal* time in seconds. The
athlete has never run a half marathon. Had it been accepted, VDOT would have
been derived from a performance that does not exist, and every prescribed pace
for the block would have come from it -- an athlete at VDOT 33 training at the
paces of VDOT 37.

`_derive_vdot` refused it, but only incidentally: 21097.5 is not a string in
the distance table. A guard that holds by accident is not a guard, so this
pins the actual rule.

Two more defects from the same probe, both fixed in the prompt:

  - `target_race_date: "2024-09-19"` — the extractor had no date anchor and
    guessed the year.
  - `sports: ["strength training"]` — outside the enum, so silently dropped.
"""
from __future__ import annotations

from datetime import date

from app.services.conversation import Turn
from app.services.onboarding_extraction import (
    _PROFILE_PROMPT,
    _derive_vdot,
    build_profile_transcript,
)


def _turn(role: str, content: str) -> Turn:
    from datetime import datetime, timezone

    return Turn(role=role, content=content, created_at=datetime.now(timezone.utc))


class TestAGoalIsNotAResult:
    def test_a_distance_in_metres_is_refused(self) -> None:
        """The live failure: the target distance arrived as a number."""
        assert _derive_vdot({"race_distance": 21097.5, "race_time_seconds": 7200}) is None

    def test_a_goal_shaped_like_a_result_cannot_be_caught_here(self) -> None:
        """States the limit of this layer rather than pretending it has none.

        "Semi en 2h" as a goal and "semi couru en 2h" as a result are the same
        two numbers. `_derive_vdot` has no way to tell them apart, so it will
        accept either. The distinction lives in the prompt, pinned below --
        which is why the prompt rules are tested and not just written.
        """
        assert _derive_vdot(
            {"race_distance": "half_marathon", "race_time_seconds": 7200}
        ) is not None

    def test_a_real_result_still_produces_a_vdot(self) -> None:
        """The guard must not be so tight that nothing gets through."""
        assert _derive_vdot({"race_distance": "5k", "race_time_seconds": 1607}) == 35.0

    def test_the_ten_k_result_produces_its_vdot(self) -> None:
        assert _derive_vdot({"race_distance": "10k", "race_time_seconds": 3883}) == 31.0


class TestThePromptSaysSo:
    """The parser guard is the backstop; the prompt is the actual fix."""

    def test_it_names_the_allowed_distances(self) -> None:
        for label in ("5k", "10k", "half_marathon", "marathon"):
            assert label in _PROFILE_PROMPT

    def test_it_forbids_using_the_goal_as_a_result(self) -> None:
        lowered = _PROFILE_PROMPT.lower()
        assert "goal" in lowered
        assert "already" in lowered or "completed" in lowered

    def test_it_names_the_sports_enum(self) -> None:
        """"strength training" was dropped because it is not a known value."""
        for sport in ("running", "lifting", "swimming", "biking"):
            assert sport in _PROFILE_PROMPT


class TestTheTranscriptCarriesToday:
    def test_todays_date_is_in_the_transcript(self) -> None:
        """Without it the extractor guessed 2024 for a 2026 race."""
        transcript = build_profile_transcript(
            [_turn("user", "semi le 19 septembre")], today=date(2026, 8, 21)
        )

        assert "2026-08-21" in transcript

    def test_the_turns_are_all_there(self) -> None:
        transcript = build_profile_transcript(
            [
                _turn("assistant", "Décris-toi."),
                _turn("user", "Course et lifting"),
            ],
            today=date(2026, 8, 21),
        )

        assert "Décris-toi." in transcript
        assert "Course et lifting" in transcript

    def test_roles_are_labelled_for_the_reader(self) -> None:
        transcript = build_profile_transcript(
            [_turn("user", "Salut")], today=date(2026, 8, 21)
        )

        assert "ATHLETE" in transcript

    def test_an_empty_conversation_still_carries_the_date(self) -> None:
        assert "2026-08-21" in build_profile_transcript([], today=date(2026, 8, 21))
