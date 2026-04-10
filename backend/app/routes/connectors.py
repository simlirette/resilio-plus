import json
import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Annotated, Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..connectors.apple_health import AppleHealthConnector
from ..connectors.hevy import HevyConnector
from ..connectors.strava import StravaConnector
from ..connectors.terra import TerraConnector
from ..db.models import AthleteModel, ConnectorCredentialModel, SessionLogModel, TrainingPlanModel
from ..dependencies import get_db, get_current_athlete_id
from ..schemas.connector import ConnectorCredential
from ..schemas.connector_api import (
    ConnectorListResponse,
    ConnectorStatus,
    HevyConnectRequest,
)

router = APIRouter(prefix="/athletes", tags=["connectors"])

DB = Annotated[Session, Depends(get_db)]


def _upsert_credential(
    *,
    athlete_id: str,
    provider: str,
    access_token: str | None,
    refresh_token: str | None,
    expires_at: int | None,
    extra_json: str = "{}",
    db: Session,
) -> None:
    existing = (
        db.query(ConnectorCredentialModel)
        .filter_by(athlete_id=athlete_id, provider=provider)
        .first()
    )
    if existing:
        existing.access_token = access_token
        existing.refresh_token = refresh_token
        existing.expires_at = expires_at
        existing.extra_json = extra_json
        db.commit()
    else:
        db.add(ConnectorCredentialModel(
            id=str(uuid.uuid4()),
            athlete_id=athlete_id,
            provider=provider,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            extra_json=extra_json,
        ))
        db.commit()


# ── Auth helpers ──────────────────────────────────────────────────────────────


def _require_own(
    athlete_id: str,
    current_id: Annotated[str, Depends(get_current_athlete_id)],
) -> str:
    if current_id != athlete_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return athlete_id


def _get_latest_plan(athlete_id: str, db: Session) -> TrainingPlanModel | None:
    from sqlalchemy import desc
    return (
        db.query(TrainingPlanModel)
        .filter(TrainingPlanModel.athlete_id == athlete_id)
        .order_by(desc(TrainingPlanModel.created_at))
        .first()
    )


def _upsert_session_log(
    *,
    athlete_id: str,
    plan_id: str,
    session_id: str,
    actual_duration_min: int | None,
    actual_data: dict,
    db: Session,
) -> None:
    existing = (
        db.query(SessionLogModel)
        .filter_by(athlete_id=athlete_id, session_id=session_id)
        .first()
    )
    if existing:
        existing.actual_duration_min = actual_duration_min
        existing.actual_data_json = json.dumps(actual_data)
        existing.logged_at = datetime.now(timezone.utc)
        db.commit()
    else:
        db.add(SessionLogModel(
            id=str(uuid.uuid4()),
            athlete_id=athlete_id,
            plan_id=plan_id,
            session_id=session_id,
            actual_duration_min=actual_duration_min,
            skipped=False,
            actual_data_json=json.dumps(actual_data),
            logged_at=datetime.now(timezone.utc),
        ))
        db.commit()


# ── Strava OAuth2 ────────────────────────────────────────────────────────────


@router.post("/{athlete_id}/connectors/strava/authorize")
def strava_authorize(athlete_id: str, db: DB) -> dict:
    if db.get(AthleteModel, athlete_id) is None:
        raise HTTPException(status_code=404)

    # Dummy credential — only client_id is needed for get_auth_url()
    cred = ConnectorCredential(
        athlete_id=athlete_id,  # type: ignore[arg-type]
        provider="strava",
    )
    client_id = os.getenv("STRAVA_CLIENT_ID", "")
    with StravaConnector(cred, client_id=client_id, client_secret="") as connector:
        auth_url = connector.get_auth_url()

    # Append state for anti-CSRF; not validated on callback in Phase 1
    auth_url += f"&state={athlete_id}"
    return {"auth_url": auth_url}


