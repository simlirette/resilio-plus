"""LiftingStore persistence + Hevy workout sync (full and incremental)."""

from __future__ import annotations

from datetime import datetime, timezone

from resilio.core.lifting.store import LiftingStore
from resilio.core.lifting.sync import sync_templates, sync_workouts
from resilio.schemas.lifting import HevyWorkout


def _w(wid: str, start: str, title: str = "Upper", reps: int = 10) -> dict:
    return {
        "id": wid,
        "title": title,
        "start_time": start,
        "end_time": start,
        "updated_at": start,
        "exercises": [
            {
                "index": 0,
                "title": "Bench Press (Dumbbell)",
                "exercise_template_id": "T-BENCH",
                "sets": [
                    {"index": 0, "type": "warmup", "weight_kg": 10, "reps": 12},
                    {"index": 1, "type": "normal", "weight_kg": 25, "reps": reps},
                ],
            }
        ],
    }


class FakeClient:
    def __init__(self, workouts=None, events=None, templates=None):
        self.workouts = workouts or []
        self.events = events or []
        self.templates = templates or []
        self.since = None

    def iter_workouts(self):
        return iter(self.workouts)

    def iter_workout_events(self, since_iso):
        self.since = since_iso
        return iter(self.events)

    def iter_exercise_templates(self):
        return iter(self.templates)


NOW = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)


def test_store_roundtrip_by_month(tmp_path):
    store = LiftingStore(tmp_path)
    w = HevyWorkout.model_validate(_w("a", "2026-09-30T10:00:00+00:00"))
    store.save_workout(w)
    assert (tmp_path / "workouts" / "2026-09" / "a.yaml").exists()
    loaded = store.load_workouts()
    assert len(loaded) == 1 and loaded[0].exercises[0].sets[1].weight_kg == 25


def test_store_moves_file_when_month_changes(tmp_path):
    store = LiftingStore(tmp_path)
    store.save_workout(HevyWorkout.model_validate(_w("a", "2026-09-30T10:00:00+00:00")))
    store.save_workout(HevyWorkout.model_validate(_w("a", "2026-10-01T10:00:00+00:00")))
    assert not (tmp_path / "workouts" / "2026-09" / "a.yaml").exists()
    assert len(store.load_workouts()) == 1


def test_full_sync_adds_all_and_records_state(tmp_path):
    store = LiftingStore(tmp_path)
    client = FakeClient(
        workouts=[_w("a", "2026-10-01T10:00:00+00:00"), _w("b", "2026-10-03T10:00:00+00:00")]
    )
    summary = sync_workouts(client, store, now=NOW)
    assert summary.mode == "full" and summary.added == 2 and summary.total_stored == 2
    assert store.load_state().last_sync_at == NOW


def test_full_sync_removes_workouts_deleted_remotely(tmp_path):
    store = LiftingStore(tmp_path)
    sync_workouts(
        FakeClient(
            workouts=[_w("a", "2026-10-01T10:00:00+00:00"), _w("b", "2026-10-02T10:00:00+00:00")]
        ),
        store,
        now=NOW,
    )
    summary = sync_workouts(
        FakeClient(workouts=[_w("a", "2026-10-01T10:00:00+00:00")]), store, full=True, now=NOW
    )
    assert summary.deleted == 1 and [w.id for w in store.load_workouts()] == ["a"]


def test_incremental_sync_applies_updates_and_deletes(tmp_path):
    store = LiftingStore(tmp_path)
    sync_workouts(
        FakeClient(
            workouts=[_w("a", "2026-10-01T10:00:00+00:00"), _w("b", "2026-10-02T10:00:00+00:00")]
        ),
        store,
        now=NOW,
    )
    client = FakeClient(
        events=[
            {"type": "updated", "workout": _w("a", "2026-10-01T10:00:00+00:00", reps=12)},
            {"type": "updated", "workout": _w("c", "2026-10-13T10:00:00+00:00")},
            {"type": "deleted", "id": "b", "deleted_at": "2026-10-13T00:00:00Z"},
        ]
    )
    later = datetime(2026, 10, 15, 12, 0, tzinfo=timezone.utc)
    summary = sync_workouts(client, store, now=later)
    assert summary.mode == "incremental"
    assert (summary.added, summary.updated, summary.deleted) == (1, 1, 1)
    assert client.since == "2026-10-14T11:50:00Z"  # last sync minus 10 min overlap
    ids = {w.id: w for w in store.load_workouts()}
    assert set(ids) == {"a", "c"} and ids["a"].exercises[0].sets[1].reps == 12


def test_failed_sync_does_not_advance_state(tmp_path):
    store = LiftingStore(tmp_path)

    class Boom(FakeClient):
        def iter_workouts(self):
            yield _w("a", "2026-10-01T10:00:00+00:00")
            raise RuntimeError("network")

    try:
        sync_workouts(Boom(), store, now=NOW)
    except RuntimeError:
        pass
    assert store.load_state().last_sync_at is None


def test_sync_templates_caches_catalog_source(tmp_path):
    store = LiftingStore(tmp_path)
    n = sync_templates(
        FakeClient(
            templates=[
                {
                    "id": "T1",
                    "title": "Squat (Barbell)",
                    "type": "weight_reps",
                    "primary_muscle_group": "quadriceps",
                    "secondary_muscle_groups": ["glutes"],
                    "equipment": "barbell",
                    "is_custom": False,
                }
            ]
        ),
        store,
        now=NOW,
    )
    assert n == 1 and store.load_templates()["T1"].primary_muscle_group == "quadriceps"
    assert store.load_state().templates_synced_at == NOW
