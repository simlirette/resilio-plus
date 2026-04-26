"""D6 TDD — chat_turn injury handling (consult_recovery_coach node, DEP-C3-001)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


def _make_athlete(athlete_id: str = "a1") -> MagicMock:
    m = MagicMock()
    m.id = athlete_id
    m.journey_phase = "steady_state"
    m.sports_json = '["running"]'
    m.primary_sport = "running"
    m.hours_per_week = 8.0
    m.coaching_mode = "full"
    m.clinical_context_flag = None
    return m


def _mock_llm(text: str = "r") -> MagicMock:
    block = MagicMock()
    block.text = text
    msg = MagicMock()
    msg.content = [block]
    return msg


class TestHandleInjuryReport:
    def test_recovery_consulted_on_injury_report(self):
        """CHAT_INJURY_REPORT event: Recovery consulted, result includes escalation flag."""
        from app.graphs.chat_turn import run_injury_report

        athlete = _make_athlete()

        with (
            patch("app.graphs.chat_turn.anthropic.Anthropic") as MockClient,
            patch("app.graphs.chat_turn._get_athlete", return_value=athlete),
            patch("app.graphs.chat_turn._persist_messages"),
        ):
            MockClient.return_value.messages.create.return_value = _mock_llm(
                "action: escalate_to_takeover\ninjury_payload_draft: {}"
            )
            result = run_injury_report(
                athlete_id="a1",
                user_message="je me suis blessé au genou",
                db=MagicMock(),
            )

        assert result["specialists_consulted"] == ["recovery"]
        assert result["intent_decision"] == "CHAT_INJURY_REPORT"

    def test_escalate_to_takeover_flag_set(self):
        """Recovery response with escalate_to_takeover → takeover_requested=True."""
        from app.graphs.chat_turn import run_injury_report

        athlete = _make_athlete()

        with (
            patch("app.graphs.chat_turn.anthropic.Anthropic") as MockClient,
            patch("app.graphs.chat_turn._get_athlete", return_value=athlete),
            patch("app.graphs.chat_turn._persist_messages"),
        ):
            MockClient.return_value.messages.create.return_value = _mock_llm(
                "action: escalate_to_takeover\ninjury_payload_draft: {}"
            )
            result = run_injury_report(
                athlete_id="a1",
                user_message="genou",
                db=MagicMock(),
            )

        assert result.get("takeover_requested") is True

    def test_no_takeover_when_not_escalated(self):
        """Recovery response without escalate → takeover_requested=False."""
        from app.graphs.chat_turn import run_injury_report

        athlete = _make_athlete()

        with (
            patch("app.graphs.chat_turn.anthropic.Anthropic") as MockClient,
            patch("app.graphs.chat_turn._get_athlete", return_value=athlete),
            patch("app.graphs.chat_turn._persist_messages"),
        ):
            MockClient.return_value.messages.create.return_value = _mock_llm(
                "action: monitor\nrecommendation: rest 2 days"
            )
            result = run_injury_report(
                athlete_id="a1",
                user_message="courbatures",
                db=MagicMock(),
            )

        assert result.get("takeover_requested") is False

    def test_missing_injury_payload_raises(self):
        """escalate_to_takeover without injury_payload_draft raises ValueError (RA7)."""
        from app.graphs.chat_turn import run_injury_report

        athlete = _make_athlete()

        with (
            patch("app.graphs.chat_turn.anthropic.Anthropic") as MockClient,
            patch("app.graphs.chat_turn._get_athlete", return_value=athlete),
            patch("app.graphs.chat_turn._persist_messages"),
        ):
            # escalate_to_takeover but no injury_payload_draft → should raise
            MockClient.return_value.messages.create.return_value = _mock_llm(
                "action: escalate_to_takeover"  # missing injury_payload_draft
            )
            with pytest.raises(ValueError, match="injury_payload_draft"):
                run_injury_report(
                    athlete_id="a1",
                    user_message="genou",
                    db=MagicMock(),
                )
