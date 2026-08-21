from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

import app.messaging as messaging
import pytest
from app.db.models import AthleteModel, MessagingIdentityModel, OutboundMessageModel
from app.messaging import (
    Button,
    EmptyNotificationError,
    MessagingIdentityNotFoundError,
    NotificationDeliveryError,
    NotificationFormattingError,
    NotificationPersistenceError,
    NotificationService,
    NotificationTransactionError,
    UnknownMessagingChannelError,
)
from sqlalchemy import Engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

NOW = datetime(2026, 8, 18, 17, 0, tzinfo=timezone.utc)


class RecordingChannel:
    def __init__(
        self,
        name: str,
        *,
        max_length: int = 100,
        formatter: Callable[[str], str] | None = None,
        fail_on_call: int | None = None,
    ) -> None:
        self.name = name
        self._max_length = max_length
        self._formatter = formatter or (lambda text: text)
        self._fail_on_call = fail_on_call
        self.calls: list[tuple[str, str, str, list[Button] | None]] = []
        self.format_inputs: list[str] = []

    def send(self, external_id: str, text: str) -> str:
        return self._accept("send", external_id, text, None)

    def send_with_buttons(
        self,
        external_id: str,
        text: str,
        buttons: list[Button],
    ) -> str:
        return self._accept("send_with_buttons", external_id, text, buttons)

    def max_message_length(self) -> int:
        return self._max_length

    def format(self, text: str) -> str:
        self.format_inputs.append(text)
        return self._formatter(text)

    def _accept(
        self,
        method: str,
        external_id: str,
        text: str,
        buttons: list[Button] | None,
    ) -> str:
        call_number = len(self.calls) + 1
        self.calls.append((method, external_id, text, buttons))
        if self._fail_on_call == call_number:
            raise RuntimeError("provider exploded with sensitive details")
        return f"{self.name}-provider-{call_number}"


def _add_identity(
    db_session: Session,
    athlete_id: str,
    *,
    channel: str = "telegram",
    external_id: str = "chat-123",
    identity_id: str = "identity-1",
    created_at: datetime = NOW,
) -> None:
    db_session.add(
        MessagingIdentityModel(
            id=identity_id,
            athlete_id=athlete_id,
            channel=channel,
            external_id=external_id,
            verified_at=created_at,
            created_at=created_at,
        )
    )
    db_session.commit()


def test_notification_service_contract_is_public() -> None:
    expected = {
        "EmptyNotificationError",
        "MessagingIdentityNotFoundError",
        "NotificationDeliveryError",
        "NotificationFormattingError",
        "NotificationPersistenceError",
        "NotificationService",
        "NotificationTransactionError",
    }

    assert expected <= set(messaging.__all__)
    assert all(hasattr(messaging, name) for name in expected)


