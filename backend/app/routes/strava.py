# backend/app/routes/strava.py
"""Strava OAuth 2.0 + activity sync routes."""
from typing import Annotated, Any

import httpx as _httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..connectors.base import ConnectorRateLimitError
from ..db.models import AthleteModel
from ..dependencies import get_current_athlete_id, get_db
from ..integrations.strava.oauth_service import callback as oauth_callback
from ..integrations.strava.oauth_service import connect as oauth_connect
from ..integrations.strava.sync_service import sync as strava_sync
from ..jobs.registry import register_athlete_jobs
from ..jobs.scheduler import get_scheduler
from ..schemas.strava import SyncSummary

DB = Annotated[Session, Depends(get_db)]

router = APIRouter(prefix="/integrations/strava", tags=["strava"])


@router.post("/connect")
def connect(
    athlete_id: Annotated[str, Depends(get_current_athlete_id)],
    db: DB,
) -> dict[str, Any]:
    """Generate Strava OAuth authorization URL."""
    if db.get(AthleteModel, athlete_id) is None:
        raise HTTPException(status_code=404, detail="Athlete not found")
    return oauth_connect(athlete_id, db)


@router.get("/callback")
def callback(
    code: str,
    state: str,
    db: DB,
) -> dict[str, Any]:
    """Handle Strava OAuth callback — exchange code for encrypted tokens."""
    try:
        result = oauth_callback(code=code, state=state, db=db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except _httpx.HTTPStatusError:
        raise HTTPException(status_code=502, detail="Strava token exchange failed")

    try:
        register_athlete_jobs(result["athlete_id"], "strava", get_scheduler())
    except RuntimeError:
        pass  # scheduler not started (testing)

    return result


@router.post("/sync", response_model=SyncSummary)
def sync_activities(
    athlete_id: Annotated[str, Depends(get_current_athlete_id)],
    db: DB,
) -> SyncSummary:
    """Sync Strava activities incrementally since last sync."""
    try:
        return strava_sync(athlete_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ConnectorRateLimitError as e:
        raise HTTPException(
            status_code=429,
            headers={"Retry-After": str(e.retry_after)},
            detail="Strava rate limit reached",
        )
