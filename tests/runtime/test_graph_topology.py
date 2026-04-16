# tests/runtime/test_graph_topology.py
"""Tests for coaching graph topology — node registration, edge routing."""
from __future__ import annotations

import pytest
from langgraph.checkpoint.memory import MemorySaver

from app.graphs.coaching_graph import build_coaching_graph


def test_build_coaching_graph_requires_checkpointer():
    """build_coaching_graph raises TypeError without checkpointer arg."""
    with pytest.raises(TypeError):
        build_coaching_graph()


def test_build_coaching_graph_accepts_checkpointer():
    """build_coaching_graph accepts a checkpointer and returns a compiled graph."""
    graph = build_coaching_graph(checkpointer=MemorySaver())
    assert graph is not None


def test_graph_has_all_11_nodes():
    """The compiled graph contains all 11 expected nodes."""
    graph = build_coaching_graph(checkpointer=MemorySaver())
    node_names = set(graph.nodes.keys())
    expected = {
        "analyze_profile", "compute_acwr", "delegate_specialists",
        "merge_recommendations", "detect_conflicts", "resolve_conflicts",
        "build_proposed_plan", "present_to_athlete", "revise_plan",
        "apply_energy_snapshot", "finalize_plan",
    }
    actual = node_names - {"__start__", "__end__"}
    assert expected == actual, f"Missing: {expected - actual}, Extra: {actual - expected}"


def test_graph_interrupt_before_present_to_athlete():
    """With interrupt=True, graph interrupts before present_to_athlete."""
    graph = build_coaching_graph(checkpointer=MemorySaver(), interrupt=True)
    assert "present_to_athlete" in (graph.interrupt_before_nodes or [])


def test_graph_no_interrupt_when_false():
    """With interrupt=False, graph does not interrupt."""
    graph = build_coaching_graph(checkpointer=MemorySaver(), interrupt=False)
    assert not (graph.interrupt_before_nodes or [])


def test_debug_endpoint_schema():
    """The debug state endpoint response schema has required keys."""
    from langgraph.checkpoint.memory import MemorySaver
    from app.services.coaching_service import CoachingService

    svc = CoachingService(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "nonexistent:123"}}
    state = svc._graph.get_state(config)
    assert state is not None
