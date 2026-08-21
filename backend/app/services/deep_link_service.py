"""Single-use links that hand a phone-only athlete into a provider auth flow.

The athlete is never logged into a web session, so the link itself carries the
identity: a short-lived opaque token that resolves server-side to
``(athlete_id, provider)`` and is burned on first use.
"""
from __future__ import annotations

import os
import secrets
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..db.models import (
    ConnectorCredentialModel,
    DeepLinkTokenModel,
    GoogleCalendarCredentialModel,
)

SUPPORTED_PROVIDERS: tuple[str, ...] = ("strava", "hevy", "terra", "google")

PROVIDER_LABELS: dict[str, str] = {
    "strava": "Strava",
    "hevy": "Hevy",
    "terra": "Terra",
    "google": "Google Calendar",
}

DEFAULT_TTL = timedelta(hours=2)
TOKEN_LENGTH = 24

DEFAULT_BASE_URL = "http://localhost:8000"


class UnsupportedProviderError(ValueError):
    def __init__(self, provider: str) -> None:
        super().__init__(f"Unsupported provider: {provider!r}")


class InvalidDeepLinkError(ValueError):
    """Raised for every unusable token without disclosing which way it failed."""

    def __init__(self) -> None:
        super().__init__("This link is invalid or has already been used")


class DeepLinkPersistenceError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("Unable to persist deep-link token")


