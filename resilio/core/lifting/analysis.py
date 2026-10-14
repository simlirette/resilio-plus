"""
Pure lifting analysis: e1RM, per-exercise history, weekly hard sets per muscle group,
and double-progression suggestions. Tools compute; the coach decides.
"""

from __future__ import annotations

import math
from datetime import date, timedelta
from typing import Any, Iterable, Optional

from resilio.core.lifting.catalog import load_landmarks
from resilio.schemas.lifting import (
    CatalogEntry,
    ExerciseHistory,
    ExerciseSessionSummary,
    HevyWorkout,
    MuscleVolume,
    ProgressionSuggestion,
    VolumeReport,
)

RECENT_HISTORY_DAYS = 42  # no load suggestion without a logged set in the last 6 weeks
SECONDARY_WEIGHT = 0.5


def round_load(kg: float, step: float = 0.5) -> float:
    """Nearest loadable step (Hevy stores lbs-entered loads as long kg floats)."""
    return round(round(kg / step) * step, 2)


KG_PER_LB = 0.45359237


def lbs_equivalent(kg: Optional[float]) -> Optional[float]:
    """Pound value if ``kg`` is a load the athlete entered in lb (Hevy stores kg only).

    A load counts as lb-entered when it sits on a 0.5 lb grid but not on a 0.25 kg grid,
    e.g. 54.431 kg = 120 lb. Plain kg loads (25, 27.5, 22.5) return None.
    """
    if not kg:
        return None
    lbs = kg / KG_PER_LB
    on_lb_grid = abs(lbs * 2 - round(lbs * 2)) < 0.02
    on_kg_grid = abs(kg * 4 - round(kg * 4)) < 0.02
    if on_lb_grid and not on_kg_grid:
        value = round(lbs * 2) / 2
        return int(value) if value == int(value) else value
    return None


def e1rm(weight_kg: Optional[float], reps: Optional[int]) -> Optional[float]:
    """Epley estimate; unreliable above 12 reps, so returns None there."""
    if not weight_kg or not reps or reps < 1 or reps > 12:
        return None
    return round(weight_kg * (1 + reps / 30.0), 1)


# ------------------------------------------------------------------ history


def exercise_history(
    workouts: Iterable[HevyWorkout],
    template_id: str,
    title: str,
    weeks: int = 8,
    today: Optional[date] = None,
) -> ExerciseHistory:
    today = today or date.today()
    since = today - timedelta(weeks=weeks)
    sessions: list[ExerciseSessionSummary] = []
    for w in sorted(workouts, key=lambda x: x.start_time):
        if w.local_date < since or w.local_date > today:
            continue
        working = [
            s
            for ex in w.exercises
            if ex.exercise_template_id == template_id
            for s in ex.sets
            if s.is_working
        ]
        if not working:
            continue
        weighted = [s for s in working if s.weight_kg]
        top = max(weighted, key=lambda s: (s.weight_kg or 0, s.reps or 0)) if weighted else None
        e1rms = [v for v in (e1rm(s.weight_kg, s.reps) for s in working) if v is not None]
        sessions.append(
            ExerciseSessionSummary(
                date=w.local_date,
                workout_id=w.id,
                workout_title=w.title,
                working_sets=len(working),
                total_reps=sum(s.reps or 0 for s in working),
                top_weight_kg=round(top.weight_kg, 2) if top and top.weight_kg else None,
                top_set_reps=(top.reps if top else max((s.reps or 0) for s in working) or None),
                best_e1rm_kg=max(e1rms) if e1rms else None,
                sets=working,
            )
        )
    trend = None
    with_e1rm = [s.best_e1rm_kg for s in sessions if s.best_e1rm_kg is not None]
    if len(with_e1rm) >= 2:
        trend = round(with_e1rm[-1] - with_e1rm[0], 1)
    return ExerciseHistory(
        template_id=template_id, title=title, weeks=weeks, sessions=sessions, e1rm_trend_kg=trend
    )


# ------------------------------------------------------------------- volume


def _status(sets: float, mev: int, mav: int, mrv: float) -> str:
    if sets < mev:
        return "below_mev"
    if sets <= mav:
        return "productive"
    if sets <= mrv:
        return "above_mav"
    return "above_mrv"


