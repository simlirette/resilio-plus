"""Tests for V3-D workflow endpoints: create-plan with LangGraph, approve, revise."""
from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.db import models as _models  # noqa: registers all ORM models
from app.db.models import AthleteModel
from app.main import app
from app.dependencies import get_db, get_current_athlete_id

ATHLETE_ID = "11111111-1111-1111-1111-111111111111"


def _make_engine():
    return create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


@pytest.fixture
def client_and_athlete():
    engine = _make_engine()
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)

    def override_get_db():
        with TestSession() as session:
            yield session

    # Create athlete with valid UUID and integer available_days
    with TestSession() as db:
        athlete = AthleteModel(
            id=ATHLETE_ID,
            name="Test Athlete",
            age=30,
            sex="M",
            weight_kg=70.0,
            height_cm=175.0,
            sports_json='["running"]',
            primary_sport="running",
            goals_json='["run 10k"]',
            available_days_json='[0, 2, 4]',
            hours_per_week=6.0,
            equipment_json='[]',
            coaching_mode="full",
        )
        db.add(athlete)
        db.commit()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_athlete_id] = lambda: ATHLETE_ID

    with TestClient(app) as client:
        yield client, ATHLETE_ID, engine

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def test_create_plan_returns_thread_id(client_and_athlete):
    """POST /workflow/create-plan returns thread_id and requires_approval=True."""
    client, athlete_id, _ = client_and_athlete
    start = date.today()

    with patch("app.routes.workflow.CoachingService") as MockService:
        mock_instance = MagicMock()
        mock_instance.create_plan.return_value = (
            "thread-abc-123",
            {"sessions": [], "phase": "base", "readiness_level": "green"},
        )
        MockService.return_value = mock_instance

        resp = client.post(
            f"/athletes/{athlete_id}/workflow/create-plan",
            json={"start_date": start.isoformat(), "weeks": 8},
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["success"] is True
    assert data["thread_id"] == "thread-abc-123"
    assert data["requires_approval"] is True


def test_approve_plan_returns_plan_id(client_and_athlete):
    """POST /workflow/plans/{thread_id}/approve returns success + plan_id."""
    client, athlete_id, _ = client_and_athlete
    thread_id = f"{athlete_id}:thread-abc-123"

    with patch("app.routes.workflow.CoachingService") as MockService:
        mock_instance = MagicMock()
        mock_instance.resume_plan.return_value = {
            "sessions": [],
            "phase": "base",
            "readiness_level": "green",
            "db_plan_id": "plan-xyz",
        }
        MockService.return_value = mock_instance

        resp = client.post(
            f"/athletes/{athlete_id}/workflow/plans/{thread_id}/approve",
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["success"] is True
    assert data["plan_id"] == "plan-xyz"


def test_revise_plan_returns_new_proposed(client_and_athlete):
    """POST /workflow/plans/{thread_id}/revise returns requires_approval=True."""
    client, athlete_id, _ = client_and_athlete
    thread_id = f"{athlete_id}:thread-abc-123"

    with patch("app.routes.workflow.CoachingService") as MockService:
        mock_instance = MagicMock()
        mock_instance.resume_plan.return_value = {
            "sessions": [],
            "phase": "base",
            "readiness_level": "green",
        }
        MockService.return_value = mock_instance

        resp = client.post(
            f"/athletes/{athlete_id}/workflow/plans/{thread_id}/revise",
            json={"feedback": "Trop de volume, réduire s'il te plaît"},
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["success"] is True
    assert data["requires_approval"] is True
    assert data["thread_id"] == thread_id


def test_create_plan_requires_full_mode(client_and_athlete):
    """POST /workflow/create-plan returns 403 for tracking_only mode."""
    client, athlete_id, engine = client_and_athlete
    TestSession = sessionmaker(bind=engine)

    with TestSession() as db:
        athlete = db.get(AthleteModel, athlete_id)
        athlete.coaching_mode = "tracking_only"
        db.commit()

    resp = client.post(
        f"/athletes/{athlete_id}/workflow/create-plan",
        json={"start_date": date.today().isoformat(), "weeks": 8},
    )
    assert resp.status_code == 403


def test_approve_requires_full_mode(client_and_athlete):
    """POST /workflow/plans/{thread_id}/approve returns 403 for tracking_only."""
    client, athlete_id, engine = client_and_athlete
    TestSession = sessionmaker(bind=engine)

    with TestSession() as db:
        athlete = db.get(AthleteModel, athlete_id)
        athlete.coaching_mode = "tracking_only"
        db.commit()

    resp = client.post(
        f"/athletes/{athlete_id}/workflow/plans/some-thread/approve",
    )
    assert resp.status_code == 403


def test_revise_requires_full_mode(client_and_athlete):
    """POST /workflow/plans/{thread_id}/revise returns 403 for tracking_only."""
    client, athlete_id, engine = client_and_athlete
    TestSession = sessionmaker(bind=engine)

    with TestSession() as db:
        athlete = db.get(AthleteModel, athlete_id)
        athlete.coaching_mode = "tracking_only"
        db.commit()

    resp = client.post(
        f"/athletes/{athlete_id}/workflow/plans/some-thread/revise",
        json={"feedback": "feedback"},
    )
    assert resp.status_code == 403
