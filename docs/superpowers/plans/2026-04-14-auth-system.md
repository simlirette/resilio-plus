# Auth System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the existing partial auth system with refresh token rotation, `/auth/refresh`, `/auth/logout`, `/auth/me`, and password reset via SMTP email.

**Architecture:** Access tokens (JWT, 15 min) remain stateless. Refresh tokens (30 days) are stored as SHA-256 hashes in a new `refresh_tokens` table with strict rotation on every `/auth/refresh` call. Password reset tokens (1 hour) follow the same hash-only storage pattern. All DB token operations stay in route handlers following existing codebase conventions — `security.py` remains pure crypto functions.

**Tech Stack:** FastAPI, SQLAlchemy, passlib/bcrypt (existing), Python `secrets` + `hashlib` (stdlib), `smtplib` STARTTLS (stdlib), Alembic, pytest + SQLite in-memory.

**Pytest path (Windows):** `C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe` — use `pytest` if on PATH, otherwise use the full path.

**Run all tests:** `pytest tests/ -x -q` from repo root.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `backend/app/core/security.py` | Modify | Add `generate_token`, `hash_token`, `verify_token`; lower access TTL to 15 min |
| `backend/app/core/email.py` | **Create** | `send_reset_email()` via smtplib STARTTLS |
| `backend/app/db/models.py` | Modify | Add `is_active`/`last_login_at` to `UserModel`; add `RefreshTokenModel`, `PasswordResetTokenModel` |
| `alembic/versions/0006_auth_refresh_reset_tokens.py` | **Create** | DB migration for new columns + tables |
| `backend/app/schemas/auth.py` | Modify | Add `RefreshRequest`, `LogoutRequest`, `MeResponse`, `ForgotPasswordRequest`, `ResetPasswordRequest`; update `TokenResponse` + `OnboardingResponse` with `refresh_token` |
| `backend/app/routes/auth.py` | Modify | Add `/refresh`, `/logout`, `/me`, `/forgot-password`, `/reset-password`; update `/login` to issue refresh token |
| `backend/app/routes/onboarding.py` | Modify | Issue refresh token in onboarding response |
| `.env.example` | Modify | Add `JWT_SECRET`, `JWT_ACCESS_TTL_MINUTES`, `JWT_REFRESH_TTL_DAYS`, `SMTP_*`, `APP_BASE_URL` |
| `docs/backend/AUTH.md` | **Create** | Flow, endpoints, curl/TypeScript examples |
| `tests/backend/core/test_security.py` | Modify | Add tests for new token primitives |
| `tests/backend/core/test_email.py` | **Create** | Test `send_reset_email` with mocked SMTP |
| `tests/backend/api/test_auth.py` | Modify | Add tests for all new endpoints |

---

## Task 1: Security token primitives

**Files:**
- Modify: `backend/app/core/security.py`
- Modify: `tests/backend/core/test_security.py`

- [ ] **Step 1.1: Write failing tests for new primitives**

Append to `tests/backend/core/test_security.py`:

```python
import secrets as _secrets
from app.core.security import generate_token, hash_token, verify_token


def test_generate_token_is_urlsafe_string():
    token = generate_token()
    assert isinstance(token, str)
    assert len(token) >= 40  # base64url of 32 bytes = 43 chars


def test_generate_token_is_unique():
    assert generate_token() != generate_token()


def test_hash_token_is_deterministic():
    raw = generate_token()
    assert hash_token(raw) == hash_token(raw)


def test_hash_token_differs_from_raw():
    raw = generate_token()
    assert hash_token(raw) != raw


def test_verify_token_correct():
    raw = generate_token()
    hashed = hash_token(raw)
    assert verify_token(raw, hashed) is True


def test_verify_token_wrong():
    raw = generate_token()
    hashed = hash_token(raw)
    assert verify_token("wrong-token", hashed) is False
```

- [ ] **Step 1.2: Run tests to confirm failure**

```
pytest tests/backend/core/test_security.py::test_generate_token_is_urlsafe_string -v
```

Expected: `ImportError: cannot import name 'generate_token'`

- [ ] **Step 1.3: Implement token primitives in security.py**

Add to `backend/app/core/security.py` (after existing imports):

```python
import hashlib
import hmac
import secrets
```

Change `_EXPIRE_HOURS = 24` to read from env:

```python
_ACCESS_TTL_MINUTES = int(os.getenv("JWT_ACCESS_TTL_MINUTES", "15"))
_REFRESH_TTL_DAYS = int(os.getenv("JWT_REFRESH_TTL_DAYS", "30"))
```

Update `create_access_token` to use minutes:

```python
def create_access_token(athlete_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=_ACCESS_TTL_MINUTES)
    payload = {"sub": athlete_id, "exp": expire}
    return jwt.encode(payload, _SECRET, algorithm=_ALGORITHM)
```

Add new functions:

