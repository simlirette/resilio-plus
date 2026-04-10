"""
Shared fixtures for tests/test_routes/.
Uses the same in-memory SQLite pattern as tests/backend/api/conftest.py.
"""
from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.db import models  # noqa: F401 — registers ORM models
from app.dependencies import get_db
from app.main import app


def _make_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_pragma(dbapi_connection, _record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def _onboarding_payload(**overrides):
    base = {
        "name": "TestAthlete",
        "age": 30,
        "sex": "M",
        "weight_kg": 75.0,
        "height_cm": 178.0,
        "sports": ["running", "lifting"],
        "primary_sport": "running",
        "goals": ["run 10km under 50min"],
        "available_days": [1, 3, 5],
        "hours_per_week": 8.0,
        "email": "testathlete@test.com",
        "password": "password123",
        "plan_start_date": str(date.today()),
    }
    return {**base, **overrides}


@pytest.fixture()
def authed_client():
    """TestClient with Bearer token pre-set. Yields (client, athlete_id)."""
    engine = _make_engine()
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(engine)

    def override_get_db():
        with TestSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        resp = c.post("/athletes/onboarding", json=_onboarding_payload())
        assert resp.status_code == 201, resp.text
        body = resp.json()
        token = body["access_token"]
        athlete_id = body["athlete"]["id"]
        c.headers.update({"Authorization": f"Bearer {token}"})
        yield c, athlete_id
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
