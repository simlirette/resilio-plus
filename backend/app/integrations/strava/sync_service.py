# backend/app/integrations/strava/sync_service.py
"""Incremental Strava activity sync: fetch → map → upsert strava_activities."""
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from ...connectors.strava import StravaConnector
from ...db.models import ConnectorCredentialModel, StravaActivityModel
from ...schemas.strava import SyncSummary
from .activity_mapper import SPORT_MAP, to_model
from .oauth_service import get_valid_credential


def sync(athlete_id: str, db: Session) -> SyncSummary:
    """Fetch Strava activities since last_sync_at and upsert to strava_activities.

    - If last_sync_at is NULL, fetches last 90 days (initial bootstrap).
    - Incremental on subsequent calls.
    - Idempotent: re-syncing same activities updates existing rows.
    - Raises ValueError if Strava is not connected for this athlete.
    """
    cred_row = (
        db.query(ConnectorCredentialModel)
        .filter_by(athlete_id=athlete_id, provider="strava")
        .first()
    )
    if cred_row is None:
        raise ValueError(f"Strava not connected for athlete {athlete_id}")

    cred = get_valid_credential(athlete_id, db)

    now = datetime.now(timezone.utc)
    if cred_row.last_sync_at is None:
        since = now - timedelta(days=90)
    else:
        since = cred_row.last_sync_at
        if since.tzinfo is None:
            since = since.replace(tzinfo=timezone.utc)

    client_id = os.getenv("STRAVA_CLIENT_ID", "")
    client_secret = os.getenv("STRAVA_CLIENT_SECRET", "")

    with StravaConnector(cred, client_id=client_id, client_secret=client_secret) as connector:
        activities = connector.fetch_activities(since=since, until=now)

    synced = 0
    skipped = 0
    sport_breakdown: dict[str, int] = {}

    for activity in activities:
        if activity.sport_type not in SPORT_MAP:
            skipped += 1
            continue

        model = to_model(activity, athlete_id)
        db.merge(model)

        sport = model.sport_type
        sport_breakdown[sport] = sport_breakdown.get(sport, 0) + 1
        synced += 1

    db.query(ConnectorCredentialModel).filter_by(
        athlete_id=athlete_id, provider="strava"
    ).update({"last_sync_at": now})
    db.commit()

    return SyncSummary(synced=synced, skipped=skipped, sport_breakdown=sport_breakdown)
