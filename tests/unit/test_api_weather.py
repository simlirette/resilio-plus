"""Unit tests for weather API (api/weather.py)."""

from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from resilio.api.profile import ProfileError
from resilio.api.weather import WeatherError, get_weekly_weather_forecast
from resilio.core.weather import WeatherNetworkError, WeatherNotFoundError
from resilio.schemas.weather import DailyWeatherForecast, WeatherLocation, WeeklyWeatherForecast


def _sample_weekly_forecast() -> WeeklyWeatherForecast:
    return WeeklyWeatherForecast(
        start_date=date(2026, 2, 16),
        end_date=date(2026, 2, 22),
        location=WeatherLocation(
            location_query="Paris, France",
            resolved_name="Paris, Ile-de-France, France",
            latitude=48.853,
            longitude=2.3499,
            timezone="Europe/Paris",
        ),
        daily=[
            DailyWeatherForecast(
                date=date(2026, 2, 16),
                temperature_min_c=3,
                temperature_max_c=10,
                precipitation_mm=2,
                precipitation_probability_max_pct=40,
                wind_speed_max_kph=14,
                weather_code=3,
            )
        ],
        advisories=[],
        weekly_summary="No significant weather risks detected for this week.",
    )


def test_invalid_start_date_returns_validation_error():
    result = get_weekly_weather_forecast(start_date="2026-99-99", location="Paris")

    assert isinstance(result, WeatherError)
    assert result.error_type == "invalid_input"


def test_non_monday_start_date_returns_validation_error():
    # 2026-02-17 is Tuesday
    result = get_weekly_weather_forecast(start_date="2026-02-17", location="Paris")

    assert isinstance(result, WeatherError)
    assert result.error_type == "invalid_input"
    assert "Monday" in result.message


@patch("resilio.api.weather.get_weekly_forecast_for_query")
def test_explicit_location_uses_query_lookup(mock_query_lookup):
    mock_query_lookup.return_value = _sample_weekly_forecast()

    result = get_weekly_weather_forecast(start_date="2026-02-16", location="Paris, France")

    assert isinstance(result, WeeklyWeatherForecast)
    mock_query_lookup.assert_called_once()


@patch("resilio.api.weather.get_profile")
def test_missing_profile_location_returns_actionable_error(mock_get_profile):
    profile = SimpleNamespace(weather_preferences=None)
    mock_get_profile.return_value = profile

    result = get_weekly_weather_forecast(start_date="2026-02-16")

    assert isinstance(result, WeatherError)
    assert result.error_type == "invalid_input"
    assert result.next_steps is not None
    assert "profile set --weather-location" in result.next_steps


@patch("resilio.api.weather.get_profile")
def test_profile_validation_error_maps_to_validation(mock_get_profile):
    mock_get_profile.return_value = ProfileError(
        error_type="validation",
        message="invalid profile schema",
    )

    result = get_weekly_weather_forecast(start_date="2026-02-16")

    assert isinstance(result, WeatherError)
    assert result.error_type == "validation"
    assert "validation error" in result.message.lower()


@patch("resilio.api.weather.get_profile")
def test_profile_not_found_error_maps_to_not_found(mock_get_profile):
    mock_get_profile.return_value = ProfileError(
        error_type="not_found",
        message="profile missing",
    )

    result = get_weekly_weather_forecast(start_date="2026-02-16")

    assert isinstance(result, WeatherError)
    assert result.error_type == "not_found"
    assert "profile create" in (result.next_steps or "")


@patch("resilio.api.weather.get_weekly_forecast_for_query")
def test_not_found_maps_to_not_found_error(mock_query_lookup):
    mock_query_lookup.side_effect = WeatherNotFoundError("No location match")

    result = get_weekly_weather_forecast(start_date="2026-02-16", location="unknown")

    assert isinstance(result, WeatherError)
    assert result.error_type == "not_found"


@patch("resilio.api.weather.get_weekly_forecast_for_query")
def test_network_error_maps_to_network_error(mock_query_lookup):
    mock_query_lookup.side_effect = WeatherNetworkError("timeout")

    result = get_weekly_weather_forecast(start_date="2026-02-16", location="Paris")

    assert isinstance(result, WeatherError)
    assert result.error_type == "network"


