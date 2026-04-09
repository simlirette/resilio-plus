"""
Tests unitaires — NutritionCoachAgent

Couvre : héritage BaseAgent, structure de sortie, appel LLM mocké.
"""

from unittest.mock import MagicMock, patch

import pytest

from agents.nutrition_coach.agent import NutritionCoachAgent
from models.views import AgentType


@pytest.fixture
def agent() -> NutritionCoachAgent:
    return NutritionCoachAgent()


@pytest.fixture
def nutrition_view() -> dict:
    return {
        "identity": {
            "first_name": "Simon",
            "age": 32,
            "sex": "M",
            "weight_kg": 78.5,
            "height_cm": 178,
        },
        "goals": {"primary": "run_sub_25_5k", "timeline_weeks": 16, "priority_hierarchy": []},
        "constraints": {"injuries_history": []},
        "nutrition_profile": {
            "tdee_estimated": 2800,
            "macros_target": {"protein_g": 160, "carbs_g": 300, "fat_g": 80},
            "supplements_current": ["creatine_5g"],
            "dietary_restrictions": [],
            "allergies": [],
        },
        "weekly_volumes": {
            "running_km": 22.0,
            "lifting_sessions": 3,
            "swimming_km": 0.0,
            "biking_km": 0.0,
            "total_training_hours": 6.5,
        },
        "current_phase": {"macrocycle": "base_building", "mesocycle_week": 3, "mesocycle_length": 4},
    }


def test_agent_type(agent):
    """NutritionCoachAgent expose le bon agent_type."""
    assert agent.agent_type == AgentType.nutrition_coach


def test_prescribe_returns_seven_daily_plans(agent, nutrition_view):
    """prescribe() produit exactement 7 plans journaliers."""
    with patch.object(agent, "_get_coaching_notes", return_value="Note test."):
        result = agent.prescribe(nutrition_view)
    assert len(result["daily_plans"]) == 7


def test_prescribe_includes_notes_key(agent, nutrition_view):
    """La clé 'notes' est présente dans la sortie (peut être vide si LLM échoue)."""
    with patch.object(agent, "_get_coaching_notes", return_value=""):
        result = agent.prescribe(nutrition_view)
    assert "notes" in result
    assert isinstance(result["notes"], str)


def test_prescribe_calls_llm_with_anthropic(agent, nutrition_view):
    """_get_coaching_notes appelle le client Anthropic avec le bon modèle."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Note clinique LLM.")]

    with patch.object(agent._client.messages, "create", return_value=mock_response) as mock_create:
        note = agent._get_coaching_notes(nutrition_view, {"weekly_summary": {"tdee_estimated": 2800}})

    mock_create.assert_called_once()
    call_kwargs = mock_create.call_args.kwargs
    assert call_kwargs["model"] == "claude-sonnet-4-6"
    assert note == "Note clinique LLM."
