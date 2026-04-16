# tests/e2e/test_scenario_08_luteal_phase.py
"""S8 — Luteal phase: HeadCoach.build_week() with HormonalProfile → adjusted prescription.

Uses HeadCoach.build_week() directly (bypasses CoachingService) because
HormonalProfile doesn't flow through the graph's delegate_specialists node.
This is consistent with how TestHeadCoachWorkflowE2E tests the Head Coach.

Layla: female, VDOT 40, HormonalProfile.current_phase='luteal', cycle day 20.
Expected: notes from RunningCoach and NutritionCoach contain luteal-phase
adjustments (hydration, heat avoidance, protein bonus, +200 kcal).

Note on readiness_level: with Layla's Terra data (HRV=38 stable, sleep=6.8h,
score=65), compute_readiness() returns 1.0 → readiness_level='green'. The
luteal phase does NOT directly lower readiness_modifier in the current
implementation — it only enriches coaching notes. The test validates the
actual behavior rather than a hypothetical one.
"""
from __future__ import annotations

import random
from datetime import date, timedelta

import pytest

from app.agents.head_coach import HeadCoach, WeeklyPlan
from app.agents.lifting_coach import LiftingCoach
from app.agents.nutrition_coach import NutritionCoach
from app.agents.running_coach import RunningCoach
from app.agents.base import AgentContext
from tests.fixtures.athlete_states import layla_luteal_context, STABLE_LOAD

# NOTE: This scenario uses HeadCoach.build_week() directly and does NOT instantiate
# CoachingService. If refactored to use CoachingService, pass an explicit
# MemorySaver checkpointer (see scenarios 01-07) for test isolation.

random.seed(42)

WEEK_START = date(2026, 4, 14)
WEEK_END = WEEK_START + timedelta(days=6)


@pytest.fixture(scope="module")
def layla_plan() -> WeeklyPlan:
    """Build Layla's week with luteal HormonalProfile via HeadCoach.build_week()."""
    athlete, terra, hormonal = layla_luteal_context()

    context = AgentContext(
        athlete=athlete,
        date_range=(WEEK_START, WEEK_END),
        phase="base_building",
        terra_health=terra,
        strava_activities=[],
        hevy_workouts=[],
        week_number=2,
        weeks_remaining=27,
        hormonal_profile=hormonal,
    )

    hc = HeadCoach([RunningCoach(), LiftingCoach(), NutritionCoach()])
    return hc.build_week(context, load_history=STABLE_LOAD)


def test_plan_is_weekly_plan(layla_plan: WeeklyPlan):
    assert isinstance(layla_plan, WeeklyPlan)


def test_plan_has_sessions(layla_plan: WeeklyPlan):
    assert len(layla_plan.sessions) > 0


def test_readiness_level_is_valid(layla_plan: WeeklyPlan):
    """Readiness level must be one of the three valid values.

    With HRV=38 stable and sleep=6.8h/65, compute_readiness() returns 1.0
    so readiness_level is 'green'. The luteal phase adjustments flow through
    notes, not through the readiness modifier.
    """
    assert layla_plan.readiness_level in ("green", "yellow", "red"), (
        f"Unexpected readiness_level: {layla_plan.readiness_level}"
    )


def test_sessions_within_budget(layla_plan: WeeklyPlan):
    """Total session duration respects Layla's 7h/week budget (with 1h margin)."""
    total_hours = sum(s.duration_min for s in layla_plan.sessions) / 60.0
    assert total_hours <= 8.0, f"Total {total_hours:.1f}h exceeds 8h budget"


def test_no_session_has_none_fields(layla_plan: WeeklyPlan):
    """No critical session fields are None."""
    for s in layla_plan.sessions:
        assert s.date is not None
        assert s.sport is not None
        assert s.workout_type is not None
        assert s.duration_min > 0
        assert s.fatigue_score is not None


def test_running_notes_contain_luteal_cycle_adjustment(layla_plan: WeeklyPlan):
    """RunningCoach notes reference luteal-phase adjustments (hydration, heat avoidance).

    For the luteal phase, get_running_adjustments() sets increase_hydration=True
    and avoid_heat=True, which are appended to RunningCoach notes as
    'hydration++' and 'avoid-heat'.
    """
    notes_text = " ".join(layla_plan.notes).lower()
    has_luteal_running_ref = any(
        kw in notes_text
        for kw in ["luteal", "hydration", "avoid-heat", "luteale"]
    )
    assert has_luteal_running_ref, (
        f"Expected RunningCoach notes to contain luteal adjustments "
        f"(hydration/avoid-heat). Notes: {layla_plan.notes}"
    )


def test_nutrition_notes_contain_cycle_reference(layla_plan: WeeklyPlan):
    """NutritionCoach notes reference luteal phase protein and calorie adjustments.

    For the luteal phase, get_nutrition_adjustments() returns protein_extra=0.2
    and calories_extra=200, which are injected into NutritionCoach notes.
    """
    notes_text = " ".join(layla_plan.notes).lower()
    has_cycle_ref = any(
        kw in notes_text
        for kw in ["luteal", "luteale", "0.2", "200", "proteines", "protein"]
    )
    assert has_cycle_ref, (
        f"Expected NutritionCoach to reference luteal cycle in notes. "
        f"Notes: {layla_plan.notes}"
    )