```python
def generate_token() -> str:
    """Generate a cryptographically secure URL-safe token (32 bytes)."""
    return secrets.token_urlsafe(32)


def hash_token(raw: str) -> str:
    """Hash a raw token with SHA-256 for DB storage. Deterministic — suitable for lookup."""
    return hashlib.sha256(raw.encode()).hexdigest()


def verify_token(raw: str, hashed: str) -> bool:
    """Constant-time comparison of raw token against stored hash."""
    return hmac.compare_digest(hashlib.sha256(raw.encode()).hexdigest(), hashed)
```

- [ ] **Step 1.4: Run all new tests**

```
pytest tests/backend/core/test_security.py -v
```

Expected: all pass (existing + new).

- [ ] **Step 1.5: Commit**

```bash
git add backend/app/core/security.py tests/backend/core/test_security.py
git commit -m "feat(auth): add token primitives — generate_token, hash_token, verify_token; access TTL from env"
```

---

## Task 2: Email module

**Files:**
- Create: `backend/app/core/email.py`
- Create: `tests/backend/core/test_email.py`

- [ ] **Step 2.1: Write failing test**

Create `tests/backend/core/test_email.py`:

```python
from unittest.mock import MagicMock, patch

from app.core.email import send_reset_email


def test_send_reset_email_connects_and_sends(monkeypatch):
    """Verify SMTP STARTTLS flow: connect → starttls → login → send_message."""
    mock_smtp_instance = MagicMock()
    mock_smtp_class = MagicMock(return_value=mock_smtp_instance)
    mock_smtp_instance.__enter__ = MagicMock(return_value=mock_smtp_instance)
    mock_smtp_instance.__exit__ = MagicMock(return_value=False)

    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USER", "bot@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")
    monkeypatch.setenv("SMTP_FROM", "noreply@example.com")

    with patch("smtplib.SMTP", mock_smtp_class):
        send_reset_email("athlete@test.com", "https://app.example.com/reset?token=abc123")

    mock_smtp_class.assert_called_once_with("smtp.example.com", 587)
    mock_smtp_instance.starttls.assert_called_once()
    mock_smtp_instance.login.assert_called_once_with("bot@example.com", "secret")
    mock_smtp_instance.send_message.assert_called_once()
    # Verify recipient in the message
    sent_msg = mock_smtp_instance.send_message.call_args[0][0]
    assert sent_msg["To"] == "athlete@test.com"
    assert "https://app.example.com/reset?token=abc123" in sent_msg.get_payload()
```

- [ ] **Step 2.2: Run test to confirm failure**

```
pytest tests/backend/core/test_email.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.core.email'`

- [ ] **Step 2.3: Create backend/app/core/email.py**

```python
from __future__ import annotations

import os
import smtplib
from email.mime.text import MIMEText


def send_reset_email(to_email: str, reset_url: str) -> None:
    """Send a password reset email via SMTP STARTTLS.

    Reads SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM from env.
    """
    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER", "")
    password = os.getenv("SMTP_PASSWORD", "")
    from_addr = os.getenv("SMTP_FROM", user)

    body = (
        f"You requested a password reset for your Resilio+ account.\n\n"
        f"Click the link below to set a new password (valid for 1 hour):\n\n"
        f"{reset_url}\n\n"
        f"If you did not request this, ignore this email."
    )
    msg = MIMEText(body)
    msg["Subject"] = "Reset your Resilio+ password"
    msg["From"] = from_addr
    msg["To"] = to_email

    with smtplib.SMTP(host, port) as smtp:
        smtp.starttls()
        smtp.login(user, password)
        smtp.send_message(msg)
```

- [ ] **Step 2.4: Run test to confirm pass**

```
pytest tests/backend/core/test_email.py -v
```

Expected: PASS.

- [ ] **Step 2.5: Commit**

```bash
git add backend/app/core/email.py tests/backend/core/test_email.py
git commit -m "feat(auth): add email module — send_reset_email via SMTP STARTTLS"
```

---

## Task 3: DB models

**Files:**
- Modify: `backend/app/db/models.py`

No new test file needed — `Base.metadata.create_all()` in conftest covers schema correctness; model shape is tested indirectly via API tests.

- [ ] **Step 3.1: Add columns to UserModel**

In `backend/app/db/models.py`, update `UserModel`:

```python
class UserModel(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    athlete_id = Column(String, ForeignKey("athletes.id"), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)           # NEW
    last_login_at = Column(DateTime(timezone=True), nullable=True)      # NEW
    created_at = Column(DateTime(timezone=True), nullable=False,
                        default=lambda: datetime.now(timezone.utc))

    athlete = relationship("AthleteModel", back_populates="user")
    refresh_tokens = relationship("RefreshTokenModel", back_populates="user",  # NEW
                                  cascade="all, delete-orphan")
    reset_tokens = relationship("PasswordResetTokenModel", back_populates="user",  # NEW
                                cascade="all, delete-orphan")
```

