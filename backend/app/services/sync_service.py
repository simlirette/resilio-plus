"""SyncService — centralized sync logic for all connectors.

Both the manual sync endpoints (connectors.py) and the auto-sync scheduler
(sync_scheduler.py) delegate to this service. Single source of truth for
Strava → SessionLog, Hevy → SessionLog, Terra → extra_json mappings.
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..connectors.hevy import HevyConnector
from ..connectors.terra import TerraConnector
from ..db.models import ConnectorCredentialModel, SessionLogModel, TrainingPlanModel
from ..schemas.connector import ConnectorCredential

logger = logging.getLogger(__name__)


class ConnectorNotFoundError(Exception):
    """Raised when the required connector credential is not found in the DB."""


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _get_latest_plan(athlete_id: str, db: Session) -> TrainingPlanModel | None:
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


def _set_last_sync(cred_model: ConnectorCredentialModel, db: Session) -> None:
    extra = json.loads(cred_model.extra_json or "{}")
    extra["last_sync"] = datetime.now(timezone.utc).isoformat()
    cred_model.extra_json = json.dumps(extra)
    db.commit()


# ---------------------------------------------------------------------------
# SyncService
# ---------------------------------------------------------------------------


class SyncService:
    @staticmethod
    def sync_hevy(athlete_id: str, db: Session) -> dict[str, Any]:
        """Fetch Hevy workouts (last 7 days) → map to SessionLogModel.

        Returns: {"synced": int, "skipped": int}
        Raises: ConnectorNotFoundError if Hevy not connected.
        """
        cred_model = (
            db.query(ConnectorCredentialModel)
            .filter_by(athlete_id=athlete_id, provider="hevy")
            .first()
        )
        if cred_model is None:
            raise ConnectorNotFoundError(f"Hevy not connected for athlete {athlete_id}")

        extra = json.loads(cred_model.extra_json or "{}")
        api_key = extra.get("api_key", "")

        cred = ConnectorCredential(
            athlete_id=athlete_id,  # type: ignore[arg-type]
            provider="hevy",
            extra={"api_key": api_key},
        )

        since = datetime.now(timezone.utc) - timedelta(days=7)
        until = datetime.now(timezone.utc)

        with HevyConnector(cred, client_id=api_key, client_secret="") as connector:
            workouts = connector.fetch_workouts(since, until)

        plan = _get_latest_plan(athlete_id, db)
        if plan is None:
            _set_last_sync(cred_model, db)
            return {"synced": 0, "skipped": len(workouts), "reason": "no plan found"}

        slots = json.loads(plan.weekly_slots_json)
        lifting_by_date: dict[str, str] = {
            s["date"]: s["id"] for s in slots if s.get("sport") == "lifting"
        }

        synced = 0
        skipped = 0
        for workout in workouts:
            date_key = workout.date.isoformat()
            session_id = lifting_by_date.get(date_key)
            if session_id is None:
                skipped += 1
                continue
            _upsert_session_log(
                athlete_id=athlete_id,
                plan_id=plan.id,
                session_id=session_id,
                actual_duration_min=workout.duration_seconds // 60,
                actual_data={
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
                },
                db=db,
            )
            synced += 1

        _set_last_sync(cred_model, db)
        return {"synced": synced, "skipped": skipped}

    @staticmethod
    def sync_terra(athlete_id: str, db: Session) -> dict[str, Any]:
        """Fetch Terra health data for today → store in extra_json.

        Returns: {"synced": 1, "hrv_rmssd": float|None, "sleep_hours": float|None, "sleep_score": int|None}
        Raises: ConnectorNotFoundError if Terra not connected.
        """
        from datetime import date

        cred_model = (
            db.query(ConnectorCredentialModel)
            .filter_by(athlete_id=athlete_id, provider="terra")
            .first()
        )
        if cred_model is None:
            raise ConnectorNotFoundError(f"Terra not connected for athlete {athlete_id}")

        extra = json.loads(cred_model.extra_json or "{}")
        cred = ConnectorCredential(
            athlete_id=athlete_id,  # type: ignore[arg-type]
            provider="terra",
            extra=extra,
        )
        api_key = os.getenv("TERRA_API_KEY", "")
        dev_id = os.getenv("TERRA_DEV_ID", "")

        with TerraConnector(cred, client_id=api_key, client_secret=dev_id) as connector:
            health_data = connector.fetch_daily(date.today())

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
