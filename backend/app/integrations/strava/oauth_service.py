# backend/app/integrations/strava/oauth_service.py
"""Strava OAuth service: token encryption, connect flow, auto-refresh."""
import json
import os
import secrets
import time
import uuid

from cryptography.fernet import Fernet
from sqlalchemy.orm import Session

from ...connectors.strava import StravaConnector
from ...db.models import ConnectorCredentialModel
from ...schemas.connector import ConnectorCredential


def _get_encryption_key() -> str:
    key = os.getenv("STRAVA_ENCRYPTION_KEY")
    if not key:
        raise RuntimeError("STRAVA_ENCRYPTION_KEY environment variable is not set")
    return key


def encrypt_token(plain: str, key: str) -> str:
    return Fernet(key.encode()).encrypt(plain.encode()).decode()


def decrypt_token(cipher: str, key: str) -> str:
    return Fernet(key.encode()).decrypt(cipher.encode()).decode()


def _upsert_credential(
    *,
    athlete_id: str,
    extra_json: str,
    access_token_enc: str | None = None,
    refresh_token_enc: str | None = None,
    expires_at: int | None = None,
    db: Session,
) -> ConnectorCredentialModel:
    row = (
        db.query(ConnectorCredentialModel)
        .filter_by(athlete_id=athlete_id, provider="strava")
        .first()
    )
    if row is None:
        row = ConnectorCredentialModel(
            id=str(uuid.uuid4()),
            athlete_id=athlete_id,
            provider="strava",
        )
        db.add(row)

    row.extra_json = extra_json
    if access_token_enc is not None:
        row.access_token_enc = access_token_enc
    if refresh_token_enc is not None:
        row.refresh_token_enc = refresh_token_enc
    if expires_at is not None:
        row.expires_at = expires_at

    db.commit()
    db.refresh(row)
    return row


def connect(athlete_id: str, db: Session) -> dict:
    """Generate Strava OAuth URL + store anti-CSRF state.

    Raises RuntimeError if STRAVA_ENCRYPTION_KEY is not set.
    """
    _get_encryption_key()  # Fail fast if key missing

    state = secrets.token_urlsafe(16)
    cred = ConnectorCredential(
        athlete_id=athlete_id,  # type: ignore[arg-type]
        provider="strava",
    )
    client_id = os.getenv("STRAVA_CLIENT_ID", "")
    with StravaConnector(cred, client_id=client_id, client_secret="") as connector:
        auth_url = connector.get_auth_url()

    auth_url += f"&state={state}"

    # Store state for CSRF validation on callback
    existing = (
        db.query(ConnectorCredentialModel)
        .filter_by(athlete_id=athlete_id, provider="strava")
        .first()
    )
    existing_extra = json.loads(existing.extra_json) if existing else {}
    existing_extra["state"] = state

    _upsert_credential(
        athlete_id=athlete_id,
        extra_json=json.dumps(existing_extra),
        db=db,
    )

    return {"auth_url": auth_url}


def callback(code: str, state: str, db: Session) -> dict:
    """Exchange authorization code for tokens, encrypt and persist.

    Raises ValueError if state is invalid (CSRF protection).
    Raises HTTPException(502) if Strava token exchange fails.
    """
    key = _get_encryption_key()

    # Validate state (CSRF protection)
    cred_rows = (
        db.query(ConnectorCredentialModel)
        .filter_by(provider="strava")
        .all()
    )
    matching = next(
        (r for r in cred_rows if json.loads(r.extra_json or "{}").get("state") == state),
        None,
    )
    if matching is None:
        raise ValueError(f"Invalid state parameter: {state!r}")

    cred = ConnectorCredential(
        athlete_id=matching.athlete_id,  # type: ignore[arg-type]
        provider="strava",
    )
    client_id = os.getenv("STRAVA_CLIENT_ID", "")
    client_secret = os.getenv("STRAVA_CLIENT_SECRET", "")

    with StravaConnector(cred, client_id=client_id, client_secret=client_secret) as connector:
        updated = connector.exchange_code(code)

    access_enc = encrypt_token(updated.access_token, key)
    refresh_enc = encrypt_token(updated.refresh_token, key)

    # Clear state from extra_json after successful exchange
    extra = json.loads(matching.extra_json or "{}")
    extra.pop("state", None)

    _upsert_credential(
        athlete_id=matching.athlete_id,
        extra_json=json.dumps(extra),
        access_token_enc=access_enc,
        refresh_token_enc=refresh_enc,
        expires_at=updated.expires_at,
        db=db,
    )

    return {"connected": True, "athlete_id": matching.athlete_id}


def get_valid_credential(athlete_id: str, db: Session) -> ConnectorCredential:
    """Load, decrypt, and auto-refresh Strava token if expiring within 5 min.

    Returns ConnectorCredential with plaintext tokens (in-memory only).
    Raises ValueError if no Strava credential exists for this athlete.
    """
    key = _get_encryption_key()

    row = (
        db.query(ConnectorCredentialModel)
        .filter_by(athlete_id=athlete_id, provider="strava")
        .first()
    )
    if row is None or row.access_token_enc is None:
        raise ValueError(f"Strava not connected for athlete {athlete_id}")

    access = decrypt_token(row.access_token_enc, key)
    refresh = decrypt_token(row.refresh_token_enc, key)

    cred = ConnectorCredential(
        athlete_id=athlete_id,  # type: ignore[arg-type]
        provider="strava",
        access_token=access,
        refresh_token=refresh,
        expires_at=row.expires_at,
    )

    # Auto-refresh if expiring within 5 minutes
    if row.expires_at is not None and row.expires_at < (time.time() + 300):
        client_id = os.getenv("STRAVA_CLIENT_ID", "")
        client_secret = os.getenv("STRAVA_CLIENT_SECRET", "")
        with StravaConnector(cred, client_id=client_id, client_secret=client_secret) as connector:
            updated = connector._do_refresh_token()

        new_access_enc = encrypt_token(updated.access_token, key)
        new_refresh_enc = encrypt_token(updated.refresh_token, key)
        row.access_token_enc = new_access_enc
        row.refresh_token_enc = new_refresh_enc
        row.expires_at = updated.expires_at
        db.commit()

        cred = updated

    return cred
