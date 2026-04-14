# Strava OAuth 2.0 + Activity Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the existing partial Strava OAuth implementation with a production-ready module (`backend/app/integrations/strava/`) that encrypts tokens, supports incremental sync, persists activities, and follows the V3-P JWT-auth pattern.

**Architecture:** New `integrations/strava/` module with three focused files (`oauth_service.py`, `activity_mapper.py`, `sync_service.py`) plus a new `routes/strava.py`. Encrypted tokens (`Fernet`) stored in new `_enc` columns on `ConnectorCredentialModel`. Activities persisted in a new `strava_activities` table. Old `/{athlete_id}/connectors/strava/` routes removed entirely.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, `cryptography.fernet`, `httpx`, `respx` (tests), existing `StravaConnector` (unchanged).

---

## Codebase Context (read before starting any task)

- **Existing connector:** `backend/app/connectors/strava.py` — `StravaConnector(BaseConnector)` with `get_auth_url()`, `exchange_code(code)`, `_do_refresh_token()`, `fetch_activities(since, until)`. Already handles retry + rate limits via `BaseConnector`. **Do NOT modify this file.**
- **Existing schema:** `backend/app/schemas/connector.py` — `ConnectorCredential`, `StravaActivity` (fields: `id`, `name`, `sport_type`, `date`, `duration_seconds`, `distance_meters`, `elevation_gain_meters`, `average_hr`, `max_hr`, `perceived_exertion`).
- **Existing DB model:** `backend/app/db/models.py:147` — `ConnectorCredentialModel` has `access_token`, `refresh_token` (plaintext), `expires_at` (int), `extra_json`. Migration 0008 drops `access_token`/`refresh_token` and adds `access_token_enc`, `refresh_token_enc`, `last_sync_at`.
- **Auth pattern:** `from ..core.security import get_current_athlete_id` — used in `routes/food_search.py` and `routes/integrations.py` as `Depends(get_current_athlete_id)`.
- **DB dependency:** `from ..db.database import get_db` — `DB = Annotated[Session, Depends(get_db)]`.
- **Latest migration:** `alembic/versions/0007_food_cache.py` (`down_revision="0006"`). Next: `0008`.
- **pytest:** `C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe`
- **Run all tests:** `cd C:\Users\simon\resilio-plus && C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/ -x -q`
- **`git pull --rebase` before first commit.**

---

## File Map

| Action | File | Responsibility |
|---|---|---|
| Create | `backend/app/integrations/strava/__init__.py` | Package marker |
| Create | `backend/app/integrations/strava/oauth_service.py` | Token encrypt/decrypt, connect, callback, get_valid_credential |
| Create | `backend/app/integrations/strava/activity_mapper.py` | `StravaActivity` → `StravaActivityModel` |
| Create | `backend/app/integrations/strava/sync_service.py` | Incremental sync, upsert activities |
| Create | `backend/app/schemas/strava.py` | `SyncSummary` Pydantic model |
| Create | `backend/app/routes/strava.py` | 3 endpoints |
| Create | `alembic/versions/0008_strava_v2.py` | Drop plaintext cols, add enc cols + last_sync_at, create strava_activities |
| Modify | `backend/app/db/models.py` | Add `StravaActivityModel`; replace `access_token`/`refresh_token` with `_enc` + `last_sync_at` |
| Modify | `backend/app/schemas/connector.py` | Add `avg_watts: float \| None = None` to `StravaActivity` |
| Modify | `backend/app/main.py` | Register `strava_router` |
| Modify | `backend/app/routes/connectors.py` | Remove 3 Strava route functions + remove strava from sync_all loop |
| Modify | `backend/app/services/sync_service.py` | Remove `sync_strava()` static method |
| Modify | `.env.example` | Add `STRAVA_ENCRYPTION_KEY` |
| Create | `tests/backend/integrations/strava/__init__.py` | Package marker |
| Create | `tests/backend/integrations/strava/test_oauth_service.py` | Unit tests for oauth_service |
| Create | `tests/backend/integrations/strava/test_activity_mapper.py` | Unit tests for mapper |
| Create | `tests/backend/integrations/strava/test_sync_service.py` | Unit tests for sync |
| Create | `tests/backend/api/test_strava.py` | API-level tests |
| Modify | `tests/backend/api/test_connectors.py` | Remove 6 Strava OAuth test functions + strava_env fixture |
| Modify | `tests/backend/api/test_connectors_sync.py` | Remove 2 Strava sync test functions |
| Modify | `tests/backend/api/test_connectors_phase9.py` | Remove 1 Strava sync test function |
| Modify | `tests/backend/services/test_sync_service.py` | Remove 5 `sync_strava` test functions |

---

## Task 1: Schemas

**Files:**
- Modify: `backend/app/schemas/connector.py`
- Create: `backend/app/schemas/strava.py`
- Test: `tests/backend/integrations/strava/test_activity_mapper.py` (partial — schema import test)

- [ ] **Step 1: Add `avg_watts` to `StravaActivity`**

In `backend/app/schemas/connector.py`, find `class StravaActivity` and add `avg_watts` field:

