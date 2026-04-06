"""
FastAPI router — gestion des credentials connecteurs.
Strava OAuth2 + Hevy API key CRUD.
auth: athlete_id en query param (JWT en S11).
"""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from connectors.hevy import HevyConnector
from connectors.strava import StravaConnector
from models.database import Athlete, ConnectorCredential
from models.db_session import get_db

router = APIRouter()
_strava = StravaConnector()
_hevy = HevyConnector()


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_athlete_or_404(athlete_id: uuid.UUID, db: AsyncSession) -> Athlete:
    result = await db.execute(select(Athlete).where(Athlete.id == athlete_id))
    athlete = result.scalar_one_or_none()
    if athlete is None:
        raise HTTPException(status_code=404, detail=f"Athlete {athlete_id} not found")
    return athlete


async def _get_credential(
    athlete_id: uuid.UUID, provider: str, db: AsyncSession
) -> ConnectorCredential | None:
    result = await db.execute(
        select(ConnectorCredential).where(
            ConnectorCredential.athlete_id == athlete_id,
            ConnectorCredential.provider == provider,
        )
    )
    return result.scalar_one_or_none()


# ── Strava ────────────────────────────────────────────────────────────────────

@router.get("/strava/auth")
async def strava_auth() -> dict:
    return {"authorization_url": _strava.get_authorization_url()}


@router.get("/strava/callback")
async def strava_callback(
    code: str = Query(...),
    athlete_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _get_athlete_or_404(athlete_id, db)
    cred = await _strava.exchange_code(code, athlete_id, db)
    return {"connected": True, "strava_athlete_id": cred.external_athlete_id}


@router.post("/strava/sync")
async def strava_sync(
    athlete_id: uuid.UUID = Query(...),
    days: int = Query(default=30),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _get_athlete_or_404(athlete_id, db)
    cred = await _get_credential(athlete_id, "strava", db)
    if cred is None:
        raise HTTPException(status_code=404, detail="Strava not connected for this athlete")
    cred = await _strava.refresh_token_if_expired(cred, db)
    since = datetime.now(tz=UTC) - timedelta(days=days)
    activities = await _strava.fetch_activities(cred, since)
    synced = await _strava.ingest_activities(athlete_id, activities, db)
    return {"synced": synced}


@router.get("/strava/status")
async def strava_status(
    athlete_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _get_athlete_or_404(athlete_id, db)
    cred = await _get_credential(athlete_id, "strava", db)
    if cred is None:
        return {"connected": False, "last_sync": None, "token_expires_at": None}
    return {
        "connected": True,
        "last_sync": cred.updated_at.isoformat() if cred.updated_at else None,
        "token_expires_at": (
            cred.token_expires_at.isoformat() if cred.token_expires_at else None
        ),
    }


@router.delete("/strava/disconnect")
async def strava_disconnect(
    athlete_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _get_athlete_or_404(athlete_id, db)
    cred = await _get_credential(athlete_id, "strava", db)
    if cred is not None:
        await db.delete(cred)
    return {"disconnected": True}


# ── Hevy ──────────────────────────────────────────────────────────────────────

class HevyConnectBody(BaseModel):
    api_key: str


@router.post("/hevy/connect")
async def hevy_connect(
    athlete_id: uuid.UUID = Query(...),
    body: HevyConnectBody = Body(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _get_athlete_or_404(athlete_id, db)
    if not await _hevy.validate_api_key(body.api_key):
        raise HTTPException(status_code=400, detail="Invalid Hevy API key")
    stmt = (
        pg_insert(ConnectorCredential)
        .values(athlete_id=athlete_id, provider="hevy", api_key=body.api_key)
        .on_conflict_do_update(
            index_elements=["athlete_id", "provider"],
            set_={"api_key": body.api_key},
        )
    )
    await db.execute(stmt)
    return {"connected": True}


@router.post("/hevy/sync")
async def hevy_sync(
    athlete_id: uuid.UUID = Query(...),
    days: int = Query(default=30),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _get_athlete_or_404(athlete_id, db)
    cred = await _get_credential(athlete_id, "hevy", db)
    if cred is None:
        raise HTTPException(status_code=404, detail="Hevy not connected for this athlete")
    if cred.api_key is None:
        raise HTTPException(status_code=400, detail="Hevy credential has no API key stored")
    since = datetime.now(tz=UTC) - timedelta(days=days)
    workouts = await _hevy.fetch_all_since(cred.api_key, since)
    synced = await _hevy.ingest_workouts(athlete_id, workouts, db)
    return {"synced": synced}


@router.get("/hevy/status")
async def hevy_status(
    athlete_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _get_athlete_or_404(athlete_id, db)
    cred = await _get_credential(athlete_id, "hevy", db)
    if cred is None:
        return {"connected": False, "last_sync": None}
    return {
        "connected": True,
        "last_sync": cred.updated_at.isoformat() if cred.updated_at else None,
    }


@router.delete("/hevy/disconnect")
async def hevy_disconnect(
    athlete_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _get_athlete_or_404(athlete_id, db)
    cred = await _get_credential(athlete_id, "hevy", db)
    if cred is not None:
        await db.delete(cred)
    return {"disconnected": True}
