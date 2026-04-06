"""
FastAPI router — upload fichiers GPX/FIT → RunActivity.
auth: athlete_id en query param (JWT en S11).
"""

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from connectors.fit import FitConnector
from connectors.gpx import GpxConnector
from models.database import Athlete
from models.db_session import get_db

router = APIRouter()
_gpx = GpxConnector()
_fit = FitConnector()


async def _get_athlete_or_404(athlete_id: uuid.UUID, db: AsyncSession) -> Athlete:
    result = await db.execute(select(Athlete).where(Athlete.id == athlete_id))
    athlete = result.scalar_one_or_none()
    if athlete is None:
        raise HTTPException(status_code=404, detail=f"Athlete {athlete_id} not found")
    return athlete


@router.post("/files/gpx")
async def upload_gpx(
    file: UploadFile = File(...),
    athlete_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Upload fichier GPX → RunActivity."""
    await _get_athlete_or_404(athlete_id, db)
    content = await file.read()
    try:
        run = await _gpx.ingest_gpx(athlete_id, content, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid GPX file: {e}") from e
    return {
        "activity_date": run.activity_date.isoformat() if run.activity_date else None,
        "distance_km": run.distance_km,
        "duration_seconds": run.duration_seconds,
    }


@router.post("/files/fit")
async def upload_fit(
    file: UploadFile = File(...),
    athlete_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Upload fichier FIT binaire → RunActivity."""
    await _get_athlete_or_404(athlete_id, db)
    content = await file.read()
    try:
        run = await _fit.ingest_fit(athlete_id, content, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid FIT file: {e}") from e
    return {
        "activity_date": run.activity_date.isoformat() if run.activity_date else None,
        "distance_km": run.distance_km,
        "duration_seconds": run.duration_seconds,
    }
