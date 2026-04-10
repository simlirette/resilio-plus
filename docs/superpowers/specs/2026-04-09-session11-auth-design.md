# Session 11 — Auth, CORS & OpenAPI Design Spec

## Goal

Add JWT authentication (register + login), a `get_current_athlete` FastAPI dependency, CORS middleware, and OpenAPI metadata improvements to the Resilio+ backend. Expose via `POST /api/v1/auth/register` and `POST /api/v1/auth/login`. Add `GET /api/v1/athletes/me` as the first authenticated endpoint.

---

## Architecture

```
POST /api/v1/auth/register
      ↓
  validate RegisterRequest
      ↓
  check email uniqueness (DB async)
      ↓
  hash_password (pwdlib argon2)
      ↓
  insert Athlete row
      ↓
  create_access_token (PyJWT)
      ↓
  201 { id, email, first_name, access_token }

POST /api/v1/auth/login
      ↓
  fetch Athlete by email (DB async)
      ↓
  verify_password (pwdlib argon2)
      ↓
  create_access_token (PyJWT)
      ↓
  200 { access_token, token_type: "bearer" }

GET /api/v1/athletes/me
      ↓
  get_current_athlete dep (Bearer → decode JWT → fetch Athlete)
      ↓
  200 { id, email, first_name, age, sex, weight_kg, height_cm, ... }
```

---

## `models/database.py` — Athlete model additions

Add two columns to the existing `Athlete` table:

```python
email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
```

These go after `first_name`. Migration to be added in S2 (DB migrations session). For now, tests use `Base.metadata.create_all` against the test DB.

---

## `core/security.py` — New file

```python
from datetime import UTC, datetime, timedelta
import uuid

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from fastapi import HTTPException, status

from core.config import settings

_pwd_hash = PasswordHash([Argon2Hasher()])


def hash_password(plain: str) -> str:
    return _pwd_hash.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_hash.verify(plain, hashed)


def create_access_token(athlete_id: uuid.UUID) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(athlete_id), "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def decode_access_token(token: str) -> uuid.UUID:
    """Decode JWT and return athlete_id. Raises 401 on any error."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return uuid.UUID(payload["sub"])
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
```

---

## `api/deps.py` — New file

FastAPI dependency for all authenticated endpoints:

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.security import decode_access_token
from models.database import Athlete
from models.db_session import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_athlete(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Athlete:
    athlete_id = decode_access_token(token)
    result = await db.execute(select(Athlete).where(Athlete.id == athlete_id))
    athlete = result.scalar_one_or_none()
    if athlete is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Athlete not found")
    return athlete
```

---

## `api/v1/auth.py` — New file

```python
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import create_access_token, hash_password, verify_password
from models.database import Athlete
from models.db_session import get_db

router = APIRouter()


class RegisterRequest(BaseModel):
    email: str
    password: str
    first_name: str
    age: int
    sex: str        # "M" | "F"
    weight_kg: float
    height_cm: float


class RegisterResponse(BaseModel):
    id: str
    email: str
    first_name: str
    access_token: str


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check email uniqueness
    existing = await db.execute(select(Athlete).where(Athlete.email == body.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Email already registered")

    athlete = Athlete(
        email=body.email,
        password_hash=hash_password(body.password),
        first_name=body.first_name,
        age=body.age,
        sex=body.sex,
        weight_kg=body.weight_kg,
        height_cm=body.height_cm,
        profile_data={},
        available_days={},
    )
    db.add(athlete)
    await db.commit()
    await db.refresh(athlete)

    return RegisterResponse(
        id=str(athlete.id),
        email=athlete.email,
        first_name=athlete.first_name,
        access_token=create_access_token(athlete.id),
    )


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Athlete).where(Athlete.email == body.email))
    athlete = result.scalar_one_or_none()
    if athlete is None or not verify_password(body.password, athlete.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return LoginResponse(access_token=create_access_token(athlete.id))
```

---

## `api/v1/athletes.py` — New file

```python
from fastapi import APIRouter, Depends
from models.database import Athlete
from api.deps import get_current_athlete

router = APIRouter()


@router.get("/me")
async def get_me(athlete: Athlete = Depends(get_current_athlete)) -> dict:
    return {
        "id": str(athlete.id),
        "email": athlete.email,
        "first_name": athlete.first_name,
        "age": athlete.age,
        "sex": athlete.sex,
        "weight_kg": athlete.weight_kg,
        "height_cm": athlete.height_cm,
        "body_fat_percent": athlete.body_fat_percent,
        "resting_hr": athlete.resting_hr,
        "max_hr_measured": athlete.max_hr_measured,
    }
```

---

## `api/main.py` — Updates

1. Add `CORSMiddleware` (before any router includes):
   - `allow_origins=["http://localhost:3000"]`
   - `allow_credentials=True`
   - `allow_methods=["*"]`
   - `allow_headers=["*"]`

2. Improve `FastAPI(...)` constructor with description, contact, and OpenAPI tags metadata.

3. Mount `auth_router` at `/api/v1/auth`, `athletes_router` at `/api/v1/athletes`.

---

## Tests

### `tests/test_security.py` — 4 tests

```python
def test_hash_and_verify_password():
    """hash_password → verify_password round-trip returns True."""

def test_verify_wrong_password():
    """verify_password with wrong plain text returns False."""

def test_create_and_decode_access_token():
    """create_access_token → decode_access_token round-trip returns same UUID."""

def test_decode_invalid_token_raises_401():
    """decode_access_token with garbage token raises HTTPException 401."""
```

### `tests/test_auth_route.py` — 5 tests

Auth route tests mock `get_db` (no real DB required):

```python
def test_register_returns_201(mock_db):
    """Valid register payload → 201 + access_token in response."""

def test_register_duplicate_email_returns_409(mock_db):
    """Second register with same email → 409 Conflict."""

def test_register_invalid_payload_returns_422():
    """Missing required fields → 422 Unprocessable Entity."""

def test_login_success_returns_token(mock_db):
    """Correct email + password → 200 + access_token."""

def test_login_wrong_password_returns_401(mock_db):
    """Correct email + wrong password → 401 Unauthorized."""
```

---

## Files — Summary

| File | Action |
|------|--------|
| `models/database.py` | Modify — add `email` + `password_hash` to `Athlete` |
| `core/security.py` | Create — JWT + pwdlib password functions |
| `api/deps.py` | Create — `get_current_athlete` dependency |
| `api/v1/auth.py` | Create — POST /register + POST /login |
| `api/v1/athletes.py` | Create — GET /athletes/me |
| `api/main.py` | Modify — CORS + routers + OpenAPI metadata |
| `tests/test_security.py` | Create — 4 tests |
| `tests/test_auth_route.py` | Create — 5 tests |
| `CLAUDE.md` | Modify — S11 ✅ FAIT at end of session |

---

## Invariants post-S11

- All existing tests continue to pass (147 → ~156 tests)
- `ruff check` clean
- `decode_access_token` raises `HTTPException(401)` — never leaks JWT errors as 500
- `verify_password` always runs (no short-circuit on missing athlete) to prevent timing attacks
- `email` uniqueness enforced at DB level (unique=True) + at application level (409 before insert)
- CORS allows `localhost:3000` only — no wildcard `*` in production config
- No refresh token / logout in V1 (YAGNI — S14 scope)
