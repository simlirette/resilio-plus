"""Every athlete message goes through the agentic loop.

Onboarding and chat were two different code paths with two different failure
modes: a six-block script on one side, an intent classifier and a specialist
chain on the other. Neither could answer "quand t'ai-je dit 8h ?" — one was
collecting, the other was routing.

There is now one path. The difference between onboarding and steady state is
not the code, it is what the profile already contains: the coach sees the gaps
as facts and decides for itself whether this turn is a question, an answer or a
plan.

`journey_phase` still gates *whether* a graph runs at all — a brand-new athlete
in `signup` is walked forward first — but once a turn happens, it is this loop.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from app.services.graph_invoker import DefaultGraphInvoker


@pytest.fixture
def invoker() -> DefaultGraphInvoker:
    return DefaultGraphInvoker()


def _turn(reply: str = "Réponse.", tools: list[str] | None = None) -> MagicMock:
    result = MagicMock()
    result.reply = reply
    result.ok = True
    result.tools_used = tools or []
    return result


class TestBothPathsUseTheLoop:
    @pytest.mark.parametrize("graph", ["chat_turn", "onboarding"])
    def test_the_athlete_message_reaches_the_loop(
        self, invoker: DefaultGraphInvoker, graph: str
    ) -> None:
        with patch(
            "app.services.graph_invoker.run_coach_turn", return_value=_turn()
        ) as loop:
            invoker.invoke(graph, "a1", "t1", {"message": "salut"}, MagicMock())

        assert loop.called
        assert loop.call_args.kwargs.get("user_message") == "salut"

    @pytest.mark.parametrize("graph", ["chat_turn", "onboarding"])
    def test_the_reply_comes_back_as_the_message(
        self, invoker: DefaultGraphInvoker, graph: str
    ) -> None:
        with patch(
            "app.services.graph_invoker.run_coach_turn",
            return_value=_turn("Tu ne me l'as jamais dit."),
        ):
            result = invoker.invoke(
                graph, "a1", "t1", {"message": "quand ?"}, MagicMock()
            )

        assert result is not None
        assert "jamais dit" in str(result)

    def test_the_turn_is_recorded_for_the_next_one(
        self, invoker: DefaultGraphInvoker
    ) -> None:
        """Without this the loop loses the memory Phase A gave it."""
        with (
            patch(
                "app.services.graph_invoker.run_coach_turn",
                return_value=_turn("Réponse."),
            ),
            patch("app.services.graph_invoker.record_turn") as record,
        ):
            invoker.invoke("chat_turn", "a1", "t1", {"message": "salut"}, MagicMock())

        assert record.called


class TestNoMessageNoTurn:
    def test_a_payload_without_a_message_does_nothing(
        self, invoker: DefaultGraphInvoker
    ) -> None:
        """A system event is not an athlete speaking."""
        with patch("app.services.graph_invoker.run_coach_turn") as loop:
            result = invoker.invoke("chat_turn", "a1", "t1", {}, MagicMock())

        assert not loop.called
        assert result is None


class TestTheOldPathsAreGone:
    @pytest.mark.parametrize(
        "module", ["app.graphs.onboarding", "app.graphs.chat_turn"]
    )
    def test_the_invoker_no_longer_imports_the_old_graphs(self, module: str) -> None:
        """Leaving a second path alive is how the two drifted apart.

        Checked on imports, not on any substring: `_run_chat_turn` must keep
        its name because the coordinator resolves a graph by `_run_{name}`.
        """
        import ast
        import inspect

        from app.services import graph_invoker

        tree = ast.parse(inspect.getsource(graph_invoker))
        imported = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        }
        tail = module.rsplit(".", 2)[-2:]
        assert not any(
            name.endswith(".".join(tail)) for name in imported
        ), f"{module} still wired into the invoker"