```python
class StravaActivity(BaseModel):
    id: str  # "strava_{strava_id}"
    name: str
    sport_type: str
    date: date
    duration_seconds: int
    distance_meters: float | None = None
    elevation_gain_meters: float | None = None
    average_hr: float | None = None
    max_hr: float | None = None
    avg_watts: float | None = None          # ← add this line
    perceived_exertion: int | None = Field(default=None, ge=1, le=10)
    laps: list[StravaLap] = Field(default_factory=list)
```

- [ ] **Step 2: Create `backend/app/schemas/strava.py`**

```python
from pydantic import BaseModel


class SyncSummary(BaseModel):
    synced: int
    skipped: int  # activities with unrecognized sport_type
    sport_breakdown: dict[str, int]  # {"running": N, "biking": N, "swimming": N}
```

- [ ] **Step 3: Verify imports work**

```bash
cd C:\Users\simon\resilio-plus
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\python.exe -c "from backend.app.schemas.strava import SyncSummary; from backend.app.schemas.connector import StravaActivity; print('ok')"
```

Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git pull --rebase
git add backend/app/schemas/connector.py backend/app/schemas/strava.py
git commit -m "feat(strava): add SyncSummary schema + avg_watts to StravaActivity"
```

---

## Task 2: DB Models

**Files:**
- Modify: `backend/app/db/models.py`

- [ ] **Step 1: Write failing test**

Create `tests/backend/integrations/strava/__init__.py` (empty):
```python
```

Create `tests/backend/integrations/strava/test_activity_mapper.py` with a schema import test first:

```python
# tests/backend/integrations/strava/test_activity_mapper.py
from app.db.models import StravaActivityModel, ConnectorCredentialModel


def test_strava_activity_model_has_enc_columns():
    cols = {c.key for c in StravaActivityModel.__table__.columns}
    assert "access_token_enc" not in cols  # belongs to ConnectorCredentialModel
    assert "strava_id" in cols
    assert "sport_type" in cols
    assert "raw_json" in cols


def test_connector_credential_has_enc_columns():
    cols = {c.key for c in ConnectorCredentialModel.__table__.columns}
    assert "access_token_enc" in cols
    assert "refresh_token_enc" in cols
    assert "last_sync_at" in cols
    assert "access_token" not in cols
    assert "refresh_token" not in cols
```

- [ ] **Step 2: Run to verify it fails**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/integrations/strava/test_activity_mapper.py -v
```

Expected: FAIL — `StravaActivityModel` not defined, `access_token_enc` not in `ConnectorCredentialModel`

- [ ] **Step 3: Patch `ConnectorCredentialModel` in `backend/app/db/models.py`**

Replace the existing `access_token` and `refresh_token` columns with encrypted versions. Find the `ConnectorCredentialModel` class (around line 147) and replace it with:

```python
class ConnectorCredentialModel(Base):
    __tablename__ = "connector_credentials"

    id = Column(String, primary_key=True)
    athlete_id = Column(String, ForeignKey("athletes.id"), nullable=False)
    provider = Column(String, nullable=False)          # "strava"|"hevy"|"fatsecret"|"terra"
    access_token_enc = Column(Text, nullable=True)     # Fernet ciphertext (Strava only)
    refresh_token_enc = Column(Text, nullable=True)    # Fernet ciphertext (Strava only)
    expires_at = Column(Integer, nullable=True)        # Unix timestamp
    last_sync_at = Column(DateTime(timezone=True), nullable=True)  # NULL = never synced
    extra_json = Column(Text, nullable=False, default="{}")
    # Relationships
    athlete = relationship("AthleteModel", back_populates="credentials")

    __table_args__ = (UniqueConstraint("athlete_id", "provider"),)
```

- [ ] **Step 4: Add `StravaActivityModel` to `backend/app/db/models.py`**

Append this class after `ConnectorCredentialModel`:

```python
class StravaActivityModel(Base):
    __tablename__ = "strava_activities"

    id = Column(String, primary_key=True)                  # "strava_{strava_id}"
    athlete_id = Column(String, ForeignKey("athletes.id"), nullable=False)
    strava_id = Column(BigInteger, nullable=False, unique=True)
    sport_type = Column(String, nullable=False)            # "running"|"biking"|"swimming"
    name = Column(String, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False)
    duration_s = Column(Integer, nullable=False)
    distance_m = Column(Float, nullable=True)
    elevation_m = Column(Float, nullable=True)
    avg_hr = Column(Integer, nullable=True)
    max_hr = Column(Integer, nullable=True)
    avg_watts = Column(Float, nullable=True)
    perceived_exertion = Column(Float, nullable=True)
    raw_json = Column(Text, nullable=False, default="{}")
```

Make sure `BigInteger` is imported at the top of models.py — check the existing imports line and add it if missing:
```python
from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, Float, ForeignKey,
    Integer, String, Text, UniqueConstraint,
)
```

