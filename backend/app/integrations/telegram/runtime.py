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
from ...messaging.approval_service import ApprovalService, CalendarPusher
from ...messaging.approvals import ApprovalOwnershipError, parse_callback
from ...messaging.commands import CommandRouter
from ...messaging.gateway import InvalidLinkCodeError, MessagingGateway
from ...messaging.notification_service import NotificationService
from ...services.graph_invoker import build_live_coordinator
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


def build_approval_callback_handler(
    approval_factory: Callable[[Session], ApprovalService],
) -> Callable[[Mapping[str, Any], Session], None]:
    """Map a Telegram callback_query onto the approval it names.

    The chat is the identity: the athlete is resolved from the verified
    messaging identity, never from anything inside ``callback_data``.
    """

    def handle(callback: Mapping[str, Any], db: Session) -> None:
        data = callback.get("data")
        if not isinstance(data, str):
            return
        parsed = parse_callback(data)
        if parsed is None:
            return
        token, resolution = parsed

        external_id = _callback_external_id(callback)
        if external_id is None:
            return

        athlete_id = db.scalar(
            select(MessagingIdentityModel.athlete_id).where(
                MessagingIdentityModel.channel == "telegram",
                MessagingIdentityModel.external_id == external_id,
                MessagingIdentityModel.verified_at.is_not(None),
            )
        )
        if athlete_id is None:
            return

        try:
            approval_factory(db).handle_button(
                athlete_id=athlete_id,
                channel="telegram",
                external_id=external_id,
                token=token,
                resolution=resolution,
            )
        except ApprovalOwnershipError:
            logger.warning("telegram_approval_forbidden")

    return handle


def _callback_external_id(callback: Mapping[str, Any]) -> str | None:
    message = callback.get("message")
    chat = message.get("chat") if isinstance(message, dict) else None
    chat_id = chat.get("id") if isinstance(chat, dict) else None
    if isinstance(chat_id, bool) or not isinstance(chat_id, (int, str)):
        return None
    return str(chat_id)


def _resolve_weekly_cycle() -> Callable[[str, Session], None] | None:
    """Manual weekly-cycle trigger — V4-T6 supplies the implementation."""
    return None


def _resolve_calendar_pusher() -> CalendarPusher | None:
    """Calendar seam — V4-T5 supplies the Google Calendar implementation."""
    from ...messaging.calendar_hook import get_calendar_pusher

    return get_calendar_pusher()


def build_telegram_runtime() -> TelegramRuntime:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise TelegramConfigurationError(
            "TELEGRAM_BOT_TOKEN is required when Telegram is enabled"
        )

    client = TelegramBotClient(token)
    channel = TelegramChannel(client)
    channels = {channel.name: channel}

    def approval_factory(db: Session) -> ApprovalService:
        return ApprovalService(
            db,
            notifier=NotificationService(db, channels),
            calendar_pusher=_resolve_calendar_pusher(),
        )

    def gateway_factory(db: Session) -> MessagingGateway:
        notifier = NotificationService(db, channels)
        return MessagingGateway(
            db,
            channels,
            coordinator=build_live_coordinator(),
            notifier=notifier,
            approvals=approval_factory(db),
            commands=CommandRouter(
                db,
                notifier=notifier,
                weekly_cycle=_resolve_weekly_cycle(),
            ),
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
        callback_handler=build_approval_callback_handler(approval_factory),
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
