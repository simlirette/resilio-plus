import json
import logging
import os
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from ..connectors.hevy import HevyConnector
from ..connectors.strava import StravaConnector
from ..db.models import ConnectorCredentialModel
from ..schemas.connector import ConnectorCredential, HevyWorkout, StravaActivity, TerraHealthData

logger = logging.getLogger(__name__)

_WEEK_SECONDS = 7 * 24 * 3600


def _model_to_credential(m: ConnectorCredentialModel) -> ConnectorCredential:
    return ConnectorCredential(
        id=UUID(m.id),
        athlete_id=UUID(m.athlete_id),
        provider=m.provider,
        access_token=m.access_token_enc,
        refresh_token=m.refresh_token_enc,
        expires_at=m.expires_at,
        extra=json.loads(m.extra_json),
    )


def _persist_token_update(
    m: ConnectorCredentialModel, cred: ConnectorCredential, db: Session
) -> None:
    m.access_token_enc = cred.access_token
    m.refresh_token_enc = cred.refresh_token
    m.expires_at = cred.expires_at
    db.commit()


def fetch_connector_data(athlete_id: str, db: Session) -> dict:
    """Fetch live data from all connected providers for the athlete.

    Always returns all keys even on error:
        {
            "strava_activities": list[StravaActivity],
            "hevy_workouts": list[HevyWorkout],
            "terra_health": TerraHealthData | None,
        }
    Terra data is read from cached extra_json (written by SyncService.sync_terra) —
    no live API call needed here.
    """
    now = datetime.now(timezone.utc)
    since = datetime.fromtimestamp(now.timestamp() - _WEEK_SECONDS, tz=timezone.utc)

    strava_activities: list[StravaActivity] = []
    hevy_workouts: list[HevyWorkout] = []
    terra_health: TerraHealthData | None = None

    # ── Strava ──────────────────────────────────────────────────────────────
    strava_model = (
        db.query(ConnectorCredentialModel)
        .filter_by(athlete_id=athlete_id, provider="strava")
        .first()
    )
    if strava_model:
        original_token = strava_model.access_token_enc
        cred = _model_to_credential(strava_model)
        client_id = os.getenv("STRAVA_CLIENT_ID", "")
        client_secret = os.getenv("STRAVA_CLIENT_SECRET", "")
        try:
            with StravaConnector(cred, client_id=client_id, client_secret=client_secret) as connector:
                strava_activities = connector.fetch_activities(since=since, until=now)
                if connector.credential.access_token != original_token:
                    _persist_token_update(strava_model, connector.credential, db)
        except Exception:
            logger.warning("Strava fetch failed for athlete %s", athlete_id, exc_info=True)

    # ── Hevy ─────────────────────────────────────────────────────────────────
    hevy_model = (
        db.query(ConnectorCredentialModel)
        .filter_by(athlete_id=athlete_id, provider="hevy")
        .first()
    )
    if hevy_model:
        cred = _model_to_credential(hevy_model)
        try:
            with HevyConnector(cred, client_id="", client_secret="") as connector:
                hevy_workouts = connector.fetch_workouts(since=since, until=now)
        except Exception:
            logger.warning("Hevy fetch failed for athlete %s", athlete_id, exc_info=True)

    # ── Terra (cached) ────────────────────────────────────────────────────────
    terra_model = (
        db.query(ConnectorCredentialModel)
        .filter_by(athlete_id=athlete_id, provider="terra")
        .first()
    )
    if terra_model:
        from datetime import date
        extra = json.loads(terra_model.extra_json or "{}")
        terra_health = TerraHealthData(
            date=date.today(),
            hrv_rmssd=extra.get("last_hrv_rmssd"),
            sleep_duration_hours=extra.get("last_sleep_hours"),
            sleep_score=extra.get("last_sleep_score"),
            steps=extra.get("last_steps"),
            active_energy_kcal=None,
        )

    return {
        "strava_activities": strava_activities,
        "hevy_workouts": hevy_workouts,
        "terra_health": terra_health,
    }
