"""The conflict path must terminate.

`resolve_conflicts_node` is deliberately a no-op — its own docstring says
arbitration happens in `build_proposed_plan` — yet the graph routed it back to
`detect_conflicts`, which recomputes conflicts from unchanged recommendations
and reaches the same verdict. Any critical conflict therefore spun until
LangGraph's recursion limit killed the run.

It stayed hidden because ACWR was pinned at 0.00 and the agents, receiving no
connector data, never produced a critical conflict. Wiring real data in made it
fire on the first realistic plan.
"""
from __future__ import annotations

from app.graphs.coaching_graph import build_coaching_graph
from langgraph.checkpoint.memory import MemorySaver


def _edges() -> list[tuple[str, str, bool]]:
    graph = build_coaching_graph(checkpointer=MemorySaver())
    return [(e.source, e.target, e.conditional) for e in graph.get_graph().edges]


def test_resolve_conflicts_does_not_route_back_to_detection() -> None:
    back_edges = [
        (s, t)
        for s, t, _ in _edges()
        if s == "resolve_conflicts" and t == "detect_conflicts"
    ]
    assert back_edges == [], (
        "resolve_conflicts makes no state change, so returning to detect_conflicts "
        "cannot converge - it loops until the recursion limit"
    )


def test_resolve_conflicts_moves_the_plan_forward() -> None:
    targets = {t for s, t, _ in _edges() if s == "resolve_conflicts"}
    assert targets == {"build_proposed_plan"}


def test_detection_still_routes_both_ways() -> None:
    targets = {t for s, t, _ in _edges() if s == "detect_conflicts"}
    assert targets == {"resolve_conflicts", "build_proposed_plan"}


def test_the_conflict_path_has_no_cycle() -> None:
    """Walk forward from detect_conflicts; it must reach an end, not itself."""
    edges = _edges()
    adjacency: dict[str, set[str]] = {}
    for source, target, _ in edges:
        adjacency.setdefault(source, set()).add(target)

    seen: set[str] = set()
    frontier = ["detect_conflicts"]
    while frontier:
        node = frontier.pop()
        if node in seen:
            continue
        seen.add(node)
        # present_to_athlete is where the graph parks for the human; the revise
        # loop beyond it is bounded by _after_revise and is not under test here.
        if node == "present_to_athlete":
            continue
        frontier.extend(adjacency.get(node, ()))

    assert "detect_conflicts" not in {
        target
        for source in seen
        for target in adjacency.get(source, ())
        if source != "merge_recommendations"
    }, "something downstream of detection routes back into it"
