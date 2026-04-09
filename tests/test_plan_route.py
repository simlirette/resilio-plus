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


_MOCK_LIFTING_PLAN = {
    "agent": "lifting_coach",
    "week": 3,
    "phase": "base_building",
    "dup_model": "DUP 3-way (Hypertrophie / Force / Mixte)",
    "cns_tier3_allowed": True,
    "coaching_notes": ["Note de test."],
    "sessions": [],
}


def test_post_lifting_plan_returns_200(simon_pydantic_state):
    """POST /api/v1/plan/lifting avec payload valide → 200 + plan JSON."""
    from api.main import app

    client = TestClient(app)

    with patch("api.v1.plan.LiftingCoachAgent") as mock_cls:
        mock_agent = MagicMock()
        mock_agent.run.return_value = _MOCK_LIFTING_PLAN
        mock_cls.return_value = mock_agent

        response = client.post(
            "/api/v1/plan/lifting",
            json={"athlete_state": simon_pydantic_state.model_dump(mode="json")},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["agent"] == "lifting_coach"
    assert "sessions" in data


def test_post_lifting_plan_invalid_body():
    """POST avec athlete_state invalide → 422 Unprocessable Entity."""
    from api.main import app

    client = TestClient(app)

    response = client.post(
        "/api/v1/plan/lifting",
        json={"athlete_state": {"invalid_field": "bad_data"}},
    )

    assert response.status_code == 422


def test_post_lifting_plan_agent_receives_state(simon_pydantic_state):
    """Le body transmis à LiftingCoachAgent.run() est bien un AthleteState valide."""
    from api.main import app
    from models.athlete_state import AthleteState

    client = TestClient(app)
    received_states: list = []

    def capture_run(state):
        received_states.append(state)
        return _MOCK_LIFTING_PLAN

    with patch("api.v1.plan.LiftingCoachAgent") as mock_cls:
        mock_agent = MagicMock()
        mock_agent.run.side_effect = capture_run
        mock_cls.return_value = mock_agent

        client.post(
            "/api/v1/plan/lifting",
            json={"athlete_state": simon_pydantic_state.model_dump(mode="json")},
        )

    assert len(received_states) == 1
    assert isinstance(received_states[0], AthleteState)


_MOCK_RECOVERY_VERDICT = {
    "agent": "recovery_coach",
    "readiness_score": 68.0,
    "color": "yellow",
    "factors": {
        "hrv_score": 50.0,
        "sleep_score": 80.0,
        "acwr_score": 70.0,
        "hr_rest_score": 70.0,
        "subjective_score": 70.0,
    },
    "modification_params": {
        "intensity_reduction_pct": 15,
        "tier_max": 1,
        "volume_reduction_pct": 0,
    },
    "overtraining_alert": False,
    "notes": "Note de test.",
}


def test_post_recovery_plan_returns_200(simon_pydantic_state):
    """POST /api/v1/plan/recovery avec payload valide → 200 + verdict JSON."""
    from api.main import app

    client = TestClient(app)

    with patch("api.v1.plan.RecoveryCoachAgent") as mock_cls:
        mock_agent = MagicMock()
        mock_agent.run.return_value = _MOCK_RECOVERY_VERDICT
        mock_cls.return_value = mock_agent

        response = client.post(
            "/api/v1/plan/recovery",
            json={"athlete_state": simon_pydantic_state.model_dump(mode="json")},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["agent"] == "recovery_coach"
    assert "readiness_score" in data


def test_post_recovery_plan_invalid_body():
    """POST avec athlete_state invalide → 422 Unprocessable Entity."""
    from api.main import app

    client = TestClient(app)

    response = client.post(
        "/api/v1/plan/recovery",
        json={"athlete_state": {"invalid_field": "bad_data"}},
    )

    assert response.status_code == 422


def test_post_recovery_plan_agent_receives_state(simon_pydantic_state):
    """Le body transmis à RecoveryCoachAgent.run() est bien un AthleteState valide."""
    from api.main import app
    from models.athlete_state import AthleteState

    client = TestClient(app)
    received_states: list = []

    def capture_run(state):
        received_states.append(state)
        return _MOCK_RECOVERY_VERDICT

    with patch("api.v1.plan.RecoveryCoachAgent") as mock_cls:
        mock_agent = MagicMock()
        mock_agent.run.side_effect = capture_run
        mock_cls.return_value = mock_agent

        client.post(
            "/api/v1/plan/recovery",
            json={"athlete_state": simon_pydantic_state.model_dump(mode="json")},
        )

    assert len(received_states) == 1
    assert isinstance(received_states[0], AthleteState)


_MOCK_NUTRITION_PLAN = {
    "agent": "nutrition_coach",
    "weekly_summary": {
        "tdee_estimated": 2700,
        "avg_macros_g": {"protein_g": 157, "carbs_g": 353, "fat_g": 71},
        "active_supplements": ["creatine_5g"],
        "dietary_restrictions": [],
    },
    "daily_plans": [
        {
            "day": "Monday", "day_type": "lifting_only",
            "kcal_target": 2700, "macros_g": {"protein_g": 157, "carbs_g": 353, "fat_g": 71},
            "fiber_g_target": 30, "hydration_ml": 3344, "timing": {},
        }
    ] * 7,
    "notes": "Note de test.",
}


def test_post_nutrition_plan_returns_200(simon_pydantic_state):
    """POST /api/v1/plan/nutrition avec payload valide → 200 + plan JSON."""
    from api.main import app

    client = TestClient(app)

    with patch("api.v1.plan.NutritionCoachAgent") as mock_cls:
        mock_agent = MagicMock()
        mock_agent.run.return_value = _MOCK_NUTRITION_PLAN
        mock_cls.return_value = mock_agent

        response = client.post(
            "/api/v1/plan/nutrition",
            json={"athlete_state": simon_pydantic_state.model_dump(mode="json")},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["agent"] == "nutrition_coach"
    assert "daily_plans" in data


def test_post_nutrition_plan_invalid_body():
    """POST avec athlete_state invalide → 422 Unprocessable Entity."""
    from api.main import app

    client = TestClient(app)

    response = client.post(
        "/api/v1/plan/nutrition",
        json={"athlete_state": {"invalid_field": "bad_data"}},
    )

    assert response.status_code == 422


_MOCK_SWIMMING_PLAN = {
    "agent": "swimming_coach",
    "technique_level": "beginner",
    "css_sec_per_100m": 150.0,
    "weekly_volume_km": 0.0,
    "sessions": [],
    "coaching_notes": [],
    "notes": "Note test.",
}


def test_post_swimming_plan_returns_200(simon_pydantic_state):
    """POST /api/v1/plan/swimming avec payload valide → 200 + plan JSON."""
    from api.main import app

    client = TestClient(app)

    with patch("api.v1.plan.SwimmingCoachAgent") as mock_cls:
        mock_agent = MagicMock()
        mock_agent.run.return_value = _MOCK_SWIMMING_PLAN
        mock_cls.return_value = mock_agent

        response = client.post(
            "/api/v1/plan/swimming",
            json={"athlete_state": simon_pydantic_state.model_dump(mode="json")},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["agent"] == "swimming_coach"
    assert "sessions" in data


def test_post_swimming_plan_invalid_body():
    """POST avec athlete_state invalide → 422 Unprocessable Entity."""
    from api.main import app

    client = TestClient(app)

    response = client.post(
        "/api/v1/plan/swimming",
        json={"athlete_state": {"invalid_field": "bad_data"}},
    )

    assert response.status_code == 422
