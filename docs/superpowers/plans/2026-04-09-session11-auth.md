# S11 — Auth, CORS & OpenAPI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add JWT authentication (register + login), `get_current_athlete` dependency, CORS middleware, and OpenAPI metadata to the FastAPI backend.

**Architecture:** `core/security.py` provides pure JWT/password functions. `api/v1/auth.py` exposes register + login routes using the async DB session. `api/deps.py` provides the `get_current_athlete` FastAPI dependency. `api/main.py` gains CORSMiddleware and mounts the two new routers.

**Tech Stack:** PyJWT 2.x, pwdlib[argon2] 0.2.x, FastAPI, SQLAlchemy 2.0 async, pytest

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `models/database.py` | Modify | Add `email` + `password_hash` to `Athlete` |
| `core/security.py` | Create | hash_password, verify_password, create_access_token, decode_access_token |
| `api/deps.py` | Create | `get_current_athlete` FastAPI dependency |
| `api/v1/auth.py` | Create | POST /register, POST /login |
| `api/v1/athletes.py` | Create | GET /athletes/me |
| `api/main.py` | Modify | CORSMiddleware + auth + athletes routers + OpenAPI metadata |
| `tests/test_security.py` | Create | 4 unit tests for security functions |
| `tests/test_auth_route.py` | Create | 5 integration tests for auth routes (mocked DB) |
| `CLAUDE.md` | Modify | Mark S11 ✅ FAIT, update file tree |

---

### Task 1: Add `email` and `password_hash` to `Athlete` DB model

**Files:**
- Modify: `models/database.py`
- Modify: `tests/conftest.py` (add email/password_hash to `simon_athlete` fixture)

- [ ] **Step 1: Write failing test — Athlete model has email and password_hash**

```python
# tests/test_auth_route.py (create file, add first test)
from models.database import Athlete


def test_athlete_model_has_email_and_password_hash():
    """Athlete model declares email and password_hash columns."""
    mapper = Athlete.__mapper__
    assert "email" in mapper.columns
    assert "password_hash" in mapper.columns
```

- [ ] **Step 2: Run test to verify it fails**

Run: `poetry run pytest tests/test_auth_route.py::test_athlete_model_has_email_and_password_hash -v`
Expected: FAIL with `AssertionError` (columns not found)

- [ ] **Step 3: Add `email` and `password_hash` to `Athlete` in `models/database.py`**

In `models/database.py`, in the `Athlete` class, after the `id` and before `first_name`:

```python
email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
```

- [ ] **Step 4: Update `simon_athlete` fixture in `tests/conftest.py`**

Add `email` and `password_hash` to the `Athlete(...)` constructor in the `simon_athlete` fixture:

```python
athlete = Athlete(
    id=SIMON_ID,
    email="simon@resilio.test",
    password_hash="$argon2id$hashed_placeholder",  # not a real hash — tests don't call verify_password on simon_athlete
    first_name="Simon",
    age=32,
    sex="M",
    weight_kg=78.5,
    height_cm=178,
    body_fat_percent=16.5,
    resting_hr=58,
    max_hr_measured=188,
    profile_data=SIMON_PROFILE_DATA,
    available_days=SIMON_AVAILABLE_DAYS,
)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `poetry run pytest tests/test_auth_route.py::test_athlete_model_has_email_and_password_hash -v`
Expected: PASS

- [ ] **Step 6: Run full suite to verify no regressions**

Run: `poetry run pytest tests/ -v --ignore=tests/test_auth_route.py -x`
Expected: all existing tests pass (if DB tests fail due to schema change, note: `create_all` picks up new columns automatically in test DB)

- [ ] **Step 7: Commit**

```bash
git add models/database.py tests/conftest.py tests/test_auth_route.py
git commit -m "feat: add email + password_hash columns to Athlete model"
```

---

### Task 2: `core/security.py` — JWT + password functions

**Files:**
- Create: `core/security.py`
- Create: `tests/test_security.py`

- [ ] **Step 1: Write the 4 failing tests**

Create `tests/test_security.py`:

```python
"""Tests for core/security.py — JWT + password hashing."""
import uuid

import pytest
from fastapi import HTTPException

from core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_and_verify_password():
    """hash_password → verify_password round-trip returns True."""
    plain = "MySecretP@ssw0rd"
    hashed = hash_password(plain)
    assert verify_password(plain, hashed) is True


