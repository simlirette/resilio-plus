"""resilio.api.lifting — orchestration over store/catalog/analysis with typed errors."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from resilio.api import lifting as api
from resilio.core.lifting.hevy_client import HevyAuthError, HevyConfigError
from resilio.core.lifting.store import LiftingStore
from resilio.schemas.lifting import ExerciseTemplate, HevyWorkout, LiftingProfile


@pytest.fixture
def store(tmp_path, monkeypatch):
    s = LiftingStore(tmp_path / "lifting")
    monkeypatch.setattr(api, "_store", lambda: s)
    s.save_templates(
        [
            ExerciseTemplate(
                id="INC",
                title="Incline Bench Press (Dumbbell)",
                primary_muscle_group="chest",
                secondary_muscle_groups=["shoulders", "triceps"],
            ),
            ExerciseTemplate(
                id="RDL",
                title="Romanian Deadlift (Dumbbell)",
                primary_muscle_group="hamstrings",
                secondary_muscle_groups=["glutes"],
            ),
            ExerciseTemplate(
                id="RDLB", title="Romanian Deadlift (Barbell)", primary_muscle_group="hamstrings"
            ),
        ]
    )
    for wid, day, tid, title, load, reps in [
        ("a", 6, "INC", "Incline Bench Press (Dumbbell)", 25, 10),
        ("b", 8, "RDL", "Romanian Deadlift (Dumbbell)", 20, 12),
    ]:
        s.save_workout(
            HevyWorkout.model_validate(
                {
                    "id": wid,
                    "title": "S",
                    "start_time": datetime(2026, 10, day, 10, tzinfo=timezone.utc).isoformat(),
                    "exercises": [
                        {
                            "index": 0,
                            "title": title,
                            "exercise_template_id": tid,
                            "sets": [
                                {"index": i, "type": "normal", "weight_kg": load, "reps": reps}
                                for i in range(3)
                            ],
                        }
                    ],
                }
            )
        )
    return s


@pytest.fixture
def profile(monkeypatch):
    lp = LiftingProfile(
        gym_days=["monday", "tuesday", "wednesday"],
        compound_rep_range=[6, 10],
        accessory_rep_range=[10, 15],
    )
    monkeypatch.setattr(api, "_lifting_profile", lambda: lp)
    return lp


def test_resolve_exercise_by_id_exact_title_and_unique_substring(store):
    assert api.resolve_exercise("INC") == ("INC", "Incline Bench Press (Dumbbell)")
    assert api.resolve_exercise("incline bench press (dumbbell)")[0] == "INC"
    assert api.resolve_exercise("incline")[0] == "INC"


def test_resolve_exercise_ambiguous_returns_error(store):
    err = api.resolve_exercise("romanian")
    assert isinstance(err, api.LiftError) and err.error_type == "validation"
    assert "Romanian Deadlift (Barbell)" in err.message


def test_history_and_progression(store, profile):
    h = api.get_lift_history("Incline Bench Press (Dumbbell)", weeks=8, today=date(2026, 10, 14))
    assert len(h.sessions) == 1 and h.sessions[0].top_weight_kg == 25
    p = api.get_lift_progression("INC", today=date(2026, 10, 14))
    # INC is a compound push → compound range 6-10; 3×10 at 25 kg → add upper increment
    assert p.action == "increase_load" and p.suggested_load_kg == 27.5 and p.rep_range == [6, 10]
    p2 = api.get_lift_progression("RDL", today=date(2026, 10, 14))
    # RDL is lower body: 3×12 in compound range 6-10 → increase by lower increment 5 kg
    assert p2.suggested_load_kg == 25


def test_volume_for_week(store):
    rep = api.get_lift_volume(week_start="2026-10-05")
    g = {m.group: m.hard_sets for m in rep.groups}
    assert g["chest"] == 3 and g["hamstrings"] == 3 and g["glutes"] == 1.5


def test_volume_rejects_non_monday(store):
    err = api.get_lift_volume(week_start="2026-10-06")
    assert isinstance(err, api.LiftError) and err.error_type == "invalid_input"


def test_sync_maps_missing_key_to_config_error(store, monkeypatch):
    def boom():
        raise HevyConfigError("HEVY_API_KEY is not set")

    monkeypatch.setattr(api, "_client", boom)
    err = api.sync_lifting()
    assert isinstance(err, api.LiftError) and err.error_type == "config"


def test_sync_maps_auth_error(store, monkeypatch):
    class C:
        def iter_workouts(self):
            raise HevyAuthError("401")

    monkeypatch.setattr(api, "_client", lambda: C())
    err = api.sync_lifting(full=True)
    assert isinstance(err, api.LiftError) and err.error_type == "auth"


def test_template_search_filters_by_muscle(store):
    res = api.search_templates("deadlift", muscle="hamstrings")
    assert {e.template_id for e in res} == {"RDL", "RDLB"}
    assert api.search_templates("deadlift", muscle="chest") == []
