"""D9 TDD — followup_transition graph (baseline_active → steady_state)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch


def _make_athlete(
    athlete_id: str = "a1",
    journey_phase: str = "baseline_active",
    thread_id: str | None = None,
) -> MagicMock:
    m = MagicMock()
    m.id = athlete_id
    m.journey_phase = journey_phase
    m.sports_json = '["running"]'
    m.primary_sport = "running"
    m.hours_per_week = 8.0
    m.coaching_mode = "full"
    m.clinical_context_flag = None
    m.active_followup_thread_id = thread_id
    return m


def _mock_llm(text: str = "response") -> MagicMock:
    block = MagicMock()
    block.text = text
    msg = MagicMock()
    msg.content = [block]
    return msg


def _make_db(athlete: MagicMock) -> MagicMock:
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = athlete
    return db


class TestFollowupTransitionNominal:
    def test_start_followup_creates_thread(self):
        """run_followup_start creates thread and returns baseline_summary question."""
        from app.graphs.followup_transition import run_followup_start

        athlete = _make_athlete()
        db = _make_db(athlete)

        with patch("app.graphs.followup_transition.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm("Résultats baseline")
            result = run_followup_start(athlete_id="a1", db=db)

        assert result["thread_id"] is not None
        assert "a1:followup:" in result["thread_id"]
        assert result["step"] == "present_baseline"
        assert result["status"] == "in_progress"

    def test_thread_id_stored_on_athlete(self):
        """After start, athlete.active_followup_thread_id is set."""
        from app.graphs.followup_transition import run_followup_start

        athlete = _make_athlete()
        db = _make_db(athlete)

        with patch("app.graphs.followup_transition.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm()
            result = run_followup_start(athlete_id="a1", db=db)

        assert athlete.active_followup_thread_id == result["thread_id"]

    def test_respond_to_feedback_advances_to_confirm(self):
        """Athlete feedback response → advances to confirm_first_plan step."""
        from app.graphs.followup_transition import run_followup_respond, run_followup_start

        athlete = _make_athlete()
        db = _make_db(athlete)

        with patch("app.graphs.followup_transition.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm()
            start = run_followup_start("a1", db)

        thread_id = start["thread_id"]

        with patch("app.graphs.followup_transition.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm("Confirmation?")
            result = run_followup_respond(
                thread_id=thread_id,
                user_response="Satisfait du baseline",
                db=db,
            )

        assert result["step"] == "confirm_first_plan"
        assert result["status"] == "in_progress"

    def test_confirm_triggers_steady_state(self):
        """Confirming first plan → journey_phase=steady_state."""
        from app.graphs.followup_transition import run_followup_respond, run_followup_start

        athlete = _make_athlete()
        db = _make_db(athlete)

        with patch("app.graphs.followup_transition.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm()
            start = run_followup_start("a1", db)

        thread_id = start["thread_id"]

        # Step 1: feedback
        with patch("app.graphs.followup_transition.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm()
            run_followup_respond(thread_id, "bon baseline", db=db)

        # Step 2: confirm
        with patch("app.graphs.followup_transition.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm()
            result = run_followup_respond(thread_id, "je confirme", db=db)

        assert result["status"] == "completed"
        assert result.get("journey_phase") == "steady_state"
        assert athlete.journey_phase == "steady_state"


class TestFollowupTransitionAdjustment:
    def test_objective_adjustment_sets_reentry_overlay(self):
        """Feedback signals objective change → onboarding_reentry_active=True."""
        from app.graphs.followup_transition import run_followup_respond, run_followup_start

        athlete = _make_athlete()
        db = _make_db(athlete)

        with patch("app.graphs.followup_transition.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm()
            start = run_followup_start("a1", db)

        thread_id = start["thread_id"]

        # Respond with adjustment signal
        with patch("app.graphs.followup_transition.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm()
            result = run_followup_respond(
                thread_id=thread_id,
                user_response="Je veux changer mon objectif",
                db=db,
                adjust_objective=True,  # explicit signal for test
            )

        assert result.get("onboarding_reentry_active") is True

    def test_invalid_thread_raises(self):
        """Unknown thread_id raises ValueError."""
        from app.graphs.followup_transition import run_followup_respond

        import pytest

        with pytest.raises(ValueError, match="not found"):
            run_followup_respond(
                thread_id="no-such-thread",
                user_response="...",
                db=MagicMock(),
            )