def weekly_volume(
    workouts: Iterable[HevyWorkout],
    catalog: dict[str, CatalogEntry],
    week_start: date,
    hybrid: bool = True,
) -> VolumeReport:
    """Hard (non-warm-up) sets per landmark group for the Monday-Sunday week.

    Primary group counts 1 per set, each secondary group 0.5. With ``hybrid`` the MRV is
    reduced by the landmark's ``hybrid_reduction`` (running already loads the legs).
    """
    week_end = week_start + timedelta(days=6)
    landmarks = load_landmarks()
    totals: dict[str, float] = {g: 0.0 for g in landmarks}
    unmapped: list[str] = []
    counted = 0
    for w in workouts:
        if not (week_start <= w.local_date <= week_end):
            continue
        counted += 1
        for ex in w.exercises:
            n = sum(1 for s in ex.sets if s.is_working)
            if n == 0:
                continue
            entry = catalog.get(ex.exercise_template_id)
            if entry is None:
                if ex.title not in unmapped:
                    unmapped.append(ex.title)
                continue
            if entry.primary_group in totals:
                totals[entry.primary_group] += n
            for g in entry.secondary_groups:
                if g in totals:
                    totals[g] += n * SECONDARY_WEIGHT
    groups = []
    for g, lm in landmarks.items():
        mrv = lm["MRV"] * (1 - lm.get("hybrid_reduction", 0.0)) if hybrid else lm["MRV"]
        mrv = round(mrv, 1)
        groups.append(
            MuscleVolume(
                group=g,
                hard_sets=totals[g],
                mev=lm["MEV"],
                mav=lm["MAV"],
                mrv=mrv,
                status=_status(totals[g], lm["MEV"], lm["MAV"], mrv),
            )
        )
    return VolumeReport(
        week_start=week_start,
        week_end=week_end,
        hybrid_adjusted=hybrid,
        workouts_counted=counted,
        groups=groups,
        unmapped_exercises=unmapped,
    )


# -------------------------------------------------------------- progression


def progression(
    history: ExerciseHistory,
    rep_range: list[int],
    increment_kg: float,
    deload: bool = False,
    today: Optional[date] = None,
) -> ProgressionSuggestion:
    """Double progression inside ``rep_range`` based on the latest session."""
    today = today or date.today()
    low, high = rep_range
    base: dict[str, Any] = dict(
        template_id=history.template_id, title=history.title, rep_range=[low, high]
    )
    if not history.sessions:
        return ProgressionSuggestion(
            **base,
            action="no_recent_history",
            reason="No logged sets for this exercise; prescribe by RIR and find the working load.",
        )
    last = history.sessions[-1]
    if (today - last.date).days > RECENT_HISTORY_DAYS:
        return ProgressionSuggestion(
            **base,
            last_session_date=last.date,
            action="no_recent_history",
            reason=f"Last logged {last.date.isoformat()} (> 6 weeks ago); re-find the working load by RIR.",
        )
    reps = [s.reps or 0 for s in last.sets]
    n_sets = len(last.sets)
    common: dict[str, Any] = dict(
        base, last_session_date=last.date, last_reps=reps, suggested_sets=n_sets
    )

    if not last.top_weight_kg:
        target = min(high + 3, (min(reps) if reps else low) + 1)
        return ProgressionSuggestion(
            **common,
            action="bodyweight",
            target_reps=max(target, low),
            reason="Bodyweight: add a rep per set; add load once all sets pass the top of the range.",
        )

    load = last.top_weight_kg
    raw_load = max((s.weight_kg or 0) for s in last.sets)
    at_load = [s.reps or 0 for s in last.sets if s.weight_kg == raw_load] or reps
    common["last_load_kg"] = load

    if deload:
        common["suggested_sets"] = max(1, math.floor(n_sets * 0.6))
        return ProgressionSuggestion(
            **common,
            action="deload",
            suggested_load_kg=load,
            target_reps=low,
            reason="Deload week: ~40% fewer sets, same load, stop well short of failure.",
        )
    if min(at_load) >= high:
        lbs = lbs_equivalent(load)
        if lbs is not None:
            step_lb = 5 if increment_kg <= 2.5 else 10
            new_kg = round((lbs + step_lb) * KG_PER_LB, 2)
            reason = (f"All sets hit {high}+ reps at {lbs} lb; add {step_lb} lb ({lbs + step_lb} lb) "
                      f"and restart at {low}.")
        else:
            new_kg = round_load(load + increment_kg)
            reason = f"All sets hit {high}+ reps at {load} kg; add {increment_kg} kg and restart at {low}."
        return ProgressionSuggestion(**common, action="increase_load", suggested_load_kg=new_kg,
                                     target_reps=low, reason=reason)
    if min(at_load) < low:
        return ProgressionSuggestion(
            **common,
            action="hold",
            suggested_load_kg=load,
            target_reps=low,
            reason=f"Some sets below {low} reps at {load} kg; repeat the load and reach {low} on every set.",
        )
    return ProgressionSuggestion(
        **common,
        action="add_reps",
        suggested_load_kg=load,
        target_reps=min(high, min(at_load) + 1),
        reason=f"Inside {low}-{high}; same load, add a rep to the weakest set.",
    )
