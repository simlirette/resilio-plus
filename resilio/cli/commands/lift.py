"""resilio lift - Hevy-backed lifting: sync, catalog, history, volume, progression, profile."""

from __future__ import annotations

from typing import Optional

import typer

from resilio.api import lifting as api
from resilio.cli.errors import api_result_to_envelope, get_exit_code_from_envelope
from resilio.cli.output import output_json

app = typer.Typer(help="Lifting (Hevy): sync, analysis and prescription tools")
templates_app = typer.Typer(help="Hevy exercise templates (catalog)")
profile_app = typer.Typer(help="Lifting profile (goal, gym days, rep ranges)")
app.add_typer(templates_app, name="templates")
app.add_typer(profile_app, name="profile")


def _emit(result, message: str) -> None:
    envelope = api_result_to_envelope(result, success_message=message)
    output_json(envelope)
    raise typer.Exit(code=get_exit_code_from_envelope(envelope))


def _range(value: Optional[str], name: str) -> Optional[list[int]]:
    if value is None:
        return None
    try:
        lo, hi = (int(x) for x in value.replace(" ", "").split("-", 1))
    except ValueError:
        raise typer.BadParameter(f"{name} must look like 8-12") from None
    return [lo, hi]


def _list(value: Optional[str], sep: str = ",") -> Optional[list[str]]:
    if value is None:
        return None
    return [x.strip() for x in value.split(sep) if x.strip()]


@app.callback()
def lift_callback() -> None:
    """Lifting command group."""


@app.command(name="sync")
def lift_sync_command(
    full: bool = typer.Option(
        False, "--full", help="Re-download every workout instead of replaying changes"
    ),
) -> None:
    """Pull Hevy workouts (sets, reps, kg) into data/lifting/.

    Examples:
        resilio lift sync
        resilio lift sync --full
    """
    result = api.sync_lifting(full=full)
    msg = "Hevy sync complete"
    if not api.is_lift_error(result):
        msg = (
            f"Hevy sync ({result.mode}): +{result.added} new, {result.updated} updated, "
            f"{result.deleted} deleted, {result.total_stored} stored"
        )
    _emit(result, msg)


@templates_app.command(name="sync")
def templates_sync_command() -> None:
    """Cache Hevy exercise templates (muscle groups, equipment)."""
    result = api.sync_exercise_templates()
    _emit(
        result,
        "Exercise templates cached"
        if api.is_lift_error(result)
        else f"Cached {result['templates']} exercise templates",
    )


@templates_app.command(name="search")
def templates_search_command(
    query: str = typer.Argument("", help="Words in the exercise title"),
    muscle: Optional[str] = typer.Option(
        None, "--muscle", help="Hevy muscle group, e.g. hamstrings, chest"
    ),
    limit: int = typer.Option(25, "--limit"),
) -> None:
    """Find exercise template ids (needed in prescriptions).

    Examples:
        resilio lift templates search "romanian deadlift"
        resilio lift templates search --muscle hamstrings
    """
    result = api.search_templates(query, muscle=muscle)
    if not api.is_lift_error(result):
        total = len(result)
        result = result[:limit]
        _emit(
            result, f"{total} template(s) match" + (f"; showing {limit}" if total > limit else "")
        )
    _emit(result, "")


@app.command(name="history")
def lift_history_command(
    exercise: str = typer.Option(..., "--exercise", "-e", help="Template id or title"),
    weeks: int = typer.Option(8, "--weeks", min=1, max=104),
) -> None:
    """Per-session top set, working sets and e1RM for one exercise.

    Example:
        resilio lift history --exercise "Incline Bench Press (Dumbbell)" --weeks 12
    """
    result = api.get_lift_history(exercise, weeks=weeks)
    msg = (
        ""
        if api.is_lift_error(result)
        else f"{result.title}: {len(result.sessions)} session(s) in {weeks} weeks"
    )
    _emit(result, msg)


