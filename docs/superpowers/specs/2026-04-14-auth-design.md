# Auth System Design — Resilio+

**Date:** 2026-04-14  
**Status:** Approved  
**Scope:** Complete production-ready auth for FastAPI backend — refresh tokens, password reset via SMTP, `/auth/me`, logout.

---

## Context

A partial auth system already exists:
- `UserModel` — `users` table (id, email, hashed_password, athlete_id FK, created_at)
- `core/security.py` — bcrypt password hashing, JWT HS256 24h access tokens
- `POST /auth/login` — returns `access_token + athlete_id`
- `POST /athletes/onboarding` — registration + plan creation + token
- `get_current_athlete_id` FastAPI dependency — used on ~12 routes
- Tests for login + security primitives

This design extends the existing system without breaking it.

---

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Token strategy | Access (15min) + Refresh (30d) | Balance security vs UX; avoids 24h token risk |
| Refresh rotation | Strict (each use invalidates old token) | Replay detection at no infra cost |
| Refresh storage | DB table, store hash only | Consistent with password storage; no Redis needed for V1 |
| Password hashing | bcrypt (existing, via passlib) | Already works; argon2 migration is V2 |
| Password reset delivery | SMTP email | Proper UX; uses stdlib smtplib, no extra deps |
| Email verification | Skipped V1 | Personal use — deferred to V2 |
| 2FA | Skipped V1 | Documented as V2 feature |
| Logout | Server-side refresh token revocation | Client discards access token; refresh token invalidated in DB |

---

## Database Changes

### `users` table — 2 new columns

```sql
is_active       BOOLEAN NOT NULL DEFAULT TRUE
last_login_at   TIMESTAMP WITH TIME ZONE NULL
```

### New table: `refresh_tokens`

```sql
CREATE TABLE refresh_tokens (
    id          VARCHAR PRIMARY KEY,           -- UUID
    user_id     VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash  VARCHAR NOT NULL UNIQUE,       -- bcrypt hash of raw token
    expires_at  TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at  TIMESTAMP WITH TIME ZONE NOT NULL,
    revoked     BOOLEAN NOT NULL DEFAULT FALSE
);
```

Raw token is **never stored** — only its hash. Same pattern as passwords.

### New table: `password_reset_tokens`

```sql
CREATE TABLE password_reset_tokens (
    id          VARCHAR PRIMARY KEY,           -- UUID
    user_id     VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash  VARCHAR NOT NULL UNIQUE,       -- bcrypt hash of raw token
    expires_at  TIMESTAMP WITH TIME ZONE NOT NULL,  -- TTL: 1 hour
    used        BOOLEAN NOT NULL DEFAULT FALSE
);
```

One Alembic migration file covers both tables + the 2 `users` columns.

---

## Endpoints

### Existing — modified

| Method | Path | Change |
|---|---|---|
| `POST` | `/auth/login` | Add `refresh_token` to response; set `last_login_at`; access TTL → 15min |
| `POST` | `/athletes/onboarding` | Add `refresh_token` to response |

### New

| Method | Path | Auth required | Description |
|---|---|---|---|
| `POST` | `/auth/refresh` | No | Exchange refresh token → new access + refresh token (rotation) |
| `POST` | `/auth/logout` | Bearer | Revoke refresh token in DB |
| `GET` | `/auth/me` | Bearer | Return current user info |
| `POST` | `/auth/forgot-password` | No | Generate reset token, send SMTP email |
| `POST` | `/auth/reset-password` | No | Validate token, update password |

### Request/Response schemas

```python
# /auth/refresh
class RefreshRequest(BaseModel):
    refresh_token: str

# /auth/logout
class LogoutRequest(BaseModel):
    refresh_token: str

# /auth/me response
class MeResponse(BaseModel):
    athlete_id: str
    email: str
    created_at: datetime
    is_active: bool

# /auth/forgot-password
class ForgotPasswordRequest(BaseModel):
    email: str

# /auth/reset-password
class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)

# Updated TokenResponse
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str   # NEW
    token_type: str = "bearer"
    athlete_id: str
```

### Security notes

- `POST /auth/forgot-password` always returns HTTP 200 regardless of whether email exists — prevents user enumeration
- Replay detection: if a revoked refresh token is used, return 401 (possible token theft signal)
- Reset token single-use: marked `used=True` immediately on consumption

---

## Token TTLs

| Token | TTL | Storage |
|---|---|---|
| Access token (JWT) | 15 minutes | Stateless (client only) |
| Refresh token | 30 days | DB (hash only) |
| Password reset token | 1 hour | DB (hash only) |

---

## Core Module Changes

### `core/security.py` — additions

```python
def generate_token() -> str:
    """Generate cryptographically secure random token (URL-safe base64, 32 bytes)."""

def hash_token(raw: str) -> str:
    """Hash raw token with bcrypt for DB storage."""

def verify_token(raw: str, hashed: str) -> bool:
    """Verify raw token against stored hash."""

def create_access_token(athlete_id: str) -> str:
    """Unchanged — TTL now reads JWT_ACCESS_TTL_MINUTES env var (default 15)."""

def create_refresh_token_record(user_id: str, db: Session) -> str:
    """Generate token, store hash in DB, return raw token."""
```

### `core/email.py` — new module

```python
def send_reset_email(to_email: str, reset_url: str) -> None:
    """Send password reset email via SMTP STARTTLS (smtplib stdlib)."""
```

Reads: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `APP_BASE_URL`.

---

## Environment Variables

Added to `.env.example`:

```bash
# Auth — JWT
JWT_SECRET=changeme-generate-with-openssl-rand-hex-32
JWT_ACCESS_TTL_MINUTES=15
JWT_REFRESH_TTL_DAYS=30

# Auth — SMTP (password reset)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@email.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=noreply@resilio.app
APP_BASE_URL=http://localhost:3000
```

**CHECK-IN REQUIRED:** Generate `JWT_SECRET` locally before running:
```bash
openssl rand -hex 32
```
Place in `.env`. Never commit `.env`.

---

## File Structure

```
backend/app/
  core/
    security.py        ← extend: generate_token, hash_token, verify_token, create_refresh_token_record
    email.py           ← NEW: send_reset_email()
  db/
    models.py          ← extend: RefreshTokenModel, PasswordResetTokenModel
                          + is_active, last_login_at on UserModel
  routes/
    auth.py            ← extend: /refresh, /logout, /me, /forgot-password, /reset-password
  schemas/
    auth.py            ← extend: RefreshRequest, LogoutRequest, MeResponse,
                                  ForgotPasswordRequest, ResetPasswordRequest
                          update: TokenResponse (add refresh_token field)
  dependencies/
    __init__.py        ← unchanged
migrations/
  versions/
    XXXX_add_refresh_and_reset_tokens.py   ← NEW Alembic migration
tests/
  backend/
    core/
      test_security.py     ← extend: hash_token, verify_token, generate_token
    api/
      test_auth.py         ← extend: refresh rotation, logout, me, forgot/reset flow
docs/
  backend/
    AUTH.md                ← NEW: flow diagrams, curl examples, TypeScript examples
```

---

## V2 Roadmap (not in scope)

- Email verification on registration
- 2FA (TOTP via pyotp)
- Password hashing migration: bcrypt → argon2
- Immediate access token revocation (Redis blocklist)
- OAuth2 social login (Google)
- LLM token usage tracking per user (billing layer — separate feature)
