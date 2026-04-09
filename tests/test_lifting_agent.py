"""
Tests pour agents/lifting_coach/agent.py — orchestration prescriber + LLM.
Anthropic est toujours mocké — aucun appel API réel.
"""
from unittest.mock import MagicMock, patch


def _make_mock_message(text: str) -> MagicMock:
    """Crée un faux message Anthropic avec le texte donné."""
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=text)]
    return mock_message


def test_prescribe_mocked_llm(simon_pydantic_state):
    """Agent avec LLM mocké → retourne dict avec 'sessions' et 'coaching_notes'."""
    from agents.lifting_coach.agent import LiftingCoachAgent

    mock_msg = _make_mock_message("- Note technique 1.\n- Note technique 2.")

    with patch("agents.lifting_coach.agent.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_msg
        mock_cls.return_value = mock_client

        agent = LiftingCoachAgent()
        plan = agent.run(simon_pydantic_state)

    assert isinstance(plan, dict)
    assert "sessions" in plan
    assert len(plan["sessions"]) > 0
    assert "coaching_notes" in plan
    assert isinstance(plan["coaching_notes"], list)


def test_output_schema_valid(simon_pydantic_state):
    """Chaque session a hevy_workout.id, .exercises, et .exercises[].sets."""
    from agents.lifting_coach.agent import LiftingCoachAgent

    mock_msg = _make_mock_message("- Note.")

    with patch("agents.lifting_coach.agent.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_msg
        mock_cls.return_value = mock_client

        plan = LiftingCoachAgent().run(simon_pydantic_state)

    for session in plan["sessions"]:
        hw = session["hevy_workout"]
        assert "id" in hw, f"Session manque 'id': {hw}"
        assert "exercises" in hw, f"Session manque 'exercises': {hw}"
        for ex in hw["exercises"]:
            assert "sets" in ex, f"Exercise manque 'sets': {ex}"


def test_coaching_notes_merged(simon_pydantic_state):
    """Les coaching_notes du LLM sont parsées (sans tirets) et incluses dans le plan."""
    from agents.lifting_coach.agent import LiftingCoachAgent

    mock_msg = _make_mock_message(
        "- Réduire le volume quadriceps.\n- Prioriser le RIR 2 sur le développé.\n- Core activé."
    )

    with patch("agents.lifting_coach.agent.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_msg
        mock_cls.return_value = mock_client

        plan = LiftingCoachAgent().run(simon_pydantic_state)

    notes = plan["coaching_notes"]
    assert isinstance(notes, list)
    assert len(notes) >= 1
    assert all(not note.startswith("-") for note in notes), (
        "Les tirets Markdown doivent être retirés du parsing"
    )


def test_llm_error_returns_empty_notes(simon_pydantic_state):
    """Si le LLM lève une exception, coaching_notes = [] (plan toujours retourné)."""
    from agents.lifting_coach.agent import LiftingCoachAgent

    with patch("agents.lifting_coach.agent.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("API overloaded")
        mock_cls.return_value = mock_client

        plan = LiftingCoachAgent().run(simon_pydantic_state)

    assert "sessions" in plan
    assert plan["coaching_notes"] == []
