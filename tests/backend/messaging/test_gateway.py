from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any

import pytest
from app.db.models import (
    AthleteModel,
    MessagingIdentityModel,
    MessagingLinkCodeModel,
)
from app.messaging import (
    InvalidLinkCodeError,
    MessagingGateway,
    MessagingPersistenceError,
    MessagingTransactionError,
    UnknownMessagingChannelError,
)
from sqlalchemy import func, select
from sqlalchemy.orm import Session

NOW = datetime(2026, 8, 18, 16, 0, tzinfo=timezone.utc)


class RecordingChannel:
    def __init__(self, name: str = "telegram") -> None:
        self.name = name
        self.sent: list[tuple[str, str]] = []
        self.formatted: list[str] = []

    def send(self, external_id: str, text: str) -> str:
        self.sent.append((external_id, text))
        return "provider-message-id"

    def send_with_buttons(
        self,
        external_id: str,
        text: str,
        buttons: list[Any],
    ) -> str:
        return self.send(external_id, text)

    def max_message_length(self) -> int:
        return 4096

    def format(self, text: str) -> str:
        self.formatted.append(text)
        return f"formatted:{text}"


class RecordingCoordinator:
    def __init__(self, output: dict[str, Any] | None = None) -> None:
        self.output = output
        self.calls: list[tuple[str, str, dict[str, str], Session]] = []

    def dispatch(
        self,
        athlete_id: str,
        event_type: str,
        payload: dict[str, str],
        db: Session,
    ) -> SimpleNamespace:
        self.calls.append((athlete_id, event_type, payload, db))
        return SimpleNamespace(output=self.output, pending=self.output is None)


class RecordingNotifier:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, Any]] = []

    def send(
        self,
        athlete_id: str,
        text: str,
        buttons: list[Any] | None = None,
    ) -> None:
        self.calls.append((athlete_id, text, buttons))


def _gateway(
    db_session: Session,
    *,
    output: dict[str, Any] | None = None,
    extra_channels: dict[str, RecordingChannel] | None = None,
) -> tuple[MessagingGateway, RecordingChannel, RecordingCoordinator, RecordingNotifier]:
    channel = RecordingChannel()
    coordinator = RecordingCoordinator(output)
    notifier = RecordingNotifier()
    channels = {"telegram": channel}
    channels.update(extra_channels or {})
    gateway = MessagingGateway(
        db_session,
        channels,
        coordinator=coordinator,
        notifier=notifier,
        clock=lambda: NOW,
    )
    return gateway, channel, coordinator, notifier


def _add_identity(
    db_session: Session,
    athlete_id: str,
    *,
    channel: str = "telegram",
    external_id: str = "chat-123",
    identity_id: str | None = None,
) -> MessagingIdentityModel:
    identity = MessagingIdentityModel(
        id=identity_id or str(uuid.uuid4()),
        athlete_id=athlete_id,
        channel=channel,
        external_id=external_id,
        verified_at=NOW,
    )
    db_session.add(identity)
    db_session.commit()
    return identity


def _add_link_code(
    db_session: Session,
    athlete_id: str,
    *,
    code: str = "LINK-123",
    expires_at: datetime | None = None,
) -> MessagingLinkCodeModel:
    link_code = MessagingLinkCodeModel(
        code=code,
        athlete_id=athlete_id,
        expires_at=expires_at or NOW + timedelta(minutes=15),
    )
    db_session.add(link_code)
    db_session.commit()
    return link_code


def _add_athlete(db_session: Session, athlete_id: str) -> str:
    db_session.add(
        AthleteModel(
            id=athlete_id,
            name="Second Messaging Athlete",
            age=31,
            sex="M",
            weight_kg=75.0,
            height_cm=178.0,
            primary_sport="cycling",
            hours_per_week=9.0,
            sports_json='["cycling"]',
            goals_json='["fitness"]',
            available_days_json="[0, 2, 4]",
            equipment_json="[]",
        )
    )
    db_session.commit()
    return athlete_id


def test_unknown_identity_sends_formatted_link_instruction_without_side_effects(
    db_session: Session,
) -> None:
    gateway, channel, coordinator, notifier = _gateway(db_session)

    gateway.handle_inbound("telegram", "unknown-chat", "hello")

    assert len(channel.sent) == 1
    assert channel.sent[0][0] == "unknown-chat"
    assert channel.sent[0][1].startswith("formatted:")
    assert "link code" in channel.sent[0][1].lower()
    assert channel.formatted == [channel.sent[0][1].removeprefix("formatted:")]
    assert coordinator.calls == []
    assert notifier.calls == []
    assert db_session.scalar(select(func.count()).select_from(AthleteModel)) == 0
    assert db_session.scalar(select(func.count()).select_from(MessagingIdentityModel)) == 0


