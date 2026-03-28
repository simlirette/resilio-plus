import json
import os
import uuid
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.connectors.strava import StravaConnector
from app.db.models import AthleteModel, ConnectorCredentialModel
from app.dependencies import get_db
from app.schemas.connector import ConnectorCredential
from app.schemas.connector_api import (
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
def delete_connector(athlete_id: str, provider: str, db: DB) -> None:
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
