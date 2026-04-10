"""Tests for POST /api/v1/workflow routes. Graph always mocked — no real LangGraph run."""
from unittest.mock import MagicMock, patch

_MOCK_UNIFIED_PLAN = {
    "agent": "head_coach",
    "week": 3,
    "phase": "base_building",
    "sessions": [],
    "acwr": 1.05,
    "conflicts_resolved": [],
    "coaching_summary": "",
}


def test_post_plan_returns_200_complete(simon_pydantic_state):
    """POST /api/v1/workflow/plan with healthy state → 200 + unified_plan."""
    from fastapi.testclient import TestClient

    from api.main import app

    client = TestClient(app)

    mock_invoke_result = {**simon_pydantic_state.model_dump(mode="json"), "unified_plan": _MOCK_UNIFIED_PLAN}
    mock_graph_state = MagicMock()
    mock_graph_state.next = []  # No pending nodes → complete

    with patch("api.v1.workflow.head_coach_graph") as mock_graph:
        mock_graph.invoke.return_value = mock_invoke_result
        mock_graph.get_state.return_value = mock_graph_state

        response = client.post(
            "/api/v1/workflow/plan",
            json={"athlete_state": simon_pydantic_state.model_dump(mode="json")},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "complete"
    assert "unified_plan" in data


def test_post_plan_returns_202_on_interrupt(simon_pydantic_state):
    """POST /api/v1/workflow/plan when graph is interrupted → 202 + thread_id."""
    from fastapi.testclient import TestClient

    from api.main import app

    client = TestClient(app)

    mock_invoke_result = {
        **simon_pydantic_state.model_dump(mode="json"),
        "pending_decision": {"conflict_id": "PLAN_CONFIRMATION", "status": "awaiting_user_input"},
    }
    mock_graph_state = MagicMock()
    mock_graph_state.next = ["present_plan"]  # Graph still has pending nodes → interrupted

    with patch("api.v1.workflow.head_coach_graph") as mock_graph:
        mock_graph.invoke.return_value = mock_invoke_result
        mock_graph.get_state.return_value = mock_graph_state

        response = client.post(
            "/api/v1/workflow/plan",
            json={"athlete_state": simon_pydantic_state.model_dump(mode="json")},
        )

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "awaiting_decision"
    assert "thread_id" in data


def test_post_plan_invalid_body():
    """POST /api/v1/workflow/plan with invalid athlete_state → 422."""
    from fastapi.testclient import TestClient

    from api.main import app

    client = TestClient(app)

    response = client.post(
        "/api/v1/workflow/plan",
        json={"athlete_state": {"invalid_field": "bad"}},
    )

    assert response.status_code == 422


def test_post_resume_plan_complete(simon_pydantic_state):
    """POST /api/v1/workflow/plan/resume with valid thread_id → 200 complete."""
    from fastapi.testclient import TestClient

    from api.main import app

    client = TestClient(app)

    # First call: graph is interrupted
    mock_state_interrupted = MagicMock()
    mock_state_interrupted.next = ["present_plan"]

    # Second call: graph is complete
    mock_state_complete = MagicMock()
    mock_state_complete.next = []

    mock_invoke_result = {**simon_pydantic_state.model_dump(mode="json"), "unified_plan": _MOCK_UNIFIED_PLAN}

    with patch("api.v1.workflow.head_coach_graph") as mock_graph:
        mock_graph.get_state.side_effect = [mock_state_interrupted, mock_state_complete]
        mock_graph.invoke.return_value = mock_invoke_result

        response = client.post(
            "/api/v1/workflow/plan/resume",
            json={"thread_id": "test-thread-123", "user_decision": "CONFIRM"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "complete"
