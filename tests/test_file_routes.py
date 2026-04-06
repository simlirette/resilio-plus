"""
Tests des nouvelles routes FastAPI S4 :
- POST /files/gpx
- POST /files/fit
- GET  /food/search
"""

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.main import app
from models.db_session import get_db

# GPX sample minimal pour le test d'upload
GPX_BYTES = b"""<?xml version="1.0"?>
<gpx xmlns="http://www.topografix.com/GPX/1/1" version="1.1">
  <trk><trkseg>
    <trkpt lat="48.8566" lon="2.3522"><ele>30.0</ele><time>2026-04-01T08:00:00Z</time></trkpt>
    <trkpt lat="48.8580" lon="2.3545"><ele>35.0</ele><time>2026-04-01T08:20:00Z</time></trkpt>
  </trkseg></trk>
</gpx>"""


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


# ── test_upload_gpx_returns_activity ─────────────────────────────────────────

async def test_upload_gpx_returns_activity(api_client, simon_athlete):
    response = await api_client.post(
        "/api/v1/connectors/files/gpx",
        params={"athlete_id": str(simon_athlete.id)},
        files={"file": ("run.gpx", GPX_BYTES, "application/gpx+xml")},
    )

    assert response.status_code == 200
    data = response.json()
    assert "activity_date" in data
    assert data["activity_date"] == "2026-04-01"
    assert "distance_km" in data
    assert "duration_seconds" in data


# ── test_upload_fit_returns_activity ─────────────────────────────────────────

async def test_upload_fit_returns_activity(api_client, simon_athlete):
    parsed_mock = {
        "activity_date": date(2026, 4, 2),
        "activity_type": "running",
        "distance_km": 5.0,
        "duration_seconds": 1800,
        "avg_pace_sec_per_km": 360.0,
        "avg_hr": 150,
        "max_hr": 175,
        "elevation_gain_m": 50.0,
    }

    with patch("api.v1.files._fit.parse_fit", return_value=parsed_mock):
        response = await api_client.post(
            "/api/v1/connectors/files/fit",
            params={"athlete_id": str(simon_athlete.id)},
            files={"file": ("activity.fit", b"fake_fit_content", "application/octet-stream")},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["activity_date"] == "2026-04-02"
    assert data["distance_km"] == 5.0


# ── test_food_search_returns_list ─────────────────────────────────────────────

async def test_food_search_returns_list(api_client):
    mock_results = [
        {
            "fdcId": 1,
            "description": "Chicken breast",
            "nutrients": {"calories": 165.0, "protein_g": 31.0, "fat_g": 3.6, "carbs_g": 0.0},
        }
    ]

    with patch(
        "api.v1.food._food.search_usda",
        new=AsyncMock(return_value=mock_results),
    ):
        response = await api_client.get(
            "/api/v1/connectors/food/search",
            params={"q": "chicken"},
        )

    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert len(data["results"]) == 1
    assert data["results"][0]["description"] == "Chicken breast"