def test_send_rejects_caller_transaction_before_any_database_touch(
    db_session: Session,
    athlete_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _add_identity(db_session, athlete_id)
    athlete = db_session.get(AthleteModel, athlete_id)
    assert athlete is not None
    athlete.name = "Pending caller-owned name"
    channel = RecordingChannel("telegram")
    service = NotificationService(db_session, {"telegram": channel})

    def forbidden_database_touch(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("notification service touched caller transaction")

    for method_name in ("execute", "flush", "commit", "rollback"):
        monkeypatch.setattr(db_session, method_name, forbidden_database_touch)

    with pytest.raises(
        NotificationTransactionError,
        match="requires a clean database session",
    ):
        service.send(athlete_id, "Do not touch caller state")

    assert db_session.in_transaction()
    assert athlete in db_session.dirty
    assert athlete.name == "Pending caller-owned name"
    assert channel.calls == []


@pytest.mark.parametrize(
    ("scenario", "expected_error"),
    [
        ("identity-not-found", MessagingIdentityNotFoundError),
        ("unknown-channel", UnknownMessagingChannelError),
        ("formatting-failure", NotificationFormattingError),
        ("first-provider-failure", NotificationDeliveryError),
    ],
)
def test_pre_delivery_failures_leave_owned_session_clean(
    db_session: Session,
    athlete_id: str,
    scenario: str,
    expected_error: type[Exception],
) -> None:
    identity_channel = "telegram"
    if scenario != "identity-not-found":
        if scenario == "unknown-channel":
            identity_channel = "signal"
        _add_identity(db_session, athlete_id, channel=identity_channel)

    if scenario == "formatting-failure":
        channel = RecordingChannel("telegram", max_length=0)
    elif scenario == "first-provider-failure":
        channel = RecordingChannel("telegram", fail_on_call=1)
    else:
        channel = RecordingChannel("telegram")
    service = NotificationService(db_session, {"telegram": channel})

    with pytest.raises(expected_error):
        service.send(athlete_id, "Clean up the owned lookup transaction")

    assert not db_session.in_transaction()


def test_lookup_database_failure_is_sanitized_and_leaves_session_clean(
    db_session: Session,
    athlete_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    channel = RecordingChannel("telegram")
    service = NotificationService(db_session, {"telegram": channel})
    real_execute = db_session.execute

    def fail_lookup(*_args: object, **_kwargs: object) -> None:
        real_execute(select(1))
        raise IntegrityError(
            "SELECT SECRET-SQL",
            {"athlete": athlete_id},
            RuntimeError("database lookup secret"),
        )

    monkeypatch.setattr(db_session, "execute", fail_lookup)

    with pytest.raises(NotificationPersistenceError) as caught:
        service.send(athlete_id, "Lookup should fail safely")

    assert str(caught.value) == "Unable to persist outbound notification audit"
    assert caught.value.__suppress_context__
    assert not db_session.in_transaction()
    assert channel.calls == []


def test_send_uses_verified_identity_and_audits_provider_accepted_message(
    db_session: Session,
    athlete_id: str,
) -> None:
    _add_identity(db_session, athlete_id)
    channel = RecordingChannel("telegram")
    service = NotificationService(db_session, {"telegram": channel})

    provider_ids = service.send(athlete_id, "Recovery run today.", kind="daily_reminder")

    assert provider_ids == ["telegram-provider-1"]
    assert channel.calls == [("send", "chat-123", "Recovery run today.", None)]
    rows = db_session.scalars(select(OutboundMessageModel)).all()
    assert len(rows) == 1
    row = rows[0]
    assert str(uuid.UUID(row.id)) == row.id
    assert row.athlete_id == athlete_id
    assert row.channel == "telegram"
    assert row.external_id == "chat-123"
    assert row.provider_message_id == "telegram-provider-1"
    assert row.body == "Recovery run today."
    assert row.kind == "daily_reminder"
    assert row.created_at is not None


def test_send_selects_the_oldest_verified_identity_deterministically(
    db_session: Session,
    athlete_id: str,
) -> None:
    _add_identity(
        db_session,
        athlete_id,
        channel="telegram",
        external_id="newer-chat",
        identity_id="identity-newer",
        created_at=NOW,
    )
    _add_identity(
        db_session,
        athlete_id,
        channel="sms",
        external_id="oldest-phone",
        identity_id="identity-oldest",
        created_at=NOW - timedelta(days=1),
    )
    telegram = RecordingChannel("telegram")
    sms = RecordingChannel("sms")
    service = NotificationService(
        db_session,
        {"telegram": telegram, "sms": sms},
    )

    assert service.send(athlete_id, "Stable route") == ["sms-provider-1"]
    assert sms.calls == [("send", "oldest-phone", "Stable route", None)]
    assert telegram.calls == []


def test_send_chunks_to_channel_limit_and_puts_buttons_only_on_final_chunk(
    db_session: Session,
    athlete_id: str,
) -> None:
    _add_identity(db_session, athlete_id)
    channel = RecordingChannel("telegram", max_length=5)
    service = NotificationService(db_session, {"telegram": channel})
    buttons = [Button(label="Approuver", token="opaque-approve")]

    provider_ids = service.send(
        athlete_id,
        "abcdefghijkl",
        buttons,
        kind="weekly_plan",
    )

    assert provider_ids == [
        "telegram-provider-1",
        "telegram-provider-2",
        "telegram-provider-3",
    ]
    assert channel.calls == [
        ("send", "chat-123", "abcde", None),
        ("send", "chat-123", "fghij", None),
        ("send_with_buttons", "chat-123", "kl", buttons),
    ]
    rows = db_session.scalars(select(OutboundMessageModel)).all()
    assert len(rows) == 3
    assert {row.provider_message_id for row in rows} == set(provider_ids)
    assert {row.body for row in rows} == {"abcde", "fghij", "kl"}
    assert {row.kind for row in rows} == {"weekly_plan"}


def test_send_rechunks_until_every_formatted_body_fits_provider_limit(
    db_session: Session,
    athlete_id: str,
) -> None:
    _add_identity(db_session, athlete_id)
    channel = RecordingChannel(
        "telegram",
        max_length=10,
        formatter=lambda text: text.replace("x", "xx"),
    )
    service = NotificationService(db_session, {"telegram": channel})

    provider_ids = service.send(athlete_id, "x" * 12)

    sent_bodies = [call[2] for call in channel.calls]
    assert sent_bodies == ["x" * 10, "x" * 10, "x" * 4]
    assert all(len(body) <= channel.max_message_length() for body in sent_bodies)
    rows = db_session.scalars(select(OutboundMessageModel)).all()
    rows_by_provider_id = {row.provider_message_id: row for row in rows}
    assert [rows_by_provider_id[item].body for item in provider_ids] == sent_bodies


@pytest.mark.parametrize("text", ["", "  \n\t"], ids=["empty", "whitespace"])
def test_send_rejects_empty_text_without_provider_or_audit_side_effects(
    db_session: Session,
    athlete_id: str,
    text: str,
) -> None:
    _add_identity(db_session, athlete_id)
    channel = RecordingChannel("telegram")
    service = NotificationService(db_session, {"telegram": channel})

    with pytest.raises(EmptyNotificationError, match="must not be empty"):
        service.send(athlete_id, text)

    assert channel.calls == []
    assert db_session.scalars(select(OutboundMessageModel)).all() == []


def test_send_requires_a_verified_identity_without_fabricating_a_destination(
    db_session: Session,
    athlete_id: str,
) -> None:
    channel = RecordingChannel("telegram")
    service = NotificationService(db_session, {"telegram": channel})

    with pytest.raises(MessagingIdentityNotFoundError, match="No verified messaging identity"):
        service.send(athlete_id, "Do not invent a destination")

    assert channel.calls == []
    assert db_session.scalars(select(OutboundMessageModel)).all() == []


def test_send_rejects_identity_for_an_unconfigured_channel_without_fallback(
    db_session: Session,
    athlete_id: str,
) -> None:
    _add_identity(db_session, athlete_id, channel="signal", external_id="signal-user")
    telegram = RecordingChannel("telegram")
    service = NotificationService(db_session, {"telegram": telegram})

    with pytest.raises(UnknownMessagingChannelError, match="signal"):
        service.send(athlete_id, "Do not route this elsewhere")

    assert telegram.calls == []
    assert db_session.scalars(select(OutboundMessageModel)).all() == []


def test_send_rejects_channel_registered_under_the_wrong_name(
    db_session: Session,
    athlete_id: str,
) -> None:
    _add_identity(db_session, athlete_id, channel="telegram")
    misregistered_channel = RecordingChannel("sms")
    service = NotificationService(db_session, {"telegram": misregistered_channel})

    with pytest.raises(UnknownMessagingChannelError, match="telegram"):
        service.send(athlete_id, "Do not use a misregistered adapter")

    assert misregistered_channel.calls == []
    assert db_session.scalars(select(OutboundMessageModel)).all() == []


def test_partial_provider_failure_keeps_accepted_chunk_audit_durable(
    sqlite_engine: Engine,
    db_session: Session,
    athlete_id: str,
) -> None:
    _add_identity(db_session, athlete_id)
    channel = RecordingChannel("telegram", max_length=5, fail_on_call=2)
    service = NotificationService(db_session, {"telegram": channel})

    with pytest.raises(NotificationDeliveryError) as caught:
        service.send(athlete_id, "abcdefghij", kind="weekly_plan")

    assert caught.value.accepted_provider_ids == ("telegram-provider-1",)
    assert str(caught.value) == "Notification delivery failed after 1 accepted chunk(s)"
    assert "provider exploded" not in str(caught.value)
    assert len(channel.calls) == 2
    with Session(sqlite_engine) as verification_session:
        rows = verification_session.scalars(select(OutboundMessageModel)).all()
        assert len(rows) == 1
        assert rows[0].provider_message_id == "telegram-provider-1"
        assert rows[0].body == "abcde"
        assert rows[0].kind == "weekly_plan"


def test_audit_commit_failure_rolls_back_and_raises_sanitized_domain_error(
    sqlite_engine: Engine,
    db_session: Session,
    athlete_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _add_identity(db_session, athlete_id)
    channel = RecordingChannel("telegram")
    service = NotificationService(db_session, {"telegram": channel})

    def fail_commit() -> None:
        raise IntegrityError(
            "INSERT INTO outbound_messages SECRET-SQL",
            {"athlete": athlete_id, "external": "chat-123"},
            RuntimeError("database secret"),
        )

    monkeypatch.setattr(db_session, "commit", fail_commit)

    with pytest.raises(NotificationPersistenceError) as caught:
        service.send(athlete_id, "Accepted but audit failed", kind="coach_reply")

    assert str(caught.value) == "Unable to persist outbound notification audit"
    assert caught.value.__suppress_context__
    assert channel.calls == [("send", "chat-123", "Accepted but audit failed", None)]
    assert not db_session.in_transaction()
    with Session(sqlite_engine) as verification_session:
        assert verification_session.scalars(select(OutboundMessageModel)).all() == []


def test_audit_failure_exposes_non_secret_reconciliation_handles(
    sqlite_engine: Engine,
    db_session: Session,
    athlete_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _add_identity(db_session, athlete_id)
    channel = RecordingChannel("telegram", max_length=5)
    service = NotificationService(db_session, {"telegram": channel})
    real_commit = db_session.commit
    audit_commit_count = 0

    def fail_second_audit_commit() -> None:
        nonlocal audit_commit_count
        audit_commit_count += 1
        if audit_commit_count == 2:
            raise IntegrityError(
                "INSERT INTO outbound_messages SECRET-SQL",
                {"external": "chat-123"},
                RuntimeError("database secret"),
            )
        real_commit()

    monkeypatch.setattr(db_session, "commit", fail_second_audit_commit)

    with pytest.raises(NotificationPersistenceError) as caught:
        service.send(athlete_id, "abcdefghij", kind="weekly_plan")

    assert caught.value.unaudited_provider_id == "telegram-provider-2"
    assert caught.value.audited_provider_ids == ("telegram-provider-1",)
    assert str(caught.value) == "Unable to persist outbound notification audit"
    assert "telegram-provider" not in str(caught.value)
    assert not db_session.in_transaction()
    with Session(sqlite_engine) as verification_session:
        rows = verification_session.scalars(select(OutboundMessageModel)).all()
        assert len(rows) == 1
        assert rows[0].provider_message_id == "telegram-provider-1"


@pytest.mark.parametrize(
    ("max_length", "text"),
    [
        (0, "ordinary text"),
        (10, "- protected bullet content that cannot fit\n"),
    ],
    ids=["invalid-provider-limit", "oversized-protected-unit"],
)
def test_chunking_failures_are_sanitized_before_any_provider_send(
    db_session: Session,
    athlete_id: str,
    max_length: int,
    text: str,
) -> None:
    _add_identity(db_session, athlete_id)
    channel = RecordingChannel("telegram", max_length=max_length)
    service = NotificationService(db_session, {"telegram": channel})

    with pytest.raises(NotificationFormattingError) as caught:
        service.send(athlete_id, text)

    assert str(caught.value) == "Notification cannot be formatted within the channel limit"
    assert channel.calls == []
    assert db_session.scalars(select(OutboundMessageModel)).all() == []


def test_recursive_chunk_failure_after_format_expands_raw_fitting_bullet_is_sanitized(
    db_session: Session,
    athlete_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _add_identity(db_session, athlete_id)
    raw_fitting_bullet = "- abcde\n"
    channel = RecordingChannel(
        "telegram",
        max_length=10,
        formatter=lambda text: text * 2,
    )
    service = NotificationService(db_session, {"telegram": channel})
    real_chunk_message = messaging.chunk_message
    chunk_calls = 0

    def fail_recursive_chunk(text: str, max_length: int) -> list[str]:
        nonlocal chunk_calls
        chunk_calls += 1
        if chunk_calls == 2:
            raise ValueError("recursive chunker leaked internal details")
        return real_chunk_message(text, max_length)

    monkeypatch.setattr(
        "app.messaging.notification_service.chunk_message",
        fail_recursive_chunk,
    )

    with pytest.raises(NotificationFormattingError) as caught:
        service.send(athlete_id, raw_fitting_bullet)

    assert len(raw_fitting_bullet) <= channel.max_message_length()
    assert len(channel.format(raw_fitting_bullet)) > channel.max_message_length()
    assert str(caught.value) == "Notification cannot be formatted within the channel limit"
    assert chunk_calls == 2
    assert channel.calls == []


def test_fixed_oversized_formatter_fails_boundedly_without_recursion_error(
    db_session: Session,
    athlete_id: str,
) -> None:
    _add_identity(db_session, athlete_id)
    max_length = 1_500
    channel = RecordingChannel(
        "telegram",
        max_length=max_length,
        formatter=lambda _text: "y" * (max_length + 1),
    )
    service = NotificationService(db_session, {"telegram": channel})

    with pytest.raises(NotificationFormattingError):
        service.send(athlete_id, "x" * max_length)

    assert channel.calls == []
    assert not db_session.in_transaction()


def test_send_delivers_and_audits_a_12000_character_plan(
    sqlite_engine: Engine,
    db_session: Session,
    athlete_id: str,
) -> None:
    _add_identity(db_session, athlete_id)
    channel = RecordingChannel("telegram", max_length=500)
    service = NotificationService(db_session, {"telegram": channel})
    plan_fragment = "Run easy today. Recover fully tomorrow.\n\n"
    text = (plan_fragment * 400)[:12_000]
    buttons = [Button(label="Approuver", token="opaque-plan-approval")]

    provider_ids = service.send(athlete_id, text, buttons, kind="weekly_plan")

    assert len(text) == 12_000
    assert len(provider_ids) == len(channel.calls) > 1
    assert "".join(call[2] for call in channel.calls) == text
    assert all(len(call[2]) <= channel.max_message_length() for call in channel.calls)
    assert all(call[0] == "send" for call in channel.calls[:-1])
    assert channel.calls[-1][0] == "send_with_buttons"
    assert channel.calls[-1][3] == buttons
    with Session(sqlite_engine) as verification_session:
        rows = verification_session.scalars(select(OutboundMessageModel)).all()
        assert len(rows) == len(provider_ids)
        assert {row.provider_message_id for row in rows} == set(provider_ids)
        assert {row.kind for row in rows} == {"weekly_plan"}
