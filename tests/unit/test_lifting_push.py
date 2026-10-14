"""SP5: plan week → Hevy routines (slot reuse, folder, dry-run, 404 recreate, unused rename)."""

from __future__ import annotations

from datetime import date

import pytest

from resilio.core.lifting.hevy_client import HevyAPIError
from resilio.core.lifting.push import build_routine_payload, push_week
from resilio.core.lifting.store import LiftingStore
from resilio.schemas.lifting import ExercisePrescription
from resilio.schemas.plan import StrengthSession

MON = date(2026, 10, 19)


def ex(tid="INC", title="Incline Bench Press (Dumbbell)", **kw):
    base = dict(exercise_template_id=tid, title=title, sets=3, rep_range=[8, 10], target_rir=2,
                load_kg=25, rest_seconds=120)
    base.update(kw)
    return ExercisePrescription(**base)


def sess(day, exercises, title="Upper A", stype="upper"):
    return StrengthSession(date=date.fromordinal(MON.toordinal() + day), day_of_week=day,
                           session_type=stype, week_number=3, title=title, exercises=exercises)


class FakeHevy:
    def __init__(self, folders=(), routines=None, missing=()):
        self.folders = list(folders)
        self.routines = dict(routines or {})
        self.missing = set(missing)
        self.calls = []
        self._n = 0

    def iter_routine_folders(self):
        return iter(self.folders)

    def create_routine_folder(self, title):
        self.calls.append(("create_folder", title))
        f = {"id": 99, "title": title}
        self.folders.append(f)
        return f

    def create_routine(self, routine):
        self._n += 1
        rid = f"new{self._n}"
        self.calls.append(("create", routine["title"], routine.get("folder_id")))
        self.routines[rid] = routine
        return {"id": rid, **routine}

    def update_routine(self, rid, routine):
        if rid in self.missing:
            raise HevyAPIError(404, "Routine doesn't exist")
        self.calls.append(("update", rid, routine["title"]))
        self.routines[rid] = routine
        return {"id": rid, **routine}

    def get_routine(self, rid):
        if rid in self.missing:
            raise HevyAPIError(404, "Routine doesn't exist")
        r = self.routines[rid]
        return {"id": rid, "title": r["title"], "folder_id": 99,
                "exercises": [dict(e, index=i, title="X") for i, e in enumerate(r["exercises"])]}


def test_payload_sets_warmups_rep_range_load_and_notes():
    p = build_routine_payload(sess(0, [ex(warmup_sets=1, notes="Slow eccentric")]), week_number=3)
    assert p["title"] == "Resilio · Mon · Upper A"
    e = p["exercises"][0]
    assert e["exercise_template_id"] == "INC" and e["rest_seconds"] == 120
    assert [s["type"] for s in e["sets"]] == ["warmup", "normal", "normal", "normal"]
    assert e["sets"][1]["rep_range"] == {"start": 8, "end": 10}
    assert e["sets"][1]["weight_kg"] == 25 and e["sets"][0]["weight_kg"] is None
    assert e["sets"][1]["reps"] == 8
    assert e["notes"] == "RIR 2 · Slow eccentric"
    assert "Week 3" in p["notes"]


def test_payload_duration_exercise():
    p = build_routine_payload(sess(0, [ex("PLK", "Plank", rep_range=None, duration_seconds=45,
                                          load_kg=None, target_rir=None, kind="core")]), 3)
    s = p["exercises"][0]["sets"][0]
    assert s["duration_seconds"] == 45 and s["reps"] is None and s.get("rep_range") is None


def test_first_push_creates_folder_and_routines_and_saves_slots(tmp_path):
    store, hevy = LiftingStore(tmp_path), FakeHevy()
    rep = push_week(hevy, store, [sess(0, [ex()]), sess(1, [ex("NOR", "Nordic")], "Legs", "legs")], week_number=3)
    assert ("create_folder", "Resilio") in hevy.calls
    assert [a.action for a in rep.actions] == ["create", "create"]
    assert all(c[2] == 99 for c in hevy.calls if c[0] == "create")
    assert store.load_routine_map()["slots"] == {"mon": "new1", "tue": "new2"}


