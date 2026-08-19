"""Channel-neutral messaging contracts and utilities."""

from .approval_service import ApprovalOutcome, ApprovalService, CalendarPusher
from .approvals import (
    AlreadyResolvedApprovalError,
    ApprovalOwnershipError,
    ExpiredApprovalError,
    PendingApproval,
    UnknownApprovalError,
    create_approval,
    encode_callback,
    parse_callback,
    resolve,
)
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
from .plan_renderer import render_week

__all__ = [
    "AlreadyResolvedApprovalError",
    "ApprovalOutcome",
    "ApprovalOwnershipError",
    "ApprovalService",
    "Button",
    "CalendarPusher",
    "EmptyNotificationError",
    "ExpiredApprovalError",
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
    "PendingApproval",
    "UnknownApprovalError",
    "UnknownMessagingChannelError",
    "chunk_message",
    "create_approval",
    "encode_callback",
    "parse_callback",
    "render_week",
    "resolve",
]