- [ ] **Step 3.2: Add RefreshTokenModel**

Add after `UserModel` in `backend/app/db/models.py`:

```python
class RefreshTokenModel(Base):
    __tablename__ = "refresh_tokens"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String, unique=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False,
                        default=lambda: datetime.now(timezone.utc))
    revoked = Column(Boolean, nullable=False, default=False)

    user = relationship("UserModel", back_populates="refresh_tokens")
```

- [ ] **Step 3.3: Add PasswordResetTokenModel**

Add after `RefreshTokenModel` in `backend/app/db/models.py`:

```python
class PasswordResetTokenModel(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String, unique=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, nullable=False, default=False)

    user = relationship("UserModel", back_populates="reset_tokens")
```

- [ ] **Step 3.4: Run existing tests to confirm no regression**

```
pytest tests/backend/db/ tests/backend/api/test_auth.py -v
```

Expected: all existing tests pass (SQLite in-memory picks up new models automatically via `Base.metadata.create_all()`).

- [ ] **Step 3.5: Commit**

```bash
git add backend/app/db/models.py
git commit -m "feat(auth): add RefreshTokenModel, PasswordResetTokenModel; extend UserModel"
```

---

## Task 4: Alembic migration

**Files:**
- Create: `alembic/versions/0006_auth_refresh_reset_tokens.py`

- [ ] **Step 4.1: Create migration file**

Create `alembic/versions/0006_auth_refresh_reset_tokens.py`:

```python
"""Add refresh_tokens, password_reset_tokens tables and auth columns on users

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-14 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add columns to users
    op.add_column("users", sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"))
    op.add_column("users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))

    # Create refresh_tokens table
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default="0"),
    )

    # Create password_reset_tokens table
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used", sa.Boolean(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("password_reset_tokens")
    op.drop_table("refresh_tokens")
    op.drop_column("users", "last_login_at")
    op.drop_column("users", "is_active")
```

- [ ] **Step 4.2: Apply migration (requires running PostgreSQL)**

From repo root:

```bash
cd backend && alembic upgrade head
```

Expected output ends with: `Running upgrade 0005 -> 0006, Add refresh_tokens...`

> If PostgreSQL is not running locally, skip this step — tests use SQLite in-memory and don't need Alembic. Apply before next production deploy.

- [ ] **Step 4.3: Commit**

```bash
git add alembic/versions/0006_auth_refresh_reset_tokens.py
git commit -m "feat(auth): migration 0006 — refresh_tokens, password_reset_tokens, user auth columns"
```

---

## Task 5: Auth schemas

**Files:**
- Modify: `backend/app/schemas/auth.py`

- [ ] **Step 5.1: Update schemas**

Replace the full content of `backend/app/schemas/auth.py`:

```python
from datetime import date, datetime

from pydantic import BaseModel, Field

from .athlete import AthleteCreate, AthleteResponse
from .plan import TrainingPlanResponse


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    athlete_id: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class MeResponse(BaseModel):
    athlete_id: str
    email: str
    created_at: datetime
    is_active: bool


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)


class OnboardingRequest(AthleteCreate):
    email: str
    password: str = Field(..., min_length=8)
    plan_start_date: date


class OnboardingResponse(BaseModel):
    athlete: AthleteResponse
    plan: TrainingPlanResponse
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
```

- [ ] **Step 5.2: Run existing auth tests to check nothing breaks**

```
pytest tests/backend/api/test_auth.py tests/backend/api/test_onboarding.py -v
```

Expected: existing tests still pass (schemas are validated at response time — existing routes don't emit `refresh_token` yet, so they'll fail response validation on `/auth/login`). 

> **Note:** Tests for login will fail at this step because `TokenResponse` now requires `refresh_token` but the route doesn't emit it yet. This is expected — we fix it in Task 6. Move on.

- [ ] **Step 5.3: Commit**

```bash
git add backend/app/schemas/auth.py
git commit -m "feat(auth): extend auth schemas — TokenResponse + OnboardingResponse with refresh_token"
```

---

## Task 6: Update login and onboarding to issue refresh tokens

**Files:**
- Modify: `backend/app/routes/auth.py`
- Modify: `backend/app/routes/onboarding.py`
- Modify: `tests/backend/api/test_auth.py`

- [ ] **Step 6.1: Write failing test for login returning refresh token**

Add to `tests/backend/api/test_auth.py`:

```python
def test_login_returns_refresh_token(client_and_db):
    client, db = client_and_db
    _seed_user(db)

    resp = client.post("/auth/login", json={"email": "alice@test.com", "password": "password123"})
    assert resp.status_code == 200
    body = resp.json()
    assert "refresh_token" in body
    assert len(body["refresh_token"]) > 20
```

- [ ] **Step 6.2: Run test to confirm failure**

