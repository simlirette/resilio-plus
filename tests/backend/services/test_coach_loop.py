"""The model drives the turn. The loop only carries messages and tool results.

The failure this replaces, verbatim from 2026-08-21:

    Simon : Quand est-ce que je t'ai indiqué que j'ai 8h à consacré ?
    Coach : Pour calibrer ton programme : tu pratiques uniquement la course … ?
    Simon : Je veux recommencer l'onboarding.
    Coach : Tu reviens sur la course — est-ce ton sport principal … ?

Two direct speech acts ignored, the same question three times. The cause was an
imperative sent every turn: "Demande à l'athlète uniquement ce qui manque." The
model obeyed the order instead of answering, because it was never asked to
answer.

Here nothing tells the model what to say. It gets the conversation, the facts
with their provenance, and the tools. What the turn *is* — an answer, an
acknowledgement, a question, a plan — is its decision.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from app.services.coach_loop import MAX_ITERATIONS, run_coach_turn


def _text_block(text: str) -> MagicMock:
    block = MagicMock()
    block.type = "text"
    block.text = text
    return block


def _tool_block(name: str, args: dict, block_id: str = "t1") -> MagicMock:
    block = MagicMock()
    block.type = "tool_use"
    block.name = name
    block.input = args
    block.id = block_id
    return block


def _reply(blocks: list[MagicMock], stop: str = "end_turn") -> MagicMock:
    message = MagicMock()
    message.content = blocks
    message.stop_reason = stop
    return message


@pytest.fixture
def captured() -> dict:
    return {}


def _client(replies: list[MagicMock], captured: dict) -> MagicMock:
    client = MagicMock()
    calls = {"n": 0}

    def _create(**kwargs):
        captured.setdefault("calls", []).append(kwargs)
        index = min(calls["n"], len(replies) - 1)
        calls["n"] += 1
        return replies[index]

    client.messages.create.side_effect = _create
    return client


class TestAPlainAnswer:
    def test_a_text_reply_is_returned(self, captured) -> None:
        replies = [_reply([_text_block("Tu ne me l'as jamais dit.")])]

        with patch(
            "app.services.coach_loop._make_client",
            return_value=_client(replies, captured),
        ):
            result = run_coach_turn("a1", "Quand t'ai-je dit 8h ?", db=MagicMock())

        assert result.reply == "Tu ne me l'as jamais dit."
        assert result.tools_used == []

    def test_the_tools_are_offered_every_turn(self, captured) -> None:
        replies = [_reply([_text_block("ok")])]

        with patch(
            "app.services.coach_loop._make_client",
            return_value=_client(replies, captured),
        ):
            run_coach_turn("a1", "salut", db=MagicMock())

        names = {t["name"] for t in captured["calls"][0]["tools"]}
        assert "update_profile" in names
        assert "review_training" in names

    def test_nothing_instructs_the_model_what_to_say(self, captured) -> None:
        """The imperative is the bug. Its absence is the fix."""
        replies = [_reply([_text_block("ok")])]

        with patch(
            "app.services.coach_loop._make_client",
            return_value=_client(replies, captured),
        ):
            run_coach_turn("a1", "salut", db=MagicMock())

        sent = str(captured["calls"][0])
        for imperative in ("Demande à l'athlète", "Pose la question", "Collecte"):
            assert imperative not in sent


class TestToolUse:
    def test_a_tool_call_is_executed_and_fed_back(self, captured) -> None:
        replies = [
            _reply([_tool_block("update_profile", {"resting_hr": 52})], "tool_use"),
            _reply([_text_block("Noté, 52 au repos.")]),
        ]

        with (
            patch(
                "app.services.coach_loop._make_client",
                return_value=_client(replies, captured),
            ),
            patch("app.services.coach_loop.run_tool") as tool,
        ):
            tool.return_value.ok = True
            tool.return_value.content = "Enregistré : resting_hr."
            result = run_coach_turn("a1", "mon pouls repos est 52", db=MagicMock())

        assert tool.called
        assert result.reply == "Noté, 52 au repos."
        assert result.tools_used == ["update_profile"]

    def test_the_tool_result_reaches_the_next_call(self, captured) -> None:
        replies = [
            _reply([_tool_block("assess_goal", {})], "tool_use"),
            _reply([_text_block("done")]),
        ]

        with (
            patch(
                "app.services.coach_loop._make_client",
                return_value=_client(replies, captured),
            ),
            patch("app.services.coach_loop.run_tool") as tool,
        ):
            tool.return_value.ok = True
            tool.return_value.content = "Projection 2h24."
            run_coach_turn("a1", "je peux faire sous 2h ?", db=MagicMock())

        assert "2h24" in str(captured["calls"][1]["messages"])

    def test_a_failing_tool_is_reported_to_the_model_not_raised(
        self, captured
    ) -> None:
        replies = [
            _reply([_tool_block("generate_plan", {})], "tool_use"),
            _reply([_text_block("Je n'ai pas pu construire la semaine.")]),
        ]

        with (
            patch(
                "app.services.coach_loop._make_client",
                return_value=_client(replies, captured),
            ),
            patch("app.services.coach_loop.run_tool") as tool,
        ):
            tool.return_value.ok = False
            tool.return_value.content = "La génération a échoué."
            result = run_coach_turn("a1", "fais mon plan", db=MagicMock())

        assert "pas pu" in result.reply


class TestItAlwaysTerminates:
    def test_a_model_that_only_calls_tools_is_cut_off(self, captured) -> None:
        """Without a ceiling a tool-happy model loops until the athlete gives up."""
        forever = [_reply([_tool_block("assess_goal", {})], "tool_use")]

        with (
            patch(
                "app.services.coach_loop._make_client",
                return_value=_client(forever, captured),
            ),
            patch("app.services.coach_loop.run_tool") as tool,
        ):
            tool.return_value.ok = True
            tool.return_value.content = "ok"
            result = run_coach_turn("a1", "salut", db=MagicMock())

        assert len(captured["calls"]) <= MAX_ITERATIONS + 1
        assert result.reply.strip()

    def test_an_api_failure_yields_a_sentence_not_an_exception(self) -> None:
        with patch(
            "app.services.coach_loop._make_client",
            side_effect=RuntimeError("api down"),
        ):
            result = run_coach_turn("a1", "salut", db=MagicMock())

        assert result.reply.strip()
        assert not result.ok

    def test_an_empty_reply_still_says_something(self, captured) -> None:
        replies = [_reply([])]

        with patch(
            "app.services.coach_loop._make_client",
            return_value=_client(replies, captured),
        ):
            result = run_coach_turn("a1", "salut", db=MagicMock())

        assert result.reply.strip()
