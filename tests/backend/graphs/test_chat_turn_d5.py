"""D5 TDD — chat_turn extensions: chain, clinical escalation, out-of-scope, clarification."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


def _make_athlete(athlete_id: str = "a1", clinical_flag=None) -> MagicMock:
    m = MagicMock()
    m.id = athlete_id
    m.journey_phase = "steady_state"
    m.sports_json = '["running", "nutrition"]'
    m.primary_sport = "running"
    m.hours_per_week = 8.0
    m.coaching_mode = "full"
    m.clinical_context_flag = clinical_flag
    return m


def _mock_classify(decision: str, specialist_chain=None, escalation_type=None,
                   clarification_axes=None, acknowledged=False) -> MagicMock:
    from app.schemas.intent import IntentClassification, SpecialistTarget
    chain = None
    if specialist_chain:
        chain = [SpecialistTarget(specialist=s, reason="test") for s in specialist_chain]
    return IntentClassification(
        decision=decision,
        specialist_chain=chain,
        clinical_escalation_type=escalation_type,
        clarification_axes=clarification_axes,
        confidence=0.9,
        reasoning="test",
        language_detected="fr",
        clinical_context_active_acknowledged=acknowledged,
    )


def _mock_llm(text: str = "réponse") -> MagicMock:
    block = MagicMock()
    block.text = text
    msg = MagicMock()
    msg.content = [block]
    return msg


# ─── SPECIALIST chain ─────────────────────────────────────────────────────────

class TestSpecialistChain:
    def test_chain_2_specialist_context_shared(self):
        """Chain 2: specialist[1] receives specialist[0]'s notes in its input."""
        from app.graphs.chat_turn import run_chat_turn

        intent = _mock_classify("SPECIALIST_TECHNICAL", specialist_chain=["energy", "nutrition"])
        athlete = _make_athlete()
        sp0_resp = _mock_llm("énergie: dormis 8h")
        sp1_resp = _mock_llm("nutrition: glucides")
        hc_resp = _mock_llm("synthèse HC")

        calls: list[dict] = []

        def capture_call(**kwargs):
            calls.append(kwargs)
            return [sp0_resp, sp1_resp, hc_resp][len(calls) - 1]

        with (
            patch("app.graphs.chat_turn.classify_intent", return_value=intent),
            patch("app.graphs.chat_turn.anthropic.Anthropic") as MockClient,
            patch("app.graphs.chat_turn._get_athlete", return_value=athlete),
            patch("app.graphs.chat_turn._persist_messages"),
        ):
            MockClient.return_value.messages.create.side_effect = capture_call
            result = run_chat_turn(
                athlete_id="a1", user_message="sommeil+nutrition marathon",
                db=MagicMock(), last_3_intents=[],
            )

        assert result["final_response"] == "synthèse HC"
        assert result["specialists_consulted"] == ["energy", "nutrition"]
        # 3 LLM calls: sp0 + sp1 + HC synthesis
        assert len(calls) == 3
        # specialist[1] call should mention prior notes from specialist[0]
        sp1_content = calls[1]["messages"][0]["content"]
        assert "energy" in sp1_content.lower() or "prior" in sp1_content.lower()

    def test_chain_3_specialists(self):
        """Chain 3: 4 LLM calls total (3 specialists + 1 HC synthesis)."""
        from app.graphs.chat_turn import run_chat_turn

        intent = _mock_classify("SPECIALIST_TECHNICAL",
                                specialist_chain=["running", "energy", "nutrition"])
        athlete = _make_athlete()

        with (
            patch("app.graphs.chat_turn.classify_intent", return_value=intent),
            patch("app.graphs.chat_turn.anthropic.Anthropic") as MockClient,
            patch("app.graphs.chat_turn._get_athlete", return_value=athlete),
            patch("app.graphs.chat_turn._persist_messages"),
        ):
            MockClient.return_value.messages.create.return_value = _mock_llm("r")
            result = run_chat_turn(
                athlete_id="a1", user_message="marathon complet",
                db=MagicMock(), last_3_intents=[],
            )
            assert MockClient.return_value.messages.create.call_count == 4
            assert result["specialists_consulted"] == ["running", "energy", "nutrition"]

    def test_chain_cap_3_max(self):
        """Specialist chain is capped at 3 — Pydantic validator on IntentClassification."""
        from app.schemas.intent import IntentClassification, SpecialistTarget
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            IntentClassification(
                decision="SPECIALIST_TECHNICAL",
                specialist_chain=[
                    SpecialistTarget(specialist="running", reason="a"),
                    SpecialistTarget(specialist="nutrition", reason="b"),
                    SpecialistTarget(specialist="energy", reason="c"),
                    SpecialistTarget(specialist="lifting", reason="d"),  # 4th → error
                ],
                confidence=0.9, reasoning="test", language_detected="fr",
                clinical_context_active_acknowledged=False,
            )


# ─── CLINICAL_ESCALATION_IMMEDIATE ───────────────────────────────────────────

