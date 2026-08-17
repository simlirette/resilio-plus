"""D10 TDD — recovery_takeover graph (DEP-C3-002)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch


def _make_athlete(
    athlete_id: str = "a1",
    journey_phase: str = "steady_state",
) -> MagicMock:
    m = MagicMock()
    m.id = athlete_id
    m.journey_phase = journey_phase
    m.sports_json = '["running"]'
    m.primary_sport = "running"
    m.hours_per_week = 8.0
    m.coaching_mode = "full"
    m.clinical_context_flag = None
    m.active_recovery_thread_id = None
    m.recovery_takeover_active = False
    m.previous_journey_phase = None
    m.suspended_active_plan_id = None
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


class TestRecoveryTakeoverActivation:
    def test_start_sets_takeover_active(self):
        """run_recovery_takeover_start sets recovery_takeover_active=True."""
        from app.graphs.recovery_takeover import run_recovery_takeover_start

        athlete = _make_athlete(journey_phase="steady_state")
        db = _make_db(athlete)

        with patch("app.graphs.recovery_takeover.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm("Protocole proposé")
            result = run_recovery_takeover_start(
                athlete_id="a1",
                injury_message="genou douloureux",
                db=db,
            )

        assert result["recovery_takeover_active"] is True
        assert result["thread_id"] is not None
        assert "a1:recovery:" in result["thread_id"]
        assert result["step"] == "assess_injury"

    def test_previous_journey_phase_stored(self):
        """Previous journey_phase stored before overlay activation."""
        from app.graphs.recovery_takeover import run_recovery_takeover_start

        athlete = _make_athlete(journey_phase="steady_state")
        db = _make_db(athlete)

        with patch("app.graphs.recovery_takeover.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm()
            run_recovery_takeover_start("a1", "injury", db=db)

        assert athlete.previous_journey_phase == "steady_state"

    def test_plan_suspended_on_start(self):
        """Active plan ID stored as suspended_active_plan_id."""
        from app.graphs.recovery_takeover import run_recovery_takeover_start

        athlete = _make_athlete()
        athlete.active_plan_id = "plan-xyz"
        db = _make_db(athlete)

        with patch("app.graphs.recovery_takeover.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm()
            run_recovery_takeover_start("a1", "injury", db=db)

        assert athlete.suspended_active_plan_id == "plan-xyz"


class TestRecoveryTakeoverFlow:
    def test_respond_propose_protocol_advances_step(self):
        """Respond to assess_injury → advances to monitor_recovery."""
        from app.graphs.recovery_takeover import (
            run_recovery_takeover_respond,
            run_recovery_takeover_start,
        )

        athlete = _make_athlete()
        db = _make_db(athlete)

        with patch("app.graphs.recovery_takeover.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm()
            start = run_recovery_takeover_start("a1", "genou", db=db)

        thread_id = start["thread_id"]

        with patch("app.graphs.recovery_takeover.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm("Repos 5j")
            result = run_recovery_takeover_respond(thread_id, "ok", db=db)

        assert result["step"] == "monitor_recovery"

    def test_evaluate_readiness_proposes_return(self):
        """evaluate_readiness + propose_return_plan fused in one step (DEP-C3-002)."""
        from app.graphs.recovery_takeover import (
            run_recovery_takeover_respond,
            run_recovery_takeover_start,
        )

        athlete = _make_athlete()
        db = _make_db(athlete)

        with patch("app.graphs.recovery_takeover.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm()
            start = run_recovery_takeover_start("a1", "genou", db=db)

        thread_id = start["thread_id"]

        # assess_injury → monitor_recovery
        with patch("app.graphs.recovery_takeover.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm()
            run_recovery_takeover_respond(thread_id, "ok", db=db)

        # monitor_recovery with ready_to_return=True → evaluate_and_return step
        with patch("app.graphs.recovery_takeover.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm("Retour proposé")
            result = run_recovery_takeover_respond(
                thread_id, "je me sens mieux", db=db, ready_to_return=True
            )

        assert result["step"] == "evaluate_and_return"

    def test_handoff_to_baseline_from_steady_state(self):
        """Completing from steady_state → journey_phase=baseline_pending_confirmation."""
        from app.graphs.recovery_takeover import (
            run_recovery_takeover_respond,
            run_recovery_takeover_start,
        )

        athlete = _make_athlete(journey_phase="steady_state")
        db = _make_db(athlete)

        with patch("app.graphs.recovery_takeover.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm()
            start = run_recovery_takeover_start("a1", "genou", db=db)

        thread_id = start["thread_id"]

        # assess_injury
        with patch("app.graphs.recovery_takeover.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm()
            run_recovery_takeover_respond(thread_id, "ok", db=db)

        # monitor → evaluate_and_return
        with patch("app.graphs.recovery_takeover.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm()
            run_recovery_takeover_respond(thread_id, "mieux", db=db, ready_to_return=True)

        # confirm return → handoff
        with patch("app.graphs.recovery_takeover.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm()
            result = run_recovery_takeover_respond(thread_id, "je confirme", db=db)

        assert result["status"] == "completed"
        assert result.get("journey_phase") == "baseline_pending_confirmation"
        assert result.get("recovery_takeover_active") is False

    def test_handoff_from_onboarding_delegates_to_coordinator(self):
        """Completing from onboarding → returns previous_phase=onboarding for Coordinator."""
        from app.graphs.recovery_takeover import (
            run_recovery_takeover_respond,
            run_recovery_takeover_start,
        )

        athlete = _make_athlete(journey_phase="onboarding")
        db = _make_db(athlete)

        with patch("app.graphs.recovery_takeover.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm()
            start = run_recovery_takeover_start("a1", "blessure", db=db)

        thread_id = start["thread_id"]

        # Fast-track through all steps
        with patch("app.graphs.recovery_takeover.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm()
            run_recovery_takeover_respond(thread_id, "ok", db=db)

        with patch("app.graphs.recovery_takeover.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm()
            run_recovery_takeover_respond(thread_id, "mieux", db=db, ready_to_return=True)

        with patch("app.graphs.recovery_takeover.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm()
            result = run_recovery_takeover_respond(thread_id, "confirme", db=db)

        assert result.get("previous_journey_phase") == "onboarding"