def test_verify_wrong_password():
    """verify_password with wrong plain text returns False."""
    hashed = hash_password("correct-password")
    assert verify_password("wrong-password", hashed) is False


def test_create_and_decode_access_token():
    """create_access_token → decode_access_token round-trip returns same UUID."""
    athlete_id = uuid.uuid4()
    token = create_access_token(athlete_id)
    decoded = decode_access_token(token)
    assert decoded == athlete_id


def test_decode_invalid_token_raises_401():
    """decode_access_token with garbage token raises HTTPException 401."""
    with pytest.raises(HTTPException) as exc_info:
        decode_access_token("garbage.token.value")
    assert exc_info.value.status_code == 401
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `poetry run pytest tests/test_security.py -v`
Expected: FAIL with ImportError (module not found)

- [ ] **Step 3: Create `core/security.py`**

```python
"""
SECURITY — Resilio+
JWT access tokens (PyJWT) + password hashing (pwdlib argon2).
"""
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import HTTPException, status
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from core.config import settings

_pwd_hash = PasswordHash([Argon2Hasher()])


def hash_password(plain: str) -> str:
    """Hash a plaintext password using argon2."""
    return _pwd_hash.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against an argon2 hash."""
    return _pwd_hash.verify(plain, hashed)


def create_access_token(athlete_id: uuid.UUID) -> str:
    """Create a JWT access token with athlete_id as subject."""
    expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(athlete_id), "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def decode_access_token(token: str) -> uuid.UUID:
    """Decode JWT and return athlete_id. Raises HTTP 401 on any error."""
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

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run pytest tests/test_security.py -v`
Expected: 4 PASS

- [ ] **Step 5: Ruff check**

Run: `poetry run ruff check core/security.py tests/test_security.py`
Expected: no issues

- [ ] **Step 6: Commit**

```bash
git add core/security.py tests/test_security.py
git commit -m "feat: add core/security.py — JWT + argon2 password functions"
```

---

### Task 3: `api/deps.py` — `get_current_athlete` dependency

**Files:**
- Create: `api/deps.py`

No separate test file — this dependency is tested implicitly via the `GET /athletes/me` route test in Task 5. The `decode_access_token` path is already covered by `test_security.py`.

- [ ] **Step 1: Create `api/deps.py`**

```python
"""
FASTAPI DEPENDENCIES — Resilio+
Shared dependencies for authenticated endpoints.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import decode_access_token
from models.database import Athlete
from models.db_session import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_athlete(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Athlete:
    """Decode Bearer JWT → fetch Athlete from DB. Raises 401 if invalid or not found."""
    athlete_id = decode_access_token(token)
    result = await db.execute(select(Athlete).where(Athlete.id == athlete_id))
    athlete = result.scalar_one_or_none()
    if athlete is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Athlete not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return athlete
```

- [ ] **Step 2: Ruff check**

Run: `poetry run ruff check api/deps.py`
Expected: no issues

- [ ] **Step 3: Commit**

```bash
git add api/deps.py
git commit -m "feat: add api/deps.py — get_current_athlete FastAPI dependency"
```

---

### Task 4: `api/v1/auth.py` — register + login routes

**Files:**
- Create: `api/v1/auth.py`
- Modify: `tests/test_auth_route.py` (add 4 more tests)

The auth route tests mock `get_db` using FastAPI's `app.dependency_overrides`. The `mock_db` fixture returns an `AsyncMock` that simulates the DB session.

- [ ] **Step 1: Write the 4 auth route failing tests**

Add to `tests/test_auth_route.py`:

