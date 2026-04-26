"""D3 TDD — classify_intent_service (classify_intent function)."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from app.schemas.intent import (
    ConversationContextMinimal,
    IntentClassification,
    IntentClassificationRequest,
    SpecialistTarget,
    UserProfileMinimal,
)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _make_request(user_message: str = "test", clinical_flag=None) -> IntentClassificationRequest:
    return IntentClassificationRequest(
        user_message=user_message,
        conversation_context_minimal=ConversationContextMinimal(
            last_3_intents=[],
            last_user_message=None,
        ),
        user_profile_minimal=UserProfileMinimal(
            athlete_id="a1",
            journey_phase="steady_state",
            sports=["running"],
            clinical_context_flag=clinical_flag,
        ),
    )


def _make_contract_payload(**overrides) -> dict:
    base = {
        "decision": "HEAD_COACH_DIRECT",
        "specialist_chain": None,
        "clinical_escalation_type": None,
        "clarification_axes": None,
        "confidence": 0.9,
        "reasoning": "Salutation simple.",
        "language_detected": "fr",
        "clinical_context_active_acknowledged": False,
    }
    base.update(overrides)
    return base


def _mock_haiku_xml(payload: dict) -> MagicMock:
    xml = f"<reasoning>test</reasoning><message_to_user></message_to_user><contract_payload>{json.dumps(payload)}</contract_payload>"
    block = MagicMock()
    block.text = xml
    message = MagicMock()
    message.content = [block]
    return message


# ─── Tests ───────────────────────────────────────────────────────────────────

class TestClassifyIntentRoutes:
    def test_head_coach_direct(self):
        from app.services.classify_intent_service import classify_intent

        payload = _make_contract_payload(decision="HEAD_COACH_DIRECT")
        with patch("app.services.classify_intent_service.anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.return_value = _mock_haiku_xml(payload)
            result = classify_intent(_make_request("bonjour"))

        assert isinstance(result, IntentClassification)
        assert result.decision == "HEAD_COACH_DIRECT"
        assert result.specialist_chain is None

    def test_specialist_technical_single(self):
        from app.services.classify_intent_service import classify_intent

        payload = _make_contract_payload(
            decision="SPECIALIST_TECHNICAL",
            specialist_chain=[{"specialist": "nutrition", "reason": "question nutrition"}],
        )
        with patch("app.services.classify_intent_service.anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.return_value = _mock_haiku_xml(payload)
            result = classify_intent(_make_request("créatine ?"))

        assert result.decision == "SPECIALIST_TECHNICAL"
        assert result.specialist_chain is not None
        assert len(result.specialist_chain) == 1
        assert result.specialist_chain[0].specialist == "nutrition"

    def test_specialist_technical_chain_3(self):
        from app.services.classify_intent_service import classify_intent

        payload = _make_contract_payload(
            decision="SPECIALIST_TECHNICAL",
            specialist_chain=[
                {"specialist": "energy", "reason": "sommeil"},
                {"specialist": "nutrition", "reason": "alimentation marathon"},
                {"specialist": "running", "reason": "plan marathon"},
            ],
        )
        with patch("app.services.classify_intent_service.anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.return_value = _mock_haiku_xml(payload)
            result = classify_intent(_make_request("optimiser pour marathon"))

        assert len(result.specialist_chain) == 3

    def test_clinical_escalation_immediate(self):
        from app.services.classify_intent_service import classify_intent

        payload = _make_contract_payload(
            decision="CLINICAL_ESCALATION_IMMEDIATE",
            clinical_escalation_type="self_harm_signal",
            clinical_context_active_acknowledged=True,
        )
        with patch("app.services.classify_intent_service.anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.return_value = _mock_haiku_xml(payload)
            result = classify_intent(_make_request("..."))

        assert result.decision == "CLINICAL_ESCALATION_IMMEDIATE"
        assert result.clinical_escalation_type == "self_harm_signal"

    def test_out_of_scope(self):
        from app.services.classify_intent_service import classify_intent

        payload = _make_contract_payload(decision="OUT_OF_SCOPE", reasoning="Question hors scope coaching.")
        with patch("app.services.classify_intent_service.anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.return_value = _mock_haiku_xml(payload)
            result = classify_intent(_make_request("météo demain ?"))

        assert result.decision == "OUT_OF_SCOPE"

    def test_clarification_needed(self):
        from app.services.classify_intent_service import classify_intent

        payload = _make_contract_payload(
            decision="CLARIFICATION_NEEDED",
            clarification_axes=["Aspect nutrition ?", "Aspect récupération ?"],
        )
        with patch("app.services.classify_intent_service.anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.return_value = _mock_haiku_xml(payload)
            result = classify_intent(_make_request("améliorer mes performances"))

        assert result.decision == "CLARIFICATION_NEEDED"
        assert result.clarification_axes is not None
        assert len(result.clarification_axes) == 2


class TestClassifyIntentClinicalAcknowledgement:
    def test_clinical_flag_acknowledged_when_present(self):
        from app.services.classify_intent_service import classify_intent

        payload = _make_contract_payload(
            decision="HEAD_COACH_DIRECT",
            clinical_context_active_acknowledged=True,
        )
        with patch("app.services.classify_intent_service.anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.return_value = _mock_haiku_xml(payload)
            result = classify_intent(_make_request(clinical_flag="tca"))

        assert result.clinical_context_active_acknowledged is True

    def test_clinical_flag_not_acknowledged_when_absent(self):
        from app.services.classify_intent_service import classify_intent

        payload = _make_contract_payload(clinical_context_active_acknowledged=False)
        with patch("app.services.classify_intent_service.anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.return_value = _mock_haiku_xml(payload)
            result = classify_intent(_make_request(clinical_flag=None))

        assert result.clinical_context_active_acknowledged is False


class TestClassifyIntentRetry:
    def test_timeout_triggers_retry(self):
        """On first timeout, service retries once and succeeds."""
        from app.services.classify_intent_service import classify_intent
        import anthropic as anthropic_lib

        payload = _make_contract_payload()
        success = _mock_haiku_xml(payload)

        with patch("app.services.classify_intent_service.anthropic.Anthropic") as MockClient:
            # First call raises APITimeoutError, second succeeds
            MockClient.return_value.messages.create.side_effect = [
                anthropic_lib.APITimeoutError(request=MagicMock()),
                success,
            ]
            result = classify_intent(_make_request())

        assert result.decision == "HEAD_COACH_DIRECT"
        assert MockClient.return_value.messages.create.call_count == 2

    def test_double_timeout_raises(self):
        """Two consecutive timeouts → raises."""
        from app.services.classify_intent_service import classify_intent
        import anthropic as anthropic_lib

        with patch("app.services.classify_intent_service.anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.side_effect = anthropic_lib.APITimeoutError(
                request=MagicMock()
            )
            with pytest.raises(anthropic_lib.APITimeoutError):
                classify_intent(_make_request())


class TestClassifyIntentParsing:
    def test_language_detected_en(self):
        from app.services.classify_intent_service import classify_intent

        payload = _make_contract_payload(language_detected="en")
        with patch("app.services.classify_intent_service.anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.return_value = _mock_haiku_xml(payload)
            result = classify_intent(_make_request("hello"))

        assert result.language_detected == "en"

    def test_confidence_float_parsed(self):
        from app.services.classify_intent_service import classify_intent

        payload = _make_contract_payload(confidence=0.77)
        with patch("app.services.classify_intent_service.anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.return_value = _mock_haiku_xml(payload)
            result = classify_intent(_make_request())

        assert abs(result.confidence - 0.77) < 0.001
