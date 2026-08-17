"""D4 TDD — chat_turn graph (HEAD_COACH_DIRECT + SPECIALIST_TECHNICAL single + handle_session_log)."""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _make_athlete(
    athlete_id: str = "a1",
    journey_phase: str = "steady_state",
    sports: list[str] | None = None,
) -> MagicMock:
    """Return a minimal AthleteModel mock with all fields required by HeadCoachView."""
    m = MagicMock()
    m.id = athlete_id
    m.journey_phase = journey_phase
    m.sports_json = f'["{(sports or ["running"])[0]}"]'
    m.primary_sport = (sports or ["running"])[0]
    m.hours_per_week = 8.0
    m.coaching_mode = "full"
    m.clinical_context_flag = None
    return m


def _mock_classify(decision: str, specialist_chain=None, **kwargs) -> MagicMock:
    """Return a mock IntentClassification."""
    from app.schemas.intent import IntentClassification, SpecialistTarget
    chain = None
    if specialist_chain:
        chain = [SpecialistTarget(specialist=s, reason="test") for s in specialist_chain]
    return IntentClassification(
        decision=decision,
        specialist_chain=chain,
        clinical_escalation_type=None,
        clarification_axes=None,
        confidence=0.9,
        reasoning="test",
        language_detected="fr",
        clinical_context_active_acknowledged=False,
        **kwargs,
    )


def _mock_llm_response(text: str = "Réponse Head Coach.") -> MagicMock:
    block = MagicMock()
    block.text = text
    msg = MagicMock()
    msg.content = [block]
    return msg


# ─── HEAD_COACH_DIRECT ────────────────────────────────────────────────────────

class TestHeadCoachDirect:
    def test_head_coach_direct_returns_response(self):
        """HEAD_COACH_DIRECT: classify → head coach responds, no specialist invoked."""
        from app.graphs.chat_turn import run_chat_turn

        intent = _mock_classify("HEAD_COACH_DIRECT")
        athlete = _make_athlete()
        llm_resp = _mock_llm_response("Bonjour, voici ma réponse.")

        with (
            patch("app.graphs.chat_turn.classify_intent", return_value=intent),
            patch("app.graphs.chat_turn.anthropic.Anthropic") as MockClient,
            patch("app.graphs.chat_turn._get_athlete", return_value=athlete),
            patch("app.graphs.chat_turn._persist_messages"),
        ):
            MockClient.return_value.messages.create.return_value = llm_resp
            result = run_chat_turn(
                athlete_id="a1",
                user_message="bonjour",
                db=MagicMock(),
                last_3_intents=[],
            )

        assert result["final_response"] == "Bonjour, voici ma réponse."
        assert result["intent_decision"] == "HEAD_COACH_DIRECT"

    def test_head_coach_direct_single_llm_call(self):
        """HEAD_COACH_DIRECT makes exactly 1 LLM call (no specialist)."""
        from app.graphs.chat_turn import run_chat_turn

        intent = _mock_classify("HEAD_COACH_DIRECT")
        athlete = _make_athlete()
        llm_resp = _mock_llm_response("réponse")

        with (
            patch("app.graphs.chat_turn.classify_intent", return_value=intent),
            patch("app.graphs.chat_turn.anthropic.Anthropic") as MockClient,
            patch("app.graphs.chat_turn._get_athlete", return_value=athlete),
            patch("app.graphs.chat_turn._persist_messages"),
        ):
            MockClient.return_value.messages.create.return_value = llm_resp
            run_chat_turn(athlete_id="a1", user_message="test", db=MagicMock(), last_3_intents=[])
            assert MockClient.return_value.messages.create.call_count == 1


# ─── SPECIALIST_TECHNICAL single ─────────────────────────────────────────────