```python
"""Tests for POST /api/v1/auth/register and /login."""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.main import app
from models.database import Athlete
from models.db_session import get_db


def _make_mock_db(existing_athlete=None, new_athlete_id=None):
    """Helper: build an AsyncMock db session."""
    mock_session = AsyncMock(spec=AsyncSession)

    # scalar_one_or_none() result for SELECT by email
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_athlete
    mock_session.execute.return_value = mock_result

    # refresh populates the new athlete's id, email, first_name
    if new_athlete_id:
        async def _refresh(obj):
            obj.id = new_athlete_id
            obj.email = obj.email
            obj.first_name = obj.first_name
        mock_session.refresh.side_effect = _refresh

    return mock_session


REGISTER_PAYLOAD = {
    "email": "alice@example.com",
    "password": "SecurePass123!",
    "first_name": "Alice",
    "age": 28,
    "sex": "F",
    "weight_kg": 60.0,
    "height_cm": 165.0,
}


def test_register_returns_201():
    """Valid register payload → 201 + access_token in response."""
    new_id = uuid.uuid4()
    mock_db = _make_mock_db(existing_athlete=None, new_athlete_id=new_id)

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        client = TestClient(app)
        resp = client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
        assert resp.status_code == 201
        body = resp.json()
        assert "access_token" in body
        assert body["email"] == "alice@example.com"
        assert body["first_name"] == "Alice"
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_register_duplicate_email_returns_409():
    """Second register with same email → 409 Conflict."""
    existing = MagicMock(spec=Athlete)
    mock_db = _make_mock_db(existing_athlete=existing)

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        client = TestClient(app)
        resp = client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
        assert resp.status_code == 409
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_register_invalid_payload_returns_422():
    """Missing required fields → 422 Unprocessable Entity."""
    client = TestClient(app)
    resp = client.post("/api/v1/auth/register", json={"email": "bad@example.com"})
    assert resp.status_code == 422


def test_login_success_returns_token():
    """Correct email + password → 200 + access_token."""
    from core.security import hash_password

    hashed = hash_password("SecurePass123!")
    existing = MagicMock(spec=Athlete)
    existing.id = uuid.uuid4()
    existing.password_hash = hashed
    mock_db = _make_mock_db(existing_athlete=existing)

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        client = TestClient(app)
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "alice@example.com", "password": "SecurePass123!"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_login_wrong_password_returns_401():
    """Correct email + wrong password → 401 Unauthorized."""
    from core.security import hash_password

    hashed = hash_password("CorrectPassword!")
    existing = MagicMock(spec=Athlete)
    existing.id = uuid.uuid4()
    existing.password_hash = hashed
    mock_db = _make_mock_db(existing_athlete=existing)

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        client = TestClient(app)
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "alice@example.com", "password": "WrongPassword!"},
        )
        assert resp.status_code == 401
    finally:
        app.dependency_overrides.pop(get_db, None)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `poetry run pytest tests/test_auth_route.py -v -k "not test_athlete_model"`
Expected: FAIL with ImportError (api/v1/auth.py not found) or 404

- [ ] **Step 3: Create `api/v1/auth.py`**

```python
"""
AUTH ROUTES — Resilio+
POST /register  — Create athlete account
POST /login     — Obtain JWT access token
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
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
    sex: str
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
    result = await db.execute(select(Athlete).where(Athlete.email == body.email))
    if result.scalar_one_or_none() is not None:
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

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run pytest tests/test_auth_route.py -v`
Expected: 5 PASS (including the model test from Task 1)

- [ ] **Step 5: Ruff check**

Run: `poetry run ruff check api/v1/auth.py tests/test_auth_route.py`
Expected: no issues

- [ ] **Step 6: Commit**

```bash
git add api/v1/auth.py tests/test_auth_route.py
git commit -m "feat: add POST /auth/register and /auth/login routes with tests"
```

---

### Task 5: `api/v1/athletes.py` — GET /athletes/me

**Files:**
- Create: `api/v1/athletes.py`

No separate test — the route is trivial (pure dependency passthrough). The `get_current_athlete` dependency is covered by `test_security.py` + auth route tests. A smoke test in Task 6 (main.py update) will confirm 401 on missing token.

- [ ] **Step 1: Create `api/v1/athletes.py`**

```python
"""
ATHLETES ROUTES — Resilio+
GET /athletes/me — Return authenticated athlete's profile.
"""
from fastapi import APIRouter, Depends

from api.deps import get_current_athlete
from models.database import Athlete

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

- [ ] **Step 2: Ruff check**

Run: `poetry run ruff check api/v1/athletes.py`
Expected: no issues

- [ ] **Step 3: Commit**

```bash
git add api/v1/athletes.py
git commit -m "feat: add GET /athletes/me route"
```

---

### Task 6: Update `api/main.py` — CORS + routers + OpenAPI metadata

**Files:**
- Modify: `api/main.py`

- [ ] **Step 1: Read the current `api/main.py`**

Read `api/main.py` to confirm current imports and router mounts before editing.

- [ ] **Step 2: Update `api/main.py`**

Replace the entire file with:

```python
"""
FastAPI application — Resilio+
S11: auth JWT, CORS middleware, OpenAPI metadata.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.v1.apple_health import router as apple_health_router
from api.v1.athletes import router as athletes_router
from api.v1.auth import router as auth_router
from api.v1.connectors import router as connectors_router
from api.v1.files import router as files_router
from api.v1.food import router as food_router
from api.v1.plan import router as plan_router
from api.v1.workflow import router as workflow_router

