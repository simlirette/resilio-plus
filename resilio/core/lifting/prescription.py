"""
SP3 — strength-session prescriptions: validation against the lifting profile and
catalog, planned weekly volume, load suggestions, adherence vs Hevy, display lines.
"""

from __future__ import annotations

from datetime import date, timedelta
from types import SimpleNamespace
from typing import Any, Callable, Iterable, Optional

from pydantic import BaseModel, Field

from resilio.core.lifting.analysis import SECONDARY_WEIGHT
from resilio.core.lifting.catalog import load_landmarks
from resilio.schemas.lifting import (
    CatalogEntry,
    ExerciseKind,
    ExercisePrescription,
    HevyWorkout,
    LiftingProfile,
    MovementPattern,
    WEEKDAYS,
)

COMPOUND = {MovementPattern.SQUAT.value, MovementPattern.HINGE.value, MovementPattern.LUNGE.value,
            MovementPattern.PUSH.value, MovementPattern.PULL.value}
NON_HYPERTROPHY = {ExerciseKind.POWER.value, ExerciseKind.MOBILITY.value}
LOWER_BODY_SET_THRESHOLD = 4  # a non-"legs" session with this many lower-body sets counts as legs


class LiftValidation(BaseModel):
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    planned_volume: dict[str, float] = Field(default_factory=dict)


def _kind(e: ExercisePrescription) -> str:
    return getattr(e.kind, "value", e.kind)


def planned_volume(sessions: Iterable, catalog: dict[str, CatalogEntry]) -> dict[str, float]:
    totals: dict[str, float] = {g: 0.0 for g in load_landmarks()}
    for s in sessions:
        for e in s.exercises:
            entry = catalog.get(e.exercise_template_id)
            if entry is None or _kind(e) in NON_HYPERTROPHY:
                continue
            if entry.primary_group in totals:
                totals[entry.primary_group] += e.sets
            for g in entry.secondary_groups:
                if g in totals:
                    totals[g] += e.sets * SECONDARY_WEIGHT
    return {g: v for g, v in totals.items() if v}


def _lower_body_sets(session, catalog: dict[str, CatalogEntry]) -> int:
    return sum(e.sets for e in session.exercises
               if (c := catalog.get(e.exercise_template_id)) is not None and c.lower_body
               and _kind(e) not in NON_HYPERTROPHY)


