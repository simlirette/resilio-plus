"""Free-text after a Change tap goes to the revise path, not to chat."""
from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy.orm import Session

from app.db.models import MessagingIdentityModel
from app.messaging import MessagingGateway


class RecordingChannel:
    name = "telegram"

    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    def send(self, external_id: str, text: str) -> str:
        self.sent.append((external_id, text))
        return "provider-message-id"

    def send_with_buttons(
        self, external_id: str, text: str, buttons: list[Any]
    ) -> str:
        return self.send(external_id, text)

    def max_message_length(self) -> int:
        return 4096

    def format(self, text: str) -> str:
        return text


class RecordingCoordinator:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, str]]] = []

    def dispatch(
        self,
        athlete_id: str,
        event_type: str,
        payload: dict[str, str],
        db: Session,
    ) -> SimpleNamespace:
        self.calls.append((athlete_id, event_type, payload))
        return SimpleNamespace(output={"final_response": "chat reply"}, pending=False)


class RecordingNotifier:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    def send(
        self, athlete_id: str, text: str, buttons: list[Any] | None = None
    ) -> object:
        self.sent.append((athlete_id, text))
        return ["provider-message-id"]


class RecordingApprovals:
    def __init__(self, token: str | None) -> None:
        self._token = token
        self.pops: list[tuple[str, str]] = []
        self.revisions: list[tuple[str, str, str, str, str]] = []
        self.proposals: list[tuple[str, str, Any]] = []

    def take_pending_revision_token(
        self, *, channel: str, external_id: str
    ) -> str | None:
        self.pops.append((channel, external_id))
        token, self._token = self._token, None
        return token

    def handle_revision_text(
        self,
        *,
        athlete_id: str,
        channel: str,
        external_id: str,
        token: str,
        text: str,
    ) -> object:
        self.revisions.append((athlete_id, channel, external_id, token, text))
        return SimpleNamespace(resolution="revise")

    def send_plan_for_approval(
        self,
        *,
        athlete_id: str,
        thread_id: str,
        kind: str = "weekly_plan",
        plan: Any | None = None,
        degraded_sources: Any | None = None,
        payload: dict[str, Any] | None = None,
    ) -> str:
        self.proposals.append((athlete_id, thread_id, plan))
        return "new-token"


class RecordingCommands:
    def __init__(self, handled: bool) -> None:
        self._handled = handled
        self.calls: list[tuple[str, str]] = []

    def handle(self, athlete_id: str, text: str) -> object:
        self.calls.append((athlete_id, text))
        return SimpleNamespace(handled=self._handled)


class PlanCoordinator:
    def __init__(self, output: dict[str, Any]) -> None:
        self.output = output

    def dispatch(
        self,
        athlete_id: str,
        event_type: str,
        payload: dict[str, str],
        db: Session,
    ) -> SimpleNamespace:
        return SimpleNamespace(output=self.output, pending=False)


@pytest.fixture
def identity(db_session: Session, athlete_id: str) -> str:
    db_session.add(
        MessagingIdentityModel(
            id=str(uuid.uuid4()),
            athlete_id=athlete_id,
            channel="telegram",
            external_id="5150",
        )
    )
    db_session.commit()
    return "5150"


def build_gateway(
    db_session: Session,
    approvals: RecordingApprovals | None,
    coordinator: RecordingCoordinator,
    notifier: RecordingNotifier,
) -> MessagingGateway:
    channel = RecordingChannel()
    return MessagingGateway(
        db_session,
        {channel.name: channel},
        coordinator=coordinator,
        notifier=notifier,
        approvals=approvals,
    )


def test_armed_latch_routes_free_text_to_revise(
    db_session: Session, athlete_id: str, identity: str
) -> None:
    approvals = RecordingApprovals("tok-1")
    coordinator = RecordingCoordinator()
    notifier = RecordingNotifier()
    gateway = build_gateway(db_session, approvals, coordinator, notifier)

    gateway.handle_inbound("telegram", identity, "too much volume Wednesday")

    assert approvals.revisions == [
        (athlete_id, "telegram", identity, "tok-1", "too much volume Wednesday")
    ]
    assert coordinator.calls == []
    assert notifier.sent == []


def test_second_message_falls_back_to_normal_chat(
    db_session: Session, athlete_id: str, identity: str
) -> None:
    approvals = RecordingApprovals("tok-1")
    coordinator = RecordingCoordinator()
    notifier = RecordingNotifier()
    gateway = build_gateway(db_session, approvals, coordinator, notifier)

    gateway.handle_inbound("telegram", identity, "less volume")
    gateway.handle_inbound("telegram", identity, "how did last week go?")

    assert len(approvals.revisions) == 1
    assert coordinator.calls == [
        (athlete_id, "chat", {"message": "how did last week go?"})
    ]
    assert notifier.sent == [(athlete_id, "chat reply")]


