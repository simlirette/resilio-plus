"""D2 TDD — IntentClassification + IntentClassificationRequest schema validation."""
from __future__ import annotations

import pytest
from pydantic import ValidationError


def _valid_classification(**overrides):
    base = {
        "decision": "HEAD_COACH_DIRECT",
        "specialist_chain": None,
        "clinical_escalation_type": None,
        "clarification_axes": None,
        "confidence": 0.9,
        "reasoning": "Direct question about training plan.",
        "language_detected": "fr",
        "clinical_context_active_acknowledged": False,
    }
    base.update(overrides)
    return base


def _valid_request(**overrides):
    base = {
        "user_message": "Est-ce que je peux faire du vélo demain ?",
        "conversation_context_minimal": {
            "last_3_intents": [],
            "last_user_message": None,
        },
        "user_profile_minimal": {
            "athlete_id": "test-id",
            "journey_phase": "steady_state",
            "sports": ["running", "biking"],
            "clinical_context_flag": None,
        },
    }
    base.update(overrides)
    return base


class TestIntentClassification:
    def test_valid_head_coach_direct(self):
        from app.schemas.intent import IntentClassification
        obj = IntentClassification(**_valid_classification())
        assert obj.decision == "HEAD_COACH_DIRECT"
        assert obj.confidence == 0.9
        assert obj.specialist_chain is None

    def test_valid_specialist_technical_with_chain(self):
        from app.schemas.intent import IntentClassification, SpecialistTarget
        obj = IntentClassification(
            **_valid_classification(
                decision="SPECIALIST_TECHNICAL",
                specialist_chain=[{"specialist": "lifting", "reason": "technique question"}],
            )
        )
        assert obj.decision == "SPECIALIST_TECHNICAL"
        assert len(obj.specialist_chain) == 1

    def test_specialist_chain_max_3(self):
        from app.schemas.intent import IntentClassification
        with pytest.raises(ValidationError):
            IntentClassification(
                **_valid_classification(
                    decision="SPECIALIST_TECHNICAL",
                    specialist_chain=[
                        {"specialist": "lifting", "reason": "a"},
                        {"specialist": "running", "reason": "b"},
                        {"specialist": "swimming", "reason": "c"},
                        {"specialist": "biking", "reason": "d"},  # 4th → error
                    ],
                )
            )

    def test_confidence_bounds_0_to_1(self):
        from app.schemas.intent import IntentClassification
        with pytest.raises(ValidationError):
            IntentClassification(**_valid_classification(confidence=1.5))
        with pytest.raises(ValidationError):
            IntentClassification(**_valid_classification(confidence=-0.1))

    def test_confidence_boundary_values(self):
        from app.schemas.intent import IntentClassification
        obj_low = IntentClassification(**_valid_classification(confidence=0.0))
        assert obj_low.confidence == 0.0
        obj_high = IntentClassification(**_valid_classification(confidence=1.0))
        assert obj_high.confidence == 1.0

    def test_reasoning_max_200_chars(self):
        from app.schemas.intent import IntentClassification
        with pytest.raises(ValidationError):
            IntentClassification(**_valid_classification(reasoning="x" * 201))

    def test_reasoning_exactly_200_chars_ok(self):
        from app.schemas.intent import IntentClassification
        obj = IntentClassification(**_valid_classification(reasoning="x" * 200))
        assert len(obj.reasoning) == 200

    def test_all_decision_values(self):
        from app.schemas.intent import IntentClassification
        for decision in [
            "HEAD_COACH_DIRECT",
            "SPECIALIST_TECHNICAL",
            "CLINICAL_ESCALATION_IMMEDIATE",
            "OUT_OF_SCOPE",
            "CLARIFICATION_NEEDED",
        ]:
            obj = IntentClassification(**_valid_classification(decision=decision))
            assert obj.decision == decision

    def test_invalid_decision_raises(self):
        from app.schemas.intent import IntentClassification
        with pytest.raises(ValidationError):
            IntentClassification(**_valid_classification(decision="UNKNOWN"))

    def test_language_detected_values(self):
        from app.schemas.intent import IntentClassification
        for lang in ["fr", "en", "fr-en-mixed"]:
            obj = IntentClassification(**_valid_classification(language_detected=lang))
            assert obj.language_detected == lang

    def test_clinical_escalation_type_values(self):
        from app.schemas.intent import IntentClassification
        for et in ["tca_declared", "self_harm_signal"]:
            obj = IntentClassification(
                **_valid_classification(
                    decision="CLINICAL_ESCALATION_IMMEDIATE",
                    clinical_escalation_type=et,
                )
            )
            assert obj.clinical_escalation_type == et

    def test_clarification_axes_optional(self):
        from app.schemas.intent import IntentClassification
        obj = IntentClassification(
            **_valid_classification(
                decision="CLARIFICATION_NEEDED",
                clarification_axes=["nutrition", "recovery"],
            )
        )
        assert obj.clarification_axes == ["nutrition", "recovery"]

    def test_clinical_context_active_acknowledged_bool(self):
        from app.schemas.intent import IntentClassification
        obj = IntentClassification(**_valid_classification(clinical_context_active_acknowledged=True))
        assert obj.clinical_context_active_acknowledged is True


class TestIntentClassificationRequest:
    def test_valid_request(self):
        from app.schemas.intent import IntentClassificationRequest
        req = IntentClassificationRequest(**_valid_request())
        assert req.user_message == "Est-ce que je peux faire du vélo demain ?"

    def test_missing_user_message_raises(self):
        from app.schemas.intent import IntentClassificationRequest
        payload = _valid_request()
        del payload["user_message"]
        with pytest.raises(ValidationError):
            IntentClassificationRequest(**payload)

    def test_user_profile_minimal_fields(self):
        from app.schemas.intent import IntentClassificationRequest
        req = IntentClassificationRequest(**_valid_request())
        assert req.user_profile_minimal.journey_phase == "steady_state"
        assert req.user_profile_minimal.clinical_context_flag is None

    def test_conversation_context_minimal_fields(self):
        from app.schemas.intent import IntentClassificationRequest
        req = IntentClassificationRequest(**_valid_request())
        assert req.conversation_context_minimal.last_3_intents == []
