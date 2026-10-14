"""Hevy → local store synchronisation (workouts and exercise templates)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from resilio.core.lifting.store import LiftingStore
from resilio.schemas.lifting import ExerciseTemplate, HevyWorkout, LiftingSyncSummary

# Re-read a little before the last sync so edits made during the previous run are not missed.
_OVERLAP = timedelta(minutes=10)


def _iso_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sync_workouts(
    client, store: LiftingStore, full: bool = False, now: Optional[datetime] = None
) -> LiftingSyncSummary:
    """Pull workouts from Hevy into ``store``.

    First run (or ``full``) pages through every workout and drops local files whose
    workout no longer exists in Hevy. Later runs replay ``/v1/workouts/events`` since
    the last successful sync. State only advances after the whole run succeeds.
    """
    started = now or datetime.now(timezone.utc)
    state = store.load_state()
    summary = LiftingSyncSummary(
        mode="full" if full or state.last_sync_at is None else "incremental"
    )

    if summary.mode == "full":
        seen: set[str] = set()
        for raw in client.iter_workouts():
            w = HevyWorkout.model_validate(raw)
            seen.add(w.id)
            if store.has_workout(w.id):
                summary.updated += 1
            else:
                summary.added += 1
            store.save_workout(w)
        for stale in store.workout_ids() - seen:
            store.delete_workout(stale)
            summary.deleted += 1
    else:
        assert state.last_sync_at is not None
        for event in client.iter_workout_events(_iso_z(state.last_sync_at - _OVERLAP)):
            if event.get("type") == "deleted":
                if store.delete_workout(str(event.get("id"))):
                    summary.deleted += 1
                continue
            raw = event.get("workout")
            if not raw:
                continue
            w = HevyWorkout.model_validate(raw)
            if store.has_workout(w.id):
                summary.updated += 1
            else:
                summary.added += 1
            store.save_workout(w)

    state.last_sync_at = started
    state.workout_count = len(store.workout_ids())
    store.save_state(state)
    summary.total_stored = state.workout_count
    summary.last_sync_at = started
    return summary


def sync_templates(client, store: LiftingStore, now: Optional[datetime] = None) -> int:
    templates = [ExerciseTemplate.model_validate(t) for t in client.iter_exercise_templates()]
    store.save_templates(templates)
    state = store.load_state()
    state.templates_synced_at = now or datetime.now(timezone.utc)
    store.save_state(state)
    return len(templates)
