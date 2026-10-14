"""resilio lift CLI — envelopes and exit codes (API layer mocked)."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from resilio.api import lifting as api
from resilio.cli import app
from resilio.schemas.lifting import LiftingProfile, LiftingSyncSummary

runner = CliRunner()


def test_lift_sync_success_message(monkeypatch):
    monkeypatch.setattr(
        api,
        "sync_lifting",
        lambda full=False: LiftingSyncSummary(mode="full", added=31, total_stored=31),
    )
    res = runner.invoke(app, ["lift", "sync"])
    assert res.exit_code == 0, res.output
    body = json.loads(res.output)
    assert body["ok"] is True and "+31 new" in body["message"]


def test_lift_sync_missing_key_is_config_exit(monkeypatch):
    monkeypatch.setattr(
        api,
        "sync_lifting",
        lambda full=False: api.LiftError("config", "HEVY_API_KEY is not set", "Set it"),
    )
    res = runner.invoke(app, ["lift", "sync"])
    body = json.loads(res.output)
    assert res.exit_code != 0 and body["ok"] is False and body["error_type"] == "config"


def test_lift_profile_set_parses_lists_and_ranges(monkeypatch):
    captured = {}

    def fake_set(**changes):
        captured.update(changes)
        return LiftingProfile(gym_days=changes["gym_days"])

    monkeypatch.setattr(api, "set_lifting_profile", fake_set)
    res = runner.invoke(
        app,
        [
            "lift",
            "profile",
            "set",
            "--gym-days",
            "monday, tuesday",
            "--compound-range",
            "6-10",
            "--protected",
            "Nordic Hamstring Curl; Step Down",
            "--power",
        ],
    )
    assert res.exit_code == 0, res.output
    assert captured["gym_days"] == ["monday", "tuesday"]
    assert captured["compound_rep_range"] == [6, 10]
    assert captured["protected_exercises"] == ["Nordic Hamstring Curl", "Step Down"]
    assert captured["include_power"] is True and captured["goal"] is None


def test_lift_progression_bad_range_is_usage_error():
    res = runner.invoke(app, ["lift", "progression", "--exercise", "x", "--rep-range", "abc"])
    assert res.exit_code == 2


def test_analysis_load_reads_cli_envelope_and_stored_activities(tmp_path, monkeypatch):
    """`activity list` output feeds `analysis load`; without --activities, stored loads are used."""
    from datetime import date, timedelta
    from types import SimpleNamespace

    import resilio.api.profile as profile_api
    from resilio.cli.commands import analysis as analysis_cmd

    env = {"schema_version": "1.0", "ok": True, "data": {"activities": [{"x": 1}], "count": 1,
                                                          "date_range": {}, "filters": {}}}
    f = tmp_path / "acts.json"
    f.write_text(json.dumps(env), encoding="utf-8")
    assert analysis_cmd._read_json_input(str(f)) == [{"x": 1}]

    recent = SimpleNamespace(date=date.today() - timedelta(days=2), sport_type="strength",
                             calculated=SimpleNamespace(systemic_load_au=22.0, lower_body_load_au=10.0))
    old = SimpleNamespace(date=date.today() - timedelta(days=60), sport_type="run",
                          calculated=SimpleNamespace(systemic_load_au=40.0, lower_body_load_au=40.0))
    monkeypatch.setattr(profile_api, "_load_all_activities", lambda repo: [recent, old])
    rows = analysis_cmd._stored_activity_loads(28)
    assert rows == [{"date": recent.date.isoformat(), "sport_type": "strength",
                     "calculated": {"systemic_load_au": 22.0, "lower_body_load_au": 10.0}}]


def test_create_macro_accepts_weekly_volumes_km_key(tmp_path, monkeypatch):
    """create-macro used to reject templates that only had 'weekly_volumes_km' (the documented key)."""
    # Isolate: the CLI resolves the repo root from cwd; never touch real athlete data.
    (tmp_path / ".git").mkdir()
    monkeypatch.chdir(tmp_path)
    tpl = tmp_path / "macro.json"
    tpl.write_text(json.dumps({"total_weeks": 2, "weekly_volumes_km": [10.0, 12.0],
                               "target_systemic_load_au": [100.0, 110.0],
                               "workout_structure_hints": [{}, {}]}), encoding="utf-8")
    res = runner.invoke(app, ["plan", "create-macro", "--goal-type", "10k", "--total-weeks", "2",
                              "--start-date", "2026-10-19", "--current-ctl", "12", "--baseline-vdot", "35",
                              "--macro-template-json", str(tpl)])
    assert "must include 'weekly_volumes_km'" not in res.output
    assert "must include 'volumes_km'" not in res.output
