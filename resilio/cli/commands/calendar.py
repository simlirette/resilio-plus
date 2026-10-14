"""
resilio calendar - Google Calendar sync commands.

resilio calendar auth    — one-time browser OAuth flow
resilio calendar sync    — push plan to "Resilio Training" calendar
"""

from pathlib import Path
from typing import Iterable, Optional

import typer

from resilio.cli.errors import (
    EXIT_AUTH_FAILURE,
    EXIT_CONFIG_MISSING,
    EXIT_SUCCESS,
    get_exit_code_from_envelope,
)
from resilio.cli.output import (
    OutputEnvelope,
    create_error_envelope,
    create_success_envelope,
    output_json,
)
from resilio.core.config import ConfigError, load_config

app = typer.Typer(help="Sync training plan to Google Calendar")


def _get_client_and_settings(repo_root: Path):
    """Load config + build GoogleCalendarClient. Returns (client, settings) or raises."""
    from resilio.core.google_calendar import GoogleCalendarClient

    config_result = load_config(repo_root)
    if isinstance(config_result, ConfigError):
        raise typer.Exit(code=EXIT_CONFIG_MISSING)

    settings = config_result.settings.google_calendar
    credentials_path = repo_root / settings.credentials_path
    token_path = repo_root / settings.token_path

    client = GoogleCalendarClient(credentials_path, token_path)
    return client, settings


def sync_current_plan(
    repo_root: Path,
    weeks: Optional[int] = None,
    *,
    week_numbers: Optional[Iterable[int]] = None,
    dry_run: bool = False,
    force: bool = False,
    interactive_auth: bool = True,
) -> OutputEnvelope:
    """Synchronize selected future plan weeks and return a CLI envelope.

    ``week_numbers`` is used by automatic plan-write hooks so a newly added or
    modified week is synchronized even when it falls beyond the normal rolling
    window. Manual syncs omit it and retain the configured weeks-ahead behavior.
    """
    from datetime import date

    from resilio.api.plan import PlanError, get_current_plan
    from resilio.core.calendar_sync import PlanToCalendarSync
    from resilio.core.google_calendar import (
        GoogleCalendarAuthError,
        GoogleCalendarClient,
        GoogleCalendarError,
    )

    config_result = load_config(repo_root)
    if isinstance(config_result, ConfigError):
        return create_error_envelope(
            error_type="config",
            message="Failed to load config",
            data={"next_steps": "Run: resilio init"},
        )

    settings = config_result.settings.google_calendar
    plan = get_current_plan()
    if isinstance(plan, PlanError):
        return create_error_envelope(
            error_type="not_found",
            message=f"No plan: {plan.message}",
            data={"next_steps": "Generate a plan first"},
        )

    today = date.today()
    requested_week_numbers = set(week_numbers) if week_numbers is not None else None
    if requested_week_numbers is not None:
        target_weeks = [
            week
            for week in plan.weeks
            if week.week_number in requested_week_numbers and week.end_date >= today
        ]
    else:
        weeks_ahead = weeks if weeks is not None else settings.sync_weeks_ahead
        target_weeks = [week for week in plan.weeks if week.end_date >= today][:weeks_ahead]

    if not target_weeks:
        return create_success_envelope(
            message="No upcoming weeks in plan window",
            data={
                "inserted": 0,
                "patched": 0,
                "deleted": 0,
                "skipped": 0,
                "errors": [],
                "weeks_synced": 0,
                "dry_run": dry_run,
            },
        )

    credentials_path = repo_root / settings.credentials_path
    token_path = repo_root / settings.token_path
    state_path = repo_root / settings.state_path
    client = GoogleCalendarClient(credentials_path, token_path)

    if not dry_run:
        try:
            client.authenticate(interactive=interactive_auth)
        except GoogleCalendarAuthError as exc:
            return create_error_envelope(
                error_type="auth",
                message=str(exc),
                data={"next_steps": "Run: resilio calendar auth"},
            )

    syncer = PlanToCalendarSync(client, settings, state_path)
    try:
        report = syncer.sync(target_weeks, dry_run=dry_run, force=force)
    except GoogleCalendarError as exc:
        return create_error_envelope(error_type="api", message=str(exc))

    data = {
        "inserted": report.inserted,
        "patched": report.patched,
        "deleted": report.deleted,
        "skipped": report.skipped,
        "errors": report.errors,
        "weeks_synced": len(target_weeks),
        "dry_run": dry_run,
    }
    if report.errors:
        return create_error_envelope(
            error_type="api",
            message=f"Calendar sync incomplete: {report.summary()}",
            data=data,
        )

    return create_success_envelope(
        message=f"Calendar sync {'(dry-run) ' if dry_run else ''}complete: {report.summary()}",
        data=data,
    )


@app.command(name="auth")
def auth_command(ctx: typer.Context) -> None:
    """Authorise resilio to access Google Calendar (opens browser on first run)."""
    from resilio.core.google_calendar import GoogleCalendarAuthError

    cli_ctx = ctx.obj
    repo_root = cli_ctx.repo_root or Path.cwd()

    try:
        client, _ = _get_client_and_settings(repo_root)
        client.authenticate()
    except GoogleCalendarAuthError as exc:
        envelope = create_error_envelope(
            error_type="auth",
            message=str(exc),
            data={"next_steps": "Check credentials.json exists in repo root"},
        )
        output_json(envelope)
        raise typer.Exit(code=EXIT_AUTH_FAILURE)

    envelope = create_success_envelope(
        message="Google Calendar authenticated",
        data={"next_steps": ["Run: resilio calendar sync"]},
    )
    output_json(envelope)
    raise typer.Exit(code=EXIT_SUCCESS)


@app.command(name="sync")
def sync_command(
    ctx: typer.Context,
    weeks: int = typer.Option(
        None, "--weeks", "-w", help="Weeks ahead to sync (default from settings)"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show planned changes without calling API"
    ),
    force: bool = typer.Option(
        False, "--force", help="Ignore local state cache, re-evaluate all events"
    ),
) -> None:
    """Push training plan (runs + gym) to Google Calendar."""
    cli_ctx = ctx.obj
    repo_root = cli_ctx.repo_root or Path.cwd()
    envelope = sync_current_plan(
        repo_root,
        weeks,
        dry_run=dry_run,
        force=force,
        interactive_auth=True,
    )
    output_json(envelope)
    raise typer.Exit(code=get_exit_code_from_envelope(envelope))
