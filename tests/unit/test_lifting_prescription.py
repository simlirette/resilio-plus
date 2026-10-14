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


# ---------------------------------------------------------------- resilio-plus rules (DUP, SFR, ACWR, deload)

from resilio.core.lifting.prescription import LiftContext, run_load_level  # noqa: E402

CAT_TIERS = build_catalog({
    t.id: t for t in [
        ExerciseTemplate(id="BBS", title="Barbell Back Squat", primary_muscle_group="quadriceps"),
        ExerciseTemplate(id="LP", title="Machine Leg Press", primary_muscle_group="quadriceps"),
        ExerciseTemplate(id="RDLD", title="Romanian Deadlift (DB)", primary_muscle_group="hamstrings"),
        ExerciseTemplate(id="INC", title="Incline Bench Press (Dumbbell)", primary_muscle_group="chest"),
    ]
})
NO_PROTECT = LiftingProfile(gym_days=["monday", "tuesday", "wednesday"], include_power=False)


def _v(sessions, ctx, cat=CAT_TIERS):
    return validate_lifting_week(sessions, [], cat, NO_PROTECT, week_start=MON, week_number=5, context=ctx)


def test_run_load_level_thresholds():
    assert run_load_level(run_count=3, run_minutes=170) == "light"
    assert run_load_level(run_count=4, run_minutes=300) == "moderate"
    assert run_load_level(run_count=5, run_minutes=250) == "high"
    assert run_load_level(run_count=3, run_minutes=400) == "high"


def test_tier3_warns_unless_running_load_light():
    s = [sess(1, [ex("BBS", "Barbell Back Squat", rr=(6, 8))], stype="legs", title="Legs")]
    assert any("SFR Tier 3" in w for w in _v(s, LiftContext(run_load="moderate")).warnings)
    assert not any("SFR Tier 3" in w for w in _v(s, LiftContext(run_load="light")).warnings)


def test_hybrid_reduction_scales_with_running_load():
    s = [sess(1, [ex("LP", "Machine Leg Press", sets=7, rr=(10, 12)),
                  ex("LP", "Machine Leg Press", sets=7, rr=(12, 15))], stype="legs", title="Legs")]
    # quads MRV 20: high → ×0.6 = 12 (warn); light → ×(1-0.4/3) ≈ 17.3 (no warn)
    assert any("quads" in w and "MRV" in w for w in _v(s, LiftContext(run_load="high")).warnings)
    assert not any("quads" in w and "MRV" in w for w in _v(s, LiftContext(run_load="light")).warnings)


def test_acwr_above_1_3_requires_15_percent_less_lifting():
    s = [sess(0, [ex("INC", "Incline Bench Press (Dumbbell)", sets=10)])]
    assert any("ACWR" in w for w in _v(s, LiftContext(acwr=1.4, prev_week_sets=10)).warnings)
    assert not any("ACWR" in w for w in _v(s, LiftContext(acwr=1.4, prev_week_sets=12)).warnings)
    assert not any("ACWR" in w for w in _v(s, LiftContext(acwr=1.1, prev_week_sets=10)).warnings)


def test_deload_cadence_and_recovery_week_rir():
    s = [sess(0, [ex("INC", "Incline Bench Press (Dumbbell)", rir=2)])]
    assert any("deload" in w.lower() for w in _v(s, LiftContext(weeks_since_deload=4)).warnings)
    assert not any("deload" in w.lower() for w in _v(s, LiftContext(weeks_since_deload=2)).warnings)
    rec = _v(s, LiftContext(is_recovery_week=True))
    assert any("Recovery week" in w and "RIR" in w for w in rec.warnings)


def test_dup_warns_when_all_sessions_same_rep_zone():
    same = [sess(d, [ex("INC", "Incline Bench Press (Dumbbell)", rr=(8, 10))], title=f"S{d}") for d in (0, 1, 2)]
    varied = [sess(0, [ex("INC", "Incline Bench Press (Dumbbell)", rr=(6, 8))], title="A"),
              sess(1, [ex("INC", "Incline Bench Press (Dumbbell)", rr=(8, 10))], title="B"),
              sess(2, [ex("INC", "Incline Bench Press (Dumbbell)", rr=(12, 15))], title="C")]
    assert any("undulat" in w.lower() for w in _v(same, LiftContext()).warnings)
    assert not any("undulat" in w.lower() for w in _v(varied, LiftContext()).warnings)


