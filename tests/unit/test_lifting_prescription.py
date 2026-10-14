"""SP3 prescription: weekly lifting validation, planned volume, load suggestions, adherence."""

from __future__ import annotations

from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest

from resilio.core.lifting.catalog import build_catalog
from resilio.core.lifting.prescription import (
    adherence,
    apply_load_suggestions,
    format_exercise_line,
    planned_volume,
    validate_lifting_week,
)
from resilio.schemas.lifting import ExercisePrescription, ExerciseTemplate, HevyWorkout, LiftingProfile
from resilio.schemas.plan import StrengthSession

MON = date(2026, 10, 19)
CAT = build_catalog({
    t.id: t for t in [
        ExerciseTemplate(id="INC", title="Incline Bench Press (Dumbbell)", primary_muscle_group="chest",
                         secondary_muscle_groups=["shoulders", "triceps"]),
        ExerciseTemplate(id="ROW", title="Dumbbell Row", primary_muscle_group="upper_back",
                         secondary_muscle_groups=["biceps"]),
        ExerciseTemplate(id="SQ", title="Squat (Barbell)", primary_muscle_group="quadriceps",
                         secondary_muscle_groups=["glutes"]),
        ExerciseTemplate(id="NOR", title="Nordic Hamstrings Curls", primary_muscle_group="hamstrings"),
        ExerciseTemplate(id="BOX", title="Box Jump", primary_muscle_group="quadriceps", type="reps_only"),
    ]
})
PROFILE = LiftingProfile(gym_days=["monday", "tuesday", "wednesday"], optional_days=["thursday"],
                         protected_exercises=["Nordic Hamstrings Curls"], blacklist=["Squat (Barbell)"])


def ex(tid, title, sets=3, rr=(8, 10), rir=2, kind="hypertrophy", load=None):
    return ExercisePrescription(exercise_template_id=tid, title=title, sets=sets, rep_range=list(rr),
                                target_rir=rir, kind=kind, load_kg=load)


def sess(day, exercises, stype="upper", title="Upper A"):
    return StrengthSession(date=date.fromordinal(MON.toordinal() + day), day_of_week=day,
                           session_type=stype, week_number=1, title=title, exercises=exercises)


def run(day, wtype):
    return SimpleNamespace(day_of_week=day, workout_type=wtype)


def _validate(sessions, workouts=()):
    return validate_lifting_week(sessions, list(workouts), CAT, PROFILE, week_start=MON, week_number=1)


def test_clean_week_has_no_errors():
    res = _validate([sess(0, [ex("INC", "Incline Bench Press (Dumbbell)"), ex("ROW", "Dumbbell Row")]),
                     sess(1, [ex("NOR", "Nordic Hamstrings Curls", rr=(5, 8), kind="prehab"),
                              ex("BOX", "Box Jump", sets=3, rr=(3, 5), kind="power", rir=None)],
                          stype="legs", title="Legs")])
    assert res.errors == []
    assert not any("protected" in w for w in res.warnings)


def test_unknown_template_and_blacklist_are_errors():
    res = _validate([sess(0, [ex("NOPE", "Made Up"), ex("SQ", "Squat (Barbell)")])])
    assert any("NOPE" in e for e in res.errors)
    assert any("blacklist" in e.lower() for e in res.errors)


def test_low_reps_error_except_power():
    res = _validate([sess(0, [ex("INC", "Incline Bench Press (Dumbbell)", rr=(3, 5)),
                              ex("BOX", "Box Jump", rr=(3, 5), kind="power", rir=None)])])
    assert len([e for e in res.errors if "below min_reps" in e]) == 1


def test_non_gym_day_is_error_optional_day_ok():
    res = _validate([sess(3, [ex("INC", "Incline Bench Press (Dumbbell)")]),
                     sess(4, [ex("ROW", "Dumbbell Row")])])
    assert len([e for e in res.errors if "not a gym day" in e]) == 1


def test_missing_protected_and_low_rir_warn():
    res = _validate([sess(0, [ex("INC", "Incline Bench Press (Dumbbell)", rir=0)])])
    assert any("Nordic Hamstrings Curls" in w for w in res.warnings)
    assert any("RIR 0" in w for w in res.warnings)


def test_placement_warning_legs_before_long_run():
    res = _validate([sess(1, [ex("NOR", "Nordic Hamstrings Curls", kind="prehab")], stype="legs", title="Legs")],
                    workouts=[run(2, "long_run")])
    assert any("legs" in w.lower() and "long_run" in w for w in res.warnings)


def test_planned_volume_primary_and_secondary():
    vol = planned_volume([sess(0, [ex("INC", "Incline Bench Press (Dumbbell)", sets=4)])], CAT)
    assert vol["chest"] == 4 and vol["shoulders"] == 2 and vol["triceps"] == 2


def test_above_mrv_warns():
    res = _validate([sess(0, [ex("INC", "Incline Bench Press (Dumbbell)", sets=10),
                              ex("INC", "Incline Bench Press (Dumbbell)", sets=10),
                              ex("INC", "Incline Bench Press (Dumbbell)", sets=5)])])
    assert any("chest" in w and "MRV" in w for w in res.warnings)


def test_format_exercise_line():
    line = format_exercise_line(ex("INC", "Incline Bench Press (Dumbbell)", sets=3, load=25))
    assert line == "3×8–10 Incline Bench Press (Dumbbell) @ 25 kg · RIR 2 · rest 90s"


