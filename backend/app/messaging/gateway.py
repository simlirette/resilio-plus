from __future__ import annotations

import uuid
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
from typing import Any, Protocol

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from ..db.models import MessagingIdentityModel, MessagingLinkCodeModel
from ..services.coordinator_service import DispatchResult, coordinator_service
from .base import Button, MessagingChannel


class NotificationSender(Protocol):
    """Structural subset of NotificationService used by the gateway."""

    def send(
        self,
        athlete_id: str,
        text: str,
        buttons: list[Button] | None = None,
    ) -> object: ...


class ApprovalRouter(Protocol):
    """Structural subset of ApprovalService used by the gateway."""

    def take_pending_revision_token(
        self,
        *,
        channel: str,
        external_id: str,
    ) -> str | None: ...

    def send_plan_for_approval(
        self,
        *,
        athlete_id: str,
        thread_id: str,
        kind: str = ...,
        plan: Mapping[str, Any] | None,
        degraded_sources: Sequence[str] | None = ...,
        payload: dict[str, Any] | None = ...,
    ) -> str: ...

    def handle_revision_text(
        self,
        *,
        athlete_id: str,
        channel: str,
        external_id: str,
        token: str,
        text: str,
    ) -> object: ...


class CommandHandler(Protocol):
    """Structural subset of CommandRouter used by the gateway."""

    def handle(self, athlete_id: str, text: str) -> object: ...


class _CoordinatorDispatcher(Protocol):
    def dispatch(
        self,
        athlete_id: str,
        event_type: str,
        payload: dict[str, Any],
        db: Session,
    ) -> DispatchResult: ...


class UnknownMessagingChannelError(ValueError):
    """Raised when a gateway operation names an unconfigured channel."""

    def __init__(self, channel: str) -> None:
        super().__init__(f"Unknown messaging channel: {channel}")


class MessagingDeliveryError(RuntimeError):
    """Raised when an inbound response cannot be delivered safely."""

    def __init__(self) -> None:
        super().__init__("Unable to deliver messaging response")


class InvalidLinkCodeError(ValueError):
    """Raised for every unusable link code without disclosing its state."""

    def __init__(self) -> None:
        super().__init__("Invalid or expired link code")


class MessagingTransactionError(RuntimeError):
    """Raised when a gateway operation cannot own a clean transaction."""

    def __init__(self) -> None:
        super().__init__("Messaging operation requires a clean database session")


