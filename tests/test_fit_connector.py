"""
Tests unitaires FitConnector.
Parse les fichiers FIT binaires Garmin/Polar → RunActivity.
fitparse.FitFile est mocké pour éviter la dépendance à de vrais fichiers FIT.
"""

import math
from datetime import UTC, date, datetime
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import select

from connectors.fit import FitConnector
from models.database import RunActivity

# ── test_parse_fit_session_message ────────────────────────────────────────────

def test_parse_fit_session_message():
    connector = FitConnector()

    # Mock FitFile qui retourne un message session
    mock_message = MagicMock()
    mock_message.get_value.side_effect = lambda key: {
        "start_time": datetime(2026, 4, 1, 8, 0, 0, tzinfo=UTC),
        "total_distance": 10000.0,    # mètres
        "total_elapsed_time": 3600.0,  # secondes
        "avg_heart_rate": 155,
        "max_heart_rate": 180,
        "total_ascent": 120.0,         # mètres
        "sport": "running",
    }.get(key)

    mock_fitfile = MagicMock()
    mock_fitfile.get_messages.return_value = [mock_message]

    with patch("connectors.fit.FitFile", return_value=mock_fitfile):
        result = connector.parse_fit(b"fake_fit_bytes")

    assert result["distance_km"] == pytest.approx(10.0)
    assert result["duration_seconds"] == 3600
    assert result["avg_hr"] == 155
    assert result["max_hr"] == 180
    assert result["elevation_gain_m"] == pytest.approx(120.0)
    assert result["activity_date"] == date(2026, 4, 1)
    assert result["activity_type"] == "running"


# ── test_ingest_fit_creates_run_activity ──────────────────────────────────────

async def test_ingest_fit_creates_run_activity(db_session, simon_athlete):
    connector = FitConnector()
    parsed = {
        "activity_date": date(2026, 4, 1),
        "activity_type": "running",
        "distance_km": 10.0,
        "duration_seconds": 3600,
        "avg_pace_sec_per_km": 360.0,
        "avg_hr": 155,
        "max_hr": 180,
        "elevation_gain_m": 120.0,
    }

    with patch.object(connector, "parse_fit", return_value=parsed):
        run = await connector.ingest_fit(simon_athlete.id, b"fake", db_session)

    assert run.athlete_id == simon_athlete.id
    assert run.distance_km == pytest.approx(10.0)
    assert run.activity_type == "running"
    assert run.strava_raw == {"source": "fit"}
    # TRIMP: HR-based since avg_hr and max_hr are present
    expected_ratio = 155 / 180
    expected_trimp = (3600 / 60) * expected_ratio * math.exp(1.92 * expected_ratio)
    assert run.trimp == pytest.approx(expected_trimp, rel=1e-3)

    # Verify stored in DB
    result = await db_session.execute(
        select(RunActivity).where(RunActivity.id == run.id)
    )
    stored = result.scalar_one()
    assert stored.strava_raw == {"source": "fit"}
