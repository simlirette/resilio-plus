"""
Tests pour SwimmingCoachAgent — pattern BaseAgent + LLM mock.
"""
from unittest.mock import MagicMock, patch

import pytest

from models.views import AgentType


def test_agent_type():
    """agent_type doit être AgentType.swimming_coach."""
    from agents.swimming_coach.agent import SwimmingCoachAgent

    with patch("agents.swimming_coach.agent.anthropic.Anthropic"):
        agent = SwimmingCoachAgent()

    assert agent.agent_type == AgentType.swimming_coach


def test_prescribe_returns_notes_key(simon_pydantic_state):
    """prescribe() retourne bien une clé 'notes' (str)."""
    from agents.swimming_coach.agent import SwimmingCoachAgent

    with patch("agents.swimming_coach.agent.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_client.messages.create.return_value.content = [
            MagicMock(text="CSS 150 s/100m. 0 sessions planifiées.")
        ]
        mock_cls.return_value = mock_client

        agent = SwimmingCoachAgent()
        # Use the swimming view directly
        view = {
            "swimming_profile": {
                "reference_times": {},
                "technique_level": "beginner",
                "weekly_volume_km": 0.0,
            }
        }
        result = agent.prescribe(view)

    assert "notes" in result
    assert isinstance(result["notes"], str)


def test_prescribe_sessions_structure(simon_pydantic_state):
    """prescribe() retourne une clé 'sessions' liste."""
    from agents.swimming_coach.agent import SwimmingCoachAgent

    with patch("agents.swimming_coach.agent.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_client.messages.create.return_value.content = [
            MagicMock(text="Note clinique.")
        ]
        mock_cls.return_value = mock_client

        agent = SwimmingCoachAgent()
        view = {
            "swimming_profile": {
                "reference_times": {},
                "technique_level": "beginner",
                "weekly_volume_km": 2.0,
            }
        }
        result = agent.prescribe(view)

    assert "sessions" in result
    assert isinstance(result["sessions"], list)
    assert len(result["sessions"]) == 2


def test_get_coaching_notes_calls_llm(simon_pydantic_state):
    """_get_coaching_notes() appelle client.messages.create avec model='claude-sonnet-4-6'."""
    from agents.swimming_coach.agent import SwimmingCoachAgent

    with patch("agents.swimming_coach.agent.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_client.messages.create.return_value.content = [
            MagicMock(text="CSS 150 s/100m.")
        ]
        mock_cls.return_value = mock_client

        agent = SwimmingCoachAgent()
        view = {
            "swimming_profile": {
                "reference_times": {},
                "technique_level": "beginner",
                "weekly_volume_km": 1.0,
            }
        }
        plan = {
            "css_sec_per_100m": 150.0,
            "technique_level": "beginner",
            "sessions": [],
        }
        agent._get_coaching_notes(view, plan)

    mock_client.messages.create.assert_called_once()
    call_kwargs = mock_client.messages.create.call_args
    assert call_kwargs.kwargs["model"] == "claude-sonnet-4-6"


def test_agent_handles_llm_failure(simon_pydantic_state):
    """Si le LLM lève une exception, notes='' et pas de crash."""
    from agents.swimming_coach.agent import SwimmingCoachAgent

    with patch("agents.swimming_coach.agent.anthropic.Anthropic") as mock_cls:
        mock_cls.return_value.messages.create.side_effect = RuntimeError("API down")

        agent = SwimmingCoachAgent()
        view = {
            "swimming_profile": {
                "reference_times": {},
                "technique_level": "beginner",
                "weekly_volume_km": 0.0,
            }
        }
        result = agent.prescribe(view)

    assert result["notes"] == ""
    assert result["agent"] == "swimming_coach"