def validate_lifting_week(
    sessions: list,
    workouts: list,
    catalog: dict[str, CatalogEntry],
    profile: LiftingProfile,
    week_start: date,
    week_number: int,
    hybrid: bool = True,
) -> LiftValidation:
    """Errors block the week; warnings are coaching flags the coach must address or accept."""
    from resilio.core.plan import validate_strength_placement

    res = LiftValidation()
    week_end = week_start + timedelta(days=6)
    allowed_days = set(profile.gym_days) | set(profile.optional_days)
    blacklist = {b.lower() for b in profile.blacklist}
    seen_titles: set[str] = set()
    has_power = False

    if not catalog:
        res.warnings.append("Exercise catalog not synced — template ids not checked (run: resilio lift templates sync)")

    for s in sessions:
        label = f"{s.date} {s.title or getattr(s.session_type, 'value', s.session_type)}"
        if not (week_start <= s.date <= week_end):
            res.errors.append(f"{label}: date outside week {week_start}..{week_end}")
        day_name = WEEKDAYS[s.date.weekday()]
        if allowed_days and day_name not in allowed_days:
            res.errors.append(f"{label}: {day_name} is not a gym day ({', '.join(sorted(allowed_days))})")
        for e in s.exercises:
            entry = catalog.get(e.exercise_template_id)
            name = entry.title if entry else e.title
            seen_titles.add(name.lower())
            seen_titles.add(e.title.lower())
            kind = _kind(e)
            has_power = has_power or kind == ExerciseKind.POWER.value
            if catalog and entry is None:
                res.errors.append(f"{label}: unknown Hevy template id {e.exercise_template_id} ({e.title})")
            if name.lower() in blacklist or e.title.lower() in blacklist:
                res.errors.append(f"{label}: {name} is on the athlete's blacklist")
            if e.rep_range and kind != ExerciseKind.POWER.value and e.rep_range[0] < profile.min_reps:
                res.errors.append(
                    f"{label}: {name} {e.rep_range[0]}-{e.rep_range[1]} reps is below min_reps "
                    f"{profile.min_reps} (goal {getattr(profile.goal, 'value', profile.goal)})")
            if kind == ExerciseKind.HYPERTROPHY.value and e.rep_range:
                lo, hi = (profile.compound_rep_range if entry and entry.pattern in COMPOUND
                          else profile.accessory_rep_range)
                if e.rep_range[0] < lo or e.rep_range[1] > hi + 5:
                    res.warnings.append(f"{label}: {name} {e.rep_range[0]}-{e.rep_range[1]} reps outside "
                                        f"goal range {lo}-{hi}")
            if kind == ExerciseKind.HYPERTROPHY.value:
                if e.target_rir is None:
                    res.warnings.append(f"{label}: {name} has no target RIR")
                elif e.target_rir < profile.rir_target[0]:
                    res.warnings.append(f"{label}: {name} at RIR {e.target_rir} is closer to failure than the "
                                        f"profile allows ({profile.rir_target[0]}-{profile.rir_target[1]})")

    missing = [p for p in profile.protected_exercises if p.lower() not in seen_titles]
    if sessions and missing:
        res.warnings.append("Protected exercises missing this week: " + ", ".join(missing))
    if sessions and profile.include_power and not has_power:
        res.warnings.append("No power/plyo exercise this week (profile include_power=true)")

    vol = planned_volume(sessions, catalog)
    res.planned_volume = vol
    for g, lm in load_landmarks().items():
        mrv = lm["MRV"] * (1 - lm.get("hybrid_reduction", 0.0)) if hybrid else lm["MRV"]
        if vol.get(g, 0) > mrv:
            res.warnings.append(f"{g}: {vol[g]:g} planned hard sets above MRV {mrv:g}")

    # Placement vs runs: reuse the run-aware guardrail; sessions loaded with lower-body sets count as legs.
    placement_sessions = []
    for s in sessions:
        stype = getattr(s.session_type, "value", s.session_type)
        if stype != "legs" and _lower_body_sets(s, catalog) >= LOWER_BODY_SET_THRESHOLD:
            stype = "legs"
        placement_sessions.append(SimpleNamespace(session_type=stype, day_of_week=s.day_of_week))
    week_ns = SimpleNamespace(week_number=week_number, workouts=workouts, strength_sessions=placement_sessions)
    for v in validate_strength_placement(week_ns):  # type: ignore[arg-type]
        res.warnings.append(v.message)
    return res


# ------------------------------------------------------------------- display


def _fmt_num(x: float) -> str:
    return f"{x:g}"


def format_exercise_line(e: ExercisePrescription) -> str:
    if e.rep_range:
        lo, hi = e.rep_range
        reps = f"{lo}" if lo == hi else f"{lo}–{hi}"
    else:
        reps = f"{e.duration_seconds}s"
    parts = [f"{e.sets}×{reps} {e.title}" + (f" @ {_fmt_num(e.load_kg)} kg" if e.load_kg else "")]
    if e.target_rir is not None:
        parts.append(f"RIR {e.target_rir}")
    parts.append(f"rest {e.rest_seconds}s")
    return " · ".join(parts)


# ----------------------------------------------------------------- loads


def apply_load_suggestions(
    week_json: dict,
    suggest: Callable[[str, list[int], bool], Any],
    overwrite: bool = False,
) -> list[dict]:
    """Fill ``load_kg`` in a weekly plan JSON from progression suggestions (in place)."""
    report: list[dict] = []
    for week in week_json.get("weeks", []):
        deload = bool(week.get("is_recovery_week"))
        for s in week.get("strength_sessions", []) or []:
            for e in s.get("exercises", []) or []:
                row = {"title": e.get("title"), "exercise_template_id": e.get("exercise_template_id")}
                kind = e.get("kind", ExerciseKind.HYPERTROPHY.value)
                if kind in NON_HYPERTROPHY or not e.get("rep_range"):
                    report.append({**row, "status": f"skipped_{kind}" if kind in NON_HYPERTROPHY else "skipped_duration"})
                    continue
                if e.get("load_kg") is not None and not overwrite:
                    report.append({**row, "status": "kept", "load_kg": e["load_kg"]})
                    continue
                sug = suggest(e["exercise_template_id"], e["rep_range"], deload)
                if getattr(sug, "suggested_load_kg", None) is not None:
                    e["load_kg"] = sug.suggested_load_kg
                    report.append({**row, "status": "filled", "load_kg": sug.suggested_load_kg,
                                   "action": sug.action, "reason": sug.reason})
                else:
                    report.append({**row, "status": "no_load", "action": getattr(sug, "action", None),
                                   "reason": getattr(sug, "reason", None)})
    return report