```
pytest tests/backend/api/test_auth.py::test_login_returns_refresh_token -v
```

Expected: FAIL — `refresh_token` not in response body.

- [ ] **Step 6.3: Update routes/auth.py login endpoint**

Replace full content of `backend/app/routes/auth.py`:

```python
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..core.security import (
    create_access_token,
    generate_token,
    hash_token,
    verify_password,
    verify_token,
)
from ..core.email import send_reset_email
from ..core.security import hash_password
from ..db.models import PasswordResetTokenModel, RefreshTokenModel, UserModel
from ..dependencies import get_db, get_current_athlete_id
from ..schemas.auth import (
    ForgotPasswordRequest,
    LogoutRequest,
    MeResponse,
    RefreshRequest,
    ResetPasswordRequest,
    TokenResponse,
)
import os

router = APIRouter(prefix="/auth", tags=["auth"])

DB = Annotated[Session, Depends(get_db)]
AuthedId = Annotated[str, Depends(get_current_athlete_id)]

_REFRESH_TTL_DAYS = int(os.getenv("JWT_REFRESH_TTL_DAYS", "30"))


def _issue_refresh_token(user_id: str, db: Session) -> str:
    """Generate a refresh token, store its hash, return the raw token."""
    raw = generate_token()
    record = RefreshTokenModel(
        id=str(uuid.uuid4()),
        user_id=user_id,
        token_hash=hash_token(raw),
        expires_at=datetime.now(timezone.utc) + timedelta(days=_REFRESH_TTL_DAYS),
        created_at=datetime.now(timezone.utc),
    )
    db.add(record)
    return raw


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: DB) -> TokenResponse:
    from ..schemas.auth import LoginRequest  # local to avoid circular at module level
    user = db.query(UserModel).filter(UserModel.email == req.email).first()
    if user is None or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    user.last_login_at = datetime.now(timezone.utc)
    refresh = _issue_refresh_token(user.id, db)
    db.commit()

    return TokenResponse(
        access_token=create_access_token(athlete_id=user.athlete_id),
        refresh_token=refresh,
        athlete_id=user.athlete_id,
    )
```

> **Note:** The `LoginRequest` import moved to a local import to avoid a circular import issue — fix by adding it at the top. See step below.

Actually, replace `routes/auth.py` with this clean version:

```python
from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..core.email import send_reset_email
from ..core.security import (
    create_access_token,
    generate_token,
    hash_password,
    hash_token,
    verify_password,
    verify_token,
)
from ..db.models import PasswordResetTokenModel, RefreshTokenModel, UserModel
from ..dependencies import get_current_athlete_id, get_db
from ..schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    MeResponse,
    RefreshRequest,
    ResetPasswordRequest,
    TokenResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])

DB = Annotated[Session, Depends(get_db)]
AuthedId = Annotated[str, Depends(get_current_athlete_id)]

_REFRESH_TTL_DAYS = int(os.getenv("JWT_REFRESH_TTL_DAYS", "30"))


def _issue_refresh_token(user_id: str, db: Session) -> str:
    """Generate a refresh token, store its hash in DB, return raw token."""
    raw = generate_token()
    db.add(RefreshTokenModel(
        id=str(uuid.uuid4()),
        user_id=user_id,
        token_hash=hash_token(raw),
        expires_at=datetime.now(timezone.utc) + timedelta(days=_REFRESH_TTL_DAYS),
        created_at=datetime.now(timezone.utc),
    ))
    return raw


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: DB) -> TokenResponse:
    user = db.query(UserModel).filter(UserModel.email == req.email).first()
    if user is None or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    user.last_login_at = datetime.now(timezone.utc)
    refresh = _issue_refresh_token(user.id, db)
    db.commit()

    return TokenResponse(
        access_token=create_access_token(athlete_id=user.athlete_id),
        refresh_token=refresh,
        athlete_id=user.athlete_id,
    )
```

- [ ] **Step 6.4: Update onboarding to return refresh token**

In `backend/app/routes/onboarding.py`, update the return statement of `onboard_athlete`:

Change the final block from:
```python
    token = create_access_token(athlete_id=athlete_id)
    return OnboardingResponse(
        athlete=athlete,
        plan=TrainingPlanResponse.from_model(plan_model),
        access_token=token,
    )
```

To:
```python
    from ..routes.auth import _issue_refresh_token  # avoid circular at module top
    access_token = create_access_token(athlete_id=athlete_id)
    refresh_token = _issue_refresh_token(user.id, db)
    db.commit()
    return OnboardingResponse(
        athlete=athlete,
        plan=TrainingPlanResponse.from_model(plan_model),
        access_token=access_token,
        refresh_token=refresh_token,
    )
```

- [ ] **Step 6.5: Run login tests**

```
pytest tests/backend/api/test_auth.py -v
```

Expected: `test_login_returns_refresh_token` PASS. Existing login tests still pass.

