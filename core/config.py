"""
CONFIGURATION — Resilio+
Variables d'environnement via Pydantic Settings v2.
Copier .env.example → .env et remplir les valeurs.
"""

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # ── Application ──────────────────────────────────
    APP_NAME: str = "Resilio+"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    TESTING: bool = False

    # ── Base de données ──────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://resilio:resilio@localhost:5432/resilio_db"
    DB_ECHO: bool = False

    # ── Strava OAuth ─────────────────────────────────
    STRAVA_CLIENT_ID: str = ""
    STRAVA_CLIENT_SECRET: str = ""
    STRAVA_REDIRECT_URI: str = "http://localhost:8000/api/v1/connectors/strava/callback"

    # ── USDA FoodData Central ────────────────────────
    USDA_API_KEY: str = ""

    # ── Anthropic (agents) ───────────────────────────
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-6"
    ANTHROPIC_MAX_TOKENS: int = 4096

    # ── Sécurité API ─────────────────────────────────
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24h

    @model_validator(mode="after")
    def check_secret_key(self) -> "Settings":
        if not self.DEBUG and self.SECRET_KEY == "change-me-in-production":
            raise ValueError(
                "SECRET_KEY must be set in production (DEBUG=False). "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        return self


settings = Settings()
