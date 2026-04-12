"""Tests for S-3 weekly review endpoints: /plan/review/start and /plan/review/confirm."""
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

ATHLETE_ID = "22222222-2222-2222-2222-222222222222"
THREAD_ID = f"{ATHLETE_ID}:review:aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


def _make_engine():
    return create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


@pytest.fixture
def client_with_athlete():
    engine = _make_engine()
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)

    def override_get_db():
        with TestSession() as session:
            yield session

    with TestSession() as db:
        athlete = AthleteModel(
            id=ATHLETE_ID,
            name="Review Athlete",
            age=28,
            sex="F",
            weight_kg=60.0,
            height_cm=168.0,
            sports_json='["running"]',
            primary_sport="running",
            goals_json='["complete half marathon"]',
            available_days_json='[0, 2, 4]',
            hours_per_week=8.0,
            equipment_json='[]',
            coaching_mode="full",
        )
        db.add(athlete)
        db.commit()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_athlete_id] = lambda: ATHLETE_ID

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


# ---------------------------------------------------------------------------
# /plan/review/start
# ---------------------------------------------------------------------------

def test_review_start_returns_thread_id(client_with_athlete):
    """POST /plan/review/start returns thread_id and review_summary."""
    client = client_with_athlete

    mock_summary = {
        "week_number": 3,
        "week_start": date.today().isoformat(),
        "sessions_planned": 3,
        "sessions_completed": 2,
        "completion_rate": 0.667,
        "actual_hours": 2.0,
        "acwr": 1.1,
        "readiness": "green",
        "recommendations": ["Bonne semaine."],
    }

    with patch("app.routes.workflow._review_service") as mock_svc:
        mock_svc.weekly_review.return_value = (THREAD_ID, mock_summary)

        resp = client.post(f"/athletes/{ATHLETE_ID}/plan/review/start")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["thread_id"] == THREAD_ID
    assert body["review_summary"] is not None
    assert body["review_summary"]["sessions_completed"] == 2
    assert "Confirme" in body["message"]


def test_review_start_handles_service_error(client_with_athlete):
    """POST /plan/review/start returns 500 if service raises."""
    client = client_with_athlete

    with patch("app.routes.workflow._review_service") as mock_svc:
        mock_svc.weekly_review.side_effect = RuntimeError("graph failure")

        resp = client.post(f"/athletes/{ATHLETE_ID}/plan/review/start")

    assert resp.status_code == 500
    assert "graph failure" in resp.json()["detail"]


def test_review_start_null_summary(client_with_athlete):
    """POST /plan/review/start handles None review_summary gracefully."""
    client = client_with_athlete

    with patch("app.routes.workflow._review_service") as mock_svc:
        mock_svc.weekly_review.return_value = (THREAD_ID, None)

        resp = client.post(f"/athletes/{ATHLETE_ID}/plan/review/start")

    assert resp.status_code == 200
    body = resp.json()
    assert body["thread_id"] == THREAD_ID
    assert body["review_summary"] is None


# ---------------------------------------------------------------------------
# /plan/review/confirm
# ---------------------------------------------------------------------------

def test_review_confirm_approved(client_with_athlete):
    """POST /plan/review/confirm with approved=True calls resume_review and returns success."""
    client = client_with_athlete

    with patch("app.routes.workflow._review_service") as mock_svc:
        mock_svc.resume_review.return_value = None

        resp = client.post(
            f"/athletes/{ATHLETE_ID}/plan/review/confirm",
            json={"thread_id": THREAD_ID, "approved": True},
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["success"] is True
    assert "enregistrée" in body["message"]
    mock_svc.resume_review.assert_called_once()


def test_review_confirm_declined(client_with_athlete):
    """POST /plan/review/confirm with approved=False returns annulée."""
    client = client_with_athlete

    with patch("app.routes.workflow._review_service") as mock_svc:
        mock_svc.resume_review.return_value = None

        resp = client.post(
            f"/athletes/{ATHLETE_ID}/plan/review/confirm",
            json={"thread_id": THREAD_ID, "approved": False},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert "annulée" in body["message"]


def test_review_confirm_wrong_athlete_ownership(client_with_athlete):
    """POST /plan/review/confirm with thread_id belonging to different athlete → 403."""
    client = client_with_athlete
    foreign_thread = "other-athlete-id:review:aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"

    with patch("app.routes.workflow._review_service"):
        resp = client.post(
            f"/athletes/{ATHLETE_ID}/plan/review/confirm",
            json={"thread_id": foreign_thread, "approved": True},
        )

    assert resp.status_code == 403


def test_review_confirm_service_error(client_with_athlete):
    """POST /plan/review/confirm returns 500 if resume_review raises."""
    client = client_with_athlete

    with patch("app.routes.workflow._review_service") as mock_svc:
        mock_svc.resume_review.side_effect = RuntimeError("resume failed")

        resp = client.post(
            f"/athletes/{ATHLETE_ID}/plan/review/confirm",
            json={"thread_id": THREAD_ID, "approved": True},
        )

    assert resp.status_code == 500
    assert "resume failed" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------

def test_review_start_forbidden_for_different_athlete(client_with_athlete):
    """_require_own blocks access when authenticated athlete ≠ path athlete_id."""
    client = client_with_athlete
    other_id = "33333333-3333-3333-3333-333333333333"

    resp = client.post(f"/athletes/{other_id}/plan/review/start")

    assert resp.status_code == 403