def test_resolve_athlete_matches_exact_verified_channel_and_external_id(
    db_session: Session, athlete_id: str
) -> None:
    gateway, _, _, _ = _gateway(
        db_session,
        extra_channels={"sms": RecordingChannel("sms")},
    )
    _add_identity(db_session, athlete_id, channel="telegram", external_id="same-id")

    assert gateway.resolve_athlete("telegram", "same-id") == athlete_id
    assert gateway.resolve_athlete("telegram", "other-id") is None
    assert gateway.resolve_athlete("sms", "same-id") is None


@pytest.mark.parametrize(
    ("output", "expected"),
    [
        ({"final_response": "Your plan is ready.", "question": "Ignored?"}, "Your plan is ready."),
        ({"final_response": "", "question": "How did that feel?"}, "How did that feel?"),
    ],
)
def test_known_identity_dispatches_exact_chat_event_and_sends_real_text_output(
    db_session: Session,
    athlete_id: str,
    output: dict[str, Any],
    expected: str,
) -> None:
    _add_identity(db_session, athlete_id)
    gateway, channel, coordinator, notifier = _gateway(db_session, output=output)

    gateway.handle_inbound("telegram", "chat-123", "My legs feel good")

    assert coordinator.calls == [
        (athlete_id, "chat", {"message": "My legs feel good"}, db_session)
    ]
    assert notifier.calls == [(athlete_id, expected, None)]
    assert channel.sent == []


@pytest.mark.parametrize("output", [None, {}, {"internal_state": {"step": 2}}])
def test_known_identity_does_not_fabricate_text_for_pending_or_internal_output(
    db_session: Session,
    athlete_id: str,
    output: dict[str, Any] | None,
) -> None:
    _add_identity(db_session, athlete_id)
    gateway, _, coordinator, notifier = _gateway(db_session, output=output)

    gateway.handle_inbound("telegram", "chat-123", "hello")

    assert len(coordinator.calls) == 1
    assert notifier.calls == []


def test_unknown_channel_raises_without_dispatch_send_or_database_mutation(
    db_session: Session,
) -> None:
    gateway, channel, coordinator, notifier = _gateway(db_session)

    with pytest.raises(UnknownMessagingChannelError, match="signal"):
        gateway.handle_inbound("signal", "external", "hello")

    assert channel.sent == []
    assert coordinator.calls == []
    assert notifier.calls == []
    assert db_session.scalar(select(func.count()).select_from(MessagingIdentityModel)) == 0


def test_valid_link_code_is_consumed_and_creates_uuid_identity(
    db_session: Session, athlete_id: str
) -> None:
    _add_link_code(db_session, athlete_id)
    gateway, _, _, _ = _gateway(db_session)

    linked_athlete_id = gateway.link_identity("telegram", "chat-123", "LINK-123")

    assert linked_athlete_id == athlete_id
    link_code = db_session.get(MessagingLinkCodeModel, "LINK-123")
    assert link_code is not None
    assert link_code.consumed_at is not None
    identity = db_session.scalar(
        select(MessagingIdentityModel).where(
            MessagingIdentityModel.channel == "telegram",
            MessagingIdentityModel.external_id == "chat-123",
        )
    )
    assert identity is not None
    assert identity.athlete_id == athlete_id
    assert str(uuid.UUID(identity.id)) == identity.id


@pytest.mark.parametrize(
    "expires_at",
    [NOW - timedelta(microseconds=1), NOW],
    ids=["expired", "expiry-equality"],
)
def test_expired_link_code_has_same_invalid_result_and_is_not_consumed(
    db_session: Session,
    athlete_id: str,
    expires_at: datetime,
) -> None:
    _add_link_code(db_session, athlete_id, expires_at=expires_at)
    gateway, _, _, _ = _gateway(db_session)

    with pytest.raises(InvalidLinkCodeError, match="Invalid or expired link code"):
        gateway.link_identity("telegram", "chat-123", "LINK-123")

    db_session.expire_all()
    link_code = db_session.get(MessagingLinkCodeModel, "LINK-123")
    assert link_code is not None
    assert link_code.consumed_at is None


