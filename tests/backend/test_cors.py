"""Tests for the CORS whitelist (env-driven allow_origins)."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.db import models  # noqa: F401 — registers ORM models with Base
from app.dependencies import get_db
from app.main import app


def _make_client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(engine)

    def override_get_db():
        with TestSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app, raise_server_exceptions=True)


@pytest.fixture()
def client():
    c = _make_client()
    with c:
        yield c
    app.dependency_overrides.clear()


def test_cors_allowed_origin(client):
    """An origin in the whitelist must be echoed back in the CORS header."""
    resp = client.options(
        "/",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    # Either 200 (FastAPI CORS preflight) or 405 — the header is what matters
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_cors_blocked_origin(client):
    """An origin NOT in the whitelist must NOT be echoed back."""
    resp = client.options(
        "/",
        headers={
            "Origin": "http://evil.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.headers.get("access-control-allow-origin") != "http://evil.com"
