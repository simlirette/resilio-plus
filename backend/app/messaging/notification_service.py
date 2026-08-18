import uuid
from collections.abc import Mapping

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..db.models import MessagingIdentityModel, OutboundMessageModel
from .base import Button, MessagingChannel
from .chunking import chunk_message
from .gateway import UnknownMessagingChannelError


class EmptyNotificationError(ValueError):
    """Raised when a notification has no meaningful text."""

    def __init__(self) -> None:
        super().__init__("Notification text must not be empty")


class MessagingIdentityNotFoundError(LookupError):
    """Raised when an athlete has no verified messaging destination."""

    def __init__(self) -> None:
        super().__init__("No verified messaging identity is available for this athlete")


class NotificationDeliveryError(RuntimeError):
    """Raised when a provider rejects a notification chunk."""

    def __init__(self, accepted_provider_ids: tuple[str, ...] = ()) -> None:
        self.accepted_provider_ids = accepted_provider_ids
        super().__init__(
            f"Notification delivery failed after {len(accepted_provider_ids)} accepted chunk(s)"
        )


class NotificationFormattingError(ValueError):
    """Raised when channel formatting cannot produce provider-safe chunks."""

    def __init__(self) -> None:
        super().__init__("Notification cannot be formatted within the channel limit")


class NotificationPersistenceError(RuntimeError):
    """Raised when an accepted provider message cannot be audited."""

    def __init__(
        self,
        unaudited_provider_id: str | None = None,
        audited_provider_ids: tuple[str, ...] = (),
    ) -> None:
        self.unaudited_provider_id = unaudited_provider_id
        self.audited_provider_ids = audited_provider_ids
        super().__init__("Unable to persist outbound notification audit")


class NotificationTransactionError(RuntimeError):
    """Raised when notification delivery cannot own a clean session."""

    def __init__(self) -> None:
        super().__init__("Outbound notification requires a clean database session")


class NotificationService:
    """Deliver athlete notifications through configured messaging channels."""

    def __init__(
        self,
        db: Session,
        channels: Mapping[str, MessagingChannel],
    ) -> None:
        self._db = db
        self._channels = dict(channels)

    def send(
        self,
        athlete_id: str,
        text: str,
        buttons: list[Button] | None = None,
        *,
        kind: str = "notification",
    ) -> list[str]:
        if self._db.in_transaction():
            raise NotificationTransactionError
        if not text.strip():
            raise EmptyNotificationError

        try:
            with self._db.begin():
                identity = self._db.execute(
                    select(
                        MessagingIdentityModel.channel,
                        MessagingIdentityModel.external_id,
                    )
                    .where(
                        MessagingIdentityModel.athlete_id == athlete_id,
                        MessagingIdentityModel.verified_at.is_not(None),
                    )
                    .order_by(
                        MessagingIdentityModel.created_at,
                        MessagingIdentityModel.id,
                    )
                ).first()
        except SQLAlchemyError:
            raise NotificationPersistenceError from None
        if identity is None:
            raise MessagingIdentityNotFoundError

        channel = self._channels.get(identity.channel)
        if (
            channel is None
            or not isinstance(channel, MessagingChannel)
            or channel.name != identity.channel
        ):
            raise UnknownMessagingChannelError(identity.channel)

        bodies = _format_chunks(text, channel)
        provider_ids: list[str] = []
        for index, body in enumerate(bodies):
            try:
                if buttons and index == len(bodies) - 1:
                    provider_message_id = channel.send_with_buttons(
                        identity.external_id,
                        body,
                        buttons,
                    )
                else:
                    provider_message_id = channel.send(identity.external_id, body)
            except Exception:
                raise NotificationDeliveryError(tuple(provider_ids)) from None
            try:
                self._db.add(
                    OutboundMessageModel(
                        id=str(uuid.uuid4()),
                        athlete_id=athlete_id,
                        channel=identity.channel,
                        external_id=identity.external_id,
                        provider_message_id=provider_message_id,
                        body=body,
                        kind=kind,
                    )
                )
                self._db.commit()
            except SQLAlchemyError:
                self._db.rollback()
                raise NotificationPersistenceError(
                    unaudited_provider_id=provider_message_id,
                    audited_provider_ids=tuple(provider_ids),
                ) from None
            provider_ids.append(provider_message_id)
        return provider_ids


def _format_chunks(text: str, channel: MessagingChannel) -> list[str]:
    try:
        max_length = channel.max_message_length()
    except Exception:
        raise NotificationFormattingError from None
    if not isinstance(max_length, int) or max_length <= 0:
        raise NotificationFormattingError

    bodies: list[str] = []
    try:
        raw_chunks = chunk_message(text, max_length)
    except ValueError:
        raise NotificationFormattingError from None
    for raw_chunk in raw_chunks:
        bodies.extend(_fit_formatted_chunk(raw_chunk, channel, max_length))
    return bodies


def _fit_formatted_chunk(
    raw_chunk: str,
    channel: MessagingChannel,
    max_length: int,
) -> list[str]:
    bodies: list[str] = []
    work = [raw_chunk]
    processed = 0
    max_work_items = max(1, 2 * len(raw_chunk) - 1)

    while work:
        processed += 1
        if processed > max_work_items:
            raise NotificationFormattingError

        current = work.pop()
        try:
            formatted = channel.format(current)
        except Exception:
            raise NotificationFormattingError from None
        if not isinstance(formatted, str) or not formatted:
            raise NotificationFormattingError
        if len(formatted) <= max_length:
            bodies.append(formatted)
            continue
        if len(current) <= 1:
            raise NotificationFormattingError

        reduced_limit = max(
            1,
            min(
                len(current) - 1,
                len(current) * max_length // len(formatted),
            ),
        )
        try:
            smaller_chunks = chunk_message(current, reduced_limit)
        except ValueError:
            raise NotificationFormattingError from None
        if smaller_chunks == [current]:
            raise NotificationFormattingError
        work.extend(reversed(smaller_chunks))

    return bodies
