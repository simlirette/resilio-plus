"""
Configuration schemas for M2 - Config & Secrets module.

Defines Pydantic models for settings, secrets, and configuration validation.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ============================================================
# ERROR TYPES
# ============================================================


class ConfigErrorType(str, Enum):
    """Types of configuration errors."""

    FILE_NOT_FOUND = "file_not_found"
    PARSE_ERROR = "parse_error"
    VALIDATION_ERROR = "validation_error"
    MISSING_SECRET = "missing_secret"
    TOKEN_REFRESH_FAILED = "token_refresh_failed"
    NETWORK_ERROR = "network_error"


# ============================================================
# SETTINGS MODELS
# ============================================================


class PathSettings(BaseModel):
    """File path configuration (relative to repo root)."""

    athlete_dir: str = "data/athlete"
    activities_dir: str = "data/activities"
    metrics_dir: str = "data/metrics"
    plans_dir: str = "data/plans"
    state_dir: str = "data/state"


class StravaSettings(BaseModel):
    """Strava API configuration."""

    api_base_url: str = "https://www.strava.com/api/v3"
    token_url: str = "https://www.strava.com/oauth/token"
    auth_url: str = "https://www.strava.com/oauth/authorize"
    scopes: list[str] = Field(default_factory=lambda: ["read", "activity:read_all"])
    history_import_weeks: int = 12
    lap_fetch_incremental_days: int = 999999  # Fetch all laps for incremental sync (effectively unlimited)
    lap_fetch_historical_days: int = 60  # 60-day limit for historical/backfill sync


class TrainingDefaults(BaseModel):
    """Training calculation defaults."""

    ctl_time_constant: int = 42  # days (Chronic Training Load)
    atl_time_constant: int = 7  # days (Acute Training Load)
    acwr_acute_window: int = 7  # days
    acwr_chronic_window: int = 28  # days
    baseline_days_threshold: int = 14
    acwr_minimum_days: int = 28


class SystemSettings(BaseModel):
    """System configuration."""

    lock_timeout_ms: int = 300_000  # 5 minutes
    lock_retry_count: int = 3
    lock_retry_delay_ms: int = 2_000
    metrics_stale_hours: int = 24


class GoogleCalendarSettings(BaseModel):
    """Google Calendar sync configuration."""

    credentials_path: str = "credentials.json"
    token_path: str = "data/google_calendar/token.json"
    state_path: str = "data/google_calendar/state.json"
    timezone: str = "America/Toronto"
    calendar_name: str = "Resilio Training"
    sync_weeks_ahead: int = 2

    # Start time per day of week (0=Mon … 6=Sun). "allday" = all-day event.
    # am=09:00  pm=13:00  soir=19:00
    day_times: dict = Field(
        default_factory=lambda: {
            "0": "19:00",   # Monday   — soir
            "1": "19:00",   # Tuesday  — soir
            "2": "19:00",   # Wednesday — soir
            "3": "allday",  # Thursday  — all-day
            "4": "19:00",   # Friday   — soir
            "5": "allday",  # Saturday  — all-day
            "6": "allday",  # Sunday   — all-day
        }
    )

    # Reminder minutes before timed events (all-day events: no popup)
    reminders: dict = Field(
        default_factory=lambda: {
            "easy": 30,
            "tempo": 30,
            "intervals": 30,
            "fartlek": 30,
            "strides": 30,
            "long_run": 60,
            "race": 60,
            "rest": 0,
            "strength": 30,
        }
    )


class Settings(BaseModel):
    """Complete settings configuration."""

    paths: PathSettings = Field(default_factory=PathSettings)
    strava: StravaSettings = Field(default_factory=StravaSettings)
    training_defaults: TrainingDefaults = Field(default_factory=TrainingDefaults)
    system: SystemSettings = Field(default_factory=SystemSettings)
    google_calendar: GoogleCalendarSettings = Field(default_factory=GoogleCalendarSettings)


# ============================================================
# SECRETS MODELS
# ============================================================


class StravaSecrets(BaseModel):
    """Strava authentication secrets."""

    client_id: str
    client_secret: str
    access_token: str
    refresh_token: str
    token_expires_at: int  # Unix timestamp


class Secrets(BaseModel):
    """All application secrets."""

    strava: StravaSecrets


# ============================================================
# CONFIG MODEL
# ============================================================


class Config(BaseModel):
    """Complete application configuration."""

    settings: Settings
    secrets: Secrets
    loaded_at: datetime