@app.command(name="volume")
def lift_volume_command(
    week_start: Optional[str] = typer.Option(
        None, "--week-start", help="Monday YYYY-MM-DD (default: this week)"
    ),
    no_hybrid: bool = typer.Option(False, "--no-hybrid", help="Do not reduce MRV for running load"),
) -> None:
    """Hard sets per muscle group vs MEV/MAV/MRV for a Monday-Sunday week.

    Example:
        resilio lift volume --week-start 2026-10-12
    """
    result = api.get_lift_volume(week_start=week_start, hybrid=not no_hybrid)
    msg = ""
    if not api.is_lift_error(result):
        flagged = [g.group for g in result.groups if g.status in ("above_mrv",)]
        msg = (
            f"Week {result.week_start}: {result.workouts_counted} workout(s)"
            + (f"; above MRV: {', '.join(flagged)}" if flagged else "")
            + (
                f"; UNMAPPED: {', '.join(result.unmapped_exercises)}"
                if result.unmapped_exercises
                else ""
            )
        )
    _emit(result, msg)


@app.command(name="progression")
def lift_progression_command(
    exercise: str = typer.Option(..., "--exercise", "-e", help="Template id or title"),
    deload: bool = typer.Option(False, "--deload", help="Deload week suggestion"),
    rep_range: Optional[str] = typer.Option(None, "--rep-range", help="Override, e.g. 8-12"),
) -> None:
    """Next-session load/reps by double progression (no guess without recent history).

    Example:
        resilio lift progression --exercise "Romanian Deadlift (Dumbbell)"
    """
    result = api.get_lift_progression(
        exercise, deload=deload, rep_range=_range(rep_range, "--rep-range")
    )
    _emit(result, "" if api.is_lift_error(result) else f"{result.title}: {result.action}")


@profile_app.command(name="get")
def lift_profile_get_command() -> None:
    """Show the lifting profile."""
    _emit(api.get_lifting_profile(), "Lifting profile")


@profile_app.command(name="set")
def lift_profile_set_command(
    goal: Optional[str] = typer.Option(
        None, "--goal", help="hypertrophy_athletic | hypertrophy | maintenance | strength"
    ),
    gym_days: Optional[str] = typer.Option(None, "--gym-days", help="monday,tuesday,wednesday"),
    optional_days: Optional[str] = typer.Option(None, "--optional-days", help="thursday"),
    split: Optional[str] = typer.Option(None, "--split", help="Upper A,Legs,Upper B,Arms"),
    compound_range: Optional[str] = typer.Option(None, "--compound-range", help="6-10"),
    accessory_range: Optional[str] = typer.Option(None, "--accessory-range", help="10-15"),
    rir: Optional[str] = typer.Option(None, "--rir", help="1-3"),
    min_reps: Optional[int] = typer.Option(None, "--min-reps"),
    power: Optional[bool] = typer.Option(
        None, "--power/--no-power", help="Include light plyo/power work"
    ),
    protected: Optional[str] = typer.Option(
        None, "--protected", help="Semicolon-separated exercise titles"
    ),
    blacklist: Optional[str] = typer.Option(
        None, "--blacklist", help="Semicolon-separated exercise titles"
    ),
    increment_upper: Optional[float] = typer.Option(None, "--increment-upper"),
    increment_lower: Optional[float] = typer.Option(None, "--increment-lower"),
    notes: Optional[str] = typer.Option(None, "--notes"),
) -> None:
    """Create or update the lifting profile (only the options given change).

    Example:
        resilio lift profile set --goal hypertrophy_athletic --gym-days monday,tuesday,wednesday \\
            --optional-days thursday --split "Upper A,Legs,Upper B,Arms" --power
    """
    increments = None
    if increment_upper is not None or increment_lower is not None:
        current = api.get_lifting_profile()
        base = {} if api.is_lift_error(current) else dict(current.increment_kg)
        if increment_upper is not None:
            base["upper"] = increment_upper
        if increment_lower is not None:
            base["lower"] = increment_lower
        increments = base
    result = api.set_lifting_profile(
        goal=goal,
        gym_days=_list(gym_days),
        optional_days=_list(optional_days),
        split=_list(split),
        compound_rep_range=_range(compound_range, "--compound-range"),
        accessory_rep_range=_range(accessory_range, "--accessory-range"),
        rir_target=_range(rir, "--rir"),
        min_reps=min_reps,
        include_power=power,
        protected_exercises=_list(protected, ";"),
        blacklist=_list(blacklist, ";"),
        increment_kg=increments,
        notes=notes,
    )
    _emit(result, "Lifting profile updated")