def test_missing_and_consumed_link_codes_have_same_invalid_result(
    db_session: Session, athlete_id: str
) -> None:
    _add_link_code(db_session, athlete_id)
    gateway, _, _, _ = _gateway(db_session)
    assert gateway.link_identity("telegram", "first-chat", "LINK-123") == athlete_id

    messages: list[str] = []
    for external_id, code in (("second-chat", "MISSING"), ("third-chat", "LINK-123")):
        with pytest.raises(InvalidLinkCodeError) as caught:
            gateway.link_identity("telegram", external_id, code)
        messages.append(str(caught.value))

    assert messages == ["Invalid or expired link code"] * 2
    assert gateway.resolve_athlete("telegram", "second-chat") is None
    assert gateway.resolve_athlete("telegram", "third-chat") is None


def test_existing_identity_for_same_athlete_is_idempotent_and_consumes_fresh_code(
    db_session: Session, athlete_id: str
) -> None:
    _add_identity(db_session, athlete_id)
    _add_link_code(db_session, athlete_id, code="FRESH-CODE")
    gateway, _, _, _ = _gateway(db_session)

    assert gateway.link_identity("telegram", "chat-123", "FRESH-CODE") == athlete_id

    db_session.expire_all()
    link_code = db_session.get(MessagingLinkCodeModel, "FRESH-CODE")
    assert link_code is not None
    assert link_code.consumed_at is not None
    assert (
        db_session.scalar(select(func.count()).select_from(MessagingIdentityModel)) == 1
    )


def test_cross_athlete_takeover_keeps_owner_and_losing_code_unconsumed(
    db_session: Session, athlete_id: str
) -> None:
    other_athlete_id = _add_athlete(db_session, "other-athlete")
    _add_identity(db_session, athlete_id)
    _add_link_code(db_session, other_athlete_id, code="OTHER-CODE")
    gateway, _, _, _ = _gateway(db_session)

    with pytest.raises(InvalidLinkCodeError) as caught:
        gateway.link_identity("telegram", "chat-123", "OTHER-CODE")

    assert str(caught.value) == "Invalid or expired link code"
    assert caught.value.__suppress_context__
    db_session.expire_all()
    assert gateway.resolve_athlete("telegram", "chat-123") == athlete_id
    link_code = db_session.get(MessagingLinkCodeModel, "OTHER-CODE")
    assert link_code is not None
    assert link_code.consumed_at is None


def test_link_identity_rejects_an_existing_transaction_without_touching_it(
    db_session: Session,
    athlete_id: str,
) -> None:
    link_code = _add_link_code(db_session, athlete_id, code="CLEAN-SESSION-ONLY")
    db_session.refresh(link_code)
    pending_athlete = AthleteModel(
        id="pending-unrelated-athlete",
        name="Pending Athlete",
        age=29,
        sex="F",
        weight_kg=60.0,
        height_cm=168.0,
        primary_sport="running",
        hours_per_week=7.0,
        sports_json='["running"]',
        goals_json='["fitness"]',
        available_days_json="[1, 3, 5]",
        equipment_json="[]",
    )
    db_session.add(pending_athlete)
    gateway, _, _, _ = _gateway(db_session)

    with pytest.raises(
        MessagingTransactionError,
        match="requires a clean database session",
    ):
        gateway.link_identity("telegram", "transaction-chat", "CLEAN-SESSION-ONLY")

    assert db_session.in_transaction()
    assert pending_athlete in db_session.new
    assert pending_athlete.name == "Pending Athlete"
    assert link_code.consumed_at is None


def test_unrelated_identity_constraint_failure_is_sanitized_and_rolls_back_claim(
    db_session: Session,
    athlete_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _add_identity(
        db_session,
        athlete_id,
        external_id="existing-chat",
        identity_id="duplicate-identity-id",
    )
    _add_link_code(db_session, athlete_id, code="ROLLBACK-CODE")
    gateway, _, _, _ = _gateway(db_session)
    monkeypatch.setattr(
        "app.messaging.gateway.uuid.uuid4",
        lambda: "duplicate-identity-id",
    )

    with pytest.raises(MessagingPersistenceError) as caught:
        gateway.link_identity("telegram", "new-chat", "ROLLBACK-CODE")

    message = str(caught.value)
    assert message == "Unable to persist messaging identity"
    assert caught.value.__suppress_context__
    for sensitive in (
        athlete_id,
        "new-chat",
        "ROLLBACK-CODE",
        "INSERT",
        "messaging_identities",
    ):
        assert sensitive not in message
    db_session.expire_all()
    link_code = db_session.get(MessagingLinkCodeModel, "ROLLBACK-CODE")
    assert link_code is not None
    assert link_code.consumed_at is None
    assert gateway.resolve_athlete("telegram", "new-chat") is None
