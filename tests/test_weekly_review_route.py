"""Tests for POST /api/v1/workflow/weekly-review. Graph always mocked — no real LangGraph run."""
from unittest.mock import patch

_MOCK_REPORT = {
    "agent": "head_coach",
    "week_reviewed": 3,
    "completion_rate": 0.8,
    "sessions_completed": 4,
    "sessions_planned": 5,
    "trimp_total": 280.0,
    "acwr_before": 1.05,
    "acwr_after": 1.1,
    "adjustments": [],
    "next_week_notes": "",
}


def test_post_weekly_review_returns_200(simon_pydantic_state):
    """POST /api/v1/workflow/weekly-review with valid state → 200 + report."""
    from fastapi.testclient import TestClient

    from api.main import app

    client = TestClient(app)

    with patch("api.v1.workflow.weekly_review_graph") as mock_graph:
        mock_graph.invoke.return_value = {"report": _MOCK_REPORT}

        response = client.post(
            "/api/v1/workflow/weekly-review",
            json={
                "athlete_state": simon_pydantic_state.model_dump(mode="json"),
                "actual_workouts": [],
            },
        )

    assert response.status_code == 200


def test_post_weekly_review_invalid_body():
    """POST /api/v1/workflow/weekly-review with bad athlete_state → 422."""
    from fastapi.testclient import TestClient

    from api.main import app

    client = TestClient(app)

    response = client.post(
        "/api/v1/workflow/weekly-review",
        json={"athlete_state": {"not_a_valid": "state"}, "actual_workouts": []},
    )

    assert response.status_code == 422


def test_post_weekly_review_report_structure(simon_pydantic_state):
    """POST /api/v1/workflow/weekly-review → report contains all required keys."""
    from fastapi.testclient import TestClient

    from api.main import app

    client = TestClient(app)

    with patch("api.v1.workflow.weekly_review_graph") as mock_graph:
        mock_graph.invoke.return_value = {"report": _MOCK_REPORT}

        response = client.post(
            "/api/v1/workflow/weekly-review",
            json={
                "athlete_state": simon_pydantic_state.model_dump(mode="json"),
                "actual_workouts": [
                    {
                        "sport": "running",
                        "date": "2026-04-06",
                        "completed": True,
                        "actual_data": {"duration_min": 45, "type": "easy"},
                    }
                ],
            },
        )

    assert response.status_code == 200
    data = response.json()
    required_keys = {
        "agent", "week_reviewed", "completion_rate", "sessions_completed",
        "sessions_planned", "trimp_total", "acwr_before", "acwr_after",
        "adjustments", "next_week_notes",
    }
    assert required_keys.issubset(data.keys())
