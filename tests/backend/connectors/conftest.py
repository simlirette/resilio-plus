import pytest
from app.schemas.connector import ConnectorCredential


@pytest.fixture
def strava_credential():
    return ConnectorCredential(
        athlete_id="00000000-0000-0000-0000-000000000001",
        provider="strava",
        access_token="test_access_token",
        refresh_token="test_refresh_token",
        expires_at=9999999999,  # far future — valid token
    )


@pytest.fixture
def hevy_credential():
    # Hevy uses API Key — no access/refresh tokens; key lives in extra
    return ConnectorCredential(
        athlete_id="00000000-0000-0000-0000-000000000001",
        provider="hevy",
        extra={"api_key": "test_hevy_key"},
    )


@pytest.fixture
def fatsecret_credential():
    # FatSecret uses app-level Bearer token (client credentials grant)
    return ConnectorCredential(
        athlete_id="00000000-0000-0000-0000-000000000001",
        provider="fatsecret",
        access_token="test_bearer_token",
        expires_at=9999999999,
    )


@pytest.fixture
def terra_credential():
    # Terra uses API Key (env) + per-athlete terra_user_id in extra
    return ConnectorCredential(
        athlete_id="00000000-0000-0000-0000-000000000001",
        provider="terra",
        extra={"terra_user_id": "test_terra_user_123"},
    )
