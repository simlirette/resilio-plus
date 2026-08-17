"""D12 E2E — Phase D conversation flow integration tests.

Tests complete multi-step flows mocking only LLM calls (no real Anthropic API).
All DB interactions use MagicMock.

Flows covered:
  Flow 1: chat HEAD_COACH_DIRECT (classify → respond)
  Flow 2: chat SPECIALIST_TECHNICAL chain (2 specialists)
  Flow 3: injury report → recovery_takeover activation
  Flow 4: onboarding 6-bloc complete → baseline_pending_confirmation
  Flow 5: onboarding injury mid-bloc → suspend → recovery → resume
  Flow 6: followup baseline_active → steady_state
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch


def _make_athlete(
    athlete_id: str = "a1",
    journey_phase: str = "steady_state",
) -> MagicMock:
    m = MagicMock()
    m.id = athlete_id
    m.journey_phase = journey_phase
    m.sports_json = '["running", "lifting"]'
    m.primary_sport = "running"
    m.hours_per_week = 10.0
    m.coaching_mode = "full"
    m.clinical_context_flag = None
    m.active_onboarding_thread_id = None
    m.active_recovery_thread_id = None
    m.active_followup_thread_id = None
    m.recovery_takeover_active = False
    m.suspended_onboarding_block = None
    m.previous_journey_phase = None
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


class TestChatHeadCoachDirect:
    def test_head_coach_direct_flow(self):
        """Flow 1: classify → HEAD_COACH_DIRECT → head coach responds, 0 specialists."""
        from app.graphs.chat_turn import run_chat_turn

        athlete = _make_athlete()
        db = _make_db(athlete)

        # Mock IntentClassification → HEAD_COACH_DIRECT
        mock_intent = MagicMock()
        mock_intent.decision = "HEAD_COACH_DIRECT"
        mock_intent.specialist_chain = None
        mock_intent.clinical_escalation_type = None
        mock_intent.clarification_axes = None
        mock_intent.clinical_context_active_acknowledged = False

        with (
            patch("app.graphs.chat_turn._get_athlete", return_value=athlete),
            patch("app.graphs.chat_turn.classify_intent", return_value=mock_intent),
            patch("app.graphs.chat_turn._persist_messages"),
            patch("app.graphs.chat_turn.anthropic.Anthropic") as M,
        ):
            M.return_value.messages.create.return_value = _mock_llm("Réponse HC directe")
            result = run_chat_turn(
                athlete_id="a1",
                user_message="Comment améliorer ma récupération?",
                db=db,
                last_3_intents=[],
            )

        assert result["intent_decision"] == "HEAD_COACH_DIRECT"
        assert result["specialists_consulted"] == []
        assert result["final_response"] == "Réponse HC directe"
        assert result["thread_id"] is None


class TestChatSpecialistChain:
    def test_specialist_chain_2_specialists(self):
        """Flow 2: SPECIALIST_TECHNICAL chain with 2 specialists."""
        from app.graphs.chat_turn import run_chat_turn

        athlete = _make_athlete()
        db = _make_db(athlete)

        spec1 = MagicMock()
        spec1.specialist = "running"
        spec2 = MagicMock()
        spec2.specialist = "nutrition"

        mock_intent = MagicMock()
        mock_intent.decision = "SPECIALIST_TECHNICAL"
        mock_intent.specialist_chain = [spec1, spec2]
        mock_intent.clinical_escalation_type = None
        mock_intent.clarification_axes = None
        mock_intent.clinical_context_active_acknowledged = False

        call_count = 0

        def _llm_side_effect(**kwargs: object) -> MagicMock:
            nonlocal call_count
            call_count += 1
            responses = ["Running notes", "Nutrition notes", "HC synthesis"]
            return _mock_llm(responses[min(call_count - 1, 2)])

        with (
            patch("app.graphs.chat_turn._get_athlete", return_value=athlete),
            patch("app.graphs.chat_turn.classify_intent", return_value=mock_intent),
            patch("app.graphs.chat_turn._persist_messages"),
            patch("app.graphs.chat_turn.anthropic.Anthropic") as M,
        ):
            M.return_value.messages.create.side_effect = _llm_side_effect
            result = run_chat_turn(
                athlete_id="a1",
                user_message="Plan course + nutrition?",
                db=db,
                last_3_intents=[],
            )

        assert result["intent_decision"] == "SPECIALIST_TECHNICAL"
        assert "running" in result["specialists_consulted"]
        assert "nutrition" in result["specialists_consulted"]
        assert len(result["specialists_consulted"]) == 2


class TestInjuryToRecoveryTakeover:
    def test_injury_report_activates_takeover(self):
        """Flow 3: injury report → run_injury_report → run_recovery_takeover_start."""
        from app.graphs.chat_turn import run_injury_report
        from app.graphs.recovery_takeover import run_recovery_takeover_start

        athlete = _make_athlete()
        db = _make_db(athlete)

        # Step 1: run_injury_report → escalate_to_takeover
        with (
            patch("app.graphs.chat_turn.anthropic.Anthropic") as M,
            patch("app.graphs.chat_turn._get_athlete", return_value=athlete),
            patch("app.graphs.chat_turn._persist_messages"),
        ):
            M.return_value.messages.create.return_value = _mock_llm(
                "action: escalate_to_takeover\ninjury_payload_draft: {}"
            )
            injury_result = run_injury_report(
                athlete_id="a1",
                user_message="genou douloureux",
                db=db,
            )

        assert injury_result["takeover_requested"] is True

        # Step 2: activate recovery_takeover overlay
        with patch("app.graphs.recovery_takeover.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm("Protocole")
            takeover_result = run_recovery_takeover_start(
                athlete_id="a1",
                injury_message="genou douloureux",
                db=db,
            )

        assert takeover_result["recovery_takeover_active"] is True
        assert athlete.previous_journey_phase == "steady_state"


class TestOnboardingCompleteFlow:
    def test_onboarding_6_blocs_to_baseline(self):
        """Flow 4: 6 onboarding blocs → journey_phase=baseline_pending_confirmation."""
        from app.graphs.onboarding import run_onboarding_respond, run_onboarding_start

        athlete = _make_athlete(journey_phase="onboarding")
        db = _make_db(athlete)

        with patch("app.graphs.onboarding.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm()
            start = run_onboarding_start("a1", db)

        thread_id = start["thread_id"]
        responses = ["intro", "25ans/70kg", "semi 6mois", "3ans running", "DUP"]

        for resp in responses:
            with patch("app.graphs.onboarding.anthropic.Anthropic") as M:
                M.return_value.messages.create.return_value = _mock_llm()
                run_onboarding_respond(thread_id, resp, db=db)

        with patch("app.graphs.onboarding.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm()
            final = run_onboarding_respond(thread_id, "confirme", db=db)

        assert final["status"] == "completed"
        assert final.get("journey_phase") == "baseline_pending_confirmation"

    def test_onboarding_injury_mid_flow_suspend_and_resume(self):
        """Flow 5: injury during bloc 3 → suspend → recovery → resume bloc 3."""
        from app.graphs.onboarding import (
            run_onboarding_respond,
            run_onboarding_start,
            suspend_onboarding_for_injury,
            resume_onboarding_after_recovery,
            _thread_states,
        )

        athlete = _make_athlete(journey_phase="onboarding")
        db = _make_db(athlete)

        # Start and advance to block 3
        with patch("app.graphs.onboarding.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm()
            start = run_onboarding_start("a1", db)

        thread_id = start["thread_id"]

        # Block 1 response → block 2
        with patch("app.graphs.onboarding.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm()
            run_onboarding_respond(thread_id, "intro", db=db)

        # Block 2 response → block 3
        with patch("app.graphs.onboarding.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm()
            run_onboarding_respond(thread_id, "25ans", db=db)

        # Now at block 3 — injury event
        suspend_onboarding_for_injury(thread_id=thread_id, db=db)
        assert getattr(athlete, "suspended_onboarding_block") == 3

        # Recovery takeover happens (external); then resume
        with patch("app.graphs.onboarding.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm("Bloc 3 reprise")
            resumed = resume_onboarding_after_recovery(athlete_id="a1", db=db)

        assert resumed is not None
        assert resumed["current_block"] == 3
        assert resumed["status"] == "in_progress"

        # Cleanup
        _thread_states.pop(thread_id, None)


class TestFollowupTransitionFlow:
    def test_followup_baseline_to_steady_state(self):
        """Flow 6: followup_transition 2 interrupts → journey_phase=steady_state."""
        from app.graphs.followup_transition import run_followup_respond, run_followup_start

        athlete = _make_athlete(journey_phase="baseline_active")
        db = _make_db(athlete)

        with patch("app.graphs.followup_transition.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm("Résultats")
            start = run_followup_start("a1", db)

        thread_id = start["thread_id"]
        assert start["step"] == "present_baseline"

        with patch("app.graphs.followup_transition.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm("Confirmation?")
            step2 = run_followup_respond(thread_id, "satisfait", db=db)

        assert step2["step"] == "confirm_first_plan"

        with patch("app.graphs.followup_transition.anthropic.Anthropic") as M:
            M.return_value.messages.create.return_value = _mock_llm()
            final = run_followup_respond(thread_id, "je confirme", db=db)

        assert final["status"] == "completed"
        assert final.get("journey_phase") == "steady_state"
        assert athlete.journey_phase == "steady_state"
