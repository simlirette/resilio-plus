"""API integration tests for External Plan Import endpoints."""
from __future__ import annotations

import io
from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: registers all ORM models
from app.db.database import Base
from app.dependencies import get_db
from app.main import app
from app.schemas.external_plan import ExternalPlanDraft, ExternalPlanDraftSession


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


def _base_onboarding(**overrides):
    base = {
        "name": "Alice",
        "age": 30,
        "sex": "F",
        "weight_kg": 60.0,
        "height_cm": 168.0,
        "sports": ["running"],
        "primary_sport": "running",
        "goals": ["stay fit"],
        "available_days": [0, 2, 4],
        "hours_per_week": 8.0,
        "email": "alice@test.com",
        "password": "password123",
        "plan_start_date": str(date.today()),
    }
    return {**base, **overrides}


def _register(client, **overrides):
    payload = _base_onboarding(**overrides)
    resp = client.post("/athletes/onboarding", json=payload)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    return body["access_token"], body["athlete"]["id"]


def _authed(client, token):
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


def _make_draft(title: str = "Coach Plan", num_sessions: int = 1) -> ExternalPlanDraft:
    sessions = [
        ExternalPlanDraftSession(
            session_date=date(2026, 5, 1),
            sport="running",
            title=f"Session {i + 1}",
        )
        for i in range(num_sessions)
    ]
    return ExternalPlanDraft(
        title=title,
        sessions_parsed=num_sessions,
        sessions=sessions,
        parse_warnings=[],
    )


# ---------------------------------------------------------------------------
# POST /athletes/{id}/external-plan/import
# ---------------------------------------------------------------------------

def test_import_returns_draft_for_tracking_athlete(client):
    token, athlete_id = _register(
        client, email="importer@test.com", coaching_mode="tracking_only"
    )
    _authed(client, token)

    draft = _make_draft(num_sessions=2)
    with patch("app.routes.external_plan.PlanImportService.parse_file", return_value=draft):
        file_content = b"Day 1: Easy run 5k\nDay 3: Strength training"
        resp = client.post(
            f"/athletes/{athlete_id}/external-plan/import",
            files={"file": ("plan.txt", io.BytesIO(file_content), "text/plain")},
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["title"] == "Coach Plan"
    assert body["sessions_parsed"] == 2
    assert len(body["sessions"]) == 2
    assert "parse_warnings" in body


def test_import_rejected_for_full_mode_athlete(client):
    token, athlete_id = _register(client, email="full@test.com")
    _authed(client, token)
    file_content = b"Some plan"
    resp = client.post(
        f"/athletes/{athlete_id}/external-plan/import",
        files={"file": ("plan.txt", io.BytesIO(file_content), "text/plain")},
    )
    assert resp.status_code == 403


def test_import_unauthenticated_rejected(client):
    file_content = b"Some plan"
    resp = client.post(
        "/athletes/some-id/external-plan/import",
        files={"file": ("plan.txt", io.BytesIO(file_content), "text/plain")},
    )
    assert resp.status_code == 401


def test_import_returns_warnings_from_service(client):
    token, athlete_id = _register(
        client, email="warn@test.com", coaching_mode="tracking_only"
    )
    _authed(client, token)

    draft = ExternalPlanDraft(
        title="Partial Plan",
        sessions_parsed=0,
        sessions=[],
        parse_warnings=["Could not detect dates"],
    )
    with patch("app.routes.external_plan.PlanImportService.parse_file", return_value=draft):
        resp = client.post(
            f"/athletes/{athlete_id}/external-plan/import",
            files={"file": ("plan.txt", io.BytesIO(b"vague text"), "text/plain")},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert "Could not detect dates" in body["parse_warnings"]


# ---------------------------------------------------------------------------
# POST /athletes/{id}/external-plan/import/confirm
# ---------------------------------------------------------------------------

def test_confirm_creates_plan_and_returns_plan_out(client):
    token, athlete_id = _register(
        client, email="confirm@test.com", coaching_mode="tracking_only"
    )
    _authed(client, token)

    draft = _make_draft(title="Confirmed Plan", num_sessions=2)

    from datetime import datetime
    expected_out = {
        "id": "plan-123",
        "athlete_id": athlete_id,
        "title": "Confirmed Plan",
        "source": "file_import",
        "status": "active",
        "start_date": None,
        "end_date": None,
        "created_at": "2026-04-12T00:00:00",
        "sessions": [],
    }
    from app.schemas.external_plan import ExternalPlanOut

    mock_plan = MagicMock()

    with patch("app.routes.external_plan.PlanImportService.confirm_import", return_value=mock_plan):
        with patch.object(ExternalPlanOut, "model_validate", return_value=ExternalPlanOut(**expected_out)):
            resp = client.post(
                f"/athletes/{athlete_id}/external-plan/import/confirm",
                json=draft.model_dump(mode="json"),
            )

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["title"] == "Confirmed Plan"
    assert body["source"] == "file_import"
    assert body["status"] == "active"


def test_confirm_rejected_for_full_mode_athlete(client):
    token, athlete_id = _register(client, email="full2@test.com")
    _authed(client, token)
    draft = _make_draft()
    resp = client.post(
        f"/athletes/{athlete_id}/external-plan/import/confirm",
        json=draft.model_dump(mode="json"),
    )
    assert resp.status_code == 403


def test_confirm_unauthenticated_rejected(client):
    draft = _make_draft()
    resp = client.post(
        "/athletes/some-id/external-plan/import/confirm",
        json=draft.model_dump(mode="json"),
    )
    assert resp.status_code == 401