app = FastAPI(
    title="Resilio+",
    version="0.11.0",
    description=(
        "Multi-agent hybrid coaching platform for endurance and strength athletes. "
        "Orchestrates 7 specialist AI coaches (running, lifting, swimming, cycling, "
        "nutrition, recovery) under a Head Coach that manages ACWR, fatigue, and periodization."
    ),
    contact={"name": "Resilio+", "email": "simon@resilio.app"},
    openapi_tags=[
        {"name": "auth", "description": "JWT authentication — register and login"},
        {"name": "athletes", "description": "Athlete profile (authenticated)"},
        {"name": "plan", "description": "Workout plan generation (running, lifting, recovery)"},
        {"name": "workflow", "description": "Head Coach workflow — weekly review loop"},
        {"name": "connectors", "description": "Third-party integrations (Strava, Hevy)"},
        {"name": "apple-health", "description": "Apple Health data ingestion"},
        {"name": "files", "description": "GPX / FIT file import"},
        {"name": "food", "description": "Food search (USDA / Open Food Facts)"},
    ],
)

# CORS — allow Next.js dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(athletes_router, prefix="/api/v1/athletes", tags=["athletes"])
app.include_router(connectors_router, prefix="/api/v1/connectors", tags=["connectors"])
app.include_router(apple_health_router, prefix="/api/v1/connectors", tags=["apple-health"])
app.include_router(files_router, prefix="/api/v1/connectors", tags=["files"])
app.include_router(food_router, prefix="/api/v1/connectors", tags=["food"])
app.include_router(plan_router, prefix="/api/v1/plan", tags=["plan"])
app.include_router(workflow_router, prefix="/api/v1/workflow", tags=["workflow"])
```

- [ ] **Step 3: Verify GET /athletes/me returns 401 without token (smoke test)**

```bash
poetry run uvicorn api.main:app --port 8001 &
sleep 2
curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/api/v1/athletes/me
# Expected: 401
kill %1
```

- [ ] **Step 4: Ruff check**

Run: `poetry run ruff check api/main.py`
Expected: no issues

- [ ] **Step 5: Run full test suite**

Run: `poetry run pytest tests/ -v`
Expected: all tests pass (~156 tests)

- [ ] **Step 6: Commit**

```bash
git add api/main.py
git commit -m "feat: add CORS middleware, auth/athletes routers, OpenAPI metadata to main.py"
```

---

### Task 7: Update CLAUDE.md for S11

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Mark S11 as done in the session table**

In the `## ÉTAT D'AVANCEMENT` table, change:
```
| **S11** | Backend | FastAPI endpoints + OpenAPI docs + auth | ⬜ À FAIRE |
```
to:
```
| **S11** | Backend | FastAPI endpoints + OpenAPI docs + auth | ✅ FAIT |
```

- [ ] **Step 2: Update the file tree for new files**

In the `api/` section, add:
```
│       ├── auth.py                   ← ✅ S11 — POST /auth/register + /auth/login
│       └── athletes.py               ← ✅ S11 — GET /athletes/me
```

In the `api/` root section, add:
```
│   ├── deps.py                        ← ✅ S11 — get_current_athlete dependency
```

In the `core/` section, add:
```
│   └── security.py                    ← ✅ S11 — hash_password, verify_password, JWT create/decode
```

Update `api/main.py` annotation:
```
│   ├── main.py                        ← ✅ S11 — + CORS + auth + athletes routers + OpenAPI metadata
```

Update test count line:
```
│   ├── test_security.py               ← ✅ S11 — 4 tests security functions
│   └── test_auth_route.py             ← ✅ S11 — 5 tests auth routes (156 tests total)
```

- [ ] **Step 3: Run full test suite one final time**

Run: `poetry run pytest tests/ -v`
Expected: all ~156 tests pass

- [ ] **Step 4: Ruff check clean**

Run: `poetry run ruff check .`
Expected: no issues

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md
git commit -m "chore: mark S11 done in CLAUDE.md — auth JWT + CORS + OpenAPI"
```

- [ ] **Step 6: Push to origin**

```bash
git push origin main
```
