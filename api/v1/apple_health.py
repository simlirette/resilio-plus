"""
FastAPI router — Apple Health JSON upload → FatigueSnapshot.
auth: athlete_id en query param (JWT en S11).
"""

import uuid

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from connectors.apple_health import AppleHealthConnector
from models.database import Athlete
from models.db_session import get_db

router = APIRouter()
_apple_health = AppleHealthConnector()


async def _get_athlete_or_404(athlete_id: uuid.UUID, db: AsyncSession) -> Athlete:
    result = await db.execute(select(Athlete).where(Athlete.id == athlete_id))
    athlete = result.scalar_one_or_none()
    if athlete is None:
        raise HTTPException(status_code=404, detail=f"Athlete {athlete_id} not found")
    return athlete


@router.post("/apple-health/upload")
async def apple_health_upload(
    data: dict = Body(...),
    athlete_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Upload JSON Apple Health → upsert FatigueSnapshot."""
    await _get_athlete_or_404(athlete_id, db)
    try:
        snapshot = await _apple_health.ingest_snapshot(athlete_id, data, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {
        "snapshot_date": snapshot.snapshot_date.isoformat(),
        "hrv_rmssd": snapshot.hrv_rmssd,
        "hr_rest": snapshot.hr_rest,
        "sleep_hours": snapshot.sleep_hours,
        "sleep_quality_subjective": snapshot.sleep_quality_subjective,
    }
