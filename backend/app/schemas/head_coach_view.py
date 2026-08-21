"""HeadCoachView schema — the context every coaching turn is answered from.

Originally six fields, with `active_plan_summary` hardcoded to None behind a
"D6" TODO. That meant the Head Coach replied to "my legs are wrecked" knowing
only that the athlete runs and lifts eight hours a week — not their age, their
VDOT, their race, this week's plan, or what they had actually done.

Everything added here is the sort of thing a human coach would have in front of
them before answering. Fields stay optional so a caller without a database
session, or one whose database is unavailable, still gets a usable view.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class HeadCoachView(BaseModel):
    """Athlete context snapshot for Head Coach and specialist chat responses.

    Built by head_coach_view_builder.build_head_coach_view().
    Consumed by chat_turn, onboarding, followup_transition and recovery_takeover.
    """

    athlete_id: str
    journey_phase: str
    sports: list[str] = Field(default_factory=list)
    primary_sport: str
    hours_per_week: float

    # Coaching mode (full | tracking_only | manual)
    coaching_mode: str = "full"

    # Recent plan summary — null if no active plan
    active_plan_summary: dict[str, Any] | None = None

    # Clinical context flag (propagated from athlete record)
    clinical_context_flag: str | None = None

    # ─── Physiology ──────────────────────────────────────────────────────────
    age: int | None = None
    sex: str | None = None
    weight_kg: float | None = None
    height_cm: float | None = None

    # ─── Fitness markers the specialists prescribe from ──────────────────────
    vdot: float | None = None
    # "declared" when the athlete gave a tested value, "estimated_from_recent_runs"
    # when it was inferred from Strava. The coach must not present an
    # inferred VDOT as a measured one.
    vdot_source: str | None = None
    ftp_watts: int | None = None
    css_per_100m: float | None = None
    max_hr: int | None = None
    resting_hr: int | None = None

    # ─── Goal ────────────────────────────────────────────────────────────────
    goals: list[str] = Field(default_factory=list)
    # Without this the model falls back to its training prior and argues with
    # a correct race date. It happened on the first live conversation.
    today: date | None = None
    target_race_date: date | None = None
    weeks_to_race: int | None = None
    # Exact, because weeks round: 3 days out and 27 days out can read as the
    # same number of weeks and hide the urgency.
    days_to_race: int | None = None
    # What the athlete's fitness projects for their stated goal, and the
    # alternative to offer alongside it. Empty when there is nothing honest
    # to say -- no measured VDOT, or a goal with no time in it.
    goal_feasibility: str | None = None

    # ─── Current training state ──────────────────────────────────────────────
    acwr_ratio: float | None = None
    acwr_status: str | None = None
    readiness: float | None = None
    muscle_strain: dict[str, float] = Field(default_factory=dict)
    """Per-muscle-group strain 0-100; 85+ is the red zone."""

    recent_sessions: list[dict[str, Any]] = Field(default_factory=list)
    """What the athlete actually did lately, newest first, capped."""
