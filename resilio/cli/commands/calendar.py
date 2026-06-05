"""
resilio calendar - Google Calendar sync commands.

resilio calendar auth    — one-time browser OAuth flow
resilio calendar sync    — push plan to "Resilio Training" calendar
"""

from pathlib import Path
from typing import Optional

import typer

from resilio.cli.errors import EXIT_AUTH_FAILURE, EXIT_CONFIG_MISSING, EXIT_SUCCESS
from resilio.cli.output import create_error_envelope, create_success_envelope, output_json
from resilio.core.config import load_config, ConfigError

app = typer.Typer(help="Sync training plan to Google Calendar")


def _get_client_and_settings(repo_root: Path):
    """Load config + build GoogleCalendarClient. Returns (client, settings) or raises."""
    from resilio.core.google_calendar import GoogleCalendarClient, GoogleCalendarAuthError

    config_result = load_config(repo_root)
    if isinstance(config_result, ConfigError):
        raise typer.Exit(code=EXIT_CONFIG_MISSING)

    settings = config_result.settings.google_calendar
    credentials_path = repo_root / settings.credentials_path
    token_path = repo_root / settings.token_path

    client = GoogleCalendarClient(credentials_path, token_path)
    return client, settings


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
    from resilio.api.plan import get_plan_weeks, PlanError
    from resilio.core.google_calendar import GoogleCalendarAuthError, GoogleCalendarError
    from resilio.core.calendar_sync import PlanToCalendarSync

    cli_ctx = ctx.obj
    repo_root = cli_ctx.repo_root or Path.cwd()

    # Load config
    config_result = load_config(repo_root)
    if isinstance(config_result, ConfigError):
        envelope = create_error_envelope(
            error_type="config",
            message="Failed to load config",
            data={"next_steps": "Run: resilio init"},
        )
        output_json(envelope)
        raise typer.Exit(code=EXIT_CONFIG_MISSING)

    settings = config_result.settings.google_calendar
    weeks_ahead = weeks if weeks is not None else settings.sync_weeks_ahead

    # Load plan weeks (current + ahead)
    from datetime import date
    from resilio.api.plan import get_current_plan, PlanError as PE
    plan = get_current_plan()
    if isinstance(plan, PE):
        envelope = create_error_envelope(
            error_type="not_found",
            message=f"No plan: {plan.message}",
            data={"next_steps": "Generate a plan first"},
        )
        output_json(envelope)
        raise typer.Exit(code=1)

    today = date.today()
    target_weeks = [
        w for w in plan.weeks
        if w.end_date >= today
    ][:weeks_ahead]

    if not target_weeks:
        envelope = create_success_envelope(
            message="No upcoming weeks in plan window",
            data={"weeks_checked": weeks_ahead},
        )
        output_json(envelope)
        raise typer.Exit(code=EXIT_SUCCESS)

    # Build client
    from resilio.core.google_calendar import GoogleCalendarClient, GoogleCalendarAuthError
    credentials_path = repo_root / settings.credentials_path
    token_path = repo_root / settings.token_path
    state_path = repo_root / settings.state_path
    client = GoogleCalendarClient(credentials_path, token_path)

    if not dry_run:
        try:
            client.authenticate()
        except GoogleCalendarAuthError as exc:
            envelope = create_error_envelope(
                error_type="auth",
                message=str(exc),
                data={"next_steps": "Run: resilio calendar auth"},
            )
            output_json(envelope)
            raise typer.Exit(code=EXIT_AUTH_FAILURE)

    syncer = PlanToCalendarSync(client, settings, state_path)

    try:
        report = syncer.sync(target_weeks, dry_run=dry_run, force=force)
    except GoogleCalendarError as exc:
        envelope = create_error_envelope(
            error_type="api",
            message=str(exc),
        )
        output_json(envelope)
        raise typer.Exit(code=1)

    envelope = create_success_envelope(
        message=f"Calendar sync {'(dry-run) ' if dry_run else ''}complete: {report.summary()}",
        data={
            "inserted": report.inserted,
            "patched": report.patched,
            "deleted": report.deleted,
            "skipped": report.skipped,
            "errors": report.errors,
            "weeks_synced": len(target_weeks),
            "dry_run": dry_run,
        },
    )
    output_json(envelope)
    raise typer.Exit(code=EXIT_SUCCESS)