@router.get("/{athlete_id}/connectors/strava/callback")
def strava_callback(athlete_id: str, code: str, db: DB) -> dict:
    if db.get(AthleteModel, athlete_id) is None:
        raise HTTPException(status_code=404)

    cred = ConnectorCredential(
        athlete_id=athlete_id,  # type: ignore[arg-type]
        provider="strava",
    )
    client_id = os.getenv("STRAVA_CLIENT_ID", "")
    client_secret = os.getenv("STRAVA_CLIENT_SECRET", "")

    try:
        with StravaConnector(cred, client_id=client_id, client_secret=client_secret) as connector:
            updated = connector.exchange_code(code)
    except httpx.HTTPStatusError:
        raise HTTPException(status_code=502, detail="Strava token exchange failed")

    _upsert_credential(
        athlete_id=athlete_id,
        provider="strava",
        access_token=updated.access_token,
        refresh_token=updated.refresh_token,
        expires_at=updated.expires_at,
        db=db,
    )
    return {"connected": True}


# ── Hevy ─────────────────────────────────────────────────────────────────────


@router.post("/{athlete_id}/connectors/hevy", status_code=201)
def hevy_connect(athlete_id: str, req: HevyConnectRequest, db: DB) -> ConnectorStatus:
    if db.get(AthleteModel, athlete_id) is None:
        raise HTTPException(status_code=404)

    _upsert_credential(
        athlete_id=athlete_id,
        provider="hevy",
        access_token=None,
        refresh_token=None,
        expires_at=None,
        extra_json=json.dumps({"api_key": req.api_key}),
        db=db,
    )
    return ConnectorStatus(provider="hevy", connected=True, expires_at=None)


# ── Terra ─────────────────────────────────────────────────────────────────────


class TerraConnectRequest(BaseModel):
    terra_user_id: str


@router.post("/{athlete_id}/connectors/terra", status_code=201)
def terra_connect(
    athlete_id: str,
    req: TerraConnectRequest,
    db: DB,
    _: Annotated[str, Depends(_require_own)],
) -> ConnectorStatus:
    if db.get(AthleteModel, athlete_id) is None:
        raise HTTPException(status_code=404, detail="Athlete not found")

    _upsert_credential(
        athlete_id=athlete_id,
        provider="terra",
        access_token=None,
        refresh_token=None,
        expires_at=None,
        extra_json=json.dumps({"terra_user_id": req.terra_user_id}),
        db=db,
    )
    return ConnectorStatus(provider="terra", connected=True, expires_at=None)


# ── Apple Health Upload ───────────────────────────────────────────────────────


class AppleHealthUploadRequest(BaseModel):
    snapshot_date: str
    hrv_rmssd: float | None = None
    sleep_hours: float | None = None
    hr_rest: int | None = None