def test_apply_load_suggestions_fills_only_empty_loads():
    week = {"weeks": [{"week_number": 2, "is_recovery_week": False, "strength_sessions": [{
        "exercises": [
            {"exercise_template_id": "INC", "title": "Incline", "sets": 3, "rep_range": [8, 10]},
            {"exercise_template_id": "ROW", "title": "Row", "sets": 3, "rep_range": [8, 10], "load_kg": 30},
            {"exercise_template_id": "BOX", "title": "Box Jump", "sets": 3, "rep_range": [3, 5], "kind": "power"},
        ]}]}]}

    def suggest(tid, rep_range, deload):
        return SimpleNamespace(action="increase_load", suggested_load_kg=27.5, reason="r") if tid == "INC" \
            else SimpleNamespace(action="no_recent_history", suggested_load_kg=None, reason="none")

    report = apply_load_suggestions(week, suggest)
    exs = week["weeks"][0]["strength_sessions"][0]["exercises"]
    assert exs[0]["load_kg"] == 27.5 and exs[1]["load_kg"] == 30 and "load_kg" not in exs[2]
    assert [r["status"] for r in report] == ["filled", "kept", "skipped_power"]


def _hw(wid, d, exercises):
    return HevyWorkout.model_validate({
        "id": wid, "title": "Upper", "start_time": datetime(d.year, d.month, d.day, 17, tzinfo=timezone.utc).isoformat(),
        "exercises": [{"index": i, "title": t, "exercise_template_id": tid,
                       "sets": [{"index": j, "type": "normal", "weight_kg": 25, "reps": r} for j, r in enumerate(reps)]}
                      for i, (tid, t, reps) in enumerate(exercises)]})


def test_adherence_matches_same_day_then_neighbour_and_flags_missing():
    planned = [sess(0, [ex("INC", "Incline Bench Press (Dumbbell)"), ex("ROW", "Dumbbell Row")]),
               sess(1, [ex("NOR", "Nordic Hamstrings Curls", kind="prehab")], stype="legs", title="Legs"),
               sess(2, [ex("ROW", "Dumbbell Row")], title="Upper B")]
    done = [_hw("w0", MON, [("INC", "Incline", [10, 9, 8])]),
            _hw("w1", date(2026, 10, 21), [("NOR", "Nordic", [6, 6, 5])])]  # legs done a day late
    rep = adherence(planned, done)
    s0, s1, s2 = rep.sessions
    assert s0.workout_id == "w0" and s0.exercises[0].sets_done == 3 and s0.exercises[1].sets_done == 0
    assert "Dumbbell Row" in s0.missed_exercises
    assert s1.workout_id == "w1" and s1.day_shift == 1
    assert s2.workout_id is None and s2.status == "missed"
    assert rep.completed_sessions == 2 and rep.planned_sessions == 3


def test_calendar_description_lists_exercises():
    from resilio.core.calendar_sync import build_strength_event
    from resilio.schemas.config import GoogleCalendarSettings

    s = sess(0, [ex("INC", "Incline Bench Press (Dumbbell)", load=25)])
    event = build_strength_event(s, GoogleCalendarSettings())
    assert "3×8–10 Incline Bench Press (Dumbbell) @ 25 kg" in event["description"]
    assert "Upper A" in event["summary"]


def test_validate_week_plan_runs_lifting_checks(tmp_path, monkeypatch):
    import json

    from resilio.api import lifting as lift_api
    from resilio.api.plan import validate_week_plan

    monkeypatch.setattr(lift_api, "catalog", lambda: CAT)
    monkeypatch.setattr(lift_api, "_lifting_profile", lambda: PROFILE)
    week = {
        "week_number": 1, "phase": "base", "start_date": "2026-10-19", "end_date": "2026-10-25",
        "target_volume_km": 10, "target_systemic_load_au": 100,
        "workouts": [],
        "strength_sessions": [{
            "date": "2026-10-23", "day_of_week": 4, "session_type": "upper", "week_number": 1,
            "title": "Upper A",
            "exercises": [{"exercise_template_id": "INC", "title": "Incline Bench Press (Dumbbell)",
                           "sets": 3, "rep_range": [8, 10], "target_rir": 2}],
        }],
    }
    f = tmp_path / "w.json"
    f.write_text(json.dumps({"weeks": [week]}), encoding="utf-8")
    res = validate_week_plan(str(f))
    assert any("not a gym day" in e for e in res["errors"])
    assert res["lifting_planned_volume"]["chest"] == 3


def test_validate_week_plan_reads_utf8_on_windows(tmp_path):
    """Plan JSON with accents / dashes must not crash under a cp1252 default encoding."""
    import json

    from resilio.api.plan import validate_week_plan

    week = {"week_number": 1, "phase": "base", "start_date": "2026-10-19", "end_date": "2026-10-25",
            "target_volume_km": 0, "target_systemic_load_au": 0, "workouts": [],
            "notes": "Séance clé — semaine de reprise"}
    f = tmp_path / "w.json"
    f.write_text(json.dumps({"weeks": [week]}, ensure_ascii=False), encoding="utf-8")
    res = validate_week_plan(str(f))
    assert isinstance(res, dict) and "errors" in res
