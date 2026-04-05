"""
Tests des routes FastAPI connecteurs.
Utilise httpx.AsyncClient avec ASGITransport pour rester in-process.
La session DB de test est injectée via override de la dépendance get_db.
"""

from unittest.mock import AsyncMock, patch

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.main import app
from models.db_session import get_db


@pytest_asyncio.fixture
async def api_client(db_session: AsyncSession):
    """AsyncClient avec override DB — isole les tests de la vraie DB."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
    app.dependency_overrides.clear()


# ── test_strava_auth_returns_url ──────────────────────────────────────────────

async def test_strava_auth_returns_url(api_client):
    response = await api_client.get("/api/v1/connectors/strava/auth")
    assert response.status_code == 200
    data = response.json()
    assert "authorization_url" in data
    assert "strava.com" in data["authorization_url"]
    assert "scope=activity:read_all" in data["authorization_url"]


# ── test_hevy_connect_stores_credential ──────────────────────────────────────

async def test_hevy_connect_stores_credential(api_client, simon_athlete):
    with patch(
        "api.v1.connectors._hevy.validate_api_key",
        new=AsyncMock(return_value=True),
    ):
        response = await api_client.post(
            "/api/v1/connectors/hevy/connect",
            params={"athlete_id": str(simon_athlete.id)},
            json={"api_key": "my_hevy_key"},
        )

    assert response.status_code == 200
    assert response.json()["connected"] is True


# ── test_hevy_status_not_connected ────────────────────────────────────────────

async def test_hevy_status_not_connected(api_client, simon_athlete):
    response = await api_client.get(
        "/api/v1/connectors/hevy/status",
        params={"athlete_id": str(simon_athlete.id)},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["connected"] is False
