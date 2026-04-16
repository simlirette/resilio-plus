import json
import uuid
from datetime import datetime, timezone
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..connectors.apple_health import AppleHealthConnector
from ..connectors.fit import FitConnector
from ..connectors.gpx import GpxConnector
from ..db.models import AthleteModel, ConnectorCredentialModel, SessionLogModel, TrainingPlanModel
from ..dependencies import get_current_athlete_id, get_db
from ..jobs.registry import register_athlete_jobs, unregister_athlete_jobs
from ..jobs.scheduler import get_scheduler
from ..schemas.connector_api import (
    ConnectorListResponse,
    ConnectorStatus,
    HevyConnectRequest,
)
from ..services.sync_service import ConnectorNotFoundError, SyncService

router = APIRouter(prefix="/athletes", tags=["connectors"])

DB = Annotated[Session, Depends(get_db)]


def _upsert_credential(
    *,
    athlete_id: str,
    provider: str,
    access_token_enc: str | None,
    refresh_token_enc: str | None,
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
        existing.access_token_enc = access_token_enc
        existing.refresh_token_enc = refresh_token_enc
        existing.expires_at = expires_at
        existing.extra_json = extra_json
        db.commit()
    else:
        db.add(
            ConnectorCredentialModel(
                id=str(uuid.uuid4()),
                athlete_id=athlete_id,
                provider=provider,
                access_token_enc=access_token_enc,
                refresh_token_enc=refresh_token_enc,
                expires_at=expires_at,
                extra_json=extra_json,
            )
        )
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
    actual_data: dict[str, Any],
    db: Session,
) -> None:
    existing = (
        db.query(SessionLogModel).filter_by(athlete_id=athlete_id, session_id=session_id).first()
    )
    if existing:
        existing.actual_duration_min = actual_duration_min
        existing.actual_data_json = json.dumps(actual_data)
        existing.logged_at = datetime.now(timezone.utc)
        db.commit()
    else:
        db.add(
            SessionLogModel(
                id=str(uuid.uuid4()),
                athlete_id=athlete_id,
                plan_id=plan_id,
                session_id=session_id,
                actual_duration_min=actual_duration_min,
                skipped=False,
                actual_data_json=json.dumps(actual_data),
                logged_at=datetime.now(timezone.utc),
            )
        )
        db.commit()


def _file_import_to_session_log(
    athlete_id: str,
    parsed: dict[str, Any],
    sport: str,
    source: str,
    db: Session,
) -> dict[str, Any]:
    """Find matching plan session by date+sport and create SessionLogModel."""
    plan = _get_latest_plan(athlete_id, db)
    if plan is None:
        return {"imported": False, "reason": "no active plan found"}

    slots = json.loads(plan.weekly_slots_json)
    date_key = parsed["activity_date"].isoformat()
    session_id = next(
        (s["id"] for s in slots if s["date"] == date_key and s["sport"] == sport),
        None,
    )

    actual_data = {
        "source": source,
        "distance_km": parsed.get("distance_km"),
        "duration_seconds": parsed.get("duration_seconds"),
        "avg_pace_sec_per_km": parsed.get("avg_pace_sec_per_km"),
        "elevation_gain_m": parsed.get("elevation_gain_m"),
    }

    if session_id:
        _upsert_session_log(
            athlete_id=athlete_id,
            plan_id=plan.id,
            session_id=session_id,
            actual_duration_min=parsed["duration_seconds"] // 60
            if parsed.get("duration_seconds")
            else None,
            actual_data=actual_data,
            db=db,
        )
        return {"imported": True, "session_id": session_id, "source": source}
    else:
        return {"imported": False, "reason": f"no {sport} session found for {date_key}"}


# ── GPX/FIT File Upload ───────────────────────────────────────────────────────


@router.post("/{athlete_id}/connectors/files/gpx")
def upload_gpx(
    athlete_id: str,
    db: DB,
    _: Annotated[str, Depends(_require_own)],
    file: UploadFile = File(...),
) -> dict[str, Any]:
    """Upload GPX file → parse → map to running session → SessionLogModel."""
    content = file.file.read()
    connector = GpxConnector()
    try:
        parsed = connector.parse(content)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return _file_import_to_session_log(athlete_id, parsed, "running", "gpx", db)


@router.post("/{athlete_id}/connectors/files/fit")
def upload_fit(
    athlete_id: str,
    db: DB,
    _: Annotated[str, Depends(_require_own)],
    file: UploadFile = File(...),
) -> dict[str, Any]:
    """Upload FIT file → parse → map to running/biking session → SessionLogModel."""
    content = file.file.read()
    connector = FitConnector()
    try:
        parsed = connector.parse(content)
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=422, detail=str(e))

    return _file_import_to_session_log(athlete_id, parsed, "running", "fit", db)


