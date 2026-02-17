"""Weather schemas for weekly forecast planning context."""

from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class AdvisoryLevel(str, Enum):
    """Severity level for weather planning advisories."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class AdvisoryType(str, Enum):
    """Weather advisory categories relevant to training planning."""

    HEAT = "heat"
    COLD = "cold"
    WIND = "wind"
    PRECIPITATION = "precipitation"


class WeatherAdvisorySignal(str, Enum):
    """Canonical signal labels for weather advisories.

    Values are always derived from (AdvisoryType, AdvisoryLevel) via _make_signal()
    in core/weather.py. Adding a new AdvisoryType requires a corresponding entry
    here — the derivation function will raise KeyError otherwise.
    """

    HEAT_HIGH = "HEAT_HIGH"
    HEAT_MODERATE = "HEAT_MODERATE"
    COLD_HIGH = "COLD_HIGH"
    COLD_MODERATE = "COLD_MODERATE"
    WIND_HIGH = "WIND_HIGH"
    WIND_MODERATE = "WIND_MODERATE"
    PRECIPITATION_HIGH = "PRECIPITATION_HIGH"
    PRECIPITATION_MODERATE = "PRECIPITATION_MODERATE"


class WeatherLocation(BaseModel):
    """Location context used to resolve weather forecasts."""

    location_query: str = Field(..., description="User-provided location query")
    resolved_name: Optional[str] = Field(default=None, description="Resolved place name")
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    timezone: Optional[str] = None


class DailyWeatherForecast(BaseModel):
    """Single-day forecast fields for weekly planning."""

    date: date
    temperature_min_c: Optional[float] = Field(default=None, ge=-50, le=60)
    temperature_max_c: Optional[float] = Field(default=None, ge=-50, le=60)
    precipitation_mm: Optional[float] = Field(default=None, ge=0)
    precipitation_probability_max_pct: Optional[int] = Field(default=None, ge=0, le=100)
    wind_speed_max_kph: Optional[float] = Field(default=None, ge=0)
    weather_code: Optional[int] = None

    @model_validator(mode="after")
    def validate_temperature_order(self) -> "DailyWeatherForecast":
        """Ensure min temperature does not exceed max temperature."""
        if (
            self.temperature_min_c is not None
            and self.temperature_max_c is not None
            and self.temperature_min_c > self.temperature_max_c
        ):
            raise ValueError(
                f"temperature_min_c ({self.temperature_min_c}) must be <= "
                f"temperature_max_c ({self.temperature_max_c})"
            )
        return self


class WeatherAdvisory(BaseModel):
    """Advisory signal generated from weather forecast data.

    Fields:
        reason: Factual description of the condition (temperature, wind speed, etc.)
        signal: Short label for the condition (e.g. HEAT_HIGH, WIND_MODERATE).
                Intended for coach synthesis — coaching decisions belong to the AI coach,
                not the data layer.
    """

    date: date
    type: AdvisoryType
    level: AdvisoryLevel
    reason: str
    signal: WeatherAdvisorySignal


class WeeklyWeatherForecast(BaseModel):
    """Weekly forecast payload for coach planning workflows."""

    start_date: date
    end_date: date
    source: str = "open-meteo"
    location: WeatherLocation
    daily: list[DailyWeatherForecast]
    advisories: list[WeatherAdvisory] = Field(default_factory=list)
    weekly_summary: str
