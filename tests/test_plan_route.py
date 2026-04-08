"""
Tests pour POST /api/v1/plan/running.
RunningCoachAgent toujours mocké — aucun appel prescriber ni LLM réel.
"""
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

_MOCK_PLAN = {
    "agent": "running_coach",
    "week": 3,
    "phase": "base_building",
    "tid_model": "pyramidal",
    "total_km_prescribed": 23.1,
    "acwr_running": None,
    "coaching_notes": ["Note de test."],
    "sessions": [],
}


def test_post_running_plan_returns_200(simon_pydantic_state):
    """POST /api/v1/plan/running avec payload valide → 200 + plan JSON."""
    from api.main import app

    client = TestClient(app)

    with patch("api.v1.plan.RunningCoachAgent") as mock_cls:
        mock_agent = MagicMock()
        mock_agent.run.return_value = _MOCK_PLAN
        mock_cls.return_value = mock_agent

        response = client.post(
            "/api/v1/plan/running",
            json={"athlete_state": simon_pydantic_state.model_dump(mode="json")},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["agent"] == "running_coach"
    assert "sessions" in data


def test_post_running_plan_invalid_body():
    """POST avec athlete_state invalide → 422 Unprocessable Entity."""
    from api.main import app

    client = TestClient(app)

    response = client.post(
        "/api/v1/plan/running",
        json={"athlete_state": {"invalid_field": "bad_data"}},
    )

    assert response.status_code == 422


def test_post_running_plan_agent_receives_state(simon_pydantic_state):
    """Le body transmis à RunningCoachAgent.run() est bien un AthleteState valide."""
    from api.main import app
    from models.athlete_state import AthleteState

    client = TestClient(app)
    received_states: list = []

    def capture_run(state):
        received_states.append(state)
        return _MOCK_PLAN

    with patch("api.v1.plan.RunningCoachAgent") as mock_cls:
        mock_agent = MagicMock()
        mock_agent.run.side_effect = capture_run
        mock_cls.return_value = mock_agent

        client.post(
            "/api/v1/plan/running",
            json={"athlete_state": simon_pydantic_state.model_dump(mode="json")},
        )

    assert len(received_states) == 1
    assert isinstance(received_states[0], AthleteState)
