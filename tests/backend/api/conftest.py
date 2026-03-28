import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.db import models  # noqa: F401 — registers ORM models with Base
from app.dependencies import get_db
from app.main import app


def _make_test_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


@pytest.fixture()
def client():
    engine = _make_test_engine()
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(engine)

    def override_get_db():
        with TestSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def athlete_payload(**overrides):
    base = {
        "name": "Alice",
        "age": 30,
        "sex": "F",
        "weight_kg": 60.0,
        "height_cm": 168.0,
        "sports": ["running", "lifting"],
        "primary_sport": "running",
        "goals": ["run sub-4h marathon"],
        "available_days": [0, 2, 4, 6],
        "hours_per_week": 10.0,
    }
    return {**base, **overrides}