@patch("resilio.api.weather.update_profile")
@patch("resilio.api.weather.get_weekly_forecast_for_query")
@patch("resilio.api.weather.get_profile")
def test_profile_lookup_persists_cache_when_missing_fields(
    mock_get_profile,
    mock_query_lookup,
    mock_update_profile,
):
    weather_preferences = SimpleNamespace(
        location_query="Paris, France",
        resolved_name=None,
        latitude=None,
        longitude=None,
        timezone=None,
    )
    profile = SimpleNamespace(weather_preferences=weather_preferences)
    mock_get_profile.return_value = profile
    mock_query_lookup.return_value = _sample_weekly_forecast()

    result = get_weekly_weather_forecast(start_date="2026-02-16")

    assert isinstance(result, WeeklyWeatherForecast)
    mock_update_profile.assert_called_once()
    payload = mock_update_profile.call_args.kwargs["weather_preferences"]
    assert payload["location_query"] == "Paris, France"
    assert payload["latitude"] == 48.853
    assert payload["longitude"] == 2.3499
    assert payload["timezone"] == "Europe/Paris"


@patch("resilio.api.weather.update_profile")
@patch("resilio.api.weather.get_weekly_forecast_for_query")
def test_explicit_location_does_not_persist_cache(mock_query_lookup, mock_update_profile):
    mock_query_lookup.return_value = _sample_weekly_forecast()

    result = get_weekly_weather_forecast(start_date="2026-02-16", location="Paris, France")

    assert isinstance(result, WeeklyWeatherForecast)
    mock_update_profile.assert_not_called()


@patch("resilio.api.weather.update_profile")
@patch("resilio.api.weather.get_weekly_forecast_for_query")
@patch("resilio.api.weather.get_profile")
def test_cache_write_failure_does_not_fail_weather_lookup(
    mock_get_profile,
    mock_query_lookup,
    mock_update_profile,
):
    weather_preferences = SimpleNamespace(
        location_query="Paris, France",
        resolved_name=None,
        latitude=None,
        longitude=None,
        timezone=None,
    )
    profile = SimpleNamespace(weather_preferences=weather_preferences)
    mock_get_profile.return_value = profile
    mock_query_lookup.return_value = _sample_weekly_forecast()
    mock_update_profile.return_value = SimpleNamespace(
        error_type="unknown",
        message="write failed",
    )

    result = get_weekly_weather_forecast(start_date="2026-02-16")

    assert isinstance(result, WeeklyWeatherForecast)


@patch("resilio.api.weather.update_profile")
@patch("resilio.api.weather.get_weekly_forecast_for_location")
@patch("resilio.api.weather.get_profile")
def test_profile_cached_coordinates_use_location_lookup(
    mock_get_profile,
    mock_location_lookup,
    mock_update_profile,
):
    """Cached coordinates path uses get_weekly_forecast_for_location.

    When coordinates + timezone match the returned forecast, resolved_name
    differences alone do NOT trigger a cache write (resolved_name is excluded
    from change detection to avoid spurious profile writes on cosmetic name
    formatting differences).
    """
    weather_preferences = SimpleNamespace(
        location_query="Paris, France",
        resolved_name="Paris, France",  # differs from sample ("Paris, Ile-de-France, France")
        latitude=48.853,
        longitude=2.3499,
        timezone="Europe/Paris",
    )
    profile = SimpleNamespace(weather_preferences=weather_preferences)
    mock_get_profile.return_value = profile
    mock_location_lookup.return_value = _sample_weekly_forecast()

    result = get_weekly_weather_forecast(start_date="2026-02-16")

    assert isinstance(result, WeeklyWeatherForecast)
    mock_location_lookup.assert_called_once()
    # resolved_name differs but coordinates match → no cache write (excluded from change detection)
    mock_update_profile.assert_not_called()


@patch("resilio.api.weather.update_profile")
@patch("resilio.api.weather.get_weekly_forecast_for_location")
@patch("resilio.api.weather.get_profile")
def test_profile_cached_coordinates_writes_cache_when_timezone_changes(
    mock_get_profile,
    mock_location_lookup,
    mock_update_profile,
):
    """Cache write triggers when a meaningful field (e.g. timezone) differs from stored value."""
    weather_preferences = SimpleNamespace(
        location_query="Paris, France",
        resolved_name="Paris, France",
        latitude=48.853,
        longitude=2.3499,
        timezone=None,  # timezone not yet cached — sample forecast will supply it
    )
    profile = SimpleNamespace(weather_preferences=weather_preferences)
    mock_get_profile.return_value = profile
    mock_location_lookup.return_value = _sample_weekly_forecast()

    result = get_weekly_weather_forecast(start_date="2026-02-16")

    assert isinstance(result, WeeklyWeatherForecast)
    mock_update_profile.assert_called_once()
    payload = mock_update_profile.call_args.kwargs["weather_preferences"]
    assert payload["timezone"] == "Europe/Paris"
