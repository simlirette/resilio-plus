"""Tests pour BaseAgent ABC et les stubs Running/Lifting Coach (S5)."""


def test_running_coach_run_returns_plan(simon_pydantic_state):
    """RunningCoachAgent.run() retourne un dict avec 'sessions'."""
    from agents.running_coach.agent import RunningCoachAgent

    agent = RunningCoachAgent()
    plan = agent.run(simon_pydantic_state)

    assert isinstance(plan, dict)
    assert "sessions" in plan
    assert len(plan["sessions"]) > 0
    assert plan["agent"] == "running_coach"


def test_lifting_coach_run_returns_plan(simon_pydantic_state):
    """LiftingCoachAgent.run() retourne un dict avec 'sessions'."""
    from agents.lifting_coach.agent import LiftingCoachAgent

    agent = LiftingCoachAgent()
    plan = agent.run(simon_pydantic_state)

    assert isinstance(plan, dict)
    assert "sessions" in plan
    assert len(plan["sessions"]) > 0
    assert plan["agent"] == "lifting_coach"


def test_agent_uses_get_agent_view(simon_pydantic_state):
    """La vue Running ne contient pas lifting_profile (filtrage correct)."""
    from models.views import AgentType, get_agent_view

    view = get_agent_view(simon_pydantic_state, AgentType.running_coach)
    assert "running_profile" in view
    assert "lifting_profile" not in view
