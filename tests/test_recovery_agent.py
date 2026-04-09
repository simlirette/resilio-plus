"""Tests pour RecoveryCoachAgent — S8."""
from unittest.mock import MagicMock, patch


def test_agent_returns_readiness_score(simon_pydantic_state):
    """RecoveryCoachAgent.run() retourne un dict avec 'readiness_score'."""
    from agents.recovery_coach.agent import RecoveryCoachAgent

    with patch("agents.recovery_coach.agent.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_client.messages.create.return_value.content = [
            MagicMock(text="HRV normal. Verdict : VERT.")
        ]
        mock_cls.return_value = mock_client

        agent = RecoveryCoachAgent()
        result = agent.run(simon_pydantic_state)

    assert "readiness_score" in result
    assert isinstance(result["readiness_score"], int | float)


def test_agent_returns_valid_color(simon_pydantic_state):
    """La couleur retournée est bien parmi les valeurs attendues."""
    from agents.recovery_coach.agent import RecoveryCoachAgent

    with patch("agents.recovery_coach.agent.anthropic.Anthropic") as mock_cls:
        mock_cls.return_value.messages.create.return_value.content = [
            MagicMock(text="Verdict : VERT.")
        ]
        agent = RecoveryCoachAgent()
        result = agent.run(simon_pydantic_state)

    assert result["color"] in ("green", "yellow", "red")


def test_agent_appends_notes(simon_pydantic_state):
    """Avec LLM mocké, 'notes' est une str (peut être vide ou non)."""
    from agents.recovery_coach.agent import RecoveryCoachAgent

    with patch("agents.recovery_coach.agent.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_client.messages.create.return_value.content = [
            MagicMock(text="HRV RMSSD à 58ms (baseline). FC repos normale. Verdict : VERT.")
        ]
        mock_cls.return_value = mock_client

        agent = RecoveryCoachAgent()
        result = agent.run(simon_pydantic_state)

    assert isinstance(result.get("notes"), str)


def test_agent_handles_llm_failure(simon_pydantic_state):
    """Si le LLM lève une exception, notes = '' et pas de crash."""
    from agents.recovery_coach.agent import RecoveryCoachAgent

    with patch("agents.recovery_coach.agent.anthropic.Anthropic") as mock_cls:
        mock_cls.return_value.messages.create.side_effect = RuntimeError("API down")

        agent = RecoveryCoachAgent()
        result = agent.run(simon_pydantic_state)

    assert result["notes"] == ""
    assert "readiness_score" in result  # le verdict déterministe est toujours présent
