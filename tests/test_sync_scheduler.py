"""
Tests for core/sync_scheduler.py — APScheduler periodic sync.
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from core.sync_scheduler import setup_scheduler, sync_all_hevy, sync_all_strava


# ─────────────────────────────────────────────
# Helper: build mock async session
# ─────────────────────────────────────────────

def _make_mock_session(creds: list) -> AsyncMock:
    """Returns a mock async context-manager session whose execute returns creds."""
    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = False

    scalars_mock = MagicMock()
    scalars_mock.all.return_value = creds
    execute_result = MagicMock()
    execute_result.scalars.return_value = scalars_mock
    mock_session.execute = AsyncMock(return_value=execute_result)
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    return mock_session


def _make_fake_strava_cred() -> MagicMock:
    cred = MagicMock()
    cred.athlete_id = uuid.uuid4()
    cred.access_token = "tok"
    cred.refresh_token = "ref"
    cred.token_expires_at = None
    return cred


def _make_fake_hevy_cred() -> MagicMock:
    cred = MagicMock()
    cred.athlete_id = uuid.uuid4()
    cred.api_key = "hevy-key-123"
    return cred


# ─────────────────────────────────────────────
# Test 1 — setup_scheduler returns two jobs
# ─────────────────────────────────────────────

def test_setup_scheduler_returns_two_jobs() -> None:
    scheduler = setup_scheduler()
    assert isinstance(scheduler, AsyncIOScheduler)
    jobs = scheduler.get_jobs()
    assert len(jobs) == 2
    job_ids = {j.id for j in jobs}
    assert job_ids == {"strava_sync", "hevy_sync"}


# ─────────────────────────────────────────────
# Test 2 — sync_all_strava calls ingest_activities
# ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sync_all_strava_calls_ingest() -> None:
    cred = _make_fake_strava_cred()
    mock_session = _make_mock_session([cred])
    mock_factory = MagicMock(return_value=mock_session)

    with patch("core.sync_scheduler.AsyncSessionFactory", mock_factory):
        with patch("core.sync_scheduler._strava") as mock_strava:
            mock_strava.refresh_token_if_expired = AsyncMock(return_value=cred)
            mock_strava.fetch_activities = AsyncMock(return_value=[{"id": 1, "type": "Run"}])
            mock_strava.ingest_activities = AsyncMock(return_value=1)

            await sync_all_strava()

    mock_strava.ingest_activities.assert_called_once()


# ─────────────────────────────────────────────
# Test 3 — sync_all_hevy calls ingest_workouts
# ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sync_all_hevy_calls_ingest() -> None:
    cred = _make_fake_hevy_cred()
    mock_session = _make_mock_session([cred])
    mock_factory = MagicMock(return_value=mock_session)

    with patch("core.sync_scheduler.AsyncSessionFactory", mock_factory):
        with patch("core.sync_scheduler._hevy") as mock_hevy:
            mock_hevy.fetch_all_since = AsyncMock(return_value=[{"id": "w1"}])
            mock_hevy.ingest_workouts = AsyncMock(return_value=1)

            await sync_all_hevy()

    mock_hevy.ingest_workouts.assert_called_once()


# ─────────────────────────────────────────────
# Test 4 — strava per-athlete failure is caught, ingest not called
# ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sync_all_strava_handles_per_athlete_failure() -> None:
    cred = _make_fake_strava_cred()
    mock_session = _make_mock_session([cred])
    mock_factory = MagicMock(return_value=mock_session)

    with patch("core.sync_scheduler.AsyncSessionFactory", mock_factory):
        with patch("core.sync_scheduler._strava") as mock_strava:
            mock_strava.refresh_token_if_expired = AsyncMock(return_value=cred)
            mock_strava.fetch_activities = AsyncMock(
                side_effect=RuntimeError("Strava API down")
            )
            mock_strava.ingest_activities = AsyncMock(return_value=0)

            # Must not raise
            await sync_all_strava()

    # ingest should NOT have been called since fetch raised
    mock_strava.ingest_activities.assert_not_called()


# ─────────────────────────────────────────────
# Test 5 — hevy per-athlete failure is caught, ingest not called
# ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sync_all_hevy_handles_per_athlete_failure() -> None:
    cred = _make_fake_hevy_cred()
    mock_session = _make_mock_session([cred])
    mock_factory = MagicMock(return_value=mock_session)

    with patch("core.sync_scheduler.AsyncSessionFactory", mock_factory):
        with patch("core.sync_scheduler._hevy") as mock_hevy:
            mock_hevy.fetch_all_since = AsyncMock(
                side_effect=RuntimeError("Hevy API down")
            )
            mock_hevy.ingest_workouts = AsyncMock(return_value=0)

            # Must not raise
            await sync_all_hevy()

    # ingest should NOT have been called since fetch raised
    mock_hevy.ingest_workouts.assert_not_called()


# ─────────────────────────────────────────────
# Test 6 — hevy skips credentials with no api_key (DB-level filter)
# ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sync_all_hevy_skips_no_api_key() -> None:
    """
    The DB query uses .is_not(None) to exclude creds without api_key.
    We verify that when the query returns an empty list (simulating the DB filter),
    ingest_workouts is never called.
    """
    mock_session = _make_mock_session([])  # DB returns nothing (filtered out)
    mock_factory = MagicMock(return_value=mock_session)

    with patch("core.sync_scheduler.AsyncSessionFactory", mock_factory):
        with patch("core.sync_scheduler._hevy") as mock_hevy:
            mock_hevy.fetch_all_since = AsyncMock(return_value=[])
            mock_hevy.ingest_workouts = AsyncMock(return_value=0)

            await sync_all_hevy()

    mock_hevy.ingest_workouts.assert_not_called()
