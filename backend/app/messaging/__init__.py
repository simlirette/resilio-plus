"""Channel-neutral messaging contracts and utilities."""

from .base import Button, MessagingChannel
from .chunking import chunk_message
from .gateway import (
    InvalidLinkCodeError,
    MessagingDeliveryError,
    MessagingGateway,
    MessagingPersistenceError,
    MessagingTransactionError,
    NotificationSender,
    UnknownMessagingChannelError,
)
from .notification_service import (
    EmptyNotificationError,
    MessagingIdentityNotFoundError,
    NotificationDeliveryError,
    NotificationFormattingError,
    NotificationPersistenceError,
    NotificationService,
    NotificationTransactionError,
)

__all__ = [
    "Button",
    "EmptyNotificationError",
    "InvalidLinkCodeError",
    "MessagingChannel",
    "MessagingDeliveryError",
    "MessagingGateway",
    "MessagingIdentityNotFoundError",
    "MessagingPersistenceError",
    "MessagingTransactionError",
    "NotificationDeliveryError",
    "NotificationFormattingError",
    "NotificationPersistenceError",
    "NotificationService",
    "NotificationTransactionError",
    "NotificationSender",
    "UnknownMessagingChannelError",
    "chunk_message",
]
