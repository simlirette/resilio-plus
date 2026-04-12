"""CoachingService — wraps the LangGraph coaching graph.

Public API:
    service = CoachingService()
    thread_id, proposed_dict = service.create_plan(athlete_id, athlete_dict, load_history, db)
    final_dict = service.resume_plan(thread_id, approved, feedback, db)
    thread_id = service.weekly_review(athlete_id, db)
    service.resume_review(thread_id, approved, db)
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from ..graphs.coaching_graph import build_coaching_graph
from ..graphs.state import AthleteCoachingState
from ..graphs.weekly_review_graph import WeeklyReviewState, build_weekly_review_graph


class CoachingService:
    """Wraps the coaching LangGraph graph."""

    def __init__(self) -> None:
        self._graph = build_coaching_graph(interrupt=True)
        # Stores compiled review graph instances keyed by thread_id for resume_review()
        self._review_graphs: dict[str, Any] = {}

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

    # ---------------------------------------------------------------------------
    # Weekly review — S-3
    # ---------------------------------------------------------------------------

    def weekly_review(
        self,
        athlete_id: str,
        db: Session,
    ) -> tuple[str, dict[str, Any] | None]:
        """Start the weekly review graph, pause at present_review interrupt.

        Queries the latest TrainingPlan for the athlete to determine week context,
        builds the initial WeeklyReviewState, and runs the graph until the
        present_review interrupt checkpoint.

        Returns:
            (thread_id, review_summary_dict)
            review_summary_dict may be None if no sessions data is available yet.
        """
        import importlib
        from datetime import date, timedelta
        from sqlalchemy import desc
        importlib.import_module("app.models.schemas")  # registers V3 SA models first
        _db_models = importlib.import_module("app.db.models")
        TrainingPlanModel = _db_models.TrainingPlanModel
        WeeklyReviewModel = _db_models.WeeklyReviewModel

        # Determine current week context
        today = date.today()
        week_start = today - timedelta(days=today.weekday())

        plan = (
            db.query(TrainingPlanModel)
            .filter(TrainingPlanModel.athlete_id == athlete_id)
            .order_by(desc(TrainingPlanModel.created_at))
            .first()
        )
        plan_id = plan.id if plan else None
        week_number = 1
        if plan and plan.start_date:
            week_number = max(1, (today - plan.start_date).days // 7 + 1)

        # Build load_history from recent weekly reviews (sessions_completed as proxy for load)
        recent_reviews = (
            db.query(WeeklyReviewModel)
            .filter(WeeklyReviewModel.athlete_id == athlete_id)
            .order_by(desc(WeeklyReviewModel.week_start))
            .limit(28)
            .all()
        )
        import json as _json
        load_history: list[float] = []
        for rev in reversed(recent_reviews):
            try:
                results = _json.loads(rev.results_json)
                load_history.append(float(results.get("sessions_completed", 0)))
            except Exception:
                load_history.append(0.0)

        thread_id = f"{athlete_id}:review:{str(uuid.uuid4())}"
        config = {"configurable": {"thread_id": thread_id, "db": db}}

        review_graph = build_weekly_review_graph(interrupt=True)

        initial_state: WeeklyReviewState = {
            "athlete_id": athlete_id,
            "plan_id": plan_id,
            "week_start": week_start.isoformat(),
            "week_number": week_number,
            "sessions_planned": 0,
            "sessions_completed": 0,
            "completion_rate": 0.0,
            "actual_hours": 0.0,
            "load_history": load_history,
            "acwr_dict": None,
            "review_summary_dict": None,
            "human_approved": False,
            "db_review_id": None,
            "messages": [],
        }

        result = review_graph.invoke(initial_state, config=config)
        # Store graph reference for resume (keyed by thread_id)
        self._review_graphs[thread_id] = review_graph
        return thread_id, result.get("review_summary_dict")

    def resume_review(
        self,
        thread_id: str,
        approved: bool,
        db: Session,
    ) -> None:
        """Resume the weekly review graph after human confirmation.

        Injects human_approved into state, then continues the graph from
        the present_review checkpoint to apply_adjustments (DB write).

        Args:
            thread_id: Thread ID returned by weekly_review()
            approved:  True to persist WeeklyReviewModel; False to cancel
            db:        SQLAlchemy session (injected into graph config)
        """
        review_graph = self._review_graphs.get(thread_id)
        if review_graph is None:
            # Reconstruct graph for this thread (e.g., after service restart)
            review_graph = build_weekly_review_graph(interrupt=True)

        config = {"configurable": {"thread_id": thread_id, "db": db}}

        review_graph.update_state(
            config,
            {"human_approved": approved},
            as_node="present_review",
        )
        review_graph.invoke(None, config=config)
        # Clean up stored reference
        self._review_graphs.pop(thread_id, None)
