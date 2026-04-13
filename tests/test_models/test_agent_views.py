"""Tests for get_agent_view() — all 8 agents, parametric matrix validation."""
import pytest

from app.models.athlete_state import AgentView, get_agent_view

ALL_SECTIONS = frozenset({
    "profile", "metrics", "connectors", "plan",
    "energy", "recovery", "hormonal", "allostatic", "journal",
})

_EXPECTED: list[tuple[str, frozenset[str]]] = [
    ("head_coach",  frozenset(ALL_SECTIONS)),
    ("running",     frozenset({"profile", "metrics", "connectors", "plan", "hormonal"})),
    ("lifting",     frozenset({"profile", "metrics", "connectors", "plan", "hormonal"})),
    ("swimming",    frozenset({"profile", "metrics", "connectors", "plan"})),
    ("biking",      frozenset({"profile", "metrics", "connectors", "plan"})),
    ("nutrition",   frozenset({"profile", "plan", "energy", "hormonal"})),
    ("recovery",    frozenset({"profile", "metrics", "connectors", "plan", "energy", "recovery", "hormonal", "allostatic", "journal"})),
    ("energy",      frozenset({"profile", "metrics", "energy", "recovery", "hormonal", "allostatic", "journal"})),
]


@pytest.mark.parametrize("agent,expected_sections", _EXPECTED)
def test_agent_view_sections_present(agent, expected_sections, full_state):
    view = get_agent_view(full_state, agent)
    assert isinstance(view, AgentView)
    assert view.agent == agent
    for section in expected_sections:
        assert getattr(view, section) is not None, (
            f"Agent '{agent}' should have section '{section}' but it is None"
        )


@pytest.mark.parametrize("agent,expected_sections", _EXPECTED)
def test_agent_view_sections_absent(agent, expected_sections, full_state):
    view = get_agent_view(full_state, agent)
    for section in ALL_SECTIONS - expected_sections:
        assert getattr(view, section) is None, (
            f"Agent '{agent}' should NOT have section '{section}' but it is present"
        )


def test_unknown_agent_returns_empty_view(full_state):
    view = get_agent_view(full_state, "unknown_agent")
    assert isinstance(view, AgentView)
    assert view.agent == "unknown_agent"
    for section in ALL_SECTIONS:
        assert getattr(view, section) is None


def test_agent_view_is_pydantic_model(full_state):
    """AgentView must be a Pydantic BaseModel (serializable to JSON)."""
    view = get_agent_view(full_state, "running")
    dumped = view.model_dump()
    assert "profile" in dumped
    assert "agent" in dumped


def test_head_coach_gets_all_sections(full_state):
    view = get_agent_view(full_state, "head_coach")
    for section in ALL_SECTIONS:
        assert getattr(view, section) is not None
