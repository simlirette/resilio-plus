"""
Tests pour agents/running_coach/agent.py — orchestration prescriber + LLM.
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
    from agents.running_coach.agent import RunningCoachAgent

    mock_msg = _make_mock_message(
        "- Maintenir la cadence à 170 pas/min.\n- Hydratation avant la séance tempo."
    )

    with patch("agents.running_coach.agent.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_msg
        mock_cls.return_value = mock_client

        agent = RunningCoachAgent()
        plan = agent.run(simon_pydantic_state)

    assert isinstance(plan, dict)
    assert "sessions" in plan
    assert len(plan["sessions"]) > 0
    assert "coaching_notes" in plan
    assert isinstance(plan["coaching_notes"], list)


def test_output_schema_valid(simon_pydantic_state):
    """Chaque session du plan a run_workout.id, .blocks, et .sync_target."""
    from agents.running_coach.agent import RunningCoachAgent

    mock_msg = _make_mock_message("- Note 1.\n- Note 2.")

    with patch("agents.running_coach.agent.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_msg
        mock_cls.return_value = mock_client

        agent = RunningCoachAgent()
        plan = agent.run(simon_pydantic_state)

    for session in plan["sessions"]:
        rw = session["run_workout"]
        assert "id" in rw, f"Session manque 'id': {rw}"
        assert "blocks" in rw, f"Session manque 'blocks': {rw}"
        assert "sync_target" in rw, f"Session manque 'sync_target': {rw}"
        assert rw["sync_target"] == "garmin_structured_workout"


def test_coaching_notes_merged(simon_pydantic_state):
    """Les coaching_notes du LLM sont parsées et incluses dans le plan."""
    from agents.running_coach.agent import RunningCoachAgent

    mock_msg = _make_mock_message(
        "- Maintenir la cadence.\n- Hydratation requise.\n- Éviter les collines en deload."
    )

    with patch("agents.running_coach.agent.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_msg
        mock_cls.return_value = mock_client

        agent = RunningCoachAgent()
        plan = agent.run(simon_pydantic_state)

    notes = plan["coaching_notes"]
    assert isinstance(notes, list)
    assert len(notes) >= 1
    # Les tirets de Markdown ont été retirés du parsing
    assert all(not note.startswith("-") for note in notes)


def test_llm_error_returns_empty_notes(simon_pydantic_state):
    """Si le LLM lève une exception, coaching_notes = [] (plan toujours retourné)."""
    from agents.running_coach.agent import RunningCoachAgent

    with patch("agents.running_coach.agent.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("API overloaded")
        mock_cls.return_value = mock_client

        agent = RunningCoachAgent()
        plan = agent.run(simon_pydantic_state)

    assert "sessions" in plan
    assert plan["coaching_notes"] == []