def test_without_approvals_router_behaviour_is_unchanged(
    db_session: Session, athlete_id: str, identity: str
) -> None:
    coordinator = RecordingCoordinator()
    notifier = RecordingNotifier()
    gateway = build_gateway(db_session, None, coordinator, notifier)

    gateway.handle_inbound("telegram", identity, "hello")

    assert coordinator.calls == [(athlete_id, "chat", {"message": "hello"})]


def test_unknown_sender_never_consults_the_latch(
    db_session: Session, athlete_id: str
) -> None:
    approvals = RecordingApprovals("tok-1")
    coordinator = RecordingCoordinator()
    notifier = RecordingNotifier()
    gateway = build_gateway(db_session, approvals, coordinator, notifier)

    gateway.handle_inbound("telegram", "not-linked", "anything")

    assert approvals.pops == []
    assert approvals.revisions == []
    assert coordinator.calls == []


def build_gateway_with_commands(
    db_session: Session,
    coordinator: Any,
    notifier: RecordingNotifier,
    *,
    approvals: Any = None,
    commands: Any = None,
) -> MessagingGateway:
    channel = RecordingChannel()
    return MessagingGateway(
        db_session,
        {channel.name: channel},
        coordinator=coordinator,
        notifier=notifier,
        approvals=approvals,
        commands=commands,
    )


def test_handled_command_short_circuits_the_coordinator(
    db_session: Session, athlete_id: str, identity: str
) -> None:
    coordinator = RecordingCoordinator()
    notifier = RecordingNotifier()
    commands = RecordingCommands(handled=True)
    gateway = build_gateway_with_commands(
        db_session, coordinator, notifier, commands=commands
    )

    gateway.handle_inbound("telegram", identity, "/connect")

    assert commands.calls == [(athlete_id, "/connect")]
    assert coordinator.calls == []
    assert notifier.sent == []


def test_unhandled_command_falls_through_to_the_coach(
    db_session: Session, athlete_id: str, identity: str
) -> None:
    coordinator = RecordingCoordinator()
    notifier = RecordingNotifier()
    commands = RecordingCommands(handled=False)
    gateway = build_gateway_with_commands(
        db_session, coordinator, notifier, commands=commands
    )

    gateway.handle_inbound("telegram", identity, "/weird")

    assert coordinator.calls == [(athlete_id, "chat", {"message": "/weird"})]


def test_plain_text_never_reaches_the_command_router(
    db_session: Session, athlete_id: str, identity: str
) -> None:
    coordinator = RecordingCoordinator()
    notifier = RecordingNotifier()
    commands = RecordingCommands(handled=True)
    gateway = build_gateway_with_commands(
        db_session, coordinator, notifier, commands=commands
    )

    gateway.handle_inbound("telegram", identity, "how did last week go?")

    assert commands.calls == []
    assert coordinator.calls


def test_plan_proposal_output_goes_out_as_buttons(
    db_session: Session, athlete_id: str, identity: str
) -> None:
    plan = {"phase": "base", "sessions": []}
    coordinator = PlanCoordinator(
        {"question": None, "plan_proposal": plan, "plan_thread_id": "plan-thread"}
    )
    notifier = RecordingNotifier()
    approvals = RecordingApprovals(None)
    gateway = build_gateway_with_commands(
        db_session, coordinator, notifier, approvals=approvals
    )

    gateway.handle_inbound("telegram", identity, "yes")

    assert approvals.proposals == [(athlete_id, "plan-thread", plan)]
    assert notifier.sent == []


def test_question_and_plan_are_both_delivered(
    db_session: Session, athlete_id: str, identity: str
) -> None:
    plan = {"phase": "base", "sessions": []}
    coordinator = PlanCoordinator(
        {
            "question": "Here is the shape of it.",
            "plan_proposal": plan,
            "plan_thread_id": "plan-thread",
        }
    )
    notifier = RecordingNotifier()
    approvals = RecordingApprovals(None)
    gateway = build_gateway_with_commands(
        db_session, coordinator, notifier, approvals=approvals
    )

    gateway.handle_inbound("telegram", identity, "yes")

    assert notifier.sent == [(athlete_id, "Here is the shape of it.")]
    assert approvals.proposals == [(athlete_id, "plan-thread", plan)]


def test_missing_thread_id_is_not_sent_for_approval(
    db_session: Session, athlete_id: str, identity: str
) -> None:
    coordinator = PlanCoordinator(
        {"plan_proposal": {"sessions": []}, "plan_thread_id": None}
    )
    notifier = RecordingNotifier()
    approvals = RecordingApprovals(None)
    gateway = build_gateway_with_commands(
        db_session, coordinator, notifier, approvals=approvals
    )

    gateway.handle_inbound("telegram", identity, "yes")

    assert approvals.proposals == []
