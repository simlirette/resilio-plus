"""Automatic Google Calendar synchronization after plan mutations."""

from __future__ import annotations

import json
from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from resilio.cli.commands import calendar as calendar_commands
from resilio.cli.commands import plan as plan_commands
from resilio.cli.output import create_error_envelope, create_success_envelope
from resilio.core.calendar_sync import SyncReport
from resilio.core.google_calendar import GoogleCalendarAuthError, GoogleCalendarClient
from resilio.schemas.config import GoogleCalendarSettings

runner = CliRunner()


def _future_week(week_number: int) -> SimpleNamespace:
    start = date.today() + timedelta(days=7 * week_number)
    return SimpleNamespace(
        week_number=week_number,
        start_date=start,
        end_date=start + timedelta(days=6),
    )


def test_sync_current_plan_targets_changed_week_beyond_default_window(monkeypatch, tmp_path):
    settings = GoogleCalendarSettings()
    weeks = [_future_week(1), _future_week(5)]
    plan = SimpleNamespace(weeks=weeks)
    client = MagicMock()
    syncer = MagicMock()
    syncer.sync.return_value = SyncReport(inserted=3)

    monkeypatch.setattr(
        calendar_commands,
        "load_config",
        lambda _root: SimpleNamespace(
            settings=SimpleNamespace(google_calendar=settings)
        ),
    )
    monkeypatch.setattr("resilio.api.plan.get_current_plan", lambda: plan)
    monkeypatch.setattr(
        "resilio.core.google_calendar.GoogleCalendarClient",
        lambda *_args: client,
    )
    monkeypatch.setattr(
        "resilio.core.calendar_sync.PlanToCalendarSync",
        lambda *_args: syncer,
    )

    result = calendar_commands.sync_current_plan(
        tmp_path,
        week_numbers=[5],
        interactive_auth=False,
    )

    assert result.ok is True
    assert result.data["inserted"] == 3
    assert result.data["weeks_synced"] == 1
    client.authenticate.assert_called_once_with(interactive=False)
    synced_weeks = syncer.sync.call_args.args[0]
    assert [week.week_number for week in synced_weeks] == [5]


def test_noninteractive_auth_never_starts_browser_flow(monkeypatch, tmp_path):
    credentials_path = tmp_path / "credentials.json"
    credentials_path.write_text("{}")
    flow_factory = MagicMock()
    monkeypatch.setattr(
        "google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file",
        flow_factory,
    )

    client = GoogleCalendarClient(credentials_path, tmp_path / "missing-token.json")

    with pytest.raises(GoogleCalendarAuthError, match="authorization is required"):
        client.authenticate(interactive=False)

    flow_factory.assert_not_called()


def test_calendar_failure_does_not_turn_committed_plan_into_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(
        plan_commands,
        "sync_current_plan",
        lambda *_args, **_kwargs: create_error_envelope(
            error_type="auth",
            message="authorization required",
        ),
    )
    plan_envelope = create_success_envelope(
        message="Plan saved",
        data={"weeks": [{"week_number": 2}]},
    )
    ctx = SimpleNamespace(obj=SimpleNamespace(repo_root=tmp_path))

    result = plan_commands._auto_sync_calendar_after_plan_change(
        ctx,
        plan_envelope,
        [2],
    )

    assert result.ok is True
    assert result.data["weeks"] == [{"week_number": 2}]
    assert result.data["calendar_sync"]["ok"] is False
    assert "plan saved but Google Calendar sync failed" in result.message


def test_plan_populate_automatically_syncs_approved_week(monkeypatch, tmp_path):
    payload_path = tmp_path / "week-2.json"
    payload_path.write_text(json.dumps({"weeks": [{"week_number": 2}]}))
    approval_state = SimpleNamespace(
        weekly_approval=SimpleNamespace(
            week_number=2,
            approved_file=str(payload_path),
        )
    )
    calendar_sync = MagicMock(
        return_value=create_success_envelope(
            message="Calendar sync complete",
            data={"inserted": 3, "weeks_synced": 1},
        )
    )

    monkeypatch.setattr("resilio.core.state.load_approval_state", lambda: approval_state)
    monkeypatch.setattr(
        plan_commands,
        "populate_plan_workouts",
        lambda _weeks: {"weeks": [{"week_number": 2}]},
    )
    monkeypatch.setattr(plan_commands, "sync_current_plan", calendar_sync)

    result = runner.invoke(
        plan_commands.app,
        ["populate", "--from-json", str(payload_path)],
        obj=SimpleNamespace(repo_root=tmp_path),
    )

    assert result.exit_code == 0, result.stdout
    response = json.loads(result.stdout)
    assert response["ok"] is True
    assert response["data"]["calendar_sync"]["ok"] is True
    calendar_sync.assert_called_once_with(
        tmp_path,
        week_numbers=[2],
        interactive_auth=False,
    )


def test_plan_update_from_automatically_syncs_all_changed_weeks(monkeypatch, tmp_path):
    payload_path = tmp_path / "weeks.json"
    payload_path.write_text(
        json.dumps({"weeks": [{"week_number": 4}, {"week_number": 5}]})
    )
    calendar_sync = MagicMock(
        return_value=create_success_envelope(
            message="Calendar sync complete",
            data={"patched": 2, "weeks_synced": 2},
        )
    )

    monkeypatch.setattr(
        plan_commands,
        "update_plan_from_week",
        lambda _start, weeks: {"weeks": weeks},
    )
    monkeypatch.setattr(plan_commands, "sync_current_plan", calendar_sync)

    result = runner.invoke(
        plan_commands.app,
        ["update-from", "--week", "4", "--from-json", str(payload_path)],
        obj=SimpleNamespace(repo_root=tmp_path),
    )

    assert result.exit_code == 0, result.stdout
    calendar_sync.assert_called_once_with(
        tmp_path,
        week_numbers=[4, 5],
        interactive_auth=False,
    )