def test_second_push_updates_existing_slots_no_new_routines(tmp_path):
    store, hevy = LiftingStore(tmp_path), FakeHevy(folders=[{"id": 7, "title": "Resilio"}])
    push_week(hevy, store, [sess(0, [ex()])], week_number=3)
    hevy.calls.clear()
    rep = push_week(hevy, store, [sess(0, [ex(load_kg=27.5)])], week_number=4)
    assert [c[0] for c in hevy.calls] == ["update"]
    assert rep.actions[0].action == "update"


def test_existing_folder_is_reused_not_recreated(tmp_path):
    hevy = FakeHevy(folders=[{"id": 7, "title": "Resilio"}])
    push_week(hevy, LiftingStore(tmp_path), [sess(0, [ex()])], week_number=3)
    assert not any(c[0] == "create_folder" for c in hevy.calls)
    assert hevy.calls[0] == ("create", "Resilio · Mon · Upper A", 7)


def test_deleted_routine_is_recreated(tmp_path):
    store = LiftingStore(tmp_path)
    store.save_routine_map({"folder_id": 7, "slots": {"mon": "gone"}})
    hevy = FakeHevy(folders=[{"id": 7, "title": "Resilio"}], missing={"gone"})
    rep = push_week(hevy, store, [sess(0, [ex()])], week_number=3)
    assert rep.actions[0].action == "recreate"
    assert store.load_routine_map()["slots"]["mon"] == "new1"


def test_unused_slot_is_renamed_keeping_exercises(tmp_path):
    store, hevy = LiftingStore(tmp_path), FakeHevy(folders=[{"id": 7, "title": "Resilio"}])
    push_week(hevy, store, [sess(0, [ex()]), sess(3, [ex()], "Arms")], week_number=3)
    hevy.calls.clear()
    rep = push_week(hevy, store, [sess(0, [ex()])], week_number=4)
    renamed = [a for a in rep.actions if a.action == "rename_unused"]
    assert renamed and renamed[0].slot == "thu"
    assert hevy.routines["new2"]["title"] == "Resilio · Thu · (not scheduled)"
    assert hevy.routines["new2"]["exercises"][0]["exercise_template_id"] == "INC"
    assert "index" not in hevy.routines["new2"]["exercises"][0]


def test_dry_run_writes_nothing(tmp_path):
    store, hevy = LiftingStore(tmp_path), FakeHevy()
    rep = push_week(hevy, store, [sess(0, [ex()])], week_number=3, dry_run=True)
    assert hevy.calls == [] and store.load_routine_map() == {}
    assert rep.dry_run and rep.actions[0].action == "create" and rep.actions[0].payload["title"]


def test_schedule_only_sessions_are_skipped(tmp_path):
    rep = push_week(FakeHevy(), LiftingStore(tmp_path), [sess(0, [])], week_number=3, dry_run=True)
    assert rep.actions[0].action == "skip"


def test_two_sessions_same_day_get_distinct_slots(tmp_path):
    store = LiftingStore(tmp_path)
    push_week(FakeHevy(), store, [sess(0, [ex()]), sess(0, [ex()], "Core")], week_number=3)
    assert set(store.load_routine_map()["slots"]) == {"mon", "mon-2"}


def test_routine_limit_error_propagates(tmp_path):
    class Limited(FakeHevy):
        def create_routine(self, routine):
            raise HevyAPIError(403, "Routine limit exceeded")

    with pytest.raises(HevyAPIError):
        push_week(Limited(folders=[{"id": 7, "title": "Resilio"}]), LiftingStore(tmp_path), [sess(0, [ex()])], 3)


def test_dry_run_without_api_key_still_builds_payloads(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from resilio.api import lifting as api
    from resilio.core.lifting.hevy_client import HevyConfigError

    def no_key():
        raise HevyConfigError("HEVY_API_KEY is not set")

    week = SimpleNamespace(week_number=1, strength_sessions=[sess(0, [ex()])])
    monkeypatch.setattr(api, "_client", no_key)
    monkeypatch.setattr(api, "_store", lambda: LiftingStore(tmp_path))
    monkeypatch.setattr(api, "_load_plan", lambda: SimpleNamespace(weeks=[week]))
    rep = api.push_lifting_week(1, dry_run=True)
    assert not api.is_lift_error(rep), rep
    assert rep.folder_action == "unknown_no_api_key" and rep.actions[0].payload["exercises"]
    real = api.push_lifting_week(1, dry_run=False)
    assert api.is_lift_error(real) and real.error_type == "config"
