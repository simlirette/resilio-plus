"""Tests for auth routes — POST /api/v1/auth/register and /login."""
import uuid
from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import Athlete
from models.db_session import get_db


# ── Test-only app that mounts the auth router ──────────────────────────────
# We create a minimal app here so tests are independent of main.py mount order.
def _make_test_app(mock_session):
    from api.v1.auth import router as auth_router

    test_app = FastAPI()
    test_app.include_router(auth_router, prefix="/auth")

    async def override_get_db():
        yield mock_session

    test_app.dependency_overrides[get_db] = override_get_db
    return test_app


def _make_mock_db(existing_athlete=None, new_athlete_id=None):
    """Build an AsyncMock db session."""
    mock_session = AsyncMock(spec=AsyncSession)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_athlete
    mock_session.execute.return_value = mock_result

    if new_athlete_id:
        async def _refresh(obj):
            obj.id = new_athlete_id

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


# ── Schema test (Task 1) ────────────────────────────────────────────────────

def test_athlete_model_has_email_and_password_hash():
    """Athlete model declares email and password_hash columns."""
    mapper = Athlete.__mapper__
    assert "email" in mapper.columns
    assert "password_hash" in mapper.columns


# ── Route tests (Task 4) ────────────────────────────────────────────────────

def test_register_returns_201():
    """Valid register payload → 201 + access_token in response."""
    new_id = uuid.uuid4()
    mock_db = _make_mock_db(existing_athlete=None, new_athlete_id=new_id)
    client = TestClient(_make_test_app(mock_db))
    resp = client.post("/auth/register", json=REGISTER_PAYLOAD)
    assert resp.status_code == 201
    body = resp.json()
    assert "access_token" in body
    assert body["email"] == "alice@example.com"
    assert body["first_name"] == "Alice"


def test_register_duplicate_email_returns_409():
    """Second register with same email → 409 Conflict."""
    existing = MagicMock(spec=Athlete)
    mock_db = _make_mock_db(existing_athlete=existing)
    client = TestClient(_make_test_app(mock_db))
    resp = client.post("/auth/register", json=REGISTER_PAYLOAD)
    assert resp.status_code == 409


def test_register_invalid_payload_returns_422():
    """Missing required fields → 422 Unprocessable Entity."""
    mock_db = _make_mock_db()
    client = TestClient(_make_test_app(mock_db))
    resp = client.post("/auth/register", json={"email": "bad@example.com"})
    assert resp.status_code == 422


def test_login_success_returns_token():
    """Correct email + password → 200 + access_token."""
    from core.security import hash_password

    hashed = hash_password("SecurePass123!")
    existing = MagicMock(spec=Athlete)
    existing.id = uuid.uuid4()
    existing.password_hash = hashed
    mock_db = _make_mock_db(existing_athlete=existing)
    client = TestClient(_make_test_app(mock_db))
    resp = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "SecurePass123!"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_login_wrong_password_returns_401():
    """Correct email + wrong password → 401 Unauthorized."""
    from core.security import hash_password

    hashed = hash_password("CorrectPassword!")
    existing = MagicMock(spec=Athlete)
    existing.id = uuid.uuid4()
    existing.password_hash = hashed
    mock_db = _make_mock_db(existing_athlete=existing)
    client = TestClient(_make_test_app(mock_db))
    resp = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "WrongPassword!"},
    )
    assert resp.status_code == 401
