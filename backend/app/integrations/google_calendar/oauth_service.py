"""Google OAuth for the one calendar Resilio owns.

Mirrors ``integrations/strava/oauth_service.py``: encrypted tokens at rest, a
CSRF ``state`` stored server-side, and transparent refresh.

Scope is ``calendar.app.created`` — Resilio can create a secondary calendar and
manage events on the calendars it created, and nothing else. Deleting the
"Resilio Training" calendar removes every trace of the integration.
"""
from __future__ import annotations

import os
import secrets
import time
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode

import httpx
from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...db.models import GoogleCalendarCredentialModel

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"

SCOPE = "https://www.googleapis.com/auth/calendar.app.created"

DEFAULT_REDIRECT_URI = "http://localhost:8000/integrations/link/callback/google"

_REFRESH_MARGIN_S = 300


class GoogleCalendarNotConnectedError(RuntimeError):
    def __init__(self, athlete_id: str) -> None:
        super().__init__(f"Google Calendar not connected for athlete {athlete_id}")


class GoogleCalendarConfigurationError(RuntimeError):
    """Raised when the deployment is missing Google OAuth configuration."""


class InvalidOAuthStateError(ValueError):
    def __init__(self) -> None:
        super().__init__("Invalid or unknown OAuth state")


def _encryption_key() -> str:
    key = os.getenv("GOOGLE_ENCRYPTION_KEY", "").strip()
    if not key:
        raise GoogleCalendarConfigurationError(
            "GOOGLE_ENCRYPTION_KEY environment variable is not set"
        )
    return key


def encrypt_token(plain: str, key: str) -> str:
    return Fernet(key.encode()).encrypt(plain.encode()).decode()


def decrypt_token(cipher: str, key: str) -> str:
    return Fernet(key.encode()).decrypt(cipher.encode()).decode()


def redirect_uri() -> str:
    return os.getenv("GOOGLE_REDIRECT_URI", DEFAULT_REDIRECT_URI)


def _client_credentials() -> tuple[str, str]:
    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        raise GoogleCalendarConfigurationError(
            "GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set"
        )
    return client_id, client_secret


def _row(db: Session, athlete_id: str) -> GoogleCalendarCredentialModel | None:
    return db.get(GoogleCalendarCredentialModel, athlete_id)


def _upsert(db: Session, athlete_id: str) -> GoogleCalendarCredentialModel:
    row = _row(db, athlete_id)
    if row is None:
        row = GoogleCalendarCredentialModel(athlete_id=athlete_id)
        db.add(row)
    return row


def connect(athlete_id: str, db: Session) -> dict[str, Any]:
    """Return the Google consent URL and remember the CSRF state."""
    _encryption_key()
    client_id, _ = _client_credentials()

    state = secrets.token_urlsafe(16)
    row = _upsert(db, athlete_id)
    row.state = state
    db.commit()

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri(),
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "include_granted_scopes": "true",
        "prompt": "consent",
        "state": state,
    }
    return {"auth_url": f"{AUTH_URL}?{urlencode(params)}"}


def callback(code: str, state: str, db: Session) -> dict[str, Any]:
    """Exchange the authorization code, encrypt the tokens, persist them.

    Raises:
        InvalidOAuthStateError: the state does not match a pending connect.
        httpx.HTTPStatusError: Google rejected the exchange.
    """
    key = _encryption_key()
    client_id, client_secret = _client_credentials()

    athlete_id = db.scalar(
        select(GoogleCalendarCredentialModel.athlete_id).where(
            GoogleCalendarCredentialModel.state == state
        )
    )
    if athlete_id is None:
        raise InvalidOAuthStateError

    response = httpx.post(
        TOKEN_URL,
        data={
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri(),
            "grant_type": "authorization_code",
        },
        timeout=15.0,
    )
    response.raise_for_status()
    payload = response.json()

    row = _upsert(db, athlete_id)
    row.state = None
    row.scope = payload.get("scope", SCOPE)
    row.connected_at = datetime.now(timezone.utc)
    access_token = payload.get("access_token", "")
    if access_token:
        row.access_token_enc = encrypt_token(access_token, key)
        row.expires_at = int(time.time()) + int(payload.get("expires_in", 3600))
    refresh_token = payload.get("refresh_token")
    if refresh_token:
        row.refresh_token_enc = encrypt_token(refresh_token, key)
    db.commit()

    return {"connected": True, "athlete_id": athlete_id}


def get_access_token(athlete_id: str, db: Session, *, force_refresh: bool = False) -> str:
    """Return a usable access token, refreshing it when it is about to expire.

    Raises:
        GoogleCalendarNotConnectedError: no usable credential for this athlete.
    """
    key = _encryption_key()
    row = _row(db, athlete_id)
    if row is None or row.refresh_token_enc is None:
        raise GoogleCalendarNotConnectedError(athlete_id)

    fresh_enough = (
        row.access_token_enc is not None
        and row.expires_at is not None
        and row.expires_at > time.time() + _REFRESH_MARGIN_S
    )
    if fresh_enough and not force_refresh:
        return decrypt_token(row.access_token_enc or "", key)

    client_id, client_secret = _client_credentials()
    response = httpx.post(
        TOKEN_URL,
        data={
            "refresh_token": decrypt_token(row.refresh_token_enc, key),
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
        },
        timeout=15.0,
    )
    response.raise_for_status()
    payload = response.json()

    access_token = str(payload.get("access_token") or "")
    if not access_token:
        raise GoogleCalendarNotConnectedError(athlete_id)
    row.access_token_enc = encrypt_token(access_token, key)
    row.expires_at = int(time.time()) + int(payload.get("expires_in", 3600))
    rotated = payload.get("refresh_token")
    if rotated:
        row.refresh_token_enc = encrypt_token(rotated, key)
    db.commit()
    return access_token


def token_provider(athlete_id: str, db: Session) -> Callable[[], str]:
    """Return a callable the API client can use to fetch a valid access token.

    The first call reuses a cached token; every later call forces a refresh, so
    a 401 retry inside the client picks up a genuinely new token.
    """
    state = {"calls": 0}

    def provide() -> str:
        force = state["calls"] > 0
        state["calls"] += 1
        return get_access_token(athlete_id, db, force_refresh=force)

    return provide


def is_connected(athlete_id: str, db: Session) -> bool:
    row = _row(db, athlete_id)
    return row is not None and row.refresh_token_enc is not None