class TestClinicalEscalation:
    def test_no_specialist_invoked(self):
        """CLINICAL_ESCALATION_IMMEDIATE: no LLM call, resources returned."""
        from app.graphs.chat_turn import run_chat_turn

        intent = _mock_classify("CLINICAL_ESCALATION_IMMEDIATE",
                                escalation_type="self_harm_signal")
        athlete = _make_athlete()

        with (
            patch("app.graphs.chat_turn.classify_intent", return_value=intent),
            patch("app.graphs.chat_turn.anthropic.Anthropic") as MockClient,
            patch("app.graphs.chat_turn._get_athlete", return_value=athlete),
            patch("app.graphs.chat_turn._persist_messages"),
        ):
            result = run_chat_turn(
                athlete_id="a1", user_message="...",
                db=MagicMock(), last_3_intents=[],
            )
            assert MockClient.return_value.messages.create.call_count == 0

        assert result["intent_decision"] == "CLINICAL_ESCALATION_IMMEDIATE"
        assert result["specialists_consulted"] == []
        assert result["final_response"] != ""

    def test_tca_declared_escalation(self):
        """tca_declared type is handled gracefully."""
        from app.graphs.chat_turn import run_chat_turn

        intent = _mock_classify("CLINICAL_ESCALATION_IMMEDIATE",
                                escalation_type="tca_declared")
        athlete = _make_athlete()

        with (
            patch("app.graphs.chat_turn.classify_intent", return_value=intent),
            patch("app.graphs.chat_turn.anthropic.Anthropic") as MockClient,
            patch("app.graphs.chat_turn._get_athlete", return_value=athlete),
            patch("app.graphs.chat_turn._persist_messages"),
        ):
            result = run_chat_turn(
                athlete_id="a1", user_message="...",
                db=MagicMock(), last_3_intents=[],
            )
            assert MockClient.return_value.messages.create.call_count == 0
        assert result["final_response"] != ""


# ─── OUT_OF_SCOPE ─────────────────────────────────────────────────────────────

class TestOutOfScope:
    def test_hc_responds_out_of_scope(self):
        """OUT_OF_SCOPE: Head Coach responds with bounded reply (1 LLM call)."""
        from app.graphs.chat_turn import run_chat_turn

        intent = _mock_classify("OUT_OF_SCOPE")
        athlete = _make_athlete()

        with (
            patch("app.graphs.chat_turn.classify_intent", return_value=intent),
            patch("app.graphs.chat_turn.anthropic.Anthropic") as MockClient,
            patch("app.graphs.chat_turn._get_athlete", return_value=athlete),
            patch("app.graphs.chat_turn._persist_messages"),
        ):
            MockClient.return_value.messages.create.return_value = _mock_llm("Hors scope.")
            result = run_chat_turn(
                athlete_id="a1", user_message="météo demain ?",
                db=MagicMock(), last_3_intents=[],
            )
            assert MockClient.return_value.messages.create.call_count == 1

        assert result["intent_decision"] == "OUT_OF_SCOPE"
        assert result["final_response"] == "Hors scope."


# ─── CLARIFICATION_NEEDED ────────────────────────────────────────────────────

class TestClarificationNeeded:
    def test_tappable_axes_in_response(self):
        """CLARIFICATION_NEEDED: response contains clarification axes."""
        from app.graphs.chat_turn import run_chat_turn

        axes = ["Entraînement", "Récupération", "Nutrition"]
        intent = _mock_classify("CLARIFICATION_NEEDED", clarification_axes=axes)
        athlete = _make_athlete()

        with (
            patch("app.graphs.chat_turn.classify_intent", return_value=intent),
            patch("app.graphs.chat_turn.anthropic.Anthropic") as MockClient,
            patch("app.graphs.chat_turn._get_athlete", return_value=athlete),
            patch("app.graphs.chat_turn._persist_messages"),
        ):
            MockClient.return_value.messages.create.return_value = _mock_llm("intro")
            result = run_chat_turn(
                athlete_id="a1", user_message="améliorer mes perfs",
                db=MagicMock(), last_3_intents=[],
            )

        assert result["intent_decision"] == "CLARIFICATION_NEEDED"
        # clarification_axes included in result for frontend tappable UI
        assert result.get("clarification_axes") == axes

    def test_no_specialist_for_clarification(self):
        """CLARIFICATION_NEEDED: no specialist invoked."""
        from app.graphs.chat_turn import run_chat_turn

        intent = _mock_classify("CLARIFICATION_NEEDED",
                                clarification_axes=["A", "B"])
        athlete = _make_athlete()

        with (
            patch("app.graphs.chat_turn.classify_intent", return_value=intent),
            patch("app.graphs.chat_turn.anthropic.Anthropic") as MockClient,
            patch("app.graphs.chat_turn._get_athlete", return_value=athlete),
            patch("app.graphs.chat_turn._persist_messages"),
        ):
            MockClient.return_value.messages.create.return_value = _mock_llm("r")
            result = run_chat_turn(
                athlete_id="a1", user_message="perf",
                db=MagicMock(), last_3_intents=[],
            )
        assert result["specialists_consulted"] == []


# ─── Clinical context wrapping (§10.1.4) ─────────────────────────────────────

class TestClinicalContextWrapping:
    def test_tca_flag_injected_in_specialist_input(self):
        """flag tca active: clinical flag injected in specialist payload."""
        from app.graphs.chat_turn import run_chat_turn

        intent = _mock_classify("SPECIALIST_TECHNICAL",
                                specialist_chain=["nutrition"],
                                acknowledged=True)
        athlete = _make_athlete(clinical_flag="tca")

        calls: list[dict] = []

        def capture(**kwargs):
            calls.append(kwargs)
            return _mock_llm("r")

        with (
            patch("app.graphs.chat_turn.classify_intent", return_value=intent),
            patch("app.graphs.chat_turn.anthropic.Anthropic") as MockClient,
            patch("app.graphs.chat_turn._get_athlete", return_value=athlete),
            patch("app.graphs.chat_turn._persist_messages"),
        ):
            MockClient.return_value.messages.create.side_effect = capture
            run_chat_turn(
                athlete_id="a1", user_message="glucides ?",
                db=MagicMock(), last_3_intents=[],
            )

        # First call is specialist — its content should mention the clinical flag
        specialist_content = calls[0]["messages"][0]["content"]
        assert "tca" in specialist_content.lower() or "clinical" in specialist_content.lower()