- [ ] **Step 5: Run test to verify it passes**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/integrations/strava/test_activity_mapper.py::test_connector_credential_has_enc_columns tests/backend/integrations/strava/test_activity_mapper.py::test_strava_activity_model_has_enc_columns -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/db/models.py tests/backend/integrations/strava/__init__.py tests/backend/integrations/strava/test_activity_mapper.py
git commit -m "feat(strava): add StravaActivityModel + patch ConnectorCredentialModel enc columns"
```

---

## Task 3: Alembic Migration 0008

**Files:**
- Create: `alembic/versions/0008_strava_v2.py`

- [ ] **Step 1: Create migration file**

```python
# alembic/versions/0008_strava_v2.py
"""Strava V2: encrypted token columns + strava_activities table

Revision ID: 0008
Revises: 0007
Create Date: 2026-04-14 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- connector_credentials: drop plaintext, add encrypted + last_sync_at ---
    with op.batch_alter_table("connector_credentials") as batch_op:
        batch_op.drop_column("access_token")
        batch_op.drop_column("refresh_token")
        batch_op.add_column(sa.Column("access_token_enc", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("refresh_token_enc", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True)
        )

    # --- strava_activities table ---
    op.create_table(
        "strava_activities",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("athlete_id", sa.String(), sa.ForeignKey("athletes.id"), nullable=False),
        sa.Column("strava_id", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("sport_type", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_s", sa.Integer(), nullable=False),
        sa.Column("distance_m", sa.Float(), nullable=True),
        sa.Column("elevation_m", sa.Float(), nullable=True),
        sa.Column("avg_hr", sa.Integer(), nullable=True),
        sa.Column("max_hr", sa.Integer(), nullable=True),
        sa.Column("avg_watts", sa.Float(), nullable=True),
        sa.Column("perceived_exertion", sa.Float(), nullable=True),
        sa.Column("raw_json", sa.Text(), nullable=False, server_default="{}"),
    )


def downgrade() -> None:
    op.drop_table("strava_activities")
    with op.batch_alter_table("connector_credentials") as batch_op:
        batch_op.drop_column("last_sync_at")
        batch_op.drop_column("refresh_token_enc")
        batch_op.drop_column("access_token_enc")
        batch_op.add_column(sa.Column("access_token", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("refresh_token", sa.Text(), nullable=True))
```

- [ ] **Step 2: Verify migration runs without error**

```bash
cd C:\Users\simon\resilio-plus
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\python.exe -m alembic upgrade head 2>&1
```

Expected: `Running upgrade 0007 -> 0008` with no errors.

- [ ] **Step 3: Commit**

```bash
git add alembic/versions/0008_strava_v2.py
git commit -m "feat(strava): Alembic migration 0008 — enc token columns + strava_activities"
```

---

## Task 4: `oauth_service.py`

**Files:**
- Create: `backend/app/integrations/strava/__init__.py`
- Create: `backend/app/integrations/strava/oauth_service.py`
- Test: `tests/backend/integrations/strava/test_oauth_service.py`

- [ ] **Step 1: Write failing tests**

Create `backend/app/integrations/strava/__init__.py` (empty).

Create `tests/backend/integrations/strava/test_oauth_service.py`:

```python
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
            sports='["running"]', primary_sport="running",
            goals='["run fast"]', available_days="[0]",
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
```

- [ ] **Step 2: Run to verify tests fail**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/integrations/strava/test_oauth_service.py -v
```

Expected: FAIL — `cannot import name 'connect' from 'app.integrations.strava.oauth_service'`

- [ ] **Step 3: Create `backend/app/integrations/strava/oauth_service.py`**

```python
# backend/app/integrations/strava/oauth_service.py
"""Strava OAuth service: token encryption, connect flow, auto-refresh."""
import json
import os
import secrets
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
    cred_row = (
        db.query(ConnectorCredentialModel)
        .filter_by(provider="strava")
        .all()
    )
    matching = next(
        (r for r in cred_row if json.loads(r.extra_json or "{}").get("state") == state),
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

    return {"connected": True}


def get_valid_credential(athlete_id: str, db: Session) -> ConnectorCredential:
    """Load, decrypt, and auto-refresh Strava token if expiring within 5 min.

    Returns ConnectorCredential with plaintext tokens (in-memory only).
    Raises ValueError if no Strava credential exists for this athlete.
    """
    import time

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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/integrations/strava/test_oauth_service.py -v
```

Expected: All 9 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/integrations/strava/__init__.py backend/app/integrations/strava/oauth_service.py tests/backend/integrations/strava/test_oauth_service.py
git commit -m "feat(strava): oauth_service — encrypted connect/callback/auto-refresh"
```

---

## Task 5: `activity_mapper.py`

**Files:**
- Create: `backend/app/integrations/strava/activity_mapper.py`
- Extend: `tests/backend/integrations/strava/test_activity_mapper.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/backend/integrations/strava/test_activity_mapper.py`:

```python
import json
from datetime import date, datetime, timezone

from app.schemas.connector import StravaActivity
from app.integrations.strava.activity_mapper import SPORT_MAP, to_model

_ATHLETE_ID = "athlete-123"


def _make_activity(**overrides) -> StravaActivity:
    defaults = dict(
        id="strava_999",
        name="Morning Run",
        sport_type="Run",
        date=date(2026, 4, 10),
        duration_seconds=3600,
        distance_meters=10000.0,
        elevation_gain_meters=150.0,
        average_hr=145,
        max_hr=175,
        avg_watts=None,
        perceived_exertion=7,
    )
    defaults.update(overrides)
    return StravaActivity(**defaults)


def test_run_maps_to_running():
    model = to_model(_make_activity(sport_type="Run"), _ATHLETE_ID)
    assert model.sport_type == "running"


def test_trail_run_maps_to_running():
    model = to_model(_make_activity(sport_type="TrailRun"), _ATHLETE_ID)
    assert model.sport_type == "running"


def test_virtual_ride_maps_to_biking():
    model = to_model(_make_activity(sport_type="VirtualRide"), _ATHLETE_ID)
    assert model.sport_type == "biking"


def test_ride_maps_to_biking():
    model = to_model(_make_activity(sport_type="Ride"), _ATHLETE_ID)
    assert model.sport_type == "biking"


def test_swim_maps_to_swimming():
    model = to_model(_make_activity(sport_type="Swim"), _ATHLETE_ID)
    assert model.sport_type == "swimming"


def test_unknown_sport_type_lowercased():
    model = to_model(_make_activity(sport_type="Yoga"), _ATHLETE_ID)
    assert model.sport_type == "yoga"


def test_strava_id_extracted_from_id_field():
    model = to_model(_make_activity(id="strava_12345"), _ATHLETE_ID)
    assert model.strava_id == 12345


def test_optional_fields_none_when_absent():
    activity = _make_activity(
        distance_meters=None,
        elevation_gain_meters=None,
        average_hr=None,
        max_hr=None,
        avg_watts=None,
        perceived_exertion=None,
    )
    model = to_model(activity, _ATHLETE_ID)
    assert model.distance_m is None
    assert model.elevation_m is None
    assert model.avg_hr is None
    assert model.max_hr is None
    assert model.avg_watts is None
    assert model.perceived_exertion is None


def test_raw_json_stored():
    model = to_model(_make_activity(), _ATHLETE_ID)
    raw = json.loads(model.raw_json)
    assert "sport_type" in raw
    assert raw["name"] == "Morning Run"


def test_model_id_is_strava_prefixed():
    model = to_model(_make_activity(id="strava_999"), _ATHLETE_ID)
    assert model.id == "strava_999"


def test_athlete_id_set_correctly():
    model = to_model(_make_activity(), _ATHLETE_ID)
    assert model.athlete_id == _ATHLETE_ID
```

- [ ] **Step 2: Run to verify tests fail**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/integrations/strava/test_activity_mapper.py -k "not test_strava_activity_model" -v
```

Expected: FAIL — `cannot import name 'to_model'`

- [ ] **Step 3: Create `backend/app/integrations/strava/activity_mapper.py`**

```python
# backend/app/integrations/strava/activity_mapper.py
"""Map StravaActivity schema objects to StravaActivityModel DB rows."""
import json
from datetime import datetime, timezone

from ...db.models import StravaActivityModel
from ...schemas.connector import StravaActivity

SPORT_MAP: dict[str, str] = {
    "Run": "running",
    "TrailRun": "running",
    "VirtualRun": "running",
    "Ride": "biking",
    "VirtualRide": "biking",
    "EBikeRide": "biking",
    "Swim": "swimming",
}


def to_model(activity: StravaActivity, athlete_id: str) -> StravaActivityModel:
    """Convert a StravaActivity (connector schema) to a StravaActivityModel (DB row).

    `activity.id` has format "strava_{int}" — strava_id is the integer part.
    sport_type is mapped via SPORT_MAP; unrecognized types are lowercased.
    """
    sport = SPORT_MAP.get(activity.sport_type, activity.sport_type.lower())
    strava_id = int(activity.id.replace("strava_", ""))

    # Convert date → datetime at midnight UTC for started_at
    started_at = datetime(
        activity.date.year, activity.date.month, activity.date.day,
        tzinfo=timezone.utc,
    )

    raw = {
        "id": strava_id,
        "name": activity.name,
        "sport_type": activity.sport_type,
        "date": activity.date.isoformat(),
        "duration_seconds": activity.duration_seconds,
        "distance_meters": activity.distance_meters,
        "elevation_gain_meters": activity.elevation_gain_meters,
        "average_hr": activity.average_hr,
        "max_hr": activity.max_hr,
        "avg_watts": activity.avg_watts,
        "perceived_exertion": activity.perceived_exertion,
    }

    return StravaActivityModel(
        id=activity.id,
        athlete_id=athlete_id,
        strava_id=strava_id,
        sport_type=sport,
        name=activity.name,
        started_at=started_at,
        duration_s=activity.duration_seconds,
        distance_m=activity.distance_meters,
        elevation_m=activity.elevation_gain_meters,
        avg_hr=int(activity.average_hr) if activity.average_hr is not None else None,
        max_hr=int(activity.max_hr) if activity.max_hr is not None else None,
        avg_watts=activity.avg_watts,
        perceived_exertion=float(activity.perceived_exertion) if activity.perceived_exertion is not None else None,
        raw_json=json.dumps(raw),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/integrations/strava/test_activity_mapper.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/integrations/strava/activity_mapper.py tests/backend/integrations/strava/test_activity_mapper.py
git commit -m "feat(strava): activity_mapper — StravaActivity → StravaActivityModel"
```

---

## Task 6: `integrations/strava/sync_service.py`

**Files:**
- Create: `backend/app/integrations/strava/sync_service.py`
- Create: `tests/backend/integrations/strava/test_sync_service.py`

- [ ] **Step 1: Write failing tests**

Create `tests/backend/integrations/strava/test_sync_service.py`:

```python
# tests/backend/integrations/strava/test_sync_service.py
import json
import time
import uuid
from datetime import datetime, timedelta, timezone

import httpx
import pytest
import respx
from cryptography.fernet import Fernet
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db import models  # noqa: F401
from app.db.models import AthleteModel, ConnectorCredentialModel, StravaActivityModel
from app.integrations.strava.oauth_service import encrypt_token
from app.integrations.strava.sync_service import sync
from app.connectors.base import ConnectorRateLimitError

TEST_KEY = Fernet.generate_key().decode()
_ATHLETE_ID = str(uuid.uuid4())

STRAVA_ACTIVITIES_URL = "https://www.strava.com/api/v3/athlete/activities"
STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"


def _make_raw_activity(strava_id: int = 1, sport_type: str = "Run") -> dict:
    return {
        "id": strava_id,
        "name": "Morning Run",
        "sport_type": sport_type,
        "type": sport_type,
        "start_date_local": "2026-04-10T07:00:00Z",
        "elapsed_time": 3600,
        "distance": 10000.0,
        "total_elevation_gain": 100.0,
        "average_heartrate": 145.0,
        "max_heartrate": 175.0,
        "average_watts": None,
        "perceived_exertion": None,
    }


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
            sports='["running"]', primary_sport="running",
            goals='["run fast"]', available_days="[0]",
            hours_per_week=10.0,
        ))
        session.commit()
        yield session
    Base.metadata.drop_all(engine)


def _seed_strava_cred(db_session, expires_at: int | None = None) -> None:
    """Seed a valid encrypted Strava credential for _ATHLETE_ID."""
    if expires_at is None:
        expires_at = int(time.time()) + 3600
    db_session.add(ConnectorCredentialModel(
        id=str(uuid.uuid4()),
        athlete_id=_ATHLETE_ID,
        provider="strava",
        access_token_enc=encrypt_token("access_tok", TEST_KEY),
        refresh_token_enc=encrypt_token("refresh_tok", TEST_KEY),
        expires_at=expires_at,
        last_sync_at=None,
        extra_json="{}",
    ))
    db_session.commit()


@respx.mock
def test_sync_null_last_sync_at_fetches_90_days(db_session):
    """When last_sync_at is NULL, since = now - 90 days."""
    _seed_strava_cred(db_session)
    respx.get(STRAVA_ACTIVITIES_URL).mock(return_value=httpx.Response(200, json=[]))

    result = sync(_ATHLETE_ID, db_session)
    assert result.synced == 0
    assert result.skipped == 0

    # Verify request was made with 'after' param approximately 90 days ago
    request = respx.calls.last.request
    params = dict(x.split("=") for x in request.url.params.multi_items())
    after_ts = int(params["after"])
    expected = int((datetime.now(timezone.utc) - timedelta(days=90)).timestamp())
    assert abs(after_ts - expected) < 10  # within 10 seconds


@respx.mock
def test_sync_incremental_uses_last_sync_at(db_session):
    """When last_sync_at is set, 'after' param uses that timestamp."""
    _seed_strava_cred(db_session)

    last_sync = datetime(2026, 4, 1, tzinfo=timezone.utc)
    cred = db_session.query(ConnectorCredentialModel).filter_by(
        athlete_id=_ATHLETE_ID, provider="strava"
    ).first()
    cred.last_sync_at = last_sync
    db_session.commit()

    respx.get(STRAVA_ACTIVITIES_URL).mock(return_value=httpx.Response(200, json=[]))
    sync(_ATHLETE_ID, db_session)

    request = respx.calls.last.request
    params = dict(x.split("=") for x in request.url.params.multi_items())
    assert int(params["after"]) == int(last_sync.timestamp())


@respx.mock
def test_sync_upserts_activities(db_session):
    """Activities returned by API are persisted to strava_activities."""
    _seed_strava_cred(db_session)
    respx.get(STRAVA_ACTIVITIES_URL).mock(
        return_value=httpx.Response(200, json=[
            _make_raw_activity(1, "Run"),
            _make_raw_activity(2, "Ride"),
        ])
    )

    result = sync(_ATHLETE_ID, db_session)
    assert result.synced == 2
    assert result.skipped == 0
    assert result.sport_breakdown["running"] == 1
    assert result.sport_breakdown["biking"] == 1

    rows = db_session.query(StravaActivityModel).filter_by(athlete_id=_ATHLETE_ID).all()
    assert len(rows) == 2


@respx.mock
def test_sync_idempotent(db_session):
    """Re-syncing same activities does not create duplicate rows."""
    _seed_strava_cred(db_session)
    activity_json = [_make_raw_activity(1, "Run")]
    respx.get(STRAVA_ACTIVITIES_URL).mock(
        return_value=httpx.Response(200, json=activity_json)
    )

    sync(_ATHLETE_ID, db_session)
    sync(_ATHLETE_ID, db_session)

    rows = db_session.query(StravaActivityModel).filter_by(athlete_id=_ATHLETE_ID).all()
    assert len(rows) == 1


@respx.mock
def test_sync_updates_last_sync_at(db_session):
    """After sync, last_sync_at is updated to ~now."""
    _seed_strava_cred(db_session)
    respx.get(STRAVA_ACTIVITIES_URL).mock(return_value=httpx.Response(200, json=[]))

    before = datetime.now(timezone.utc)
    sync(_ATHLETE_ID, db_session)

    db_session.expire_all()
    cred = db_session.query(ConnectorCredentialModel).filter_by(
        athlete_id=_ATHLETE_ID, provider="strava"
    ).first()
    assert cred.last_sync_at is not None
    last_sync = cred.last_sync_at
    if last_sync.tzinfo is None:
        last_sync = last_sync.replace(tzinfo=timezone.utc)
    assert last_sync >= before


@respx.mock
def test_sync_skips_unknown_sport_type(db_session):
    """Activities with sport types not in SPORT_MAP go to skipped count."""
    _seed_strava_cred(db_session)
    respx.get(STRAVA_ACTIVITIES_URL).mock(
        return_value=httpx.Response(200, json=[_make_raw_activity(1, "Yoga")])
    )

    result = sync(_ATHLETE_ID, db_session)
    assert result.skipped == 1
    assert result.synced == 0


def test_sync_raises_if_not_connected(db_session):
    """ValueError raised when no Strava credential exists."""
    with pytest.raises(ValueError, match="Strava not connected"):
        sync(_ATHLETE_ID, db_session)
```

- [ ] **Step 2: Run to verify tests fail**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/integrations/strava/test_sync_service.py -v
```

Expected: FAIL — `cannot import name 'sync'`

- [ ] **Step 3: Create `backend/app/integrations/strava/sync_service.py`**

```python
# backend/app/integrations/strava/sync_service.py
"""Incremental Strava activity sync: fetch → map → upsert strava_activities."""
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from ...connectors.strava import StravaConnector
from ...db.models import ConnectorCredentialModel, StravaActivityModel
from ...schemas.strava import SyncSummary
from .activity_mapper import SPORT_MAP, to_model
from .oauth_service import get_valid_credential


def sync(athlete_id: str, db: Session) -> SyncSummary:
    """Fetch Strava activities since last_sync_at and upsert to strava_activities.

    - If last_sync_at is NULL, fetches last 90 days (initial bootstrap).
    - Incremental on subsequent calls.
    - Idempotent: re-syncing same activities updates existing rows.
    - Raises ValueError if Strava is not connected for this athlete.
    """
    cred_row = (
        db.query(ConnectorCredentialModel)
        .filter_by(athlete_id=athlete_id, provider="strava")
        .first()
    )
    if cred_row is None:
        raise ValueError(f"Strava not connected for athlete {athlete_id}")

    cred = get_valid_credential(athlete_id, db)

    now = datetime.now(timezone.utc)
    if cred_row.last_sync_at is None:
        since = now - timedelta(days=90)
    else:
        since = cred_row.last_sync_at
        if since.tzinfo is None:
            since = since.replace(tzinfo=timezone.utc)

    client_id = os.getenv("STRAVA_CLIENT_ID", "")
    client_secret = os.getenv("STRAVA_CLIENT_SECRET", "")

    with StravaConnector(cred, client_id=client_id, client_secret=client_secret) as connector:
        activities = connector.fetch_activities(since=since, until=now)

    synced = 0
    skipped = 0
    sport_breakdown: dict[str, int] = {}

    for activity in activities:
        if activity.sport_type not in SPORT_MAP:
            skipped += 1
            continue

        model = to_model(activity, athlete_id)
        db.merge(model)  # upsert by primary key (strava_id is unique)

        sport = model.sport_type
        sport_breakdown[sport] = sport_breakdown.get(sport, 0) + 1
        synced += 1

    # Update last_sync_at regardless of activity count
    db.query(ConnectorCredentialModel).filter_by(
        athlete_id=athlete_id, provider="strava"
    ).update({"last_sync_at": now})
    db.commit()

    return SyncSummary(synced=synced, skipped=skipped, sport_breakdown=sport_breakdown)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/integrations/strava/test_sync_service.py -v
```

Expected: All 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/integrations/strava/sync_service.py tests/backend/integrations/strava/test_sync_service.py
git commit -m "feat(strava): sync_service — incremental fetch + upsert strava_activities"
```

---

## Task 7: Routes + `main.py` Registration

**Files:**
- Create: `backend/app/routes/strava.py`
- Modify: `backend/app/main.py`
- Create: `tests/backend/api/test_strava.py`

- [ ] **Step 1: Write failing API tests**

Create `tests/backend/api/test_strava.py`:

```python
# tests/backend/api/test_strava.py
import json
import time
import uuid
from unittest.mock import patch

import httpx
import pytest
import respx
from cryptography.fernet import Fernet

from app.db.models import ConnectorCredentialModel
from app.integrations.strava.oauth_service import encrypt_token

TEST_KEY = Fernet.generate_key().decode()
STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"
STRAVA_ACTIVITIES_URL = "https://www.strava.com/api/v3/athlete/activities"


@pytest.fixture(autouse=True)
def strava_env(monkeypatch):
    monkeypatch.setenv("STRAVA_CLIENT_ID", "test_id")
    monkeypatch.setenv("STRAVA_CLIENT_SECRET", "test_secret")
    monkeypatch.setenv("STRAVA_REDIRECT_URI", "http://localhost/callback")
    monkeypatch.setenv("STRAVA_ENCRYPTION_KEY", TEST_KEY)


def _create_athlete(api_client):
    resp = api_client.post("/athletes", json={
        "name": "Alice", "age": 30, "sex": "F",
        "weight_kg": 60.0, "height_cm": 168.0,
        "sports": ["running"], "primary_sport": "running",
        "goals": ["run fast"], "available_days": [0, 2, 4],
        "hours_per_week": 10.0,
    })
    assert resp.status_code == 201
    return resp.json()["id"]


# ── POST /integrations/strava/connect ────────────────────────────────────────

def test_connect_returns_auth_url(api_client, auth_state):
    resp = api_client.post(
        "/integrations/strava/connect",
        headers=auth_state["headers"],
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "auth_url" in data
    assert "strava.com" in data["auth_url"]
    assert "state=" in data["auth_url"]


def test_connect_unauthenticated_returns_401(api_client):
    resp = api_client.post("/integrations/strava/connect")
    assert resp.status_code == 401


# ── GET /integrations/strava/callback ────────────────────────────────────────

@respx.mock
def test_callback_valid_state_returns_connected(api_client, auth_state):
    # First connect to generate state
    connect_resp = api_client.post(
        "/integrations/strava/connect",
        headers=auth_state["headers"],
    )
    auth_url = connect_resp.json()["auth_url"]
    state = dict(p.split("=", 1) for p in auth_url.split("?", 1)[1].split("&"))["state"]

    respx.post(STRAVA_TOKEN_URL).mock(
        return_value=httpx.Response(200, json={
            "access_token": "acc", "refresh_token": "ref", "expires_at": 9999999999,
        })
    )
    resp = api_client.get(f"/integrations/strava/callback?code=abc&state={state}")
    assert resp.status_code == 200
    assert resp.json()["connected"] is True


def test_callback_invalid_state_returns_400(api_client):
    resp = api_client.get("/integrations/strava/callback?code=abc&state=bad_state")
    assert resp.status_code == 400


# ── POST /integrations/strava/sync ───────────────────────────────────────────

def test_sync_returns_summary(api_client, auth_state):
    with patch("app.routes.strava.strava_sync") as mock_sync:
        from app.schemas.strava import SyncSummary
        mock_sync.return_value = SyncSummary(
            synced=3, skipped=0, sport_breakdown={"running": 2, "biking": 1}
        )
        resp = api_client.post(
            "/integrations/strava/sync",
            headers=auth_state["headers"],
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["synced"] == 3
    assert body["skipped"] == 0
    assert body["sport_breakdown"]["running"] == 2


def test_sync_unauthenticated_returns_401(api_client):
    resp = api_client.post("/integrations/strava/sync")
    assert resp.status_code == 401


@respx.mock
def test_sync_not_connected_returns_404(api_client, auth_state):
    with patch("app.routes.strava.strava_sync") as mock_sync:
        mock_sync.side_effect = ValueError("Strava not connected")
        resp = api_client.post(
            "/integrations/strava/sync",
            headers=auth_state["headers"],
        )
    assert resp.status_code == 404
```

- [ ] **Step 2: Run to verify tests fail**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/api/test_strava.py -v
```

Expected: FAIL — routes not registered yet

- [ ] **Step 3: Create `backend/app/routes/strava.py`**

```python
# backend/app/routes/strava.py
"""Strava OAuth 2.0 + activity sync routes."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from ..core.security import get_current_athlete_id
from ..db.database import get_db
from ..integrations.strava.oauth_service import callback as oauth_callback
from ..integrations.strava.oauth_service import connect as oauth_connect
from ..integrations.strava.sync_service import sync as strava_sync
from ..schemas.strava import SyncSummary
from sqlalchemy.orm import Session

