"""D12 E2E — Phase D clinical escalation flow tests."""
from __future__ import annotations

from unittest.mock import MagicMock, patch


def _make_athlete(
    athlete_id: str = "a1",
    clinical_flag: str | None = None,
) -> MagicMock:
    m = MagicMock()
    m.id = athlete_id
    m.journey_phase = "steady_state"
    m.sports_json = '["running"]'
    m.primary_sport = "running"
    m.hours_per_week = 8.0
    m.coaching_mode = "full"
    m.clinical_context_flag = clinical_flag
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


class TestClinicalEscalation:
    def test_tca_declared_immediate_escalation_no_specialist(self):
        """tca_declared → CLINICAL_ESCALATION_IMMEDIATE, 0 LLM calls, 0 specialists."""
        from app.graphs.chat_turn import run_chat_turn

        athlete = _make_athlete()
        db = _make_db(athlete)

        mock_intent = MagicMock()
        mock_intent.decision = "CLINICAL_ESCALATION_IMMEDIATE"
        mock_intent.clinical_escalation_type = "tca_declared"
        mock_intent.specialist_chain = None
        mock_intent.clarification_axes = None
        mock_intent.clinical_context_active_acknowledged = False

        with (
            patch("app.graphs.chat_turn._get_athlete", return_value=athlete),
            patch("app.graphs.chat_turn.classify_intent", return_value=mock_intent),
            patch("app.graphs.chat_turn._persist_messages"),
            patch("app.graphs.chat_turn.anthropic.Anthropic") as M,
        ):
            result = run_chat_turn(
                athlete_id="a1",
                user_message="j'ai des problèmes alimentaires",
                db=db,
                last_3_intents=[],
            )
            # anthropic.Anthropic should NOT be called for immediate escalation
            M.return_value.messages.create.assert_not_called()

        assert result["intent_decision"] == "CLINICAL_ESCALATION_IMMEDIATE"
        assert result["specialists_consulted"] == []
        assert "professionnel" in result["final_response"].lower()

    def test_self_harm_signal_immediate_escalation(self):
        """self_harm_signal → CLINICAL_ESCALATION_IMMEDIATE with crisis resources."""
        from app.graphs.chat_turn import run_chat_turn

        athlete = _make_athlete()
        db = _make_db(athlete)

        mock_intent = MagicMock()
        mock_intent.decision = "CLINICAL_ESCALATION_IMMEDIATE"
        mock_intent.clinical_escalation_type = "self_harm_signal"
        mock_intent.specialist_chain = None
        mock_intent.clarification_axes = None
        mock_intent.clinical_context_active_acknowledged = False

        with (
            patch("app.graphs.chat_turn._get_athlete", return_value=athlete),
            patch("app.graphs.chat_turn.classify_intent", return_value=mock_intent),
            patch("app.graphs.chat_turn._persist_messages"),
        ):
            result = run_chat_turn(
                athlete_id="a1",
                user_message="...",
                db=db,
                last_3_intents=[],
            )

        assert result["intent_decision"] == "CLINICAL_ESCALATION_IMMEDIATE"
        # Response contains crisis line info
        assert "APPELLE" in result["final_response"] or "277" in result["final_response"]

    def test_clinical_flag_active_injected_into_specialist(self):
        """flag_clinical_context_active=tca → clinical_flag injected into specialist chain."""
        from app.graphs.chat_turn import run_chat_turn

        athlete = _make_athlete(clinical_flag="tca")
        db = _make_db(athlete)

        spec = MagicMock()
        spec.specialist = "nutrition"

        mock_intent = MagicMock()
        mock_intent.decision = "SPECIALIST_TECHNICAL"
        mock_intent.specialist_chain = [spec]
        mock_intent.clinical_escalation_type = None
        mock_intent.clarification_axes = None
        mock_intent.clinical_context_active_acknowledged = True  # flag acknowledged

        captured_calls: list[dict] = []

        def _capture_create(**kwargs: object) -> MagicMock:
            captured_calls.append(dict(kwargs))
            return _mock_llm("Nutrition advice")

        with (
            patch("app.graphs.chat_turn._get_athlete", return_value=athlete),
            patch("app.graphs.chat_turn.classify_intent", return_value=mock_intent),
            patch("app.graphs.chat_turn._persist_messages"),
            patch("app.graphs.chat_turn.anthropic.Anthropic") as M,
        ):
            M.return_value.messages.create.side_effect = _capture_create
            run_chat_turn(
                athlete_id="a1",
                user_message="Comment manger?",
                db=db,
                last_3_intents=[],
            )

        # The specialist user content should include the clinical flag
        assert len(captured_calls) >= 1
        first_call_messages = captured_calls[0].get("messages", [])
        first_content = first_call_messages[0]["content"] if first_call_messages else ""
        assert "tca" in first_content.lower()
