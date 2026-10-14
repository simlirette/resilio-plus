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
