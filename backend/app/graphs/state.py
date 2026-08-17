"""AthleteCoachingState — serializable TypedDict for the LangGraph coaching graph.

All values must be JSON-serializable (no ORM objects, no SQLAlchemy sessions).
Complex domain objects are stored as plain dicts and reconstructed in nodes.
The DB session is passed via config["configurable"]["db"] — never stored in state.
"""
from __future__ import annotations

from typing import Annotated, Any, Literal, NotRequired

from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages
from typing_extensions import TypedDict


class AthleteCoachingState(TypedDict):
    """Shared state for the coaching planning graph.

    All values are primitive types or dicts — JSON-serializable so that
    MemorySaver can checkpoint state between human-in-the-loop interrupts.
    """

    athlete_id: str
    """Athlete primary key — used by nodes to load from DB when needed."""

    athlete_dict: dict[str, Any]
    """Serialized AthleteProfile (from AthleteProfile.model_dump(mode='json'))."""

    load_history: list[float]
    """Daily loads (oldest-first) for ACWR computation."""

    budgets: dict[str, float]
    """Sport → hourly budget, populated by analyze_profile node."""

    recommendations_dicts: list[dict[str, Any]]
    """Serialized AgentRecommendation list (one per active specialist)."""

    acwr_dict: dict[str, Any] | None
    """Serialized ACWRResult or None if not yet computed."""

    conflicts_dicts: list[dict[str, Any]]
    """Serialized Conflict list from detect_conflicts."""

    proposed_plan_dict: dict[str, Any] | None
    """Serialized WeeklyPlan before human approval."""

    energy_snapshot_dict: dict[str, Any] | None
    """Serialized EnergySnapshot from EnergyCycleService (may be None)."""

    human_approved: bool
    """Set to True by resume_plan(approved=True)."""

    human_feedback: str | None
    """Free-text feedback from athlete when rejecting a plan."""

    final_plan_dict: dict[str, Any] | None
    """Serialized WeeklyPlan after finalize_plan — persisted to DB."""

    messages: Annotated[list[BaseMessage], add_messages]
    """LangGraph message accumulator for debug/audit trail."""

    # ── Phase D extensions (D1) ──────────────────────────────────────────────

    generation_mode: NotRequired[Literal["baseline", "first_personalized", "block_regen"] | None]
    """Plan generation mode — injected by CoordinatorService before invoking plan_generation.

    - baseline: sous-max diagnostic plan (7–21j), mutes journey_phase → baseline_active
    - first_personalized: full macrocycle post-baseline, mutes → steady_state
    - block_regen: next-block regen only, keeps steady_state
    """

    active_plan: NotRequired[dict[str, Any] | None]
    """Structured active plan summary produced by build_proposed_plan.

    Contains blocks[], discipline_components, trade_offs_disclosed.
    Replaces the flat proposed_plan_dict for Phase D plan generation.
    """
