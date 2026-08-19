"""Tokenized approvals for human-in-the-loop decisions taken over a chat channel.

A pending approval is the durable half of a LangGraph ``interrupt``: the graph is
parked on a checkpoint, and the athlete holds an opaque token that names the
decision. The token is the *only* thing that travels to the channel — Telegram
caps ``callback_data`` at 64 bytes, so thread ids and payloads are looked up
server-side.

Public API::

    token = create_approval(db, athlete_id=..., thread_id=..., kind="weekly_plan")
    approval = resolve(db, token=token, resolution="approve", athlete_id=...)

Every function owns its transaction and requires a session with no transaction
already in flight, matching the discipline used by :mod:`app.messaging.gateway`.
"""
from __future__ import annotations

import json
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Literal, get_args

from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..db.models import MessagingIdentityModel, PendingApprovalModel

Resolution = Literal["approve", "revise", "reject"]

RESOLUTIONS: tuple[str, ...] = get_args(Resolution)

DEFAULT_TTL = timedelta(days=7)
TOKEN_LENGTH = 16

_CALLBACK_PREFIX = "ap"
_RESOLUTION_CODES: dict[str, str] = {"approve": "a", "revise": "v", "reject": "r"}
_CODE_RESOLUTIONS: dict[str, Resolution] = {"a": "approve", "v": "revise", "r": "reject"}


class UnknownApprovalError(LookupError):
    """Raised when a token names no approval at all."""

    def __init__(self) -> None:
        super().__init__("Unknown approval token")


class ExpiredApprovalError(ValueError):
    """Raised when an approval token is past its expiry."""

    def __init__(self) -> None:
        super().__init__("Approval token has expired")


class AlreadyResolvedApprovalError(ValueError):
    """Raised when an approval token is replayed after being resolved."""

    def __init__(self) -> None:
        super().__init__("Approval token has already been resolved")


class ApprovalOwnershipError(PermissionError):
    """Raised when an approval token belongs to a different athlete (HTTP 403)."""

    def __init__(self) -> None:
        super().__init__("Approval token belongs to another athlete")


class ApprovalPersistenceError(RuntimeError):
    """Raised when an approval cannot be read or written."""

    def __init__(self) -> None:
        super().__init__("Unable to persist approval state")


class ApprovalTransactionError(RuntimeError):
    """Raised when an approval operation cannot own a clean transaction."""

    def __init__(self) -> None:
        super().__init__("Approval operations require a clean database session")


