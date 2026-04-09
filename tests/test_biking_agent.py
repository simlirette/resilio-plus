"""
Tests unitaires — BikingCoachAgent

Couvre : héritage BaseAgent, agent_type, structure sortie, appel LLM mocké.
"""
from unittest.mock import MagicMock, patch

import pytest

from models.views import AgentType


def test_agent_type():
    """agent_type doit être AgentType.biking_coach."""
    from agents.biking_coach.agent import BikingCoachAgent

    with patch("agents.biking_coach.agent.anthropic.Anthropic"):
        agent = BikingCoachAgent()

    assert agent.agent_type == AgentType.biking_coach


def test_prescribe_returns_notes_key():
    """prescribe() retourne bien une clé 'notes' (str)."""
    from agents.biking_coach.agent import BikingCoachAgent

    with patch("agents.biking_coach.agent.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_client.messages.create.return_value.content = [
            MagicMock(text="FTP non défini. 0 session planifiée.")
        ]
        mock_cls.return_value = mock_client

        agent = BikingCoachAgent()
        view = {
            "biking_profile": {
                "ftp_watts": None,
                "weekly_volume_km": 0.0,
            }
        }
        result = agent.prescribe(view)

    assert "notes" in result
    assert isinstance(result["notes"], str)


def test_prescribe_sessions_structure():
    """prescribe() retourne une clé 'sessions' (liste)."""
    from agents.biking_coach.agent import BikingCoachAgent

    with patch("agents.biking_coach.agent.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_client.messages.create.return_value.content = [
            MagicMock(text="Note clinique vélo.")
        ]
        mock_cls.return_value = mock_client

        agent = BikingCoachAgent()
        view = {
            "biking_profile": {
                "ftp_watts": 250.0,
                "weekly_volume_km": 50.0,
            }
        }
        result = agent.prescribe(view)

    assert "sessions" in result
    assert isinstance(result["sessions"], list)
    assert len(result["sessions"]) == 2


def test_get_coaching_notes_calls_llm():
    """_get_coaching_notes() appelle client.messages.create avec model='claude-sonnet-4-6'."""
    from agents.biking_coach.agent import BikingCoachAgent

    with patch("agents.biking_coach.agent.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_client.messages.create.return_value.content = [
            MagicMock(text="FTP 250W. 2 sessions planifiées.")
        ]
        mock_cls.return_value = mock_client

        agent = BikingCoachAgent()
        view = {
            "biking_profile": {
                "ftp_watts": 250.0,
                "weekly_volume_km": 50.0,
            }
        }
        plan = {
            "ftp_watts": 250.0,
            "weekly_volume_km": 50.0,
            "sessions": [
                {"session_type": "endurance"},
                {"session_type": "tempo"},
            ],
        }
        agent._get_coaching_notes(view, plan)

    mock_client.messages.create.assert_called_once()
    call_kwargs = mock_client.messages.create.call_args
    assert call_kwargs.kwargs["model"] == "claude-sonnet-4-6"


def test_agent_handles_llm_failure():
    """Si le LLM lève une exception, notes='' et pas de crash."""
    from agents.biking_coach.agent import BikingCoachAgent

    with patch("agents.biking_coach.agent.anthropic.Anthropic") as mock_cls:
        mock_cls.return_value.messages.create.side_effect = RuntimeError("API down")

        agent = BikingCoachAgent()
        view = {
            "biking_profile": {
                "ftp_watts": None,
                "weekly_volume_km": 0.0,
            }
        }
        result = agent.prescribe(view)

    assert result["notes"] == ""
    assert result["agent"] == "biking_coach"
