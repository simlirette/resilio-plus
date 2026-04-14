# tests/backend/conftest.py
"""Shared fixtures for contract tests — SQLite in-memory + TestClient."""
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.db import models  # noqa: F401 — registers ORM models with Base
from app.dependencies import get_db
from app.main import app


def _make_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_pragma(dbapi_conn, _record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def _next_monday() -> str:
    d = date.today()
    days_ahead = (7 - d.weekday()) % 7 or 7
    return str(d + timedelta(days=days_ahead))


def _onboarding_payload() -> dict:
    return {
        "email": "contract@resilio.test",
        "password": "testpass123",
        "plan_start_date": _next_monday(),
        "name": "Contract Tester",
        "age": 30,
        "sex": "M",
        "weight_kg": 75.0,
        "height_cm": 180.0,
        "primary_sport": "running",
        "sports": ["running", "lifting"],
        "goals": ["test"],
        "available_days": [0, 2, 4, 6],
        "hours_per_week": 8.0,
    }


@pytest.fixture(scope="module")
def api_client():
    engine = _make_engine()
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(engine)

    def override_get_db():
        with TestSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="module")
def auth_state(api_client):
    """Create athlete via onboarding, return token + athlete_id."""
    resp = api_client.post("/athletes/onboarding", json=_onboarding_payload())
    assert resp.status_code == 201, resp.text
    body = resp.json()
    return {
        "token": body["access_token"],
        "athlete_id": body["athlete"]["id"],
        "headers": {"Authorization": f"Bearer {body['access_token']}"},
        "plan": body["plan"],
    }