@dataclass(frozen=True, slots=True)
class PendingApproval:
    """Detached snapshot of a resolved approval, safe to use after commit."""

    token: str
    athlete_id: str
    thread_id: str
    kind: str
    payload: dict[str, Any]
    resolution: Resolution


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware(value: datetime) -> datetime:
    """SQLite drops tzinfo on round-trip; treat naive timestamps as UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _require_clean_session(db: Session) -> None:
    if db.in_transaction():
        raise ApprovalTransactionError


def new_token() -> str:
    """Return a 16-character URL-safe approval token."""
    return secrets.token_urlsafe(TOKEN_LENGTH)[:TOKEN_LENGTH]


def encode_callback(token: str, resolution: Resolution) -> str:
    """Encode a channel button payload — the token plus a one-character verb."""
    code = _RESOLUTION_CODES.get(resolution)
    if code is None:
        raise ValueError(f"Unknown resolution: {resolution!r}")
    return f"{_CALLBACK_PREFIX}:{token}:{code}"


def parse_callback(data: str) -> tuple[str, Resolution] | None:
    """Decode a channel button payload, or None when it is not an approval."""
    parts = data.split(":")
    if len(parts) != 3:
        return None
    prefix, token, code = parts
    if prefix != _CALLBACK_PREFIX or not token:
        return None
    resolution = _CODE_RESOLUTIONS.get(code)
    if resolution is None:
        return None
    return token, resolution


def create_approval(
    db: Session,
    *,
    athlete_id: str,
    thread_id: str,
    kind: str,
    payload: dict[str, Any] | None = None,
    ttl: timedelta = DEFAULT_TTL,
    clock: Callable[[], datetime] = _utcnow,
) -> str:
    """Persist a pending approval and return its opaque token."""
    _require_clean_session(db)
    now = clock()
    token = new_token()
    try:
        with db.begin():
            db.add(
                PendingApprovalModel(
                    token=token,
                    athlete_id=athlete_id,
                    thread_id=thread_id,
                    kind=kind,
                    payload_json=json.dumps(payload or {}),
                    created_at=now,
                    expires_at=now + ttl,
                )
            )
    except SQLAlchemyError:
        raise ApprovalPersistenceError from None
    return token


def resolve(
    db: Session,
    *,
    token: str,
    resolution: Resolution,
    athlete_id: str,
    clock: Callable[[], datetime] = _utcnow,
) -> PendingApproval:
    """Consume an approval token exactly once and return its snapshot.

    Ownership is verified before anything else, so a token belonging to another
    athlete is never revealed, mutated, or expired on their behalf.

    Raises:
        UnknownApprovalError: no such token.
        ApprovalOwnershipError: the token belongs to another athlete (403).
        AlreadyResolvedApprovalError: the token was already consumed.
        ExpiredApprovalError: the token is past its expiry.
    """
    if resolution not in RESOLUTIONS:
        raise ValueError(f"Unknown resolution: {resolution!r}")
    _require_clean_session(db)
    now = clock()

    try:
        with db.begin():
            row = db.get(PendingApprovalModel, token)
            if row is None:
                raise UnknownApprovalError
            if row.athlete_id != athlete_id:
                raise ApprovalOwnershipError
            if row.resolved_at is not None:
                raise AlreadyResolvedApprovalError
            if _as_aware(row.expires_at) <= now:
                raise ExpiredApprovalError

            snapshot = PendingApproval(
                token=row.token,
                athlete_id=row.athlete_id,
                thread_id=row.thread_id,
                kind=row.kind,
                payload=_decode_payload(row.payload_json),
                resolution=resolution,
            )

            # Conditional update — a double tap loses the race instead of
            # resolving the same approval twice.
            claimed = db.execute(
                update(PendingApprovalModel)
                .where(
                    PendingApprovalModel.token == token,
                    PendingApprovalModel.athlete_id == athlete_id,
                    PendingApprovalModel.resolved_at.is_(None),
                )
                .values(resolved_at=now, resolution=resolution)
                .returning(PendingApprovalModel.token)
                .execution_options(synchronize_session=False)
            ).scalar_one_or_none()
            if claimed is None:
                raise AlreadyResolvedApprovalError
    except SQLAlchemyError:
        raise ApprovalPersistenceError from None

    return snapshot


def get_open_approval(
    db: Session,
    *,
    token: str,
    clock: Callable[[], datetime] = _utcnow,
) -> PendingApproval | None:
    """Return an unresolved, unexpired approval snapshot, or None."""
    _require_clean_session(db)
    now = clock()
    try:
        with db.begin():
            row = db.get(PendingApprovalModel, token)
            if row is None or row.resolved_at is not None:
                return None
            if _as_aware(row.expires_at) <= now:
                return None
            return PendingApproval(
                token=row.token,
                athlete_id=row.athlete_id,
                thread_id=row.thread_id,
                kind=row.kind,
                payload=_decode_payload(row.payload_json),
                resolution="revise",
            )
    except SQLAlchemyError:
        raise ApprovalPersistenceError from None


def arm_revision_latch(
    db: Session,
    *,
    channel: str,
    external_id: str,
    token: str,
) -> None:
    """Route this identity's next free-text message to ``token``'s revise path."""
    _require_clean_session(db)
    try:
        with db.begin():
            db.execute(
                update(MessagingIdentityModel)
                .where(
                    MessagingIdentityModel.channel == channel,
                    MessagingIdentityModel.external_id == external_id,
                )
                .values(awaiting_revision_for_token=token)
                .execution_options(synchronize_session=False)
            )
    except SQLAlchemyError:
        raise ApprovalPersistenceError from None


def pop_revision_latch(
    db: Session,
    *,
    channel: str,
    external_id: str,
) -> str | None:
    """Read and clear the revision latch atomically; None when not armed."""
    _require_clean_session(db)
    try:
        with db.begin():
            token = db.scalar(
                select(MessagingIdentityModel.awaiting_revision_for_token).where(
                    MessagingIdentityModel.channel == channel,
                    MessagingIdentityModel.external_id == external_id,
                )
            )
            if token is None:
                return None
            db.execute(
                update(MessagingIdentityModel)
                .where(
                    MessagingIdentityModel.channel == channel,
                    MessagingIdentityModel.external_id == external_id,
                    MessagingIdentityModel.awaiting_revision_for_token == token,
                )
                .values(awaiting_revision_for_token=None)
                .execution_options(synchronize_session=False)
            )
            return token
    except SQLAlchemyError:
        raise ApprovalPersistenceError from None


def _decode_payload(raw: str) -> dict[str, Any]:
    try:
        decoded = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
    return decoded if isinstance(decoded, dict) else {}
