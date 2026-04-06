# tests/test_athlete_state.py
"""
Tests pour AthleteState (Pydantic LangGraph state).
IMPORTANT : ce n'est PAS models.database.AthleteState (SQLAlchemy).
"""
from models.schemas import AthleteStateSchema


def test_athlete_state_extends_schema(simon_pydantic_state):
    """AthleteState hérite de AthleteStateSchema — a tous ses champs."""
    from models.athlete_state import AthleteState

    assert isinstance(simon_pydantic_state, AthleteState)
    assert isinstance(simon_pydantic_state, AthleteStateSchema)
    # Champs hérités de AthleteStateSchema
    assert simon_pydantic_state.profile is not None
    assert simon_pydantic_state.fatigue is not None
    assert simon_pydantic_state.running_profile is not None


def test_athlete_state_mutable(simon_pydantic_state):
    """AthleteState est mutable (frozen=False) — la mutation directe fonctionne."""
    simon_pydantic_state.pending_decision = {
        "conflict_id": "TEST",
        "status": "awaiting_user_input",
    }
    assert simon_pydantic_state.pending_decision["conflict_id"] == "TEST"

    simon_pydantic_state.acwr_computed = 1.25
    assert simon_pydantic_state.acwr_computed == 1.25


def test_athlete_state_defaults(simon_pydantic_state):
    """AthleteState a des valeurs par défaut correctes pour les champs d'orchestration."""
    assert simon_pydantic_state.pending_conflicts == []
    assert simon_pydantic_state.partial_plans == {}
    assert simon_pydantic_state.acwr_computed is None
    assert simon_pydantic_state.resolution_iterations == 0
    assert simon_pydantic_state.conflicts_resolved is True