class TestSpecialistTechnicalSingle:
    def test_specialist_invoked_and_hc_synthesizes(self):
        """SPECIALIST_TECHNICAL single: specialist invoked, then Head Coach synthesizes."""
        from app.graphs.chat_turn import run_chat_turn

        intent = _mock_classify("SPECIALIST_TECHNICAL", specialist_chain=["nutrition"])
        athlete = _make_athlete()
        specialist_resp = _mock_llm_response("Réponse nutrition.")
        hc_synth = _mock_llm_response("Synthèse Head Coach.")

        with (
            patch("app.graphs.chat_turn.classify_intent", return_value=intent),
            patch("app.graphs.chat_turn.anthropic.Anthropic") as MockClient,
            patch("app.graphs.chat_turn._get_athlete", return_value=athlete),
            patch("app.graphs.chat_turn._persist_messages"),
        ):
            MockClient.return_value.messages.create.side_effect = [specialist_resp, hc_synth]
            result = run_chat_turn(
                athlete_id="a1",
                user_message="créatine ?",
                db=MagicMock(),
                last_3_intents=[],
            )

        assert result["final_response"] == "Synthèse Head Coach."
        assert result["intent_decision"] == "SPECIALIST_TECHNICAL"

    def test_specialist_technical_two_llm_calls(self):
        """SPECIALIST_TECHNICAL single: 2 LLM calls (specialist + HC synthesis)."""
        from app.graphs.chat_turn import run_chat_turn

        intent = _mock_classify("SPECIALIST_TECHNICAL", specialist_chain=["lifting"])
        athlete = _make_athlete()

        with (
            patch("app.graphs.chat_turn.classify_intent", return_value=intent),
            patch("app.graphs.chat_turn.anthropic.Anthropic") as MockClient,
            patch("app.graphs.chat_turn._get_athlete", return_value=athlete),
            patch("app.graphs.chat_turn._persist_messages"),
        ):
            MockClient.return_value.messages.create.return_value = _mock_llm_response("r")
            run_chat_turn(athlete_id="a1", user_message="squat ?", db=MagicMock(), last_3_intents=[])
            assert MockClient.return_value.messages.create.call_count == 2

    def test_specialist_name_in_result(self):
        """Result includes which specialist was consulted."""
        from app.graphs.chat_turn import run_chat_turn

        intent = _mock_classify("SPECIALIST_TECHNICAL", specialist_chain=["running"])
        athlete = _make_athlete()

        with (
            patch("app.graphs.chat_turn.classify_intent", return_value=intent),
            patch("app.graphs.chat_turn.anthropic.Anthropic") as MockClient,
            patch("app.graphs.chat_turn._get_athlete", return_value=athlete),
            patch("app.graphs.chat_turn._persist_messages"),
        ):
            MockClient.return_value.messages.create.return_value = _mock_llm_response("r")
            result = run_chat_turn(
                athlete_id="a1", user_message="allure ?", db=MagicMock(), last_3_intents=[]
            )

        assert result["specialists_consulted"] == ["running"]


# ─── handle_session_log (DEP-C4-001) ─────────────────────────────────────────