@router.post("/{athlete_id}/connectors/apple-health/upload", status_code=200)
def apple_health_upload(
    athlete_id: str,
    req: AppleHealthUploadRequest,
    db: DB,
    _: Annotated[str, Depends(_require_own)],
) -> dict:
    """Upload Apple Health data JSON → store latest HRV/sleep in connector creds."""
    if db.get(AthleteModel, athlete_id) is None:
        raise HTTPException(status_code=404, detail="Athlete not found")

    connector = AppleHealthConnector()
    try:
        parsed = connector.parse(req.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    extra_update = connector.to_extra_dict(parsed)

    cred_model = (
        db.query(ConnectorCredentialModel)
        .filter_by(athlete_id=athlete_id, provider="apple_health")
        .first()
    )
    if cred_model:
        existing = json.loads(cred_model.extra_json or "{}")
        existing.update(extra_update)
        cred_model.extra_json = json.dumps(existing)
    else:
        db.add(ConnectorCredentialModel(
            id=str(uuid.uuid4()),
            athlete_id=athlete_id,
            provider="apple_health",
            extra_json=json.dumps(extra_update),
        ))
    db.commit()

    return {
        "uploaded": True,
        "snapshot_date": parsed.snapshot_date.isoformat(),
        "hrv_rmssd": parsed.hrv_rmssd,
        "sleep_hours": parsed.sleep_hours,
    }


# ── Hevy Sync ─────────────────────────────────────────────────────────────────


@router.post("/{athlete_id}/connectors/hevy/sync")
def hevy_sync(
    athlete_id: str,
    db: DB,
    _: Annotated[str, Depends(_require_own)],
) -> dict:
    """Fetch last 7 days of Hevy workouts → map to lifting sessions → SessionLogModel."""
    cred_model = (
        db.query(ConnectorCredentialModel)
        .filter_by(athlete_id=athlete_id, provider="hevy")
        .first()
    )
    if cred_model is None:
        raise HTTPException(status_code=404, detail="Hevy connector not connected")

    extra = json.loads(cred_model.extra_json or "{}")
    api_key = extra.get("api_key", "")

    cred = ConnectorCredential(
        athlete_id=athlete_id,  # type: ignore[arg-type]
        provider="hevy",
        extra={"api_key": api_key},
    )

    since = datetime.now(timezone.utc) - timedelta(days=7)
    until = datetime.now(timezone.utc)

    try:
        with HevyConnector(cred, client_id=api_key, client_secret="") as connector:
            workouts = connector.fetch_workouts(since, until)
    except Exception:
        raise HTTPException(status_code=502, detail="Failed to fetch Hevy workouts")

    plan = _get_latest_plan(athlete_id, db)
    if plan is None:
        return {"synced": 0, "skipped": len(workouts), "reason": "no plan found"}

    slots = json.loads(plan.weekly_slots_json)
    lifting_by_date: dict[str, str] = {
        s["date"]: s["id"]
        for s in slots
        if s.get("sport") == "lifting"
    }

    synced = 0
    skipped = 0
    for workout in workouts:
        date_key = workout.date.isoformat()
        session_id = lifting_by_date.get(date_key)
        if session_id is None:
            skipped += 1
            continue

        actual_data = {
            "source": "hevy",
            "hevy_workout_id": workout.id,
            "exercises": [
                {
                    "name": ex.name,
                    "sets": [
                        {
                            "reps": s.reps,
                            "weight_kg": s.weight_kg,
                            "rpe": s.rpe,
                            "set_type": s.set_type,
                        }
                        for s in ex.sets
                    ],
                }
                for ex in workout.exercises
            ],
        }
        _upsert_session_log(
            athlete_id=athlete_id,
            plan_id=plan.id,
            session_id=session_id,
            actual_duration_min=workout.duration_seconds // 60,
            actual_data=actual_data,
            db=db,
        )
        synced += 1

    return {"synced": synced, "skipped": skipped}


# ── Terra Sync ────────────────────────────────────────────────────────────────


@router.post("/{athlete_id}/connectors/terra/sync")
def terra_sync(
    athlete_id: str,
    db: DB,
    _: Annotated[str, Depends(_require_own)],
) -> dict:
    """Fetch today's Terra health data and store latest HRV/sleep in connector creds."""
    from datetime import date

    cred_model = (
        db.query(ConnectorCredentialModel)
        .filter_by(athlete_id=athlete_id, provider="terra")
        .first()
    )
    if cred_model is None:
        raise HTTPException(status_code=404, detail="Terra connector not connected")

    extra = json.loads(cred_model.extra_json or "{}")
    cred = ConnectorCredential(
        athlete_id=athlete_id,  # type: ignore[arg-type]
        provider="terra",
        extra=extra,
    )

    api_key = os.getenv("TERRA_API_KEY", "")
    dev_id = os.getenv("TERRA_DEV_ID", "")

    try:
        with TerraConnector(cred, client_id=api_key, client_secret=dev_id) as connector:
            health_data = connector.fetch_daily(date.today())
    except Exception:
        raise HTTPException(status_code=502, detail="Failed to fetch Terra data")

    extra["last_hrv_rmssd"] = health_data.hrv_rmssd
    extra["last_sleep_hours"] = health_data.sleep_duration_hours
    extra["last_sleep_score"] = health_data.sleep_score
    extra["last_steps"] = health_data.steps
    extra["last_sync"] = datetime.now(timezone.utc).isoformat()
    cred_model.extra_json = json.dumps(extra)
    db.commit()

    return {
        "synced": 1,
        "hrv_rmssd": health_data.hrv_rmssd,
        "sleep_hours": health_data.sleep_duration_hours,
        "sleep_score": health_data.sleep_score,
    }


# ── Strava Sync ───────────────────────────────────────────────────────────────


@router.post("/{athlete_id}/connectors/strava/sync")
def strava_sync(
    athlete_id: str,
    db: DB,
    _: Annotated[str, Depends(_require_own)],
) -> dict:
    """Fetch last 30 days of Strava activities → map to run/bike/swim sessions → SessionLogModel."""
    cred_model = (
        db.query(ConnectorCredentialModel)
        .filter_by(athlete_id=athlete_id, provider="strava")
        .first()
    )
    if cred_model is None:
        raise HTTPException(status_code=404, detail="Strava connector not connected")

    cred = ConnectorCredential(
        athlete_id=athlete_id,  # type: ignore[arg-type]
        provider="strava",
        access_token=cred_model.access_token,
        refresh_token=cred_model.refresh_token,
        expires_at=cred_model.expires_at,
    )

    client_id = os.getenv("STRAVA_CLIENT_ID", "")
    client_secret = os.getenv("STRAVA_CLIENT_SECRET", "")

    since = datetime.now(timezone.utc) - timedelta(days=30)
    until = datetime.now(timezone.utc)

    try:
        with StravaConnector(cred, client_id=client_id, client_secret=client_secret) as connector:
            activities = connector.fetch_activities(since, until)
    except Exception:
        raise HTTPException(status_code=502, detail="Failed to fetch Strava activities")

    sport_map = {
        "Run": "running",
        "Ride": "biking",
        "Swim": "swimming",
        "VirtualRide": "biking",
        "TrailRun": "running",
    }

    plan = _get_latest_plan(athlete_id, db)
    if plan is None:
        return {"synced": 0, "skipped": len(activities), "reason": "no plan found"}

    slots = json.loads(plan.weekly_slots_json)
    session_map: dict[tuple[str, str], str] = {
        (s["date"], s["sport"]): s["id"]
        for s in slots
    }

    synced = 0
    skipped = 0
    for activity in activities:
        sport = sport_map.get(activity.sport_type)
        if sport is None:
            skipped += 1
            continue

        date_key = activity.date.isoformat()
        session_id = session_map.get((date_key, sport))
        if session_id is None:
            skipped += 1
            continue

        actual_data = {
            "source": "strava",
            "strava_activity_id": activity.id,
            "distance_meters": activity.distance_meters,
            "elevation_gain_meters": activity.elevation_gain_meters,
            "average_hr": activity.average_hr,
            "max_hr": activity.max_hr,
        }
        duration_min = activity.duration_seconds // 60 if activity.duration_seconds else None
        _upsert_session_log(
            athlete_id=athlete_id,
            plan_id=plan.id,
            session_id=session_id,
            actual_duration_min=duration_min,
            actual_data=actual_data,
            db=db,
        )
        synced += 1

    return {"synced": synced, "skipped": skipped}


# ── List & Delete ─────────────────────────────────────────────────────────────


@router.get("/{athlete_id}/connectors", response_model=ConnectorListResponse)
def list_connectors(athlete_id: str, db: DB) -> ConnectorListResponse:
    if db.get(AthleteModel, athlete_id) is None:
        raise HTTPException(status_code=404)

    creds = (
        db.query(ConnectorCredentialModel)
        .filter_by(athlete_id=athlete_id)
        .all()
    )
    return ConnectorListResponse(connectors=[
        ConnectorStatus(
            provider=c.provider,
            connected=True,
            expires_at=c.expires_at,
        )
        for c in creds
    ])


@router.delete("/{athlete_id}/connectors/{provider}", status_code=204)
def delete_connector(athlete_id: str, provider: Literal["strava", "hevy"], db: DB) -> None:
    if db.get(AthleteModel, athlete_id) is None:
        raise HTTPException(status_code=404)
    cred = (
        db.query(ConnectorCredentialModel)
        .filter_by(athlete_id=athlete_id, provider=provider)
        .first()
    )
    if cred is None:
        raise HTTPException(status_code=404)
    db.delete(cred)
    db.commit()
