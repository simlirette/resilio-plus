"""Channel-neutral messaging contracts and utilities."""

from .base import Button, MessagingChannel
from .chunking import chunk_message
from .gateway import (
    InvalidLinkCodeError,
    MessagingGateway,
    MessagingPersistenceError,
    MessagingTransactionError,
    NotificationSender,
    UnknownMessagingChannelError,
)

__all__ = [
    "Button",
    "InvalidLinkCodeError",
    "MessagingChannel",
    "MessagingGateway",
    "MessagingPersistenceError",
    "MessagingTransactionError",
    "NotificationSender",
    "UnknownMessagingChannelError",
    "chunk_message",
]