DB = Annotated[Session, Depends(get_db)]

router = APIRouter(prefix="/integrations/strava", tags=["strava"])


@router.post("/connect")
def connect(
    athlete_id: Annotated[str, Depends(get_current_athlete_id)],
    db: DB,
) -> dict:
    """Generate Strava OAuth authorization URL."""
    from ..db.models import AthleteModel
    if db.get(AthleteModel, athlete_id) is None:
        raise HTTPException(status_code=404, detail="Athlete not found")
    return oauth_connect(athlete_id, db)


@router.get("/callback")
def callback(
    code: str,
    state: str,
    db: DB,
) -> dict:
    """Handle Strava OAuth callback — exchange code for encrypted tokens."""
    import httpx as _httpx
    try:
        return oauth_callback(code=code, state=state, db=db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except _httpx.HTTPStatusError:
        raise HTTPException(status_code=502, detail="Strava token exchange failed")


@router.post("/sync", response_model=SyncSummary)
def sync(
    athlete_id: Annotated[str, Depends(get_current_athlete_id)],
    db: DB,
) -> SyncSummary:
    """Sync Strava activities incrementally since last sync."""
    from ..connectors.base import ConnectorRateLimitError
    try:
        return strava_sync(athlete_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ConnectorRateLimitError as e:
        raise HTTPException(
            status_code=429,
            headers={"Retry-After": str(e.retry_after)},
            detail="Strava rate limit reached",
        )
```

- [ ] **Step 4: Register router in `backend/app/main.py`**

Add import at the top with the other route imports:
```python
from .routes.strava import router as strava_router
```

Add include call after the existing `app.include_router(integrations_router)` line:
```python
app.include_router(strava_router)
```

- [ ] **Step 5: Run API tests**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/api/test_strava.py -v
```

Expected: All 6 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/routes/strava.py backend/app/main.py tests/backend/api/test_strava.py
git commit -m "feat(strava): routes — /integrations/strava/connect|callback|sync"
```

---

## Task 8: Remove Old Strava Code + Update Affected Tests

**Files:**
- Modify: `backend/app/routes/connectors.py`
- Modify: `backend/app/services/sync_service.py`
- Modify: `tests/backend/api/test_connectors.py`
- Modify: `tests/backend/api/test_connectors_sync.py`
- Modify: `tests/backend/api/test_connectors_phase9.py`
- Modify: `tests/backend/services/test_sync_service.py`

- [ ] **Step 1: Remove Strava routes from `backend/app/routes/connectors.py`**

Delete the entire `# ── Strava OAuth2 ────` section (the two functions `strava_authorize` and `strava_callback`), the `# ── Strava Sync ───` section (the `strava_sync` function), and the strava entry in the `sync_all` loop.

The section to delete (lines ~202–251):
```python
# ── Strava OAuth2 ────────────────────────────────────────────────────────────


@router.post("/{athlete_id}/connectors/strava/authorize")
def strava_authorize(athlete_id: str, db: DB) -> dict:
    ...

@router.get("/{athlete_id}/connectors/strava/callback")
def strava_callback(athlete_id: str, code: str, db: DB) -> dict:
    ...
```

The section to delete (lines ~398–411):
```python
# ── Strava Sync ───────────────────────────────────────────────────────────────


@router.post("/{athlete_id}/connectors/strava/sync")
def strava_sync(...) -> dict:
    ...
```

In `sync_all`, remove the strava line from the loop:
```python
# Remove this line:
("strava", SyncService.sync_strava),
```

Also remove any now-unused import of `StravaConnector` if it was only used by the deleted functions. Check imports at the top — if `StravaConnector` is no longer referenced, remove it. Read the file top to verify.

- [ ] **Step 2: Remove `sync_strava` from `backend/app/services/sync_service.py`**

Delete the `SyncService.sync_strava` static method (lines ~92–177). The class and its other methods (`sync_hevy`, `sync_terra`) stay.

Also verify `StravaConnector` import at the top is still needed (for `sync_hevy` / `sync_terra`). If only used in `sync_strava`, remove it.

- [ ] **Step 3: Remove strava tests from `tests/backend/api/test_connectors.py`**

Delete these 6 test functions and the `strava_env` autouse fixture:
- `strava_env` fixture (autouse, lines ~13–18)
- `test_strava_authorize_returns_auth_url`
- `test_strava_authorize_unknown_athlete_returns_404`
- `test_strava_callback_strava_error_returns_502`
- `test_strava_callback_unknown_athlete_returns_404`
- `test_strava_callback_stores_credential`
- `test_strava_callback_upsert_updates_existing`

Also remove `import httpx` and `import respx` if no longer used after removal.

- [ ] **Step 4: Remove strava tests from `tests/backend/api/test_connectors_sync.py`**

Delete these 2 test functions:
- `test_strava_sync_no_credential_returns_404`
- `test_strava_sync_wrong_athlete_returns_403`

- [ ] **Step 5: Remove strava test from `tests/backend/api/test_connectors_phase9.py`**

Delete `test_strava_sync_delegates_to_sync_service` function.

- [ ] **Step 6: Remove strava tests from `tests/backend/services/test_sync_service.py`**

Delete these 5 test functions and the `# ── sync_strava ──` comment block:
- `test_sync_strava_raises_if_not_connected`
- `test_sync_strava_maps_activity_to_session_log`
- `test_sync_strava_updates_last_sync`
- `test_sync_strava_persists_refreshed_token`
- `test_sync_strava_returns_zero_when_no_plan`

- [ ] **Step 7: Run full test suite to verify no regressions**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/ -x -q
```

Expected: All tests PASS. Count should be higher than before (new tests) with no failures.

- [ ] **Step 8: Commit**

```bash
git add backend/app/routes/connectors.py backend/app/services/sync_service.py
git add tests/backend/api/test_connectors.py tests/backend/api/test_connectors_sync.py
git add tests/backend/api/test_connectors_phase9.py tests/backend/services/test_sync_service.py
git commit -m "refactor(strava): remove old OAuth routes + plaintext sync; clean test files"
```

---

## Task 9: `.env.example` Update

**Files:**
- Modify: `.env.example`

- [ ] **Step 1: Add `STRAVA_ENCRYPTION_KEY` to `.env.example`**

Find the existing `STRAVA_CLIENT_ID` block in `.env.example` and add the encryption key entry:

```bash
STRAVA_CLIENT_ID=your_client_id
STRAVA_CLIENT_SECRET=your_client_secret
STRAVA_REDIRECT_URI=http://localhost:8000/integrations/strava/callback
STRAVA_ENCRYPTION_KEY=your_fernet_key  # Generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

- [ ] **Step 2: Run full test suite one final time**

```bash
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/ -q
```

Expected: All tests pass. No failures.

- [ ] **Step 3: Commit**

```bash
git add .env.example
git commit -m "docs(strava): add STRAVA_ENCRYPTION_KEY to .env.example"
```