- [ ] **Step 6.6: Run onboarding tests**

```
pytest tests/backend/api/test_onboarding.py -v
```

Expected: all pass.

- [ ] **Step 6.7: Commit**

```bash
git add backend/app/routes/auth.py backend/app/routes/onboarding.py tests/backend/api/test_auth.py
git commit -m "feat(auth): login and onboarding now issue refresh tokens"
```

---

## Task 7: /auth/refresh endpoint

**Files:**
- Modify: `backend/app/routes/auth.py`
- Modify: `tests/backend/api/test_auth.py`

- [ ] **Step 7.1: Write failing tests**

Add to `tests/backend/api/test_auth.py`:

```python
def test_refresh_returns_new_tokens(client_and_db):
    client, db = client_and_db
    _seed_user(db)

    # Login to get initial tokens
    resp = client.post("/auth/login", json={"email": "alice@test.com", "password": "password123"})
    original_refresh = resp.json()["refresh_token"]
    original_access = resp.json()["access_token"]

    # Refresh
    resp2 = client.post("/auth/refresh", json={"refresh_token": original_refresh})
    assert resp2.status_code == 200
    body = resp2.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["refresh_token"] != original_refresh  # rotated
    assert body["access_token"] != original_access    # new token


def test_refresh_old_token_is_invalidated(client_and_db):
    client, db = client_and_db
    _seed_user(db)

    resp = client.post("/auth/login", json={"email": "alice@test.com", "password": "password123"})
    original_refresh = resp.json()["refresh_token"]

    # Use refresh token once
    client.post("/auth/refresh", json={"refresh_token": original_refresh})

    # Try to use old refresh token again — must fail
    resp3 = client.post("/auth/refresh", json={"refresh_token": original_refresh})
    assert resp3.status_code == 401


def test_refresh_invalid_token_returns_401(client):
    resp = client.post("/auth/refresh", json={"refresh_token": "not-a-real-token"})
    assert resp.status_code == 401
```

- [ ] **Step 7.2: Run tests to confirm failure**

```
pytest tests/backend/api/test_auth.py::test_refresh_returns_new_tokens -v
```

