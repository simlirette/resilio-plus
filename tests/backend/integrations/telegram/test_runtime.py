from __future__ import annotations

from collections.abc import Mapping
from contextlib import nullcontext
from typing import Any

import pytest
from app.db.models import AthleteModel, MessagingIdentityModel
from app.integrations.telegram.channel import TelegramChannel
from app.integrations.telegram.client import TelegramBotClient
from app.integrations.telegram.runtime import (
    TelegramConfigurationError,
    TelegramUpdateProcessor,
    build_telegram_runtime,
    close_telegram_runtime,
    get_telegram_runtime,
)
from app.messaging.gateway import InvalidLinkCodeError
from sqlalchemy import select
from sqlalchemy.orm import Session


class EventClient:
    def __init__(
        self,
        events: list[tuple[object, ...]],
        *,
        fail_typing: bool = False,
        fail_callback: bool = False,
    ) -> None:
        self._events = events
        self._fail_typing = fail_typing
        self._fail_callback = fail_callback

    def send_message(
        self,
        chat_id: str,
        text: str,
        *,
        reply_markup: dict[str, object] | None = None,
    ) -> str:
        self._events.append(("send", chat_id, text, reply_markup))
        return "provider-1"

    def send_chat_action(self, chat_id: str, action: str = "typing") -> bool:
        self._events.append(("action", chat_id, action))
        if self._fail_typing:
            raise RuntimeError("typing unavailable")
        return True

    def answer_callback_query(self, callback_query_id: str) -> bool:
        self._events.append(("callback", callback_query_id))
        if self._fail_callback:
            raise RuntimeError("callback acknowledgement unavailable")
        return True


class KnownGateway:
    def __init__(self, events: list[tuple[object, ...]]) -> None:
        self._events = events

    def resolve_athlete(self, channel: str, external_id: str) -> str | None:
        self._events.append(("resolve", channel, external_id))
        return "athlete-1"

    def link_identity(
        self,
        channel: str,
        external_id: str,
        link_code: str,
    ) -> str:
        raise AssertionError("known senders must not enter the link flow")

    def handle_inbound(self, channel: str, external_id: str, text: str) -> None:
        self._events.append(("handle", channel, external_id, text))


class LinkableGateway:
    def __init__(
        self,
        events: list[tuple[object, ...]],
        *,
        valid_code: str | None = None,
    ) -> None:
        self._events = events
        self._valid_code = valid_code

    def resolve_athlete(self, channel: str, external_id: str) -> str | None:
        self._events.append(("resolve", channel, external_id))
        return None

    def link_identity(
        self,
        channel: str,
        external_id: str,
        link_code: str,
    ) -> str:
        self._events.append(("link", channel, external_id, link_code))
        if link_code != self._valid_code:
            raise InvalidLinkCodeError
        return "athlete-1"

    def handle_inbound(self, channel: str, external_id: str, text: str) -> None:
        self._events.append(("handle", channel, external_id, text))


class DatabaseGateway:
    def __init__(self, db: Session, events: list[tuple[object, ...]]) -> None:
        self._db = db
        self._events = events

    def resolve_athlete(self, channel: str, external_id: str) -> str | None:
        with self._db.begin():
            return self._db.scalar(
                select(MessagingIdentityModel.athlete_id).where(
                    MessagingIdentityModel.channel == channel,
                    MessagingIdentityModel.external_id == external_id,
                )
            )

    def link_identity(
        self,
        channel: str,
        external_id: str,
        link_code: str,
    ) -> str:
        raise InvalidLinkCodeError

    def handle_inbound(self, channel: str, external_id: str, text: str) -> None:
        self._events.append(("handle", channel, external_id, text))


def test_message_sends_typing_before_dispatching_known_sender() -> None:
    events: list[tuple[object, ...]] = []
    gateway = KnownGateway(events)
    processor = TelegramUpdateProcessor(
        channel=TelegramChannel(EventClient(events)),
        session_factory=lambda: nullcontext(object()),
        gateway_factory=lambda _db: gateway,
    )

    processor.process_update(
        {
            "update_id": 10,
            "message": {
                "chat": {"id": 12345, "type": "private"},
                "text": "How should I train?",
            },
        }
    )

    assert events == [
        ("resolve", "telegram", "12345"),
        ("action", "12345", "typing"),
        ("handle", "telegram", "12345", "How should I train?"),
    ]