def test_activation_sets_for_tier2_and_tier3_compounds():
    s = [sess(1, [ex("RDLD", "Romanian Deadlift (DB)", rr=(8, 10))], stype="legs", title="Legs")]
    assert any("activation" in w.lower() for w in _v(s, LiftContext(run_load="light")).warnings)
    s_ok = [sess(1, [ExercisePrescription(exercise_template_id="RDLD", title="Romanian Deadlift (DB)", sets=3,
                                          warmup_sets=1, rep_range=[8, 10], target_rir=2)], stype="legs",
                 title="Legs")]
    assert not any("activation" in w.lower() for w in _v(s_ok, LiftContext(run_load="light")).warnings)


def test_format_line_shows_pounds_for_lbs_entered_loads():
    line = format_exercise_line(ex("TP", "Triceps Pushdown", sets=2, rr=(10, 12), load=54.431084))
    assert "@ 120 lb (54.4 kg)" in line


def test_strength_sessions_inherit_week_number(monkeypatch):
    from resilio.api import lifting as lift_api

    monkeypatch.setattr(lift_api, "catalog", lambda: CAT)
    monkeypatch.setattr(lift_api, "_lifting_profile", lambda: PROFILE)
    monkeypatch.setattr(lift_api, "_week_context", lambda week, start: None)
    week = {"week_number": 3, "start_date": "2026-10-19", "workouts": [],
            "strength_sessions": [{"date": "2026-10-19", "day_of_week": 0, "session_type": "upper",
                                   "exercises": [{"exercise_template_id": "INC", "title": "Incline Bench Press (Dumbbell)",
                                                  "sets": 3, "rep_range": [8, 10], "target_rir": 2}]}]}
    out = lift_api.validate_week_lifting(week)
    assert not any("invalid" in e for e in out["errors"]), out["errors"]


def test_save_plan_review_handles_non_ascii(tmp_path, monkeypatch):
    """save-review crashed on ✅ under cp1252; review files are UTF-8 now."""
    from types import SimpleNamespace

    import resilio.core.plan as core_plan

    monkeypatch.setattr(core_plan, "_generate_approval_block", lambda *a, **k: "Approuvé ✅")
    monkeypatch.setattr(core_plan, "current_plan_review_path", lambda: "review.md")
    src = tmp_path / "src.md"
    src.write_text("# Plan — semaine clé ✅ Séance", encoding="utf-8")
    repo = SimpleNamespace(resolve_path=lambda p: str(tmp_path / p))
    core_plan.save_plan_review(str(src), plan=None, repo=repo)
    assert "Séance" in (tmp_path / "review.md").read_text(encoding="utf-8")


def test_populate_inherits_week_number_on_workouts(monkeypatch):
    """export-week output omits workouts[].week_number; populate fills it from the week."""
    import resilio.api.plan as plan_api

    seen = {}

    def fake_validate(week_data):
        seen["numbers"] = [w.get("week_number") for w in week_data["workouts"]]
        raise RuntimeError("stop after inheritance")

    monkeypatch.setattr(plan_api, "_validate_explicit_workouts", fake_validate)
    monkeypatch.setattr(plan_api, "get_current_plan", lambda: SimpleNamespace(weeks=[]))
    week = {"week_number": 4, "workouts": [{"date": "2026-11-09"}, {"date": "2026-11-11", "week_number": 4}]}
    with pytest.raises(RuntimeError):
        plan_api.populate_plan_workouts([week])
    assert seen["numbers"] == [4, 4]


def test_load_suggestion_report_has_display_with_pounds():
    week = {"weeks": [{"week_number": 2, "strength_sessions": [{"exercises": [
        {"exercise_template_id": "TP", "title": "Triceps Pushdown", "sets": 2, "rep_range": [10, 12]}]}]}]}

    def suggest(tid, rep_range, deload):
        return SimpleNamespace(action="hold", suggested_load_kg=54.431084, reason="r")

    report = apply_load_suggestions(week, suggest)
    assert report[0]["display"] == "120 lb (54.4 kg)"