class MessagingPersistenceError(RuntimeError):
    """Raised when an unexpected gateway database failure is hidden."""

    def __init__(self) -> None:
        super().__init__("Unable to persist messaging identity")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MessagingGateway:
    """Resolve messaging identities and route inbound text to the coordinator."""

    def __init__(
        self,
        db: Session,
        channels: Mapping[str, MessagingChannel],
        *,
        coordinator: _CoordinatorDispatcher = coordinator_service,
        notifier: NotificationSender,
        approvals: ApprovalRouter | None = None,
        commands: CommandHandler | None = None,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        self._db = db
        self._channels = dict(channels)
        self._coordinator = coordinator
        self._notifier = notifier
        self._approvals = approvals
        self._commands = commands
        self._clock = clock

    def resolve_athlete(self, channel: str, external_id: str) -> str | None:
        """Return the athlete for an exact verified external identity."""
        self._require_clean_session()
        self._get_channel(channel)
        return self._resolve_verified_athlete(channel, external_id)

    def handle_inbound(self, channel: str, external_id: str, text: str) -> None:
        """Dispatch known senders' text and send any user-facing graph output."""
        self._require_clean_session()
        messaging_channel = self._get_channel(channel)
        athlete_id = self._resolve_verified_athlete(channel, external_id)
        if athlete_id is None:
            try:
                instruction = messaging_channel.format(
                    "Send your link code here to connect this chat to your Resilio account."
                )
                messaging_channel.send(external_id, instruction)
            except Exception:
                raise MessagingDeliveryError from None
            return

        if self._commands is not None and text.strip().startswith("/"):
            outcome = self._commands.handle(athlete_id, text)
            if getattr(outcome, "handled", False):
                return

        if self._approvals is not None:
            pending_token = self._approvals.take_pending_revision_token(
                channel=channel,
                external_id=external_id,
            )
            if pending_token is not None:
                self._approvals.handle_revision_text(
                    athlete_id=athlete_id,
                    channel=channel,
                    external_id=external_id,
                    token=pending_token,
                    text=text,
                )
                return

        try:
            result = self._coordinator.dispatch(
                athlete_id,
                "chat",
                {"message": text},
                self._db,
            )
            self._db.commit()
        except SQLAlchemyError:
            self._db.rollback()
            raise MessagingPersistenceError from None
        except Exception:
            self._db.rollback()
            raise
        output = getattr(result, "output", None)
        response = self._render_response(output)
        if response is not None:
            self._notifier.send(athlete_id, response)
        self._maybe_send_plan_for_approval(athlete_id, output)

    def _maybe_send_plan_for_approval(
        self,
        athlete_id: str,
        output: object,
    ) -> None:
        """A graph that produced a week hands it over as buttons, not as text."""
        if self._approvals is None or not isinstance(output, dict):
            return
        plan = output.get("plan_proposal")
        thread_id = output.get("plan_thread_id")
        if plan is None or not isinstance(thread_id, str) or not thread_id:
            return
        self._approvals.send_plan_for_approval(
            athlete_id=athlete_id,
            thread_id=thread_id,
            plan=plan,
        )

    def link_identity(self, channel: str, external_id: str, link_code: str) -> str:
        """Atomically redeem a code using a clean, dedicated unit-of-work session.

        The injected session must not already have an active transaction. This
        method owns its transaction so it cannot commit or roll back caller work.
        """
        self._require_clean_session()
        self._get_channel(channel)

        try:
            with self._db.begin():
                now = self._clock()
                claim = (
                    update(MessagingLinkCodeModel)
                    .where(
                        MessagingLinkCodeModel.code == link_code,
                        MessagingLinkCodeModel.consumed_at.is_(None),
                        MessagingLinkCodeModel.expires_at > now,
                    )
                    .values(consumed_at=now)
                    .returning(MessagingLinkCodeModel.athlete_id)
                    .execution_options(synchronize_session=False)
                )
                athlete_id = self._db.execute(claim).scalar_one_or_none()
                if athlete_id is None:
                    raise InvalidLinkCodeError

                try:
                    with self._db.begin_nested():
                        self._db.add(
                            MessagingIdentityModel(
                                id=str(uuid.uuid4()),
                                athlete_id=athlete_id,
                                channel=channel,
                                external_id=external_id,
                                verified_at=now,
                            )
                        )
                        self._db.flush()
                except IntegrityError:
                    current_owner = self._db.scalar(
                        select(MessagingIdentityModel.athlete_id).where(
                            MessagingIdentityModel.channel == channel,
                            MessagingIdentityModel.external_id == external_id,
                            MessagingIdentityModel.verified_at.is_not(None),
                        )
                    )
                    if current_owner is None:
                        raise
                    if current_owner != athlete_id:
                        raise InvalidLinkCodeError from None

            return athlete_id
        except SQLAlchemyError:
            raise MessagingPersistenceError from None

    def _resolve_verified_athlete(self, channel: str, external_id: str) -> str | None:
        try:
            with self._db.begin():
                return self._db.scalar(
                    select(MessagingIdentityModel.athlete_id).where(
                        MessagingIdentityModel.channel == channel,
                        MessagingIdentityModel.external_id == external_id,
                        MessagingIdentityModel.verified_at.is_not(None),
                    )
                )
        except SQLAlchemyError:
            raise MessagingPersistenceError from None

    def _require_clean_session(self) -> None:
        if self._db.in_transaction():
            raise MessagingTransactionError

    def _get_channel(self, channel: str) -> MessagingChannel:
        messaging_channel = self._channels.get(channel)
        if (
            messaging_channel is None
            or not isinstance(messaging_channel, MessagingChannel)
            or messaging_channel.name != channel
        ):
            raise UnknownMessagingChannelError(channel) from None
        return messaging_channel

    @staticmethod
    def _render_response(output: object) -> str | None:
        if not isinstance(output, dict):
            return None
        for key in ("final_response", "question"):
            value = output.get(key)
            if isinstance(value, str) and value.strip():
                return value
        return None