def test_typing_failure_does_not_drop_inbound_message() -> None:
    events: list[tuple[object, ...]] = []
    gateway = KnownGateway(events)
    processor = TelegramUpdateProcessor(
        channel=TelegramChannel(EventClient(events, fail_typing=True)),
        session_factory=lambda: nullcontext(object()),
        gateway_factory=lambda _db: gateway,
    )

    processor.process_update(
        {
            "message": {
                "chat": {"id": 12345, "type": "private"},
                "text": "Still process this",
            }
        }
    )

    assert events[-1] == ("handle", "telegram", "12345", "Still process this")


def test_unknown_sender_can_redeem_one_time_link_code() -> None:
    events: list[tuple[object, ...]] = []
    gateway = LinkableGateway(events, valid_code="LINK42")
    processor = TelegramUpdateProcessor(
        channel=TelegramChannel(EventClient(events)),
        session_factory=lambda: nullcontext(object()),
        gateway_factory=lambda _db: gateway,
    )

    processor.process_update(
        {
            "message": {
                "chat": {"id": 12345, "type": "private"},
                "text": "  LINK42  ",
            }
        }
    )

    assert events == [
        ("resolve", "telegram", "12345"),
        ("link", "telegram", "12345", "LINK42"),
        ("send", "12345", "Telegram connected to Resilio.", None),
    ]


@pytest.mark.parametrize(
    "chat",
    [
        pytest.param({"id": 12345}, id="missing-type"),
        pytest.param({"id": -12345, "type": "group"}, id="group"),
        pytest.param(
            {"id": -10012345, "type": "supergroup"},
            id="supergroup",
        ),
        pytest.param({"id": -10012345, "type": "channel"}, id="channel"),
    ],
)
def test_non_private_message_never_reaches_identity_gateway(
    chat: dict[str, object],
) -> None:
    events: list[tuple[object, ...]] = []
    gateway = LinkableGateway(events, valid_code="LINK42")
    processor = TelegramUpdateProcessor(
        channel=TelegramChannel(EventClient(events)),
        session_factory=lambda: nullcontext(object()),
        gateway_factory=lambda _db: gateway,
    )

    processor.process_update(
        {"message": {"chat": chat, "text": "LINK42"}}
    )

    assert events == []


def test_bootstrap_chat_links_existing_admin_idempotently(db_session: Session) -> None:
    db_session.add(
        AthleteModel(
            id="admin-athlete",
            name="Admin Athlete",
            age=35,
            sex="M",
            weight_kg=75.0,
            height_cm=180.0,
            primary_sport="running",
            hours_per_week=8.0,
            sports_json='["running"]',
            goals_json='["stay healthy"]',
            available_days_json="[1, 3, 5]",
            equipment_json="[]",
        )
    )
    db_session.commit()
    events: list[tuple[object, ...]] = []
    processor = TelegramUpdateProcessor(
        channel=TelegramChannel(EventClient(events)),
        session_factory=lambda: nullcontext(db_session),
        gateway_factory=lambda db: DatabaseGateway(db, events),
        bootstrap_chat_id="12345",
        admin_athlete_id="admin-athlete",
    )
    update = {
        "message": {
            "chat": {"id": 12345, "type": "private"},
            "text": "Hello coach",
        }
    }

    processor.process_update(update)
    processor.process_update(update)

    identities = db_session.scalars(select(MessagingIdentityModel)).all()
    assert [(identity.athlete_id, identity.external_id) for identity in identities] == [
        ("admin-athlete", "12345")
    ]
    assert events.count(("handle", "telegram", "12345", "Hello coach")) == 2


