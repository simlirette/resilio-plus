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