# ── Hevy ─────────────────────────────────────────────────────────────────────


@router.post("/{athlete_id}/connectors/hevy", status_code=201)
def hevy_connect(
    athlete_id: str,
    req: HevyConnectRequest,
    db: DB,
    _: Annotated[str, Depends(_require_own)],
) -> ConnectorStatus:
    if db.get(AthleteModel, athlete_id) is None:
        raise HTTPException(status_code=404)

    _upsert_credential(
        athlete_id=athlete_id,
        provider="hevy",
        access_token_enc=None,
        refresh_token_enc=None,
        expires_at=None,
        extra_json=json.dumps({"api_key": req.api_key}),
        db=db,
    )
    try:
        register_athlete_jobs(athlete_id, "hevy", get_scheduler())
    except RuntimeError:
        pass  # scheduler not started (testing)
    return ConnectorStatus(provider="hevy", connected=True, expires_at=None)


# ── Terra ─────────────────────────────────────────────────────────────────────


ProviderStatus = Literal["ok", "skipped", "error"]


class SyncAllResponse(BaseModel):
    synced_at: datetime
    results: dict[str, ProviderStatus]
    errors: dict[str, str]


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
        access_token_enc=None,
        refresh_token_enc=None,
        expires_at=None,
        extra_json=json.dumps({"terra_user_id": req.terra_user_id}),
        db=db,
    )
    try:
        register_athlete_jobs(athlete_id, "terra", get_scheduler())
    except RuntimeError:
        pass  # scheduler not started (testing)
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
) -> dict[str, Any]:
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
        db.add(
            ConnectorCredentialModel(
                id=str(uuid.uuid4()),
                athlete_id=athlete_id,
                provider="apple_health",
                extra_json=json.dumps(extra_update),
            )
        )
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
) -> dict[str, Any]:
    """Fetch last 7 days of Hevy workouts → map to lifting sessions → SessionLogModel."""
    try:
        return SyncService.sync_hevy(athlete_id, db)
    except ConnectorNotFoundError:
        raise HTTPException(status_code=404, detail="Hevy connector not connected")


# ── Terra Sync ────────────────────────────────────────────────────────────────


@router.post("/{athlete_id}/connectors/terra/sync")
def terra_sync(
    athlete_id: str,
    db: DB,
    _: Annotated[str, Depends(_require_own)],
) -> dict[str, Any]:
    """Fetch today's Terra health data and store latest HRV/sleep in connector creds."""
    try:
        return SyncService.sync_terra(athlete_id, db)
    except ConnectorNotFoundError:
        raise HTTPException(status_code=404, detail="Terra connector not connected")


# ── List & Delete ─────────────────────────────────────────────────────────────


@router.get("/{athlete_id}/connectors", response_model=ConnectorListResponse)
def list_connectors(
    athlete_id: str,
    db: DB,
    _: Annotated[str, Depends(_require_own)],
) -> ConnectorListResponse:
    if db.get(AthleteModel, athlete_id) is None:
        raise HTTPException(status_code=404)

    creds = db.query(ConnectorCredentialModel).filter_by(athlete_id=athlete_id).all()
    return ConnectorListResponse(
        connectors=[
            ConnectorStatus(
                provider=c.provider,
                connected=True,
                expires_at=c.expires_at,
                last_sync=json.loads(c.extra_json or "{}").get("last_sync"),
            )
            for c in creds
        ]
    )


@router.post("/{athlete_id}/connectors/sync", response_model=SyncAllResponse)
def sync_all(
    athlete_id: str,
    db: DB,
    _: Annotated[str, Depends(_require_own)],
) -> SyncAllResponse:
    results: dict[str, Literal["ok", "skipped", "error"]] = {}
    errors: dict[str, str] = {}

    for provider, sync_fn in [
        ("hevy", SyncService.sync_hevy),
        ("terra", SyncService.sync_terra),
    ]:
        try:
            sync_fn(athlete_id, db)
            results[provider] = "ok"
        except ConnectorNotFoundError:
            results[provider] = "skipped"
        except Exception as exc:  # noqa: BLE001
            results[provider] = "error"
            errors[provider] = str(exc)

    return SyncAllResponse(
        synced_at=datetime.now(timezone.utc),
        results=results,
        errors=errors,
    )


@router.delete("/{athlete_id}/connectors/{provider}", status_code=204)
def delete_connector(
    athlete_id: str,
    provider: Literal["strava", "hevy", "terra"],
    db: DB,
    _: Annotated[str, Depends(_require_own)],
) -> None:
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
    try:
        unregister_athlete_jobs(athlete_id, provider, get_scheduler())
    except RuntimeError:
        pass  # scheduler not started (testing)
    db.commit()