def test_bootstrap_never_creates_missing_admin_athlete(db_session: Session) -> None:
    events: list[tuple[object, ...]] = []
    processor = TelegramUpdateProcessor(
        channel=TelegramChannel(EventClient(events)),
        session_factory=lambda: nullcontext(db_session),
        gateway_factory=lambda db: DatabaseGateway(db, events),
        bootstrap_chat_id="12345",
        admin_athlete_id="missing-admin",
    )

    processor.process_update(
        {
            "message": {
                "chat": {"id": 12345, "type": "private"},
                "text": "Hello coach",
            }
        }
    )

    assert db_session.scalars(select(AthleteModel)).all() == []
    assert db_session.scalars(select(MessagingIdentityModel)).all() == []
    assert events == [("handle", "telegram", "12345", "Hello coach")]


def test_callback_query_is_acknowledged_before_optional_t3_handler() -> None:
    events: list[tuple[object, ...]] = []

    def callback_handler(callback: Mapping[str, Any], _db: object) -> None:
        events.append(("callback_handler", callback["data"]))

    processor = TelegramUpdateProcessor(
        channel=TelegramChannel(EventClient(events)),
        session_factory=lambda: nullcontext(object()),
        gateway_factory=lambda _db: KnownGateway(events),
        callback_handler=callback_handler,
    )

    processor.process_update(
        {
            "update_id": 11,
            "callback_query": {
                "id": "callback-7",
                "data": "opaque-token",
                "message": {"chat": {"id": 12345, "type": "private"}},
            },
        }
    )

    assert events == [
        ("callback", "callback-7"),
        ("callback_handler", "opaque-token"),
    ]


def test_callback_acknowledgement_failure_does_not_drop_t3_handler() -> None:
    events: list[tuple[object, ...]] = []

    def callback_handler(callback: Mapping[str, Any], _db: object) -> None:
        events.append(("callback_handler", callback["data"]))

    processor = TelegramUpdateProcessor(
        channel=TelegramChannel(EventClient(events, fail_callback=True)),
        session_factory=lambda: nullcontext(object()),
        gateway_factory=lambda _db: KnownGateway(events),
        callback_handler=callback_handler,
    )

    processor.process_update(
        {
            "callback_query": {
                "id": "callback-8",
                "data": "opaque-token",
                "message": {"chat": {"id": 12345, "type": "private"}},
            }
        }
    )

    assert events == [
        ("callback", "callback-8"),
        ("callback_handler", "opaque-token"),
    ]


@pytest.mark.parametrize(
    "chat",
    [
        pytest.param({"id": 12345}, id="missing-type"),
        pytest.param({"id": -12345, "type": "group"}, id="group"),
        pytest.param(
            {"id": -10012345, "type": "supergroup"},
            id="supergroup",
        ),
        pytest.param({"id": -10012345, "type": "channel"}, id="channel"),
    ],
)
def test_non_private_callback_is_acknowledged_but_not_forwarded(
    chat: dict[str, object],
) -> None:
    events: list[tuple[object, ...]] = []

    def callback_handler(callback: Mapping[str, Any], _db: object) -> None:
        events.append(("callback_handler", callback["data"]))

    processor = TelegramUpdateProcessor(
        channel=TelegramChannel(EventClient(events)),
        session_factory=lambda: nullcontext(object()),
        gateway_factory=lambda _db: KnownGateway(events),
        callback_handler=callback_handler,
    )

    processor.process_update(
        {
            "callback_query": {
                "id": "callback-9",
                "data": "opaque-token",
                "message": {"chat": chat},
            }
        }
    )

    assert events == [("callback", "callback-9")]


def test_runtime_configuration_is_lazy_and_requires_token_when_built(
    monkeypatch,
) -> None:
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)

    with pytest.raises(TelegramConfigurationError, match="TELEGRAM_BOT_TOKEN"):
        build_telegram_runtime()

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "bot-token")
    runtime = build_telegram_runtime()
    try:
        assert isinstance(runtime.client, TelegramBotClient)
        assert isinstance(runtime.channel, TelegramChannel)
        assert isinstance(runtime.processor, TelegramUpdateProcessor)
    finally:
        runtime.close()


def test_process_runtime_is_reused_and_closed_at_lifespan_boundary(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "bot-token")
    close_telegram_runtime()

    first = get_telegram_runtime()
    second = get_telegram_runtime()
    assert second is first

    close_telegram_runtime()
    replacement = get_telegram_runtime()
    try:
        assert replacement is not first
    finally:
        close_telegram_runtime()
