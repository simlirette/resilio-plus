"""
Tests unitaires StravaConnector — httpx.MockTransport, pas de vraies requêtes réseau.
"""

from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import select

from connectors.strava import StravaConnector
from models.database import ConnectorCredential, RunActivity

# ── test_get_authorization_url ────────────────────────────────────────────────

def test_get_authorization_url():
    connector = StravaConnector()
    url = connector.get_authorization_url()
    assert "client_id=215637" in url
    assert "scope=activity:read_all" in url
    assert "redirect_uri=" in url
    assert url.startswith("https://www.strava.com/oauth/authorize")


# ── test_exchange_code_stores_credential ─────────────────────────────────────

async def test_exchange_code_stores_credential(db_session, simon_athlete):
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "access_token": "acc_token_123",
                "refresh_token": "ref_token_456",
                "expires_at": 9999999999,
                "athlete": {"id": 777},
            },
        )

    connector = StravaConnector(transport=httpx.MockTransport(mock_handler))
    cred = await connector.exchange_code("auth_code_xyz", simon_athlete.id, db_session)

    assert cred.access_token == "acc_token_123"
    assert cred.refresh_token == "ref_token_456"
    assert cred.external_athlete_id == "777"
    assert cred.provider == "strava"
    assert cred.athlete_id == simon_athlete.id


# ── test_refresh_token_when_expired ──────────────────────────────────────────

async def test_refresh_token_when_expired(db_session, simon_athlete):
    now = datetime.now(tz=UTC)
    past = now - timedelta(hours=1)

    cred = ConnectorCredential(
        athlete_id=simon_athlete.id,
        provider="strava",
        access_token="old_access",
        refresh_token="old_refresh",
        token_expires_at=past,
    )
    db_session.add(cred)
    await db_session.flush()

    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "access_token": "new_access_token",
                "refresh_token": "new_refresh_token",
                "expires_at": int((now + timedelta(hours=6)).timestamp()),
            },
        )

    connector = StravaConnector(transport=httpx.MockTransport(mock_handler))
    refreshed = await connector.refresh_token_if_expired(cred, db_session)

    assert refreshed.access_token == "new_access_token"
    assert refreshed.refresh_token == "new_refresh_token"
    assert refreshed.token_expires_at > now


# ── test_ingest_activities_upsert ────────────────────────────────────────────

async def test_ingest_activities_upsert(db_session, simon_athlete):
    activity = {
        "id": 12345,
        "type": "Run",
        "start_date": "2026-01-15T08:00:00Z",
        "distance": 10000,
        "elapsed_time": 3600,
        "average_speed": 2.778,
        "average_heartrate": 155,
        "max_heartrate": 180,
        "total_elevation_gain": 50,
    }

    connector = StravaConnector()
    count1 = await connector.ingest_activities(simon_athlete.id, [activity], db_session)
    count2 = await connector.ingest_activities(simon_athlete.id, [activity], db_session)

    assert count1 == 1
    assert count2 == 1

    result = await db_session.execute(
        select(RunActivity).where(RunActivity.strava_activity_id == "12345")
    )
    activities_in_db = result.scalars().all()
    assert len(activities_in_db) == 1


# ── test_trimp_calculated_without_hr ─────────────────────────────────────────

async def test_trimp_calculated_without_hr(db_session, simon_athlete):
    activity = {
        "id": 99999,
        "type": "Run",
        "start_date": "2026-01-16T08:00:00Z",
        "distance": 5000,  # 5 km
        "elapsed_time": 1500,
        # No average_heartrate — fallback: trimp = distance_km * 1.0
    }

    connector = StravaConnector()
    await connector.ingest_activities(simon_athlete.id, [activity], db_session)

    result = await db_session.execute(
        select(RunActivity).where(RunActivity.strava_activity_id == "99999")
    )
    run = result.scalar_one()
    assert run.trimp == pytest.approx(5.0)
