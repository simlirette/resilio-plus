"""CoachingService — wraps the LangGraph coaching graph.

Public API:
    service = CoachingService()
    thread_id, proposed_dict = service.create_plan(athlete_id, athlete_dict, load_history, db)
    final_dict = service.resume_plan(thread_id, approved, feedback, db)
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from ..graphs.coaching_graph import build_coaching_graph
from ..graphs.state import AthleteCoachingState


class CoachingService:
    """Wraps the coaching LangGraph graph."""

    def __init__(self) -> None:
        self._graph = build_coaching_graph(interrupt=True)

    def create_plan(
        self,
        athlete_id: str,
        athlete_dict: dict[str, Any],
        load_history: list[float],
        db: Session,
    ) -> tuple[str, dict[str, Any] | None]:
        """Run graph until present_to_athlete interrupt.

        Returns (thread_id, proposed_plan_dict).
        """
        thread_id = f"{athlete_id}:{str(uuid.uuid4())}"
        config = {"configurable": {"thread_id": thread_id, "db": db}}

        initial_state: AthleteCoachingState = {
            "athlete_id": athlete_id,
            "athlete_dict": athlete_dict,
            "load_history": load_history,
            "budgets": {},
            "recommendations_dicts": [],
            "acwr_dict": None,
            "conflicts_dicts": [],
            "proposed_plan_dict": None,
            "energy_snapshot_dict": None,
            "human_approved": False,
            "human_feedback": None,
            "final_plan_dict": None,
            "messages": [],
        }

        result = self._graph.invoke(initial_state, config=config)
        return thread_id, result.get("proposed_plan_dict")

    def resume_plan(
        self,
        thread_id: str,
        approved: bool,
        feedback: str | None,
        db: Session,
    ) -> dict[str, Any] | None:
        """Resume graph after human review.

        Uses LangGraph 0.6.x update_state + invoke(None) pattern to resume
        from the present_to_athlete interrupt checkpoint.

        Returns final_plan_dict if approved, new proposed_plan_dict if rejected.
        """
        config = {"configurable": {"thread_id": thread_id, "db": db}}

        # Update state with human decision before resuming
        self._graph.update_state(
            config,
            {
                "human_approved": approved,
                "human_feedback": feedback,
            },
            as_node="present_to_athlete",
        )

        # Resume from checkpoint (None input = continue from where we left off)
        result = self._graph.invoke(None, config=config)

        if approved:
            return result.get("final_plan_dict")
        return result.get("proposed_plan_dict")
