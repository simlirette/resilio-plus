"""
Tests unitaires AppleHealthConnector.
Écrit dans fatigue_snapshots via upsert sur (athlete_id, snapshot_date).
"""

from datetime import date

import pytest
from sqlalchemy import select

from connectors.apple_health import AppleHealthConnector
from models.database import FatigueSnapshot


# ── test_ingest_snapshot_creates_fatigue_snapshot ────────────────────────────

async def test_ingest_snapshot_creates_fatigue_snapshot(db_session, simon_athlete):
    connector = AppleHealthConnector()
    data = {
        "snapshot_date": "2026-04-01",
        "hrv_rmssd": 62.4,
        "hr_rest": 54,
        "sleep_hours": 7.5,
        "sleep_quality_subjective": 8,
    }

    snapshot = await connector.ingest_snapshot(simon_athlete.id, data, db_session)

    assert snapshot.athlete_id == simon_athlete.id
    assert snapshot.snapshot_date == date(2026, 4, 1)
    assert snapshot.hrv_rmssd == pytest.approx(62.4)
    assert snapshot.hr_rest == 54
    assert snapshot.sleep_hours == pytest.approx(7.5)
    assert snapshot.sleep_quality_subjective == 8


# ── test_ingest_snapshot_partial_data ────────────────────────────────────────

async def test_ingest_snapshot_partial_data(db_session, simon_athlete):
    connector = AppleHealthConnector()
    data = {
        "snapshot_date": "2026-04-02",
        "sleep_hours": 6.8,
    }

    snapshot = await connector.ingest_snapshot(simon_athlete.id, data, db_session)

    assert snapshot.sleep_hours == pytest.approx(6.8)
    assert snapshot.hrv_rmssd is None
    assert snapshot.hr_rest is None
    assert snapshot.sleep_quality_subjective is None


# ── test_ingest_snapshot_upsert ──────────────────────────────────────────────

async def test_ingest_snapshot_upsert(db_session, simon_athlete):
    connector = AppleHealthConnector()
    target_date = "2026-04-03"

    # First ingestion
    await connector.ingest_snapshot(
        simon_athlete.id,
        {"snapshot_date": target_date, "hrv_rmssd": 55.0},
        db_session,
    )

    # Second ingestion — updates hrv_rmssd, keeps sleep_hours intact
    await connector.ingest_snapshot(
        simon_athlete.id,
        {"snapshot_date": target_date, "hrv_rmssd": 60.0, "sleep_hours": 7.0},
        db_session,
    )

    result = await db_session.execute(
        select(FatigueSnapshot).where(
            FatigueSnapshot.athlete_id == simon_athlete.id,
            FatigueSnapshot.snapshot_date == date(2026, 4, 3),
        )
    )
    rows = result.scalars().all()
    assert len(rows) == 1  # No duplicates
    assert rows[0].hrv_rmssd == pytest.approx(60.0)
    assert rows[0].sleep_hours == pytest.approx(7.0)