Expected: FAIL — `404 Not Found` (endpoint doesn't exist yet).

- [ ] **Step 7.3: Add /auth/refresh to routes/auth.py**

Append to `backend/app/routes/auth.py`:

```python
@router.post("/refresh", response_model=TokenResponse)
def refresh(req: RefreshRequest, db: DB) -> TokenResponse:
    token_hash = hash_token(req.refresh_token)
    record = db.query(RefreshTokenModel).filter(
        RefreshTokenModel.token_hash == token_hash,
        RefreshTokenModel.revoked.is_(False),
        RefreshTokenModel.expires_at > datetime.now(timezone.utc),
    ).first()

    if record is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid or expired refresh token")

    user = db.query(UserModel).filter(UserModel.id == record.user_id).first()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    # Rotate: revoke old, issue new
    record.revoked = True
    new_refresh = _issue_refresh_token(user.id, db)
    db.commit()

    return TokenResponse(
        access_token=create_access_token(athlete_id=user.athlete_id),
        refresh_token=new_refresh,
        athlete_id=user.athlete_id,
    )
```

- [ ] **Step 7.4: Run refresh tests**

```
pytest tests/backend/api/test_auth.py -k "refresh" -v
```

Expected: all 3 refresh tests PASS.

- [ ] **Step 7.5: Commit**

```bash
git add backend/app/routes/auth.py tests/backend/api/test_auth.py
git commit -m "feat(auth): add /auth/refresh with strict token rotation"
```

---

## Task 8: /auth/logout and /auth/me

**Files:**
- Modify: `backend/app/routes/auth.py`
- Modify: `tests/backend/api/test_auth.py`

- [ ] **Step 8.1: Write failing tests**

Add to `tests/backend/api/test_auth.py`:

```python
def test_logout_revokes_refresh_token(client_and_db):
    client, db = client_and_db
    _seed_user(db)

    resp = client.post("/auth/login", json={"email": "alice@test.com", "password": "password123"})
    body = resp.json()
    access_token = body["access_token"]
    refresh_token = body["refresh_token"]

    # Logout
    resp2 = client.post(
        "/auth/logout",
        json={"refresh_token": refresh_token},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert resp2.status_code == 200

    # Refresh token should now be invalid
    resp3 = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert resp3.status_code == 401


def test_me_returns_current_user(client_and_db):
    client, db = client_and_db
    athlete_id = _seed_user(db, email="alice@test.com")

    resp = client.post("/auth/login", json={"email": "alice@test.com", "password": "password123"})
    token = resp.json()["access_token"]

    resp2 = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp2.status_code == 200
    body = resp2.json()
    assert body["email"] == "alice@test.com"
    assert body["athlete_id"] == athlete_id
    assert body["is_active"] is True


def test_me_without_token_returns_401(client):
    resp = client.get("/auth/me")
    assert resp.status_code == 401
```

- [ ] **Step 8.2: Run tests to confirm failure**

```
pytest tests/backend/api/test_auth.py::test_logout_revokes_refresh_token tests/backend/api/test_auth.py::test_me_returns_current_user -v
```

Expected: FAIL — `404 Not Found`.

- [ ] **Step 8.3: Add /auth/logout and /auth/me to routes/auth.py**

Append to `backend/app/routes/auth.py`:

```python
@router.post("/logout")
def logout(req: LogoutRequest, current_id: AuthedId, db: DB) -> dict:
    token_hash = hash_token(req.refresh_token)
    record = db.query(RefreshTokenModel).filter(
        RefreshTokenModel.token_hash == token_hash,
        RefreshTokenModel.revoked.is_(False),
    ).first()
    if record is not None:
        record.revoked = True
        db.commit()
    return {"message": "Logged out"}


@router.get("/me", response_model=MeResponse)
def me(current_id: AuthedId, db: DB) -> MeResponse:
    user = db.query(UserModel).filter(UserModel.athlete_id == current_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return MeResponse(
        athlete_id=user.athlete_id,
        email=user.email,
        created_at=user.created_at,
        is_active=user.is_active,
    )
```

- [ ] **Step 8.4: Run logout and me tests**

```
pytest tests/backend/api/test_auth.py -k "logout or me" -v
```

Expected: all PASS.

- [ ] **Step 8.5: Commit**

```bash
git add backend/app/routes/auth.py tests/backend/api/test_auth.py
git commit -m "feat(auth): add /auth/logout (revokes refresh token) and /auth/me"
```

---

## Task 9: /auth/forgot-password and /auth/reset-password

**Files:**
- Modify: `backend/app/routes/auth.py`
- Modify: `tests/backend/api/test_auth.py`

- [ ] **Step 9.1: Write failing tests**

Add to `tests/backend/api/test_auth.py`:

```python
from unittest.mock import patch as _patch


def test_forgot_password_always_returns_200(client_and_db):
    client, db = client_and_db
    _seed_user(db)

    with _patch("app.routes.auth.send_reset_email") as mock_send:
        # Known email
        resp = client.post("/auth/forgot-password", json={"email": "alice@test.com"})
        assert resp.status_code == 200
        mock_send.assert_called_once()

        # Unknown email — still 200, no email sent
        resp2 = client.post("/auth/forgot-password", json={"email": "nobody@test.com"})
        assert resp2.status_code == 200
        assert mock_send.call_count == 1  # not called again


def test_reset_password_updates_password(client_and_db):
    client, db = client_and_db
    _seed_user(db)

    captured_url = {}

    def capture_email(to_email, reset_url):
        captured_url["url"] = reset_url

    with _patch("app.routes.auth.send_reset_email", side_effect=capture_email):
        client.post("/auth/forgot-password", json={"email": "alice@test.com"})

    # Extract token from URL
    token = captured_url["url"].split("token=")[1]

    resp = client.post("/auth/reset-password", json={"token": token, "new_password": "newpassword99"})
    assert resp.status_code == 200

    # Login with new password succeeds
    resp2 = client.post("/auth/login", json={"email": "alice@test.com", "password": "newpassword99"})
    assert resp2.status_code == 200

    # Login with old password fails
    resp3 = client.post("/auth/login", json={"email": "alice@test.com", "password": "password123"})
    assert resp3.status_code == 401


def test_reset_password_token_is_single_use(client_and_db):
    client, db = client_and_db
    _seed_user(db)

    captured_url = {}

    def capture_email(to_email, reset_url):
        captured_url["url"] = reset_url

    with _patch("app.routes.auth.send_reset_email", side_effect=capture_email):
        client.post("/auth/forgot-password", json={"email": "alice@test.com"})

    token = captured_url["url"].split("token=")[1]

    client.post("/auth/reset-password", json={"token": token, "new_password": "newpassword99"})

    # Second use of same token must fail
    resp = client.post("/auth/reset-password", json={"token": token, "new_password": "anotherpass1"})
    assert resp.status_code == 400


def test_reset_password_revokes_refresh_tokens(client_and_db):
    client, db = client_and_db
    _seed_user(db)

    # Login to get a refresh token
    login_resp = client.post("/auth/login", json={"email": "alice@test.com", "password": "password123"})
    old_refresh = login_resp.json()["refresh_token"]

    captured_url = {}

    def capture_email(to_email, reset_url):
        captured_url["url"] = reset_url

    with _patch("app.routes.auth.send_reset_email", side_effect=capture_email):
        client.post("/auth/forgot-password", json={"email": "alice@test.com"})

    token = captured_url["url"].split("token=")[1]
    client.post("/auth/reset-password", json={"token": token, "new_password": "newpassword99"})

    # Old refresh token must be revoked
    resp = client.post("/auth/refresh", json={"refresh_token": old_refresh})
    assert resp.status_code == 401


def test_reset_password_invalid_token_returns_400(client):
    resp = client.post("/auth/reset-password", json={"token": "fake-token", "new_password": "newpass99"})
    assert resp.status_code == 400
```

- [ ] **Step 9.2: Run tests to confirm failure**

```
pytest tests/backend/api/test_auth.py::test_forgot_password_always_returns_200 -v
```

Expected: FAIL — `404 Not Found`.

- [ ] **Step 9.3: Add /auth/forgot-password and /auth/reset-password to routes/auth.py**

Append to `backend/app/routes/auth.py`:

```python
@router.post("/forgot-password")
def forgot_password(req: ForgotPasswordRequest, db: DB) -> dict:
    user = db.query(UserModel).filter(UserModel.email == req.email).first()
    _msg = {"message": "If this email is registered, a reset link has been sent."}

    if user is None:
        return _msg  # no-op — prevent email enumeration

    # Invalidate any existing unused reset tokens
    db.query(PasswordResetTokenModel).filter(
        PasswordResetTokenModel.user_id == user.id,
        PasswordResetTokenModel.used.is_(False),
    ).update({"used": True})

    raw = generate_token()
    db.add(PasswordResetTokenModel(
        id=str(uuid.uuid4()),
        user_id=user.id,
        token_hash=hash_token(raw),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    ))
    db.commit()

    base_url = os.getenv("APP_BASE_URL", "http://localhost:3000")
    reset_url = f"{base_url}/reset-password?token={raw}"
    send_reset_email(user.email, reset_url)

    return _msg


@router.post("/reset-password")
def reset_password(req: ResetPasswordRequest, db: DB) -> dict:
    token_hash = hash_token(req.token)
    record = db.query(PasswordResetTokenModel).filter(
        PasswordResetTokenModel.token_hash == token_hash,
        PasswordResetTokenModel.used.is_(False),
        PasswordResetTokenModel.expires_at > datetime.now(timezone.utc),
    ).first()

    if record is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid or expired reset token")

    record.used = True
    user = db.query(UserModel).filter(UserModel.id == record.user_id).first()
    user.hashed_password = hash_password(req.new_password)

    # Revoke all active refresh tokens — password changed, all sessions invalidated
    db.query(RefreshTokenModel).filter(
        RefreshTokenModel.user_id == user.id,
        RefreshTokenModel.revoked.is_(False),
    ).update({"revoked": True})

    db.commit()
    return {"message": "Password updated successfully. Please log in again."}
```

- [ ] **Step 9.4: Run all reset tests**

```
pytest tests/backend/api/test_auth.py -k "forgot or reset" -v
```

Expected: all PASS.

- [ ] **Step 9.5: Run full auth test suite**

```
pytest tests/backend/api/test_auth.py -v
```

Expected: all tests PASS.

- [ ] **Step 9.6: Commit**

```bash
git add backend/app/routes/auth.py tests/backend/api/test_auth.py
git commit -m "feat(auth): add /auth/forgot-password and /auth/reset-password with SMTP delivery"
```

---

## Task 10: Environment variables + docs

**Files:**
- Modify: `.env.example`
- Create: `docs/backend/AUTH.md`

- [ ] **Step 10.1: Update .env.example**

Add to `.env.example`:

```bash
# Auth — JWT (generate JWT_SECRET with: openssl rand -hex 32)
JWT_SECRET=changeme-run-openssl-rand-hex-32
JWT_ACCESS_TTL_MINUTES=15
JWT_REFRESH_TTL_DAYS=30

# Auth — SMTP (password reset emails)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASSWORD=your-gmail-app-password
SMTP_FROM=noreply@resilio.app
APP_BASE_URL=http://localhost:3000
```

- [ ] **Step 10.2: Create docs/backend/AUTH.md**

Create `docs/backend/AUTH.md`:

```markdown
# Auth System — Resilio+

## Overview

JWT-based auth with access + refresh tokens.

| Token | TTL | Storage |
|---|---|---|
| Access (JWT) | 15 min | Stateless — client only |
| Refresh | 30 days | DB (`refresh_tokens` table, hash only) |
| Password reset | 1 hour | DB (`password_reset_tokens` table, hash only) |

---

## Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/auth/login` | No | Email + password → access + refresh tokens |
| `POST` | `/auth/refresh` | No | Rotate refresh token → new access + refresh |
| `POST` | `/auth/logout` | Bearer | Revoke refresh token |
| `GET` | `/auth/me` | Bearer | Current user info |
| `POST` | `/auth/forgot-password` | No | Send reset email |
| `POST` | `/auth/reset-password` | No | Set new password via reset token |
| `POST` | `/athletes/onboarding` | No | Register + create plan → tokens |

---

## Flow: Login

```
POST /auth/login
{ "email": "alice@example.com", "password": "secret123" }

→ 200
{
  "access_token": "eyJ...",
  "refresh_token": "dGhpc...",
  "token_type": "bearer",
  "athlete_id": "uuid-here"
}
```

Store both tokens client-side. Use `access_token` as Bearer on protected endpoints.
When `access_token` expires (15 min), call `/auth/refresh`.

---

## Flow: Refresh

```
POST /auth/refresh
{ "refresh_token": "dGhpc..." }

→ 200
{ "access_token": "eyJ...", "refresh_token": "NEW_TOKEN...", ... }
```

Strict rotation: old refresh token is immediately revoked. Store the new one.

---

## Flow: Logout

```
POST /auth/logout
Authorization: Bearer <access_token>
{ "refresh_token": "dGhpc..." }

→ 200 { "message": "Logged out" }
```

---

## Flow: Password Reset

```
POST /auth/forgot-password
{ "email": "alice@example.com" }
→ 200 (always, no email enumeration)

# User receives email with link: https://app/reset-password?token=<raw_token>

POST /auth/reset-password
{ "token": "<raw_token>", "new_password": "newpass123" }
→ 200

# All refresh tokens revoked — user must log in again
```

---

## curl Examples

```bash
# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@example.com","password":"secret123"}'

# Protected endpoint
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer <access_token>"

# Refresh
curl -X POST http://localhost:8000/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"<refresh_token>"}'

# Logout
curl -X POST http://localhost:8000/auth/logout \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"<refresh_token>"}'
```

---

## TypeScript Client Example

```typescript
// Store tokens
localStorage.setItem('access_token', body.access_token);
localStorage.setItem('refresh_token', body.refresh_token);

// Authenticated request with auto-refresh
async function apiFetch(url: string, options: RequestInit = {}) {
  let token = localStorage.getItem('access_token');
  let res = await fetch(url, {
    ...options,
    headers: { ...options.headers, Authorization: `Bearer ${token}` },
  });

  if (res.status === 401) {
    // Access token expired — refresh
    const refreshRes = await fetch('/auth/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: localStorage.getItem('refresh_token') }),
    });
    if (!refreshRes.ok) {
      // Refresh failed — redirect to login
      window.location.href = '/login';
      throw new Error('Session expired');
    }
    const tokens = await refreshRes.json();
    localStorage.setItem('access_token', tokens.access_token);
    localStorage.setItem('refresh_token', tokens.refresh_token);
    token = tokens.access_token;
    // Retry original request
    res = await fetch(url, {
      ...options,
      headers: { ...options.headers, Authorization: `Bearer ${token}` },
    });
  }
  return res;
}
```

---

## Environment Variables

```bash
JWT_SECRET=<openssl rand -hex 32>     # NEVER commit
JWT_ACCESS_TTL_MINUTES=15
JWT_REFRESH_TTL_DAYS=30
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASSWORD=your-app-password        # Gmail: generate at myaccount.google.com/apppasswords
SMTP_FROM=noreply@resilio.app
APP_BASE_URL=http://localhost:3000
```

---

## V2 Roadmap

- Email verification on registration
- 2FA (TOTP via `pyotp`)
- Password hashing migration: bcrypt → argon2id
- Immediate access token revocation (Redis blocklist)
- OAuth2 social login (Google)
```

- [ ] **Step 10.3: Commit**

```bash
git add .env.example docs/backend/AUTH.md
git commit -m "docs(auth): add AUTH.md with flows, curl/TS examples; update .env.example"
```

---

## Task 11: Full regression + CLAUDE.md update

- [ ] **Step 11.1: Run full test suite**

```
pytest tests/ -x -q
```

Expected: ≥2115 tests passing (all existing + ~15 new auth tests), 0 failures.

- [ ] **Step 11.2: Update CLAUDE.md**

In `CLAUDE.md`, update the Phase Status table — add new row after V3-N:

```markdown
| V3-O | Auth System — refresh tokens, SMTP reset, /auth/me, /logout | ✅ Complete (2026-04-14) |
```

Update the test count line:
```
**Dernières phases complétées (2026-04-14):** Auth system livré — refresh token rotation, SMTP password reset, /auth/me + /auth/logout. ~2130 tests passing.
```

Add to Key References section:
```markdown
- **Auth System**: `docs/backend/AUTH.md` — endpoints, flows, curl/TypeScript examples
```

- [ ] **Step 11.3: Final commit**

```bash
git add CLAUDE.md
git commit -m "docs(claude): update CLAUDE.md — V3-O auth system complete"
```

---

## CHECK-IN: Generate JWT_SECRET

Before running the app (not needed for tests):

```bash
openssl rand -hex 32
# Copy output → .env as JWT_SECRET=<value>
# NEVER commit .env
```