@dataclass(frozen=True, slots=True)
class DeepLink:
    token: str
    athlete_id: str
    provider: str


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def base_url() -> str:
    """Public origin the athlete's phone can reach, without a trailing slash."""
    return os.getenv("PUBLIC_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def link_url(token: str) -> str:
    """Return the tappable URL for a deep-link token."""
    return f"{base_url()}/integrations/link/{token}"


def issue_link(
    db: Session,
    *,
    athlete_id: str,
    provider: str,
    ttl: timedelta = DEFAULT_TTL,
    clock: Callable[[], datetime] = _utcnow,
) -> str:
    """Create a single-use token for one provider and return it."""
    if provider not in SUPPORTED_PROVIDERS:
        raise UnsupportedProviderError(provider)
    now = clock()
    token = secrets.token_urlsafe(TOKEN_LENGTH)
    try:
        with db.begin():
            db.add(
                DeepLinkTokenModel(
                    token=token,
                    athlete_id=athlete_id,
                    provider=provider,
                    created_at=now,
                    expires_at=now + ttl,
                )
            )
    except SQLAlchemyError:
        raise DeepLinkPersistenceError from None
    return token


def issue_connector_links(
    db: Session,
    *,
    athlete_id: str,
    providers: Iterable[str] = SUPPORTED_PROVIDERS,
    ttl: timedelta = DEFAULT_TTL,
    clock: Callable[[], datetime] = _utcnow,
) -> dict[str, str]:
    """Return ``{provider: url}`` for every provider the athlete can connect."""
    links: dict[str, str] = {}
    for provider in providers:
        token = issue_link(
            db,
            athlete_id=athlete_id,
            provider=provider,
            ttl=ttl,
            clock=clock,
        )
        links[provider] = link_url(token)
    return links


def resolve_link(
    db: Session,
    *,
    token: str,
    clock: Callable[[], datetime] = _utcnow,
) -> DeepLink:
    """Return the link a token names without consuming it.

    Raises:
        InvalidDeepLinkError: unknown, expired, or already consumed.
    """
    now = clock()
    try:
        with db.begin():
            row = db.get(DeepLinkTokenModel, token)
            if (
                row is None
                or row.consumed_at is not None
                or _as_aware(row.expires_at) <= now
            ):
                raise InvalidDeepLinkError
            return DeepLink(
                token=row.token,
                athlete_id=row.athlete_id,
                provider=row.provider,
            )
    except SQLAlchemyError:
        raise DeepLinkPersistenceError from None


def consume_link(
    db: Session,
    *,
    token: str,
    clock: Callable[[], datetime] = _utcnow,
) -> DeepLink:
    """Burn a token and return what it named.

    Raises:
        InvalidDeepLinkError: unknown, expired, or already consumed.
    """
    now = clock()
    try:
        with db.begin():
            row = db.get(DeepLinkTokenModel, token)
            if (
                row is None
                or row.consumed_at is not None
                or _as_aware(row.expires_at) <= now
            ):
                raise InvalidDeepLinkError
            link = DeepLink(
                token=row.token,
                athlete_id=row.athlete_id,
                provider=row.provider,
            )
            claimed = db.execute(
                update(DeepLinkTokenModel)
                .where(
                    DeepLinkTokenModel.token == token,
                    DeepLinkTokenModel.consumed_at.is_(None),
                )
                .values(consumed_at=now)
                .returning(DeepLinkTokenModel.token)
                .execution_options(synchronize_session=False)
            ).scalar_one_or_none()
            if claimed is None:
                raise InvalidDeepLinkError
            return link
    except SQLAlchemyError:
        raise DeepLinkPersistenceError from None


def consume_pending(
    db: Session,
    *,
    athlete_id: str,
    provider: str,
    clock: Callable[[], datetime] = _utcnow,
) -> bool:
    """Burn the newest live link for one athlete and provider. Returns whether one was.

    Single-use attaches to *completing* a connection, not to opening the page.
    Consuming at the redirect meant anything that merely fetched the URL -- a
    link preview, a browser prefetch, a scanner -- destroyed it, and the athlete
    tapped a dead link with no explanation.

    Newest first: re-sending /connect issues a fresh link, and the one just used
    is the last one issued. Nothing pending is not an error -- a provider can be
    connected through the API without a deep link ever existing.
    """
    now = clock()
    try:
        with db.begin():
            row = (
                db.query(DeepLinkTokenModel)
                .filter(
                    DeepLinkTokenModel.athlete_id == athlete_id,
                    DeepLinkTokenModel.provider == provider,
                    DeepLinkTokenModel.consumed_at.is_(None),
                )
                .order_by(DeepLinkTokenModel.created_at.desc())
                .first()
            )
            if row is None or _as_aware(row.expires_at) <= now:
                return False
            row.consumed_at = now
            return True
    except SQLAlchemyError:
        raise DeepLinkPersistenceError from None


def settle(db: Session) -> None:
    """Close a transaction an earlier read autobegan.

    ``issue_link`` opens its own unit of work, so callers coming from a graph
    turn (which leaves a read transaction open) must hand over a clean session.
    """
    if db.in_transaction():
        db.commit()


def pending_providers(db: Session, athlete_id: str) -> list[str]:
    """Providers the athlete has not connected yet, in a stable order."""
    settle(db)
    with db.begin():
        connected = set(
            db.scalars(
                select(ConnectorCredentialModel.provider).where(
                    ConnectorCredentialModel.athlete_id == athlete_id
                )
            ).all()
        )
        if db.get(GoogleCalendarCredentialModel, athlete_id) is not None:
            connected.add("google")
    return [p for p in SUPPORTED_PROVIDERS if p not in connected]


def connector_links_message(
    db: Session,
    *,
    athlete_id: str,
    providers: Iterable[str] | None = None,
    heading: str = "**Connect your data**",
) -> str | None:
    """Return the chat text offering one tappable link per provider.

    None when there is nothing left to connect, so callers can stay quiet
    instead of sending an empty invitation.
    """
    if providers is None:
        targets = pending_providers(db, athlete_id)
    else:
        targets = list(providers)
        settle(db)
    if not targets:
        return None
    links = issue_connector_links(db, athlete_id=athlete_id, providers=targets)
    lines = [heading, ""]
    for provider, url in links.items():
        lines.append(f"- {PROVIDER_LABELS.get(provider, provider)}: {url}")
    lines.append("")
    lines.append("Each link works once and expires in two hours.")
    return "\n".join(lines)
