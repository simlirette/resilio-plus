"""Catalog mapping + pure lifting analysis (e1RM, history, weekly volume, progression)."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from resilio.core.lifting.analysis import (
    e1rm,
    exercise_history,
    progression,
    weekly_volume,
)
from resilio.core.lifting.catalog import build_catalog, classify_pattern, load_landmarks
from resilio.schemas.lifting import ExerciseTemplate, HevyWorkout


def _t(tid, title, primary, secondary=(), ttype="weight_reps"):
    return ExerciseTemplate(
        id=tid,
        title=title,
        type=ttype,
        primary_muscle_group=primary,
        secondary_muscle_groups=list(secondary),
    )


TEMPLATES = {
    t.id: t
    for t in [
        _t("SQ", "Squat (Barbell)", "quadriceps", ["glutes", "hamstrings"]),
        _t("RDL", "Romanian Deadlift (Dumbbell)", "hamstrings", ["glutes", "lower_back"]),
        _t("BSS", "Bulgarian Split Squat", "quadriceps", ["glutes"]),
        _t("ROW", "Dumbbell Row", "upper_back", ["lats", "biceps"]),
        _t("INC", "Incline Bench Press (Dumbbell)", "chest", ["shoulders", "triceps"]),
        _t("PU", "Pull Up", "lats", ["biceps"], "bodyweight_reps"),
        _t("BOX", "Box Jump", "quadriceps", [], "reps_only"),
        _t("PLK", "Plank", "abdominals", [], "duration"),
        _t("SHR", "Shrug (Barbell)", "traps", []),
    ]
}


def _w(wid, day, exercises):
    start = datetime(2026, 10, day, 10, 0, tzinfo=timezone.utc)
    return HevyWorkout.model_validate(
        {
            "id": wid,
            "title": "S",
            "start_time": start.isoformat(),
            "exercises": [
                {
                    "index": i,
                    "title": title,
                    "exercise_template_id": tid,
                    "sets": [
                        {"index": j, "type": typ, "weight_kg": wkg, "reps": reps}
                        for j, (typ, wkg, reps) in enumerate(sets)
                    ],
                }
                for i, (tid, title, sets) in enumerate(exercises)
            ],
        }
    )


# ---------------------------------------------------------------- catalog


def test_catalog_maps_groups_and_lower_body():
    cat = build_catalog(TEMPLATES)
    assert cat["SQ"].primary_group == "quads" and cat["SQ"].lower_body is True
    assert set(cat["SQ"].secondary_groups) == {"glutes", "hamstrings"}
    assert cat["ROW"].primary_group == "back" and cat["ROW"].lower_body is False
    assert cat["RDL"].secondary_groups == ["glutes"]  # lower_back is not a counted group
    assert cat["SHR"].primary_group is None  # traps not counted


@pytest.mark.parametrize(
    "title,pattern",
    [
        ("Bulgarian Split Squat", "lunge"),
        ("Squat (Barbell)", "squat"),
        ("Romanian Deadlift (Dumbbell)", "hinge"),
        ("Box Jump", "plyo"),
        ("Plank", "core"),
        ("Dumbbell Row", "pull"),
        ("Incline Bench Press (Dumbbell)", "push"),
        ("Lateral Raise (Dumbbell)", "isolation"),
        ("Medicine Ball Slam", "plyo"),
    ],
)
def test_classify_pattern(title, pattern):
    assert classify_pattern(title) == pattern


def test_sfr_tier_list_first_then_heuristic():
    def t(tid, title, primary, equipment):
        return ExerciseTemplate(id=tid, title=title, primary_muscle_group=primary, equipment=equipment)

    cat = build_catalog({x.id: x for x in [
        t("a", "Romanian Deadlift (Dumbbell)", "hamstrings", "dumbbell"),   # list: tier 2
        t("b", "Lat Pulldown (Cable)", "lats", "machine"),                  # machine/cable: 1
        t("c", "Squat (Barbell)", "quadriceps", "barbell"),                 # barbell squat: 3
        t("d", "Deadlift (Barbell)", "hamstrings", "barbell"),              # barbell deadlift: 3
        t("e", "Bent Over Row (Barbell)", "upper_back", "barbell"),         # barbell row: 2
        t("f", "Bulgarian Split Squat (Dumbbell)", "quadriceps", "dumbbell"),  # DB compound: 2
        t("g", "Lateral Raise (Dumbbell)", "shoulders", "dumbbell"),        # isolation: 1
        t("h", "Box Jump", "quadriceps", "none"),                           # plyo: none
        t("i", "Pull Up", "lats", "none"),                                  # bodyweight compound: 2
    ]})
    assert {k: v.sfr_tier for k, v in cat.items()} == {
        "a": 2, "b": 1, "c": 3, "d": 3, "e": 2, "f": 2, "g": 1, "h": None, "i": 2}


def test_landmarks_are_packaged():
    lm = load_landmarks()
    assert lm["quads"]["MEV"] == 8 and lm["quads"]["hybrid_reduction"] == 0.4


# ------------------------------------------------------------------- e1RM


def test_e1rm_epley_and_limits():
    assert e1rm(100, 5) == pytest.approx(116.7, abs=0.05)
    assert e1rm(100, 13) is None
    assert e1rm(None, 5) is None and e1rm(0, 5) is None


# ---------------------------------------------------------------- history


def test_exercise_history_ignores_warmups_and_tracks_trend():
    ws = [
        _w(
            "a",
            1,
            [("INC", "Incline", [("warmup", 10, 12), ("normal", 22.5, 10), ("normal", 22.5, 9)])],
        ),
        _w("b", 8, [("INC", "Incline", [("normal", 25, 8), ("normal", 25, 8)])]),
    ]
    h = exercise_history(ws, "INC", title="Incline", weeks=8, today=date(2026, 10, 14))
    assert [s.working_sets for s in h.sessions] == [2, 2]
    assert h.sessions[1].top_weight_kg == 25 and h.sessions[1].top_set_reps == 8
    assert h.e1rm_trend_kg == pytest.approx(e1rm(25, 8) - e1rm(22.5, 10), abs=0.1)


# ----------------------------------------------------------------- volume


def test_weekly_volume_counts_primary_full_secondary_half_and_hybrid():
    ws = [
        _w(
            "a",
            13,
            [
                ("SQ", "Squat", [("warmup", 40, 10)] + [("normal", 60, 8)] * 3),
                ("XX", "Mystery Machine", [("normal", 10, 10)]),
            ],
        ),
        _w("b", 15, [("ROW", "Row", [("normal", 25, 10)] * 4)]),
        _w("old", 5, [("SQ", "Squat", [("normal", 60, 8)] * 9)]),  # previous week
    ]
    rep = weekly_volume(ws, build_catalog(TEMPLATES), date(2026, 10, 12), hybrid=True)
    g = {m.group: m for m in rep.groups}
    assert g["quads"].hard_sets == 3
    assert g["glutes"].hard_sets == 1.5 and g["hamstrings"].hard_sets == 1.5
    # ROW: upper_back primary (back), lats secondary also maps to back → not double counted
    assert g["back"].hard_sets == 4 and g["biceps"].hard_sets == 2.0
    assert g["quads"].mrv == pytest.approx(20 * 0.6)
    assert g["quads"].status == "below_mev"
    assert rep.unmapped_exercises == ["Mystery Machine"]
    assert rep.workouts_counted == 2


def test_weekly_volume_without_hybrid_keeps_full_mrv():
    rep = weekly_volume([], build_catalog(TEMPLATES), date(2026, 10, 12), hybrid=False)
    assert {m.group: m.mrv for m in rep.groups}["quads"] == 20


# ------------------------------------------------------------ progression


def _hist(sets, day=8):
    ws = [_w("a", day, [("INC", "Incline", sets)])]
    return exercise_history(ws, "INC", title="Incline", weeks=8, today=date(2026, 10, 14))


def test_progression_increase_load_when_all_sets_at_top():
    s = progression(
        _hist([("normal", 25, 10)] * 3), [8, 10], increment_kg=2.5, today=date(2026, 10, 14)
    )
    assert s.action == "increase_load" and s.suggested_load_kg == 27.5 and s.target_reps == 8
    assert s.suggested_sets == 3


def test_progression_add_reps_inside_range():
    s = progression(
        _hist([("normal", 25, 9), ("normal", 25, 8)]), [8, 10], 2.5, today=date(2026, 10, 14)
    )
    assert s.action == "add_reps" and s.suggested_load_kg == 25 and s.target_reps == 9


def test_progression_hold_when_below_range():
    s = progression(
        _hist([("normal", 25, 6), ("normal", 25, 7)]), [8, 10], 2.5, today=date(2026, 10, 14)
    )
    assert s.action == "hold" and s.suggested_load_kg == 25 and s.target_reps == 8


def test_progression_deload_cuts_sets_keeps_load():
    s = progression(
        _hist([("normal", 25, 10)] * 4), [8, 10], 2.5, deload=True, today=date(2026, 10, 14)
    )
    assert s.action == "deload" and s.suggested_sets == 2 and s.suggested_load_kg == 25


def test_progression_no_recent_history():
    s = progression(_hist([("normal", 25, 10)], day=1), [8, 10], 2.5, today=date(2026, 11, 30))
    assert s.action == "no_recent_history" and s.suggested_load_kg is None


def test_progression_bodyweight():
    ws = [_w("a", 8, [("PU", "Pull Up", [("normal", None, 12), ("normal", None, 10)])])]
    h = exercise_history(ws, "PU", title="Pull Up", weeks=8, today=date(2026, 10, 14))
    s = progression(h, [8, 12], 2.5, today=date(2026, 10, 14))
    assert s.action == "bodyweight" and s.suggested_load_kg is None and s.target_reps == 11


def test_lbs_entered_loads_round_to_half_kg():
    ws = [_w("a", 8, [("INC", "Incline", [("normal", 40.82336184920758, 10)] * 3)])]
    h = exercise_history(ws, "INC", title="Incline", weeks=8, today=date(2026, 10, 14))
    assert h.sessions[0].top_weight_kg == 40.82
    s = progression(h, [8, 10], 2.5, today=date(2026, 10, 14))
    assert s.action == "increase_load" and s.suggested_load_kg == 43.5
