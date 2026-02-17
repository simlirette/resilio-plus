"""resilio weather - Weather forecast tools for weekly planning."""

from typing import Optional

import typer

from resilio.api.weather import get_weekly_weather_forecast
from resilio.cli.errors import api_result_to_envelope, get_exit_code_from_envelope
from resilio.cli.output import output_json
from resilio.schemas.weather import WeeklyWeatherForecast

app = typer.Typer(help="Weather forecast for training-planning context")


@app.callback()
def weather_callback() -> None:
    """Weather command group."""


@app.command(name="week")
def weather_week_command(
    ctx: typer.Context,
    start: str = typer.Option(..., "--start", help="Week start date (YYYY-MM-DD, must be Monday)"),
    location: Optional[str] = typer.Option(
        None,
        "--location",
        help="Optional location override (e.g., 'San Francisco, United States')",
    ),
) -> None:
    """Get a Monday-Sunday weather forecast for weekly planning decisions.

    Examples:
        resilio weather week --start 2026-02-16
        resilio weather week --start 2026-02-16 --location "Paris, France"
    """
    result = get_weekly_weather_forecast(start_date=start, location=location)

    success_message = "Retrieved weekly weather forecast"
    if isinstance(result, WeeklyWeatherForecast):
        location_name = result.location.resolved_name or result.location.location_query
        success_message = (
            f"Retrieved weekly weather forecast for {location_name} "
            f"({result.start_date.isoformat()} to {result.end_date.isoformat()})"
        )

    envelope = api_result_to_envelope(result, success_message=success_message)
    output_json(envelope)

    raise typer.Exit(code=get_exit_code_from_envelope(envelope))
