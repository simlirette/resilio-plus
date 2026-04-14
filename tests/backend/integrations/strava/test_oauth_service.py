# tests/backend/integrations/strava/test_oauth_service.py
import json
import time
import uuid

import httpx
import pytest
import respx
from cryptography.fernet import Fernet
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db import models  # noqa: F401
from app.db.models import AthleteModel, ConnectorCredentialModel
from app.integrations.strava.oauth_service import (
    connect,
    callback,
    get_valid_credential,
    encrypt_token,
    decrypt_token,
)


TEST_KEY = Fernet.generate_key().decode()
_ATHLETE_ID = str(uuid.uuid4())


@pytest.fixture()
def db_session(monkeypatch):
    monkeypatch.setenv("STRAVA_CLIENT_ID", "test_id")
    monkeypatch.setenv("STRAVA_CLIENT_SECRET", "test_secret")
    monkeypatch.setenv("STRAVA_REDIRECT_URI", "http://localhost/callback")
    monkeypatch.setenv("STRAVA_ENCRYPTION_KEY", TEST_KEY)

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(engine)
    with Session() as session:
        session.add(AthleteModel(
            id=_ATHLETE_ID, name="Alice", age=30, sex="F",
            weight_kg=60.0, height_cm=168.0,
            sports_json='["running"]', primary_sport="running",
            goals_json='["run fast"]', available_days_json="[0]",
            equipment_json="[]",
            hours_per_week=10.0,
        ))
        session.commit()
        yield session
    Base.metadata.drop_all(engine)


# ── encrypt/decrypt ─────────────────────────────────────────────────────────

def test_encrypt_decrypt_roundtrip():
    plain = "my_access_token_12345"
    cipher = encrypt_token(plain, TEST_KEY)
    assert cipher != plain
    assert decrypt_token(cipher, TEST_KEY) == plain


def test_encrypt_produces_different_ciphertext_each_time():
    """Fernet uses random IV — same plaintext → different ciphertext."""
    c1 = encrypt_token("token", TEST_KEY)
    c2 = encrypt_token("token", TEST_KEY)
    assert c1 != c2


# ── connect ─────────────────────────────────────────────────────────────────

def test_connect_returns_auth_url_with_state(db_session):
    result = connect(_ATHLETE_ID, db_session)
    assert "strava.com" in result["auth_url"]
    assert "state=" in result["auth_url"]


def test_connect_stores_state_in_extra_json(db_session):
    connect(_ATHLETE_ID, db_session)
    cred = db_session.query(ConnectorCredentialModel).filter_by(
        athlete_id=_ATHLETE_ID, provider="strava"
    ).first()
    assert cred is not None
    extra = json.loads(cred.extra_json)
    assert "state" in extra


def test_connect_raises_if_encryption_key_missing(db_session, monkeypatch):
    monkeypatch.delenv("STRAVA_ENCRYPTION_KEY", raising=False)
    with pytest.raises(Exception, match="STRAVA_ENCRYPTION_KEY"):
        connect(_ATHLETE_ID, db_session)


# ── callback ────────────────────────────────────────────────────────────────

@respx.mock
def test_callback_stores_encrypted_tokens(db_session):
    # First, connect to create state
    connect(_ATHLETE_ID, db_session)
    cred = db_session.query(ConnectorCredentialModel).filter_by(
        athlete_id=_ATHLETE_ID, provider="strava"
    ).first()
    state = json.loads(cred.extra_json)["state"]

    respx.post("https://www.strava.com/oauth/token").mock(
        return_value=httpx.Response(200, json={
            "access_token": "plain_access",
            "refresh_token": "plain_refresh",
            "expires_at": 9999999999,
        })
    )
    result = callback(code="abc", state=state, db=db_session)
    assert result["connected"] is True

    db_session.expire_all()
    cred = db_session.query(ConnectorCredentialModel).filter_by(
        athlete_id=_ATHLETE_ID, provider="strava"
    ).first()
    # Tokens stored as ciphertext — not plaintext
    assert cred.access_token_enc != "plain_access"
    assert cred.refresh_token_enc != "plain_refresh"
    # But decryptable
    assert decrypt_token(cred.access_token_enc, TEST_KEY) == "plain_access"
    assert decrypt_token(cred.refresh_token_enc, TEST_KEY) == "plain_refresh"
    # State cleared
    assert "state" not in json.loads(cred.extra_json)


def test_callback_invalid_state_raises_value_error(db_session):
    with pytest.raises(ValueError, match="Invalid state"):
        callback(code="abc", state="nonexistent_state", db=db_session)


# ── get_valid_credential ─────────────────────────────────────────────────────

def test_get_valid_credential_returns_plaintext(db_session):
    """After callback, get_valid_credential decrypts tokens."""
    connect(_ATHLETE_ID, db_session)
    cred_row = db_session.query(ConnectorCredentialModel).filter_by(
        athlete_id=_ATHLETE_ID, provider="strava"
    ).first()
    state = json.loads(cred_row.extra_json)["state"]

    with respx.mock:
        respx.post("https://www.strava.com/oauth/token").mock(
            return_value=httpx.Response(200, json={
                "access_token": "access_123",
                "refresh_token": "refresh_456",
                "expires_at": int(time.time()) + 3600,
            })
        )
        callback(code="abc", state=state, db=db_session)

    cred = get_valid_credential(_ATHLETE_ID, db_session)
    assert cred.access_token == "access_123"
    assert cred.refresh_token == "refresh_456"


@respx.mock
def test_get_valid_credential_auto_refreshes_expired_token(db_session):
    """When expires_at < now + 300, token is refreshed."""
    connect(_ATHLETE_ID, db_session)
    cred_row = db_session.query(ConnectorCredentialModel).filter_by(
        athlete_id=_ATHLETE_ID, provider="strava"
    ).first()
    state = json.loads(cred_row.extra_json)["state"]

    # Initial exchange — token expires in 60s (< 300s threshold → will refresh)
    respx.post("https://www.strava.com/oauth/token").mock(
        side_effect=[
            httpx.Response(200, json={
                "access_token": "old_access",
                "refresh_token": "old_refresh",
                "expires_at": int(time.time()) + 60,
            }),
            httpx.Response(200, json={
                "access_token": "new_access",
                "refresh_token": "new_refresh",
                "expires_at": int(time.time()) + 3600,
            }),
        ]
    )
    callback(code="abc", state=state, db=db_session)

    cred = get_valid_credential(_ATHLETE_ID, db_session)
    assert cred.access_token == "new_access"


def test_get_valid_credential_raises_if_no_tokens(db_session):
    """Row exists (state-only, before callback) but access_token_enc is NULL → ValueError."""
    connect(_ATHLETE_ID, db_session)  # Creates row with state but no tokens
    with pytest.raises(ValueError, match="Strava not connected"):
        get_valid_credential(_ATHLETE_ID, db_session)
