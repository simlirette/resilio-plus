"""
Tests d'intégration du Head Coach graph LangGraph.
Vérifie que le graph compile et que les 3 nœuds TODO S5 fonctionnent.
"""


def test_graph_compiles():
    """build_head_coach_graph() s'exécute sans erreur d'import ou de compilation."""
    from agents.head_coach.graph import build_head_coach_graph

    g = build_head_coach_graph()
    assert g is not None


def test_node_load_computes_acwr(simon_pydantic_state):
    """node_load_athlete_state calcule acwr_computed si daily_loads présents."""
    from agents.head_coach.graph import node_load_athlete_state

    # Injecter 28 jours de charge constante → ACWR ≈ 1.0
    simon_pydantic_state.constraint_matrix.schedule["_daily_loads_28d"] = [100.0] * 28
    result = node_load_athlete_state(simon_pydantic_state)

    assert result.acwr_computed is not None
    assert result.acwr_computed > 0.0


def test_node_detect_no_conflicts(simon_pydantic_state):
    """node_detect_conflicts ne crée pas de conflits si ACWR safe et schedule vide."""
    from agents.head_coach.graph import node_detect_conflicts

    simon_pydantic_state.acwr_computed = 1.0
    simon_pydantic_state.constraint_matrix.schedule = {}

    result = node_detect_conflicts(simon_pydantic_state)

    assert result.pending_conflicts == []
    assert result.conflicts_resolved is True


def test_node_detect_acwr_danger(simon_pydantic_state):
    """node_detect_conflicts crée un conflit 'danger' si ACWR > 1.5."""
    from agents.head_coach.graph import node_detect_conflicts

    simon_pydantic_state.acwr_computed = 1.6
    simon_pydantic_state.constraint_matrix.schedule = {}

    result = node_detect_conflicts(simon_pydantic_state)

    danger = [c for c in result.pending_conflicts if c["severity"] == "danger"]
    assert len(danger) == 1
    assert danger[0]["layer"] == "fatigue"
    assert danger[0]["acwr"] == 1.6


def test_node_delegate_dispatches_swimming(simon_pydantic_state):
    """node_delegate_to_agents appelle SwimmingCoachAgent si active_sports=[swimming]."""
    from unittest.mock import MagicMock, patch
    from agents.head_coach.graph import node_delegate_to_agents

    simon_pydantic_state.profile.active_sports = ["swimming"]
    mock_plan = {"agent": "swimming_coach", "sessions": []}

    with patch("agents.head_coach.graph._AGENT_REGISTRY", {
        "swimming": MagicMock(run=MagicMock(return_value=mock_plan))
    }):
        result = node_delegate_to_agents(simon_pydantic_state)

    assert "swimming" in result.partial_plans
    assert result.partial_plans["swimming"]["agent"] == "swimming_coach"


def test_node_delegate_dispatches_biking(simon_pydantic_state):
    """node_delegate_to_agents appelle BikingCoachAgent si active_sports=[biking]."""
    from unittest.mock import MagicMock, patch
    from agents.head_coach.graph import node_delegate_to_agents

    simon_pydantic_state.profile.active_sports = ["biking"]
    mock_plan = {"agent": "biking_coach", "sessions": []}

    with patch("agents.head_coach.graph._AGENT_REGISTRY", {
        "biking": MagicMock(run=MagicMock(return_value=mock_plan))
    }):
        result = node_delegate_to_agents(simon_pydantic_state)

    assert "biking" in result.partial_plans
    assert result.partial_plans["biking"]["agent"] == "biking_coach"


def test_node_nutrition_prescription_stores_result(simon_pydantic_state):
    """node_nutrition_prescription stocke le plan nutrition dans unified_plan."""
    from unittest.mock import MagicMock, patch
    from agents.head_coach.graph import node_nutrition_prescription

    simon_pydantic_state.unified_plan = {"running": {}, "lifting": {}}
    mock_plan = {"agent": "nutrition_coach", "daily_plans": [], "notes": ""}

    with patch("agents.head_coach.graph.NutritionCoachAgent") as mock_cls:
        mock_agent = MagicMock()
        mock_agent.run.return_value = mock_plan
        mock_cls.return_value = mock_agent

        result = node_nutrition_prescription(simon_pydantic_state)

    assert "nutrition" in result.unified_plan
    assert result.unified_plan["nutrition"]["agent"] == "nutrition_coach"


def test_node_nutrition_prescription_handles_none_unified_plan(simon_pydantic_state):
    """node_nutrition_prescription initialise unified_plan si None avant d'y écrire."""
    from unittest.mock import MagicMock, patch
    from agents.head_coach.graph import node_nutrition_prescription

    simon_pydantic_state.unified_plan = None
    mock_plan = {"agent": "nutrition_coach", "daily_plans": [], "notes": ""}

    with patch("agents.head_coach.graph.NutritionCoachAgent") as mock_cls:
        mock_agent = MagicMock()
        mock_agent.run.return_value = mock_plan
        mock_cls.return_value = mock_agent

        result = node_nutrition_prescription(simon_pydantic_state)

    assert result.unified_plan is not None
    assert "nutrition" in result.unified_plan
