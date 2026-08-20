"""The intent router must never be the reason the coach goes silent.

It ran with an 800 ms hard timeout on an LLM round trip, retried once, then
raised - and the exception took the whole conversation turn with it, so the
athlete got "something broke on my side" instead of an answer. Two consecutive
real attempts timed out on 2026-08-20, which is what surfaced it.

Routing is an optimisation: it picks which specialist to consult. Losing it
should cost precision, not the conversation. The Head Coach prompt carries its
own clinical guardrails, so defaulting to it is safer than answering nothing.
"""
from __future__ import annotations

from typing import Any

import anthropic
import pytest

from app.services import classify_intent_service as svc


from unittest.mock import MagicMock, patch  # noqa: E402

from app.schemas.intent import (  # noqa: E402
    ConversationContextMinimal,
    IntentClassificationRequest,
    UserProfileMinimal,
)

VALID = """<contract_payload>
{
  "decision": "SPECIALIST_TECHNICAL",
  "specialist_chain": [
    {
      "specialist": "running",
      "reason": "legs"
    }
  ],
  "clinical_escalation_type": null,
  "clarification_axes": null,
  "confidence": 0.9,
  "reasoning": "Muscular complaint routed to running.",
  "language_detected": "fr",
  "clinical_context_active_acknowledged": false
}
</contract_payload>"""


def _request() -> IntentClassificationRequest:
    return IntentClassificationRequest(
        user_message="mes jambes sont mortes",
        conversation_context_minimal=ConversationContextMinimal(
            last_3_intents=[], last_user_message=None
        ),
        user_profile_minimal=UserProfileMinimal(
            athlete_id="a1",
            journey_phase="steady_state",
            sports=["running"],
            clinical_context_flag=None,
        ),
    )


def _client(side_effect: Any = None, return_text: str | None = None) -> Any:
    """Patch the Anthropic client the service constructs."""
    mock = patch("app.services.classify_intent_service.anthropic.Anthropic")
    handle = mock.start()
    create = handle.return_value.messages.create
    if side_effect is not None:
        create.side_effect = side_effect
    else:
        block = MagicMock()
        block.text = return_text
        message = MagicMock()
        message.content = [block]
        create.return_value = message
    return mock, create


class TestTimeoutBudget:
    def test_the_budget_is_realistic_for_an_llm_round_trip(self) -> None:
        assert svc._TIMEOUT_SECONDS >= 5, (
            "800ms cannot cover a real network round trip plus generation; "
            "it makes every message a coin flip"
        )

    def test_it_is_configurable_without_a_code_change(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("CLASSIFY_INTENT_TIMEOUT_S", "12.5")
        assert svc._timeout_seconds() == pytest.approx(12.5)

    def test_a_nonsense_value_falls_back_to_the_default(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("CLASSIFY_INTENT_TIMEOUT_S", "not-a-number")
        assert svc._timeout_seconds() == svc._TIMEOUT_SECONDS


class TestDegradation:
    def test_a_persistent_timeout_still_answers_the_athlete(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mock, create = _client(
            side_effect=anthropic.APITimeoutError(request=MagicMock())
        )
        try:
            result = svc.classify_intent(_request())
        finally:
            mock.stop()

        assert result.decision == "HEAD_COACH_DIRECT"
        assert create.call_count == 2, "should try twice before giving up"

    def test_an_api_error_degrades_the_same_way(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mock, _ = _client(side_effect=RuntimeError("upstream exploded"))
        try:
            assert svc.classify_intent(_request()).decision == "HEAD_COACH_DIRECT"
        finally:
            mock.stop()

    def test_an_unparseable_answer_degrades_the_same_way(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mock, _ = _client(return_text="no contract payload here")
        try:
            assert svc.classify_intent(_request()).decision == "HEAD_COACH_DIRECT"
        finally:
            mock.stop()

    def test_the_fallback_is_logged(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock, _ = _client(side_effect=RuntimeError("down"))
        try:
            with caplog.at_level("WARNING"):
                svc.classify_intent(_request())
        finally:
            mock.stop()

        assert "classify_intent_fallback" in caplog.text


class TestHappyPathUnchanged:
    def test_a_good_classification_is_returned_as_is(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mock, _ = _client(return_text=VALID)
        try:
            result = svc.classify_intent(_request())
        finally:
            mock.stop()

        assert result.decision == "SPECIALIST_TECHNICAL"
        assert result.specialist_chain[0].specialist == "running"

    def test_one_timeout_then_success_still_succeeds(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        block = MagicMock()
        block.text = VALID
        message = MagicMock()
        message.content = [block]
        mock, create = _client(
            side_effect=[anthropic.APITimeoutError(request=MagicMock()), message]
        )
        try:
            assert svc.classify_intent(_request()).decision == "SPECIALIST_TECHNICAL"
        finally:
            mock.stop()
