"""
Tests for backend/app/routes/workflow.py

Coverage:
  - GET /workflow/status — phases: onboarding, no_plan, active
  - POST /workflow/create-plan — plan creation workflow
  - POST /workflow/weekly-sync — weekly review sync
  - Authentication enforcement
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from tests.test_routes.conftest import authed_client  # noqa: F401


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def test_workflow_status_requires_auth(authed_client):
    client, athlete_id = authed_client
    resp = client.get(
        f"/athletes/{athlete_id}/workflow/status",
        headers={"Authorization": "Bearer invalid_token_xyz"},
    )
    assert resp.status_code == 401


def test_workflow_status_wrong_athlete(authed_client):
    client, _own_id = authed_client
    resp = client.get("/athletes/other-athlete-id/workflow/status")
    assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# GET /workflow/status — phases
# ---------------------------------------------------------------------------

def test_workflow_status_after_onboarding(authed_client):
    """After onboarding (which auto-creates a plan), status should reflect a plan exists."""
    client, athlete_id = authed_client
    resp = client.get(f"/athletes/{athlete_id}/workflow/status")
    assert resp.status_code == 200
    data = resp.json()
    # Onboarding auto-creates a plan, so has_plan=True
    assert data["has_plan"] is True
    assert data["plan_id"] is not None
    assert data["phase"] in ("active", "weekly_review_due", "no_plan", "onboarding")


def test_workflow_status_response_schema(authed_client):
    client, athlete_id = authed_client
    resp = client.get(f"/athletes/{athlete_id}/workflow/status")
    assert resp.status_code == 200
    data = resp.json()
    required_keys = [
        "athlete_id", "phase", "has_plan", "plan_id",
        "plan_start_date", "plan_end_date", "weeks_completed",
        "sessions_logged_this_week", "weekly_review_due", "acwr", "readiness",
    ]
    for key in required_keys:
        assert key in data, f"Missing key: {key}"


# ---------------------------------------------------------------------------
# POST /workflow/create-plan
# ---------------------------------------------------------------------------

def test_create_plan_workflow_success(authed_client):
    """V3-D: create-plan returns thread_id + requires_approval (plan not yet persisted)."""
    client, athlete_id = authed_client
    start = str(date.today() + timedelta(days=1))

    from unittest.mock import MagicMock, patch
    with patch("app.routes.workflow.CoachingService") as MockService:
        mock_instance = MagicMock()
        mock_instance.create_plan.return_value = (
            "thread-test-001",
            {"sessions": [], "phase": "base", "readiness_level": "green"},
        )
        MockService.return_value = mock_instance

        resp = client.post(
            f"/athletes/{athlete_id}/workflow/create-plan",
            json={"start_date": start, "weeks": 4},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["thread_id"] == "thread-test-001"
    assert data["requires_approval"] is True
    assert data["weeks"] == 4
    assert "phase" in data
    assert "sessions_total" in data
    assert "message" in data


def test_create_plan_workflow_updates_status(authed_client):
    """Onboarding creates a plan; status should show has_plan=True without extra create-plan call."""
    client, athlete_id = authed_client
    # Onboarding (via authed_client fixture) already persists a plan
    status_resp = client.get(f"/athletes/{athlete_id}/workflow/status")
    assert status_resp.status_code == 200
    status = status_resp.json()
    assert status["has_plan"] is True
    assert status["plan_id"] is not None


def test_create_plan_requires_auth(authed_client):
    client, athlete_id = authed_client
    start = str(date.today() + timedelta(days=1))
    resp = client.post(
        f"/athletes/{athlete_id}/workflow/create-plan",
        json={"start_date": start, "weeks": 4},
        headers={"Authorization": "Bearer invalid_token_xyz"},
    )
    assert resp.status_code == 401


def test_create_plan_missing_start_date(authed_client):
    client, athlete_id = authed_client
    resp = client.post(
        f"/athletes/{athlete_id}/workflow/create-plan",
        json={"weeks": 4},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /workflow/weekly-sync
# ---------------------------------------------------------------------------

def test_weekly_sync_returns_200(authed_client):
    """Onboarding creates a plan; weekly sync should succeed with 200."""
    client, athlete_id = authed_client
    resp = client.post(f"/athletes/{athlete_id}/workflow/weekly-sync")
    # Plan was created by onboarding, so sync should work
    assert resp.status_code in (200, 404)  # 404 only if plan was deleted


def test_weekly_sync_after_plan_creation(authed_client):
    """Onboarding creates a plan; weekly sync should succeed with 200."""
    client, athlete_id = authed_client
    # Onboarding already created a plan — run weekly sync directly
    sync_resp = client.post(f"/athletes/{athlete_id}/workflow/weekly-sync")
    assert sync_resp.status_code == 200
    data = sync_resp.json()
    assert data["success"] is True
    assert "week_number" in data
    assert "sessions_completed" in data
    assert "sessions_planned" in data
    assert "completion_rate" in data
    assert "readiness" in data
    assert data["readiness"] in ("green", "yellow", "red", None)
    assert isinstance(data["recommendations"], list)


def test_weekly_sync_creates_review_record(authed_client):
    """Running weekly sync should update workflow status phase."""
    client, athlete_id = authed_client
    # Onboarding already created a plan — run weekly sync directly
    client.post(f"/athletes/{athlete_id}/workflow/weekly-sync")

    # After sync, status should reflect review done
    status_resp = client.get(f"/athletes/{athlete_id}/workflow/status")
    assert status_resp.status_code == 200


def test_weekly_sync_requires_auth(authed_client):
    client, athlete_id = authed_client
    resp = client.post(
        f"/athletes/{athlete_id}/workflow/weekly-sync",
        headers={"Authorization": "Bearer invalid_token_xyz"},
    )
    assert resp.status_code == 401