class TestHandleSessionLog:
    def _run_session_log(self, rpe_actual: float | None, rpe_prescribed: float) -> dict:
        from app.graphs.chat_turn import run_chat_turn

        intent = _mock_classify(
            "SPECIALIST_TECHNICAL",
            specialist_chain=["lifting"],
        )
        # Override: simulate session_log trigger via payload
        athlete = _make_athlete()

        with (
            patch("app.graphs.chat_turn.classify_intent", return_value=intent),
            patch("app.graphs.chat_turn.anthropic.Anthropic") as MockClient,
            patch("app.graphs.chat_turn._get_athlete", return_value=athlete),
            patch("app.graphs.chat_turn._persist_messages"),
        ):
            MockClient.return_value.messages.create.return_value = _mock_llm_response("r")
            return run_chat_turn(
                athlete_id="a1",
                user_message="j'ai fini ma séance",
                db=MagicMock(),
                last_3_intents=[],
                session_log_context={
                    "rpe_actual": rpe_actual,
                    "rpe_prescribed": rpe_prescribed,
                    "recent_elevated_rpe_count": 0,
                },
            )

    def test_lifting_consulted_when_rpe_deviation_above_threshold(self):
        """Lifting consulted when RPE actual ≥ prescribed + 1.5."""
        result = self._run_session_log(rpe_actual=8.5, rpe_prescribed=7.0)
        assert "lifting" in result["specialists_consulted"]

    def test_lifting_not_consulted_below_threshold(self):
        """Lifting NOT consulted when RPE deviation < 1.5."""
        from app.graphs.chat_turn import run_chat_turn

        intent = _mock_classify("HEAD_COACH_DIRECT")
        athlete = _make_athlete()

        with (
            patch("app.graphs.chat_turn.classify_intent", return_value=intent),
            patch("app.graphs.chat_turn.anthropic.Anthropic") as MockClient,
            patch("app.graphs.chat_turn._get_athlete", return_value=athlete),
            patch("app.graphs.chat_turn._persist_messages"),
        ):
            MockClient.return_value.messages.create.return_value = _mock_llm_response("r")
            result = run_chat_turn(
                athlete_id="a1",
                user_message="j'ai fini ma séance",
                db=MagicMock(),
                last_3_intents=[],
                session_log_context={
                    "rpe_actual": 7.5,
                    "rpe_prescribed": 7.0,  # delta = 0.5 < 1.5
                    "recent_elevated_rpe_count": 0,
                },
            )

        assert result["specialists_consulted"] == []
        assert MockClient.return_value.messages.create.call_count == 1

    def test_lifting_consulted_when_pattern_two_sessions(self):
        """Lifting consulted when recent_elevated_rpe_count >= 2 (pattern rule)."""
        from app.graphs.chat_turn import run_chat_turn

        intent = _mock_classify("HEAD_COACH_DIRECT")
        athlete = _make_athlete()

        with (
            patch("app.graphs.chat_turn.classify_intent", return_value=intent),
            patch("app.graphs.chat_turn.anthropic.Anthropic") as MockClient,
            patch("app.graphs.chat_turn._get_athlete", return_value=athlete),
            patch("app.graphs.chat_turn._persist_messages"),
        ):
            MockClient.return_value.messages.create.return_value = _mock_llm_response("r")
            result = run_chat_turn(
                athlete_id="a1",
                user_message="j'ai fini",
                db=MagicMock(),
                last_3_intents=[],
                session_log_context={
                    "rpe_actual": 7.0,
                    "rpe_prescribed": 7.0,  # delta = 0.0
                    "recent_elevated_rpe_count": 2,  # pattern: 2 sessions trigger
                },
            )

        assert "lifting" in result["specialists_consulted"]


# ─── Thread lifecycle ─────────────────────────────────────────────────────────

class TestChatTurnEphemeral:
    def test_no_thread_id_in_result(self):
        """chat_turn is ephemeral: result should not expose a persistent thread_id."""
        from app.graphs.chat_turn import run_chat_turn

        intent = _mock_classify("HEAD_COACH_DIRECT")
        athlete = _make_athlete()

        with (
            patch("app.graphs.chat_turn.classify_intent", return_value=intent),
            patch("app.graphs.chat_turn.anthropic.Anthropic") as MockClient,
            patch("app.graphs.chat_turn._get_athlete", return_value=athlete),
            patch("app.graphs.chat_turn._persist_messages"),
        ):
            MockClient.return_value.messages.create.return_value = _mock_llm_response("r")
            result = run_chat_turn(
                athlete_id="a1", user_message="test", db=MagicMock(), last_3_intents=[]
            )

        assert "thread_id" not in result or result.get("thread_id") is None

    def test_messages_persisted(self):
        """_persist_messages is called once per turn."""
        from app.graphs.chat_turn import run_chat_turn

        intent = _mock_classify("HEAD_COACH_DIRECT")
        athlete = _make_athlete()

        with (
            patch("app.graphs.chat_turn.classify_intent", return_value=intent),
            patch("app.graphs.chat_turn.anthropic.Anthropic") as MockClient,
            patch("app.graphs.chat_turn._get_athlete", return_value=athlete),
            patch("app.graphs.chat_turn._persist_messages") as mock_persist,
        ):
            MockClient.return_value.messages.create.return_value = _mock_llm_response("r")
            run_chat_turn(athlete_id="a1", user_message="test", db=MagicMock(), last_3_intents=[])

        mock_persist.assert_called_once()
