from __future__ import annotations

import logging
import os
import uuid
from collections.abc import Callable, Mapping
from contextlib import AbstractContextManager
from dataclasses import dataclass
from threading import Lock
from typing import Any, Protocol, cast

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ...db.database import SessionLocal
from ...db.models import AthleteModel, MessagingIdentityModel
from ...messaging.gateway import InvalidLinkCodeError, MessagingGateway
from ...messaging.notification_service import NotificationService
from .channel import TelegramChannel
from .client import TelegramBotClient

logger = logging.getLogger(__name__)
_runtime_lock = Lock()
_runtime: TelegramRuntime | None = None


class TelegramConfigurationError(RuntimeError):
    """Raised when Telegram is enabled without valid environment configuration."""


@dataclass(slots=True)
class TelegramRuntime:
    client: TelegramBotClient
    channel: TelegramChannel
    processor: TelegramUpdateProcessor

    def close(self) -> None:
        self.client.close()


class _InboundGateway(Protocol):
    def resolve_athlete(self, channel: str, external_id: str) -> str | None: ...

    def link_identity(self, channel: str, external_id: str, link_code: str) -> str: ...

    def handle_inbound(self, channel: str, external_id: str, text: str) -> None: ...


class TelegramUpdateProcessor:
    """Shared synchronous handler used by webhook and polling deliveries."""

    def __init__(
        self,
        *,
        channel: TelegramChannel,
        session_factory: Callable[[], AbstractContextManager[Session]],
        gateway_factory: Callable[[Session], _InboundGateway],
        bootstrap_chat_id: str | None = None,
        admin_athlete_id: str | None = None,
        callback_handler: Callable[[Mapping[str, Any], Session], None] | None = None,
    ) -> None:
        self._channel = channel
        self._session_factory = session_factory
        self._gateway_factory = gateway_factory
        self._bootstrap_chat_id = bootstrap_chat_id
        self._admin_athlete_id = admin_athlete_id
        self._callback_handler = callback_handler

    def process_update(self, update: Mapping[str, Any]) -> None:
        callback = update.get("callback_query")
        if isinstance(callback, dict):
            callback_id = callback.get("id")
            if isinstance(callback_id, str) and callback_id:
                try:
                    self._channel.answer_callback_query(callback_id)
                except Exception:
                    logger.warning("telegram_callback_acknowledgement_failed")
                if self._callback_handler is not None:
                    callback_message = callback.get("message")
                    callback_chat = (
                        callback_message.get("chat")
                        if isinstance(callback_message, dict)
                        else None
                    )
                    if (
                        not isinstance(callback_chat, dict)
                        or callback_chat.get("type") != "private"
                    ):
                        return
                    with self._session_factory() as db:
                        self._callback_handler(
                            cast(Mapping[str, Any], callback),
                            db,
                        )
            return

        message = update.get("message")
        if not isinstance(message, dict):
            return
        chat = message.get("chat")
        text = message.get("text")
        if (
            not isinstance(chat, dict)
            or chat.get("type") != "private"
            or not isinstance(text, str)
        ):
            return
        chat_id = chat.get("id")
        if isinstance(chat_id, bool) or not isinstance(chat_id, (int, str)):
            return
        external_id = str(chat_id)

        with self._session_factory() as db:
            self._ensure_bootstrap_identity(db, external_id)
            gateway = self._gateway_factory(db)
            athlete_id = gateway.resolve_athlete("telegram", external_id)
            if athlete_id is None:
                try:
                    gateway.link_identity("telegram", external_id, text.strip())
                except InvalidLinkCodeError:
                    gateway.handle_inbound("telegram", external_id, text)
                else:
                    confirmation = self._channel.format("Telegram connected to Resilio.")
                    self._channel.send(external_id, confirmation)
                return

            try:
                self._channel.send_typing(external_id)
            except Exception:
                logger.warning("telegram_typing_action_failed")
            gateway.handle_inbound("telegram", external_id, text)

    def _ensure_bootstrap_identity(self, db: Session, external_id: str) -> None:
        if (
            self._bootstrap_chat_id is None
            or self._admin_athlete_id is None
            or external_id != self._bootstrap_chat_id
        ):
            return

        try:
            with db.begin():
                existing_owner = db.scalar(
                    select(MessagingIdentityModel.athlete_id).where(
                        MessagingIdentityModel.channel == "telegram",
                        MessagingIdentityModel.external_id == external_id,
                    )
                )
                if existing_owner is not None:
                    return
                athlete_exists = db.scalar(
                    select(AthleteModel.id).where(
                        AthleteModel.id == self._admin_athlete_id,
                    )
                )
                if athlete_exists is None:
                    logger.warning("telegram_bootstrap_admin_not_found")
                    return
                db.add(
                    MessagingIdentityModel(
                        id=str(uuid.uuid4()),
                        athlete_id=self._admin_athlete_id,
                        channel="telegram",
                        external_id=external_id,
                    )
                )
        except IntegrityError:
            db.rollback()
            with db.begin():
                existing_owner = db.scalar(
                    select(MessagingIdentityModel.athlete_id).where(
                        MessagingIdentityModel.channel == "telegram",
                        MessagingIdentityModel.external_id == external_id,
                    )
                )
            if existing_owner is None:
                raise


def build_telegram_runtime() -> TelegramRuntime:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise TelegramConfigurationError(
            "TELEGRAM_BOT_TOKEN is required when Telegram is enabled"
        )

    client = TelegramBotClient(token)
    channel = TelegramChannel(client)
    channels = {channel.name: channel}

    def gateway_factory(db: Session) -> MessagingGateway:
        notifier = NotificationService(db, channels)
        return MessagingGateway(
            db,
            channels,
            notifier=notifier,
        )

    def session_factory() -> Session:
        return SessionLocal()

    bootstrap_chat_id = os.getenv("TELEGRAM_BOOTSTRAP_CHAT_ID") or None
    admin_athlete_id = os.getenv("ADMIN_ATHLETE_ID") or None
    processor = TelegramUpdateProcessor(
        channel=channel,
        session_factory=session_factory,
        gateway_factory=gateway_factory,
        bootstrap_chat_id=bootstrap_chat_id,
        admin_athlete_id=admin_athlete_id,
    )
    return TelegramRuntime(
        client=client,
        channel=channel,
        processor=processor,
    )


def get_telegram_runtime() -> TelegramRuntime:
    global _runtime

    with _runtime_lock:
        if _runtime is None:
            _runtime = build_telegram_runtime()
        return _runtime


def close_telegram_runtime() -> None:
    global _runtime

    with _runtime_lock:
        runtime = _runtime
        _runtime = None
    if runtime is not None:
        runtime.close()
