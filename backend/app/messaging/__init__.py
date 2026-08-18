"""Channel-neutral messaging contracts and utilities."""

from .base import Button, MessagingChannel
from .chunking import chunk_message

__all__ = ["Button", "MessagingChannel", "chunk_message"]
