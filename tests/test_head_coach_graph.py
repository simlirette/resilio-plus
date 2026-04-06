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
