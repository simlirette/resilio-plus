"""Tests pour RecoveryPrescriber — S8."""


def test_fatigue_state_accepts_hr_rest_today():
    """FatigueState accepte le champ hr_rest_today optionnel."""
    from models.schemas import FatigueState

    state = FatigueState(hr_rest_today=65)
    assert state.hr_rest_today == 65


def test_recovery_view_includes_resting_hr(simon_pydantic_state):
    """_recovery_view expose resting_hr (baseline FC repos) dans identity."""
    from models.views import AgentType, get_agent_view

    view = get_agent_view(simon_pydantic_state, AgentType.recovery_coach)
    assert "resting_hr" in view["identity"]
