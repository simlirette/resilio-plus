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
