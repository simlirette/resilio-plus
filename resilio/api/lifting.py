"""
Lifting API — Hevy sync, exercise catalog, history, weekly volume, progression,
lifting profile. Every function returns a model or a ``LiftError``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Optional, Union

from resilio.core.lifting.analysis import exercise_history, progression, weekly_volume
from resilio.core.lifting.catalog import build_catalog
from resilio.core.lifting.hevy_client import (
    HevyAPIError,
    HevyAuthError,
    HevyClient,
    HevyConfigError,
    HevyRateLimitError,
)
from resilio.core.lifting.store import LiftingStore
from resilio.core.lifting.sync import sync_templates, sync_workouts
from resilio.schemas.lifting import (
    CatalogEntry,
    ExerciseHistory,
    LiftingProfile,
    LiftingSyncSummary,
    MovementPattern,
    ProgressionSuggestion,
    VolumeReport,
)

COMPOUND_PATTERNS = {
    MovementPattern.SQUAT.value,
    MovementPattern.HINGE.value,
    MovementPattern.LUNGE.value,
    MovementPattern.PUSH.value,
    MovementPattern.PULL.value,
}


@dataclass
class LiftError:
    """Error result from lifting operations."""

    error_type: str  # config | auth | rate_limit | network | validation | invalid_input | not_found | api_error
    message: str
    next_steps: Optional[str] = None


# ------------------------------------------------------------ seams (tests patch)


def _store() -> LiftingStore:
    return LiftingStore()


def _client() -> HevyClient:
    return HevyClient.from_env()


def _lifting_profile() -> LiftingProfile:
    from resilio.api.profile import ProfileError, get_profile

    p = get_profile()
    if isinstance(p, ProfileError) or p.lifting is None:
        return LiftingProfile()
    return p.lifting


def _map_hevy_error(exc: Exception) -> LiftError:
    if isinstance(exc, HevyConfigError):
        return LiftError(
            "config",
            str(exc),
            "Set HEVY_API_KEY as a user environment variable, then restart the terminal and Claude Code.",
        )
    if isinstance(exc, HevyAuthError):
        return LiftError(
            "auth",
            str(exc),
            "Regenerate the key in Hevy → Settings → Developer (requires Hevy Pro).",
        )
    if isinstance(exc, HevyRateLimitError):
        return LiftError("rate_limit", str(exc), "Wait a minute and retry.")
    if isinstance(exc, HevyAPIError):
        return LiftError(
            "network" if getattr(exc, "status_code", None) == 0 else "api_error", str(exc)
        )
    raise exc


# ------------------------------------------------------------------- catalog


def catalog() -> dict[str, CatalogEntry]:
    store = _store()
    cat = build_catalog(store.load_templates())
    return cat


def _known_exercises(store: LiftingStore) -> dict[str, str]:
    """template_id → title from the template cache plus anything seen in workouts."""
    known = {tid: t.title for tid, t in store.load_templates().items()}
    for w in store.load_workouts():
        for ex in w.exercises:
            known.setdefault(ex.exercise_template_id, ex.title)
    return known


def resolve_exercise(query: str) -> Union[tuple[str, str], LiftError]:
    store = _store()
    known = _known_exercises(store)
    if not known:
        return LiftError("not_found", "No exercises cached yet.", "Run: resilio lift sync")
    if query in known:
        return query, known[query]
    q = query.strip().lower()
    exact = [(tid, title) for tid, title in known.items() if title.lower() == q]
    if len(exact) == 1:
        return exact[0]
    partial = [(tid, title) for tid, title in known.items() if q in title.lower()]
    if len(partial) == 1:
        return partial[0]
    if not partial:
        return LiftError(
            "not_found",
            f"No exercise matches '{query}'.",
            "Run: resilio lift templates search <words> to find the exact title or id.",
        )
    names = ", ".join(sorted(t for _, t in partial)[:10])
    return LiftError(
        "validation", f"'{query}' is ambiguous: {names}", "Pass the exact title or the template id."
    )


def search_templates(
    query: str = "", muscle: Optional[str] = None
) -> Union[list[CatalogEntry], LiftError]:
    store = _store()
    templates = store.load_templates()
    if not templates:
        return LiftError(
            "not_found", "Exercise templates not cached.", "Run: resilio lift templates sync"
        )
    q = query.strip().lower()
    out = []
    for tid, t in templates.items():
        if q and q not in t.title.lower():
            continue
        if muscle and muscle not in ([t.primary_muscle_group] + list(t.secondary_muscle_groups)):
            continue
        out.append(t)
    cat = build_catalog({t.id: t for t in out})
    return sorted(cat.values(), key=lambda e: e.title)


# ---------------------------------------------------------------------- sync


def sync_lifting(full: bool = False) -> Union[LiftingSyncSummary, LiftError]:
    store = _store()
    try:
        client = _client()
        summary = sync_workouts(client, store, full=full)
        if not store.load_templates():
            sync_templates(client, store)
        return summary
    except (HevyConfigError, HevyAuthError, HevyRateLimitError, HevyAPIError) as exc:
        return _map_hevy_error(exc)


def sync_exercise_templates() -> Union[dict, LiftError]:
    try:
        n = sync_templates(_client(), _store())
        return {"templates": n}
    except (HevyConfigError, HevyAuthError, HevyRateLimitError, HevyAPIError) as exc:
        return _map_hevy_error(exc)


# ------------------------------------------------------------------ analysis


def get_lift_history(
    exercise: str, weeks: int = 8, today: Optional[date] = None
) -> Union[ExerciseHistory, LiftError]:
    resolved = resolve_exercise(exercise)
    if isinstance(resolved, LiftError):
        return resolved
    tid, title = resolved
    return exercise_history(_store().load_workouts(), tid, title=title, weeks=weeks, today=today)


def rep_range_for(entry: Optional[CatalogEntry], profile: LiftingProfile) -> list[int]:
    if entry is not None and entry.pattern in COMPOUND_PATTERNS:
        return list(profile.compound_rep_range)
    return list(profile.accessory_rep_range)


def increment_for(entry: Optional[CatalogEntry], profile: LiftingProfile) -> float:
    key = "lower" if entry is not None and entry.lower_body else "upper"
    return float(profile.increment_kg.get(key, 2.5))


def get_lift_progression(
    exercise: str,
    deload: bool = False,
    rep_range: Optional[list[int]] = None,
    today: Optional[date] = None,
) -> Union[ProgressionSuggestion, LiftError]:
    resolved = resolve_exercise(exercise)
    if isinstance(resolved, LiftError):
        return resolved
    tid, title = resolved
    profile = _lifting_profile()
    entry = catalog().get(tid)
    rr = rep_range or rep_range_for(entry, profile)
    hist = exercise_history(_store().load_workouts(), tid, title=title, weeks=12, today=today)
    return progression(hist, rr, increment_for(entry, profile), deload=deload, today=today)


def get_lift_volume(
    week_start: Optional[str] = None, hybrid: bool = True
) -> Union[VolumeReport, LiftError]:
    if week_start:
        try:
            start = date.fromisoformat(week_start)
        except ValueError:
            return LiftError("invalid_input", f"Invalid date '{week_start}'. Expected YYYY-MM-DD.")
        if start.weekday() != 0:
            return LiftError(
                "invalid_input", f"Week start must be a Monday, got {start.strftime('%A')}."
            )
    else:
        today = date.today()
        start = today - timedelta(days=today.weekday())
    store = _store()
    return weekly_volume(
        store.load_workouts(since=start, until=start + timedelta(days=6)),
        catalog(),
        start,
        hybrid=hybrid,
    )


# ------------------------------------------------------------------- profile


def get_lifting_profile() -> Union[LiftingProfile, LiftError]:
    from resilio.api.profile import ProfileError, get_profile

    p = get_profile()
    if isinstance(p, ProfileError):
        return LiftError(
            "not_found", p.message, "Run the first-session workflow to create a profile."
        )
    if p.lifting is None:
        return LiftError(
            "not_found",
            "No lifting profile yet.",
            "Run: resilio lift profile set --goal hypertrophy_athletic --gym-days monday,tuesday,wednesday",
        )
    return p.lifting


def set_lifting_profile(**changes: Any) -> Union[LiftingProfile, LiftError]:
    from resilio.api.profile import ProfileError, get_profile, update_profile

    p = get_profile()
    if isinstance(p, ProfileError):
        return LiftError("not_found", p.message)
    current = (p.lifting or LiftingProfile()).model_dump(mode="json")
    current.update({k: v for k, v in changes.items() if v is not None})
    try:
        merged = LiftingProfile.model_validate(current)
    except ValueError as exc:
        return LiftError("validation", str(exc))
    result = update_profile(lifting=merged.model_dump(mode="json"))
    if isinstance(result, ProfileError):
        return LiftError("validation", result.message)
    return result.lifting or merged


def is_lift_error(result: object) -> bool:
    return isinstance(result, LiftError)


# ------------------------------------------------------------- SP3: prescription


def validate_week_lifting(week: dict) -> dict:
    """Validate ``strength_sessions`` of one weekly-plan JSON week. Never raises.

    Returns ``{"errors": [...], "warnings": [...], "planned_volume": {...}}``.
    """
    from types import SimpleNamespace

    from pydantic import ValidationError as PydValidationError

    from resilio.core.lifting.prescription import validate_lifting_week
    from resilio.schemas.plan import StrengthSession

    out: dict = {"errors": [], "warnings": [], "planned_volume": {}}
    raw_sessions = week.get("strength_sessions") or []
    sessions = []
    for i, raw in enumerate(raw_sessions):
        try:
            sessions.append(StrengthSession.model_validate(raw))
        except PydValidationError as exc:
            first = exc.errors()[0]
            loc = ".".join(str(x) for x in first.get("loc", ()))
            out["errors"].append(f"strength_sessions[{i}] invalid at {loc}: {first.get('msg')}")
    if out["errors"]:
        return out
    try:
        week_start = date.fromisoformat(str(week.get("start_date")))
    except ValueError:
        return out  # date errors are reported by the run validator
    workouts = [
        SimpleNamespace(day_of_week=w.get("day_of_week"), workout_type=w.get("workout_type"))
        for w in week.get("workouts") or []
        if w.get("day_of_week") is not None
    ]
    res = validate_lifting_week(
        sessions,
        workouts,
        catalog(),
        _lifting_profile(),
        week_start=week_start,
        week_number=int(week.get("week_number") or 0),
    )
    return res.model_dump()


def suggest_loads(file_path: str, overwrite: bool = False) -> Union[dict, LiftError]:
    """Fill load_kg in a weekly plan JSON from progression (writes the file in place)."""
    import json
    from pathlib import Path

    from resilio.core.lifting.prescription import apply_load_suggestions

    path = Path(file_path)
    if not path.exists():
        return LiftError("not_found", f"File not found: {file_path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return LiftError("validation", f"Invalid JSON: {exc}")
    store = _store()
    workouts = store.load_workouts()
    profile = _lifting_profile()
    cat = catalog()

    def suggest(template_id: str, rep_range: list[int], deload: bool):
        entry = cat.get(template_id)
        title = entry.title if entry else template_id
        hist = exercise_history(workouts, template_id, title=title, weeks=12)
        return progression(hist, rep_range, increment_for(entry, profile), deload=deload)

    report = apply_load_suggestions(data, suggest, overwrite=overwrite)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=True), encoding="utf-8")
    filled = sum(1 for r in report if r["status"] == "filled")
    return {"file": str(path), "filled": filled, "exercises": report}


def _load_plan():
    from resilio.api.plan import PlanError, get_current_plan

    plan = get_current_plan()
    if isinstance(plan, PlanError):
        return LiftError("not_found", plan.message, "Create a plan first (macro-plan-create).")
    return plan


def get_lift_adherence(week_number: int):
    """Planned strength sessions of plan week N vs Hevy workouts in that week."""
    from resilio.core.lifting.prescription import adherence

    plan = _load_plan()
    if isinstance(plan, LiftError):
        return plan
    week = next((w for w in plan.weeks if w.week_number == week_number), None)
    if week is None:
        return LiftError("not_found", f"Week {week_number} not in current plan.")
    workouts = _store().load_workouts(
        since=week.start_date - timedelta(days=1), until=week.end_date + timedelta(days=1)
    )
    return adherence(week.strength_sessions, workouts, week_number=week_number)


def set_lifting_blocks(file_path: str):
    """Replace MasterPlan.lifting_blocks from a JSON list file."""
    import json
    from pathlib import Path

    from pydantic import TypeAdapter
    from pydantic import ValidationError as PydValidationError

    from resilio.core.paths import current_plan_path
    from resilio.core.repository import RepositoryIO
    from resilio.schemas.lifting import LiftingBlock

    plan = _load_plan()
    if isinstance(plan, LiftError):
        return plan
    try:
        raw = json.loads(Path(file_path).read_text(encoding="utf-8"))
        blocks = TypeAdapter(list[LiftingBlock]).validate_python(raw.get("lifting_blocks", raw) if isinstance(raw, dict) else raw)
    except FileNotFoundError:
        return LiftError("not_found", f"File not found: {file_path}")
    except (json.JSONDecodeError, PydValidationError) as exc:
        return LiftError("validation", f"Invalid lifting blocks: {exc}")
    for b in blocks:
        if b.end_week > plan.total_weeks:
            return LiftError("validation", f"Block ends at week {b.end_week} but plan has {plan.total_weeks} weeks")
    plan.lifting_blocks = blocks
    err = RepositoryIO().write_yaml(current_plan_path(), plan)
    if err is not None:
        return LiftError("validation", f"Failed to save plan: {err}")
    return blocks


def get_lifting_blocks():
    plan = _load_plan()
    if isinstance(plan, LiftError):
        return plan
    return plan.lifting_blocks


# ----------------------------------------------------------------- SP5: push


def push_lifting_week(week_number: int, dry_run: bool = False):
    """Write plan week N's prescribed strength sessions to Hevy routines (folder "Resilio")."""
    from resilio.core.lifting.push import push_week

    plan = _load_plan()
    if isinstance(plan, LiftError):
        return plan
    week = next((w for w in plan.weeks if w.week_number == week_number), None)
    if week is None:
        return LiftError("not_found", f"Week {week_number} not in current plan.")
    if not any(s.exercises for s in week.strength_sessions):
        return LiftError(
            "validation",
            f"Week {week_number} has no prescribed exercises to push.",
            "Generate the week with exercises (weekly-plan-generate), validate and populate it first.",
        )
    try:
        report = push_week(_client(), _store(), week.strength_sessions, week_number, dry_run=dry_run)
    except HevyAPIError as exc:
        if exc.status_code == 403:
            return LiftError(
                "api_error",
                "Hevy refused to create a routine (routine limit reached).",
                "Delete unused routines in the Hevy app (outside the Resilio folder), then retry.",
            )
        return _map_hevy_error(exc)
    except (HevyConfigError, HevyAuthError, HevyRateLimitError) as exc:
        return _map_hevy_error(exc)
    return report