# -------------------------------------------------------------- adherence


class ExerciseAdherence(BaseModel):
    exercise_template_id: str
    title: str
    sets_planned: int
    sets_done: int
    rep_range: Optional[list[int]] = None
    reps_done: list[int] = Field(default_factory=list)
    load_planned_kg: Optional[float] = None
    top_load_done_kg: Optional[float] = None


class SessionAdherence(BaseModel):
    date: date
    title: Optional[str] = None
    status: str  # completed | partial | missed
    workout_id: Optional[str] = None
    workout_date: Optional[date] = None
    day_shift: int = 0
    exercises: list[ExerciseAdherence] = Field(default_factory=list)
    missed_exercises: list[str] = Field(default_factory=list)
    extra_exercises: list[str] = Field(default_factory=list)


class LiftAdherenceReport(BaseModel):
    week_number: Optional[int] = None
    planned_sessions: int
    completed_sessions: int
    sessions: list[SessionAdherence] = Field(default_factory=list)
    unplanned_workouts: list[str] = Field(default_factory=list)


def adherence(planned: list, workouts: list[HevyWorkout], week_number: Optional[int] = None) -> LiftAdherenceReport:
    """Pair planned sessions with Hevy workouts (same day first, ±1 day if exercises overlap)."""
    candidates = []
    for i, s in enumerate(planned):
        planned_ids = {e.exercise_template_id for e in s.exercises}
        for j, w in enumerate(workouts):
            shift = (w.local_date - s.date).days
            if abs(shift) > 1:
                continue
            overlap = len(planned_ids & {ex.exercise_template_id for ex in w.exercises})
            if overlap == 0 and shift != 0:
                continue
            candidates.append(((overlap, -abs(shift)), i, j))
    candidates.sort(key=lambda c: c[0], reverse=True)
    match: dict[int, int] = {}
    used: set[int] = set()
    for _, i, j in candidates:
        if i in match or j in used:
            continue
        match[i] = j
        used.add(j)

    sessions_out = []
    for i, s in enumerate(planned):
        if i not in match:
            sessions_out.append(SessionAdherence(date=s.date, title=s.title, status="missed",
                                                 missed_exercises=[e.title for e in s.exercises]))
            continue
        w = workouts[match[i]]
        done_by_id = {}
        for ex in w.exercises:
            done_by_id.setdefault(ex.exercise_template_id, []).extend(st for st in ex.sets if st.is_working)
        rows, missed = [], []
        for e in s.exercises:
            sets = done_by_id.get(e.exercise_template_id, [])
            if not sets:
                missed.append(e.title)
            loads = [st.weight_kg for st in sets if st.weight_kg]
            rows.append(ExerciseAdherence(
                exercise_template_id=e.exercise_template_id, title=e.title, sets_planned=e.sets,
                sets_done=len(sets), rep_range=e.rep_range, reps_done=[st.reps or 0 for st in sets],
                load_planned_kg=e.load_kg, top_load_done_kg=round(max(loads), 2) if loads else None))
        planned_ids = {e.exercise_template_id for e in s.exercises}
        extra = [ex.title for ex in w.exercises if ex.exercise_template_id not in planned_ids]
        status = "completed" if not missed and all(r.sets_done >= r.sets_planned for r in rows) else "partial"
        sessions_out.append(SessionAdherence(
            date=s.date, title=s.title, status=status, workout_id=w.id, workout_date=w.local_date,
            day_shift=(w.local_date - s.date).days, exercises=rows, missed_exercises=missed,
            extra_exercises=extra))
    unplanned = [f"{w.local_date} {w.title}" for j, w in enumerate(workouts) if j not in used]
    return LiftAdherenceReport(
        week_number=week_number, planned_sessions=len(planned),
        completed_sessions=sum(1 for s in sessions_out if s.status != "missed"),
        sessions=sessions_out, unplanned_workouts=unplanned)
