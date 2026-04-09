"""
Weekly review graph nodes (H1-H4) for Resilio+ Head Coach.

node_wr_collect  — H1: normalize actual_workouts (V1: data already in state)
node_wr_analyze  — H2: planned vs actual + TRIMP via WeeklyAnalyzer
node_wr_adjust   — H3: ACWR recalculation + adjustment rules via WeeklyAdjuster
node_wr_report   — H4: assemble final report + LLM coaching note
"""
import anthropic

from core.config import settings
from core.weekly_review import WeeklyAdjuster, WeeklyAnalyzer
from models.weekly_review import WeeklyReviewState


def node_wr_collect(state: WeeklyReviewState) -> WeeklyReviewState:
    """H1: Normalize actual_workouts — V1: data is already provided in state by the API caller."""
    # Future: pull from Strava/Hevy APIs here
    return state


def node_wr_analyze(state: WeeklyReviewState) -> WeeklyReviewState:
    """H2: Planned vs actual analysis + TRIMP calculation."""
    planned = (
        state.athlete_state.partial_plans.get("running", {}).get("sessions", [])
        + state.athlete_state.partial_plans.get("lifting", {}).get("sessions", [])
    )
    state.analysis = WeeklyAnalyzer().analyze(planned, state.actual_workouts)
    return state


def node_wr_adjust(state: WeeklyReviewState) -> WeeklyReviewState:
    """H3: ACWR recalculation + adjustment recommendations."""
    daily_loads: list[float] = state.athlete_state.constraint_matrix.schedule.get(
        "_daily_loads_28d", []
    )
    # Capture ACWR before overwriting it
    state.acwr_before = state.athlete_state.fatigue.acwr

    adjustments, acwr_new = WeeklyAdjuster().adjust(
        state.analysis,
        daily_loads,
        state.athlete_state.fatigue,
    )
    state.adjustments = adjustments
    state.acwr_after = acwr_new

    # Update the living constraint matrix with this week's loads
    if state.analysis:
        updated_loads = (daily_loads + state.analysis["week_loads"])[-28:]
        state.athlete_state.constraint_matrix.schedule["_daily_loads_28d"] = updated_loads

    # Sync fatigue.acwr forward
    if acwr_new is not None:
        state.athlete_state.fatigue.acwr = acwr_new

    return state


def node_wr_report(state: WeeklyReviewState) -> WeeklyReviewState:
    """H4: Assemble final report + LLM coaching note."""
    analysis = state.analysis or {}
    state.report = {
        "agent": "head_coach",
        "week_reviewed": state.athlete_state.current_phase.mesocycle_week,
        "completion_rate": analysis.get("completion_rate", 0.0),
        "sessions_completed": analysis.get("sessions_completed", 0),
        "sessions_planned": analysis.get("sessions_planned", 0),
        "trimp_total": analysis.get("trimp_total", 0.0),
        "acwr_before": state.acwr_before,
        "acwr_after": state.acwr_after,
        "adjustments": state.adjustments,
        "next_week_notes": _get_weekly_notes(state),
    }
    return state


def _get_weekly_notes(state: WeeklyReviewState) -> str:
    """
    Generate a 1-sentence coaching note via LLM.

    Returns "" on any exception (LLM unavailable, API key missing, etc.).
    """
    try:
        analysis = state.analysis or {}
        content = (
            f"Weekly review — completion: {analysis.get('completion_rate', 0):.0%}, "
            f"TRIMP total: {analysis.get('trimp_total', 0):.1f}, "
            f"ACWR before: {state.acwr_before}, after: {state.acwr_after}, "
            f"adjustments: {[a['type'] for a in state.adjustments]}. "
            "Write exactly 1 coaching sentence (max 300 chars, direct, no fluff)."
        )
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=100,
            messages=[{"role": "user", "content": content}],
        )
        return response.content[0].text.strip()[:300]
    except Exception:
        return ""
