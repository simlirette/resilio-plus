"""The router has to survive a model that does not follow its contract.

Measured against the live API on 2026-08-20: Haiku returned a ```json fence
containing a `contract_payload` key instead of `<contract_payload>` tags,
invented a decision outside the enum (`CLINICAL_ESCALATION_WITH_ROUTING`),
wrote `specialist_chain` as a bare string, spelled the language "French"
instead of "fr", and appended prose after the block. The parser rejected all of
it, so every message fell back to the Head Coach and **no specialist was ever
consulted** — the specialist chain existed but never ran.

Being strict about a format the model does not honour buys nothing. These tests
pin tolerant parsing plus one safety rule: an invented decision degrades to the
Head Coach, and only a *recognised* clinical escalation type escalates.
"""
from __future__ import annotations

import json

import pytest

from app.services.classify_intent_service import _parse_response

BASE = {
    "decision": "SPECIALIST_TECHNICAL",
    "specialist_chain": [{"specialist": "running", "reason": "legs"}],
    "clinical_escalation_type": None,
    "clarification_axes": None,
    "confidence": 0.9,
    "reasoning": "Muscular complaint.",
    "language_detected": "fr",
    "clinical_context_active_acknowledged": False,
}


class TestFormats:
    def test_the_documented_xml_form_still_works(self) -> None:
        raw = f"<contract_payload>{json.dumps(BASE)}</contract_payload>"
        assert _parse_response(raw).decision == "SPECIALIST_TECHNICAL"

    def test_a_json_fence_is_accepted(self) -> None:
        raw = f"```json\n{json.dumps(BASE)}\n```"
        assert _parse_response(raw).decision == "SPECIALIST_TECHNICAL"

    def test_a_fence_wrapping_a_contract_payload_key_is_unwrapped(self) -> None:
        raw = f"```json\n{json.dumps({'contract_payload': BASE})}\n```"
        assert _parse_response(raw).decision == "SPECIALIST_TECHNICAL"

    def test_bare_json_is_accepted(self) -> None:
        assert _parse_response(json.dumps(BASE)).decision == "SPECIALIST_TECHNICAL"

    def test_trailing_prose_after_the_block_is_ignored(self) -> None:
        raw = (
            f"```json\n{json.dumps(BASE)}\n```\n\n"
            "**Priority Flag:** URGENT - session hold recommended."
        )
        assert _parse_response(raw).decision == "SPECIALIST_TECHNICAL"


class TestCoercion:
    def test_a_language_name_is_normalised(self) -> None:
        raw = json.dumps({**BASE, "language_detected": "French"})
        assert _parse_response(raw).language_detected == "fr"

    def test_a_string_specialist_chain_becomes_a_list(self) -> None:
        raw = json.dumps({**BASE, "specialist_chain": "running"})
        chain = _parse_response(raw).specialist_chain
        assert chain is not None
        assert chain[0].specialist == "running"

    def test_unknown_extra_keys_are_dropped(self) -> None:
        raw = json.dumps({**BASE, "sub_decision": "DO_NOT_PROCEED", "priority": "red"})
        assert _parse_response(raw).decision == "SPECIALIST_TECHNICAL"

    def test_an_overlong_reasoning_is_truncated_not_rejected(self) -> None:
        raw = json.dumps({**BASE, "reasoning": "x" * 400})
        assert len(_parse_response(raw).reasoning) <= 200

    def test_a_chain_longer_than_three_is_trimmed(self) -> None:
        raw = json.dumps(
            {
                **BASE,
                "specialist_chain": [
                    {"specialist": name}
                    for name in ("running", "lifting", "recovery", "nutrition")
                ],
            }
        )
        chain = _parse_response(raw).specialist_chain
        assert chain is not None and len(chain) == 3


class TestInventedDecisions:
    def test_an_unknown_decision_degrades_to_the_head_coach(self) -> None:
        raw = json.dumps({**BASE, "decision": "CLINICAL_ESCALATION_WITH_ROUTING"})
        assert _parse_response(raw).decision == "HEAD_COACH_DIRECT"

    def test_an_invented_escalation_type_does_not_manufacture_an_emergency(
        self,
    ) -> None:
        """'Dead legs' must not become a self-harm resource message."""
        raw = json.dumps(
            {
                **BASE,
                "decision": "CLINICAL_ESCALATION_WITH_ROUTING",
                "clinical_escalation_type": "acute_neuromuscular_symptom",
            }
        )
        result = _parse_response(raw)

        assert result.decision == "HEAD_COACH_DIRECT"
        assert result.clinical_escalation_type is None

    def test_a_recognised_escalation_is_still_honoured(self) -> None:
        raw = json.dumps(
            {
                **BASE,
                "decision": "CLINICAL_ESCALATION_IMMEDIATE",
                "clinical_escalation_type": "self_harm_signal",
            }
        )
        result = _parse_response(raw)

        assert result.decision == "CLINICAL_ESCALATION_IMMEDIATE"
        assert result.clinical_escalation_type == "self_harm_signal"

    def test_a_recognised_type_under_an_invented_decision_still_escalates(self) -> None:
        raw = json.dumps(
            {
                **BASE,
                "decision": "CLINICAL_ESCALATION_WITH_ROUTING",
                "clinical_escalation_type": "tca_declared",
            }
        )
        assert _parse_response(raw).decision == "CLINICAL_ESCALATION_IMMEDIATE"


class TestUnusable:
    def test_no_json_at_all_still_raises(self) -> None:
        with pytest.raises(ValueError):
            _parse_response("I am afraid I cannot help with that.")

    def test_broken_json_still_raises(self) -> None:
        with pytest.raises(ValueError):
            _parse_response("```json\n{not valid json,,}\n```")
