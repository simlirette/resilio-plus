"""D8 TDD — onboarding blocs 4-6, handoff, blessure mid-onboarding (DEP-C3-003)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch


def _make_athlete(
    athlete_id: str = "a1",
    thread_id: str | None = None,
) -> MagicMock:
    m = MagicMock()
    m.id = athlete_id
    m.journey_phase = "onboarding"
    m.sports_json = '["running", "lifting"]'
    m.primary_sport = "running"
    m.hours_per_week = 8.0
    m.coaching_mode = "full"
    m.clinical_context_flag = None
    m.active_onboarding_thread_id = thread_id
    m.suspended_onboarding_block = None
    return m


def _mock_llm(text: str = "question") -> MagicMock:
    block = MagicMock()
    block.text = text
    msg = MagicMock()
    msg.content = [block]
    return msg


def _make_db(athlete: MagicMock) -> MagicMock:
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = athlete
    return db


def _run_through_blocks(thread_id: str, db: MagicMock, up_to_block: int) -> None:
    """Helper: advance through onboarding blocks up to (but not including) given block."""
    from app.graphs.onboarding import run_onboarding_respond

    for _ in range(up_to_block - 1):
        with patch("app.graphs.onboarding.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm()
            run_onboarding_respond(thread_id, "response", db=db)


# Changed 2026-08-21 (Phase B1). Onboarding no longer ends after a fixed six
# blocks: it ends when the profile can support a plan and the athlete has
# confirmed the summary. The six fixed instructions were what made the coach
# ask for running volume in blocks 3, 4 *and* 5 after it had already been told.
# `_MAX_BLOCK` is now a ceiling, not a schedule -- these tests drive to it so
# they still exercise the handoff.


class TestOnboardingBlocs4to6:
    def test_bloc4_sports_history(self):
        """Bloc 4 reachable after bloc 3; collects sport_history key."""
        from app.graphs.onboarding import run_onboarding_respond, run_onboarding_start

        athlete = _make_athlete()
        db = _make_db(athlete)

        with patch("app.graphs.onboarding.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm()
            start = run_onboarding_start("a1", db)

        thread_id = start["thread_id"]
        _run_through_blocks(thread_id, db, up_to_block=4)  # advance to block 4

        with patch("app.graphs.onboarding.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm("Préférences?")
            result = run_onboarding_respond(thread_id, "3 ans running", db=db)

        assert result["current_block"] == 5
        assert result["collected_data"].get("sport_history") == "3 ans running"

    def test_bloc5_methodology_preferences(self):
        """Bloc 5 collects methodology_preferences (DEP-C4-002)."""
        from app.graphs.onboarding import run_onboarding_respond, run_onboarding_start

        athlete = _make_athlete()
        db = _make_db(athlete)

        with patch("app.graphs.onboarding.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm()
            start = run_onboarding_start("a1", db)

        thread_id = start["thread_id"]
        _run_through_blocks(thread_id, db, up_to_block=5)

        with patch("app.graphs.onboarding.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm("Confirmation?")
            result = run_onboarding_respond(thread_id, "DUP, 3x/semaine", db=db)

        assert result["current_block"] == 6
        assert result["collected_data"].get("methodology_preferences") == "DUP, 3x/semaine"

    def test_bloc6_confirmation_triggers_handoff(self):
        """Completing bloc 6 sets journey_phase to baseline_pending_confirmation."""
        from app.graphs.onboarding import run_onboarding_respond, run_onboarding_start

        athlete = _make_athlete()
        db = _make_db(athlete)

        with patch("app.graphs.onboarding.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm()
            start = run_onboarding_start("a1", db)

        thread_id = start["thread_id"]
        from app.graphs.onboarding import _MAX_BLOCK

        _run_through_blocks(thread_id, db, up_to_block=_MAX_BLOCK)

        with patch("app.graphs.onboarding.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm()
            result = run_onboarding_respond(thread_id, "oui, je confirme", db=db)

        assert result["status"] == "completed"
        assert result.get("journey_phase") == "baseline_pending_confirmation"

    def test_the_ceiling_always_reaches_a_handoff(self):
        """Even with nothing extracted, the athlete reaches a plan eventually.

        The ceiling exists so a stubborn extraction failure cannot turn
        onboarding into an interrogation with no exit.
        """
        from app.graphs.onboarding import run_onboarding_respond, run_onboarding_start

        athlete = _make_athlete()
        db = _make_db(athlete)

        with patch("app.graphs.onboarding.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm()
            start = run_onboarding_start("a1", db)

        thread_id = start["thread_id"]
        from app.graphs.onboarding import _MAX_BLOCK

        with patch("app.graphs.onboarding.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm()
            result = run_onboarding_respond(thread_id, "intro", db=db)

        for _ in range(_MAX_BLOCK):
            if result["status"] == "completed":
                break
            with patch("app.graphs.onboarding.anthropic.Anthropic") as M:
                M.return_value.messages.create.return_value = _mock_llm()
                result = run_onboarding_respond(thread_id, "reponse", db=db)

        assert result["status"] == "completed", "the ceiling never fired"
        assert result.get("journey_phase") == "baseline_pending_confirmation"
        assert result["collected_data"]["intro_response"] == "intro"


class TestInjuryMidOnboarding:
    def test_suspend_onboarding_bloc_on_injury(self):
        """Injury during bloc 3 stores suspended_onboarding_block=3."""
        from app.graphs.onboarding import (
            run_onboarding_start,
            suspend_onboarding_for_injury,
        )

        athlete = _make_athlete()
        db = _make_db(athlete)

        with patch("app.graphs.onboarding.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm()
            start = run_onboarding_start("a1", db)

        thread_id = start["thread_id"]
        _run_through_blocks(thread_id, db, up_to_block=3)  # advance to block 3

        # Simulate injury event during bloc 3
        suspend_onboarding_for_injury(thread_id=thread_id, db=db)

        assert athlete.suspended_onboarding_block == 3

    def test_resume_after_recovery_returns_to_suspended_block(self):
        """Post-takeover with previous_phase=onboarding → resumes suspended block."""
        from app.graphs.onboarding import resume_onboarding_after_recovery

        athlete = _make_athlete()
        athlete.suspended_onboarding_block = 3
        athlete.active_onboarding_thread_id = "a1:onboarding:test-resume"
        db = _make_db(athlete)

        # Pre-populate thread state at block 3
        from app.graphs.onboarding import _OnboardingThread, _thread_states
        thread_id = "a1:onboarding:test-resume"
        _thread_states[thread_id] = _OnboardingThread(
            thread_id=thread_id,
            athlete_id="a1",
            current_block=3,
            collected_data={"intro_response": "x", "basic_profile": "y"},
            status="suspended",
        )

        with patch("app.graphs.onboarding.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm("Bloc 3 reprise")
            result = resume_onboarding_after_recovery(athlete_id="a1", db=db)

        assert result["current_block"] == 3
        assert result["status"] == "in_progress"

        # Cleanup
        _thread_states.pop(thread_id, None)

    def test_injury_from_baseline_goes_to_baseline_not_onboarding(self):
        """Injury from baseline_active previous_phase → post-takeover NOT onboarding."""
        from app.graphs.onboarding import resume_onboarding_after_recovery

        athlete = _make_athlete()
        athlete.journey_phase = "baseline_active"
        athlete.suspended_onboarding_block = None
        db = _make_db(athlete)

        result = resume_onboarding_after_recovery(athlete_id="a1", db=db)

        # No suspended block → returns None (handled by CoordinatorService)
        assert result is None
