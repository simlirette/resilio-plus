# Phase 9 — Connecteurs complets Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Compléter Phase 9 : créer un `SyncService` centralisé, brancher le scheduler auto-sync (Strava + Hevy + Terra toutes les 6h), fixer le pipeline Terra → Recovery Coach, et ajouter les formulaires Connect + last_sync dans le frontend.

**Architecture:** `SyncService` extrait la logique de mapping de `connectors.py` en un service réutilisable. Le scheduler APScheduler (déjà bootstrappé) et les endpoints manuels délèguent tous les deux à ce service. `fetch_connector_data` est corrigé pour exposer `terra_health` au Recovery Coach.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy 2 (sync), APScheduler, pytest + SQLite in-memory, Next.js (TypeScript).

**pytest path:** `C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe`

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| Create | `backend/app/services/sync_service.py` | Logique mapping Strava/Hevy/Terra → SessionLogModel |
| Modify | `backend/app/core/sync_scheduler.py` | Délègue à SyncService + ajoute job Terra |
| Modify | `backend/app/schemas/connector_api.py` | Ajoute `last_sync: str \| None` à ConnectorStatus |
| Modify | `backend/app/routes/connectors.py` | Endpoints manuels délèguent à SyncService + fix delete/list |
| Modify | `backend/app/services/connector_service.py` | Ajoute `terra_health` dans fetch_connector_data |
| Modify | `frontend/src/lib/api.ts` | Ajoute `last_sync`, `connectHevy`, `disconnectConnector` |
| Modify | `frontend/src/app/settings/connectors/page.tsx` | Connect forms Hevy/Terra + last_sync display + disconnect |
| Create | `tests/backend/services/test_sync_service.py` | Tests SyncService |
| Create | `tests/backend/core/test_sync_scheduler.py` | Tests scheduler 3 jobs |
| Create | `tests/backend/api/test_connectors_phase9.py` | Tests last_sync, delete terra, token refresh |
| Create | `tests/backend/services/test_connector_service_terra.py` | Tests terra_health dans fetch_connector_data |

---

### Task 1: Create SyncService

**Files:**
- Create: `backend/app/services/sync_service.py`
- Create: `tests/backend/services/test_sync_service.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/backend/services/test_sync_service.py`:

```python
"""Tests for SyncService — centralized sync logic for all connectors."""
import json
import uuid
from datetime import date, datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db.models import (
    AthleteModel, Base, ConnectorCredentialModel, SessionLogModel, TrainingPlanModel,
)
from backend.app.services.sync_service import ConnectorNotFoundError, SyncService
from backend.app.schemas.connector import (
    HevyExercise, HevySet, HevyWorkout, StravaActivity, TerraHealthData,
)

SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def _make_athlete(db):
    a = AthleteModel(
        id="a1", name="Test", age=30, sex="M", weight_kg=70.0, height_cm=175.0,
        primary_sport="running", hours_per_week=6.0,
        sports_json='["running"]', goals_json='["run 10k"]',
        available_days_json='["monday"]', equipment_json='[]',
    )
    db.add(a)
    db.commit()
    return a


def _make_plan(db, sessions_json: str = "[]"):
    p = TrainingPlanModel(
        id="plan1", athlete_id="a1",
        start_date=date.today(), end_date=date.today(),
        phase="base", total_weekly_hours=6.0, acwr=1.0,
        weekly_slots_json=sessions_json,
    )
    db.add(p)
    db.commit()
    return p


def _make_cred(db, provider: str, extra: dict | None = None):
    c = ConnectorCredentialModel(
        id=str(uuid.uuid4()), athlete_id="a1", provider=provider,
        extra_json=json.dumps(extra or {}),
    )
    db.add(c)
    db.commit()
    return c


# ── sync_strava ────────────────────────────────────────────────────────────────

def test_sync_strava_raises_if_not_connected(db):
    _make_athlete(db)
    with pytest.raises(ConnectorNotFoundError):
        SyncService.sync_strava("a1", db)


def test_sync_strava_maps_activity_to_session_log(db):
    _make_athlete(db)
    today = date.today().isoformat()
    _make_plan(db, json.dumps([
        {"id": "s1", "date": today, "sport": "running", "workout_type": "easy_z1", "duration_min": 60}
    ]))
    cred = _make_cred(db, "strava")
    cred.access_token = "tok"
    cred.refresh_token = "ref"
    db.commit()

    mock_activity = StravaActivity(
        id="strava_123", name="Morning Run", sport_type="Run",
        date=date.today(), duration_seconds=3600,
        distance_meters=10000.0, elevation_gain_meters=50.0,
        average_hr=145.0, max_hr=165.0, perceived_exertion=None,
    )

    with patch("backend.app.services.sync_service.StravaConnector") as MockStrava:
        instance = MockStrava.return_value.__enter__.return_value
        instance.fetch_activities.return_value = [mock_activity]
        instance.credential.access_token = "tok"
        result = SyncService.sync_strava("a1", db)

    assert result["synced"] == 1
    assert result["skipped"] == 0
    log = db.query(SessionLogModel).filter_by(athlete_id="a1", session_id="s1").first()
    assert log is not None
    assert log.actual_duration_min == 60
    data = json.loads(log.actual_data_json)
    assert data["source"] == "strava"
    assert data["strava_activity_id"] == "strava_123"


def test_sync_strava_updates_last_sync(db):
    _make_athlete(db)
    _make_plan(db)
    cred = _make_cred(db, "strava")
    cred.access_token = "tok"
    cred.refresh_token = "ref"
    db.commit()

    with patch("backend.app.services.sync_service.StravaConnector") as MockStrava:
        instance = MockStrava.return_value.__enter__.return_value
        instance.fetch_activities.return_value = []
        instance.credential.access_token = "tok"
        SyncService.sync_strava("a1", db)

    db.refresh(cred)
    extra = json.loads(cred.extra_json)
    assert "last_sync" in extra


def test_sync_strava_persists_refreshed_token(db):
    _make_athlete(db)
    _make_plan(db)
    cred = _make_cred(db, "strava")
    cred.access_token = "old_tok"
    cred.refresh_token = "old_ref"
    db.commit()

    with patch("backend.app.services.sync_service.StravaConnector") as MockStrava:
        instance = MockStrava.return_value.__enter__.return_value
        instance.fetch_activities.return_value = []
        instance.credential.access_token = "new_tok"
        instance.credential.refresh_token = "new_ref"
        instance.credential.expires_at = 9999999999
        SyncService.sync_strava("a1", db)

    db.refresh(cred)
    assert cred.access_token == "new_tok"
    assert cred.refresh_token == "new_ref"


def test_sync_strava_returns_zero_when_no_plan(db):
    _make_athlete(db)
    cred = _make_cred(db, "strava")
    cred.access_token = "tok"
    cred.refresh_token = "ref"
    db.commit()

    mock_activity = StravaActivity(
        id="strava_1", name="Run", sport_type="Run", date=date.today(),
        duration_seconds=3600, distance_meters=10000.0,
        elevation_gain_meters=None, average_hr=None, max_hr=None, perceived_exertion=None,
    )

    with patch("backend.app.services.sync_service.StravaConnector") as MockStrava:
        instance = MockStrava.return_value.__enter__.return_value
        instance.fetch_activities.return_value = [mock_activity]
        instance.credential.access_token = "tok"
        result = SyncService.sync_strava("a1", db)

    assert result["synced"] == 0
    assert "reason" in result


# ── sync_hevy ──────────────────────────────────────────────────────────────────

def test_sync_hevy_raises_if_not_connected(db):
    _make_athlete(db)
    with pytest.raises(ConnectorNotFoundError):
        SyncService.sync_hevy("a1", db)


def test_sync_hevy_maps_workout_to_session_log(db):
    _make_athlete(db)
    today = date.today().isoformat()
    _make_plan(db, json.dumps([
        {"id": "s2", "date": today, "sport": "lifting", "workout_type": "strength", "duration_min": 60}
    ]))
    _make_cred(db, "hevy", {"api_key": "test-key"})

    mock_workout = HevyWorkout(
        id="hevy-1", title="Upper A", date=date.today(), duration_seconds=3600,
        exercises=[HevyExercise(
            name="Bench Press",
            sets=[HevySet(reps=8, weight_kg=80.0, rpe=7, set_type="normal")]
        )]
    )

    with patch("backend.app.services.sync_service.HevyConnector") as MockHevy:
        instance = MockHevy.return_value.__enter__.return_value
        instance.fetch_workouts.return_value = [mock_workout]
        result = SyncService.sync_hevy("a1", db)

    assert result["synced"] == 1
    log = db.query(SessionLogModel).filter_by(athlete_id="a1", session_id="s2").first()
    assert log is not None
    assert log.actual_duration_min == 60
    data = json.loads(log.actual_data_json)
    assert data["source"] == "hevy"
    assert data["exercises"][0]["name"] == "Bench Press"
    assert data["exercises"][0]["sets"][0]["weight_kg"] == 80.0


def test_sync_hevy_updates_last_sync(db):
    _make_athlete(db)
    _make_plan(db)
    cred = _make_cred(db, "hevy", {"api_key": "test-key"})

    with patch("backend.app.services.sync_service.HevyConnector") as MockHevy:
        instance = MockHevy.return_value.__enter__.return_value
        instance.fetch_workouts.return_value = []
        SyncService.sync_hevy("a1", db)

    db.refresh(cred)
    extra = json.loads(cred.extra_json)
    assert "last_sync" in extra


# ── sync_terra ─────────────────────────────────────────────────────────────────

def test_sync_terra_raises_if_not_connected(db):
    _make_athlete(db)
    with pytest.raises(ConnectorNotFoundError):
        SyncService.sync_terra("a1", db)


def test_sync_terra_stores_hrv_in_extra_json(db):
    _make_athlete(db)
    cred = _make_cred(db, "terra", {"terra_user_id": "uid-abc"})

    mock_data = TerraHealthData(
        date=date.today(), hrv_rmssd=52.0, sleep_duration_hours=7.5,
        sleep_score=80, steps=8000, active_energy_kcal=400.0,
    )

    with patch("backend.app.services.sync_service.TerraConnector") as MockTerra:
        instance = MockTerra.return_value.__enter__.return_value
        instance.fetch_daily.return_value = mock_data
        result = SyncService.sync_terra("a1", db)

    assert result["synced"] == 1
    assert result["hrv_rmssd"] == 52.0
    assert result["sleep_hours"] == 7.5
    db.refresh(cred)
    extra = json.loads(cred.extra_json)
    assert extra["last_hrv_rmssd"] == 52.0
    assert extra["last_sleep_hours"] == 7.5
    assert "last_sync" in extra


def test_sync_terra_updates_last_sync_even_with_null_values(db):
    _make_athlete(db)
    cred = _make_cred(db, "terra", {"terra_user_id": "uid-abc"})

    mock_data = TerraHealthData(
        date=date.today(), hrv_rmssd=None, sleep_duration_hours=None,
        sleep_score=None, steps=None, active_energy_kcal=None,
    )

    with patch("backend.app.services.sync_service.TerraConnector") as MockTerra:
        instance = MockTerra.return_value.__enter__.return_value
        instance.fetch_daily.return_value = mock_data
        SyncService.sync_terra("a1", db)

    db.refresh(cred)
    extra = json.loads(cred.extra_json)
    assert "last_sync" in extra
```

- [ ] **Step 2: Run tests to confirm they fail**

```
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/services/test_sync_service.py -v
```
Expected: `ModuleNotFoundError` — `backend.app.services.sync_service` does not exist.

- [ ] **Step 3: Create `backend/app/services/sync_service.py`**

```python
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
    def sync_strava(athlete_id: str, db: Session) -> dict[str, Any]:
        """Fetch Strava activities (last 7 days) → map to SessionLogModel.

        Persists refreshed OAuth tokens when Strava silently renews them.

        Returns: {"synced": int, "skipped": int}
        Raises: ConnectorNotFoundError if Strava not connected.
        """
        from ..connectors.strava import StravaConnector

        cred_model = (
            db.query(ConnectorCredentialModel)
            .filter_by(athlete_id=athlete_id, provider="strava")
            .first()
        )
        if cred_model is None:
            raise ConnectorNotFoundError(f"Strava not connected for athlete {athlete_id}")

        cred = ConnectorCredential(
            athlete_id=athlete_id,  # type: ignore[arg-type]
            provider="strava",
            access_token=cred_model.access_token,
            refresh_token=cred_model.refresh_token,
            expires_at=cred_model.expires_at,
        )
        client_id = os.getenv("STRAVA_CLIENT_ID", "")
        client_secret = os.getenv("STRAVA_CLIENT_SECRET", "")

        since = datetime.now(timezone.utc) - timedelta(days=7)
        until = datetime.now(timezone.utc)

        with StravaConnector(cred, client_id=client_id, client_secret=client_secret) as connector:
            activities = connector.fetch_activities(since, until)
            if connector.credential.access_token != cred_model.access_token:
                cred_model.access_token = connector.credential.access_token
                cred_model.refresh_token = connector.credential.refresh_token
                cred_model.expires_at = connector.credential.expires_at
                db.commit()

        sport_map = {
            "Run": "running",
            "Ride": "biking",
            "Swim": "swimming",
            "VirtualRide": "biking",
            "TrailRun": "running",
        }

        plan = _get_latest_plan(athlete_id, db)
        if plan is None:
            _set_last_sync(cred_model, db)
            return {"synced": 0, "skipped": len(activities), "reason": "no plan found"}

        slots = json.loads(plan.weekly_slots_json)
        session_map: dict[tuple[str, str], str] = {
            (s["date"], s["sport"]): s["id"] for s in slots
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
            _upsert_session_log(
                athlete_id=athlete_id,
                plan_id=plan.id,
                session_id=session_id,
                actual_duration_min=activity.duration_seconds // 60 if activity.duration_seconds else None,
                actual_data={
                    "source": "strava",
                    "strava_activity_id": activity.id,
                    "distance_meters": activity.distance_meters,
                    "elevation_gain_meters": activity.elevation_gain_meters,
                    "average_hr": activity.average_hr,
                    "max_hr": activity.max_hr,
                },
                db=db,
            )
            synced += 1

        _set_last_sync(cred_model, db)
        return {"synced": synced, "skipped": skipped}

    @staticmethod
    def sync_hevy(athlete_id: str, db: Session) -> dict[str, Any]:
        """Fetch Hevy workouts (last 7 days) → map to SessionLogModel.

        Returns: {"synced": int, "skipped": int}
        Raises: ConnectorNotFoundError if Hevy not connected.
        """
        from ..connectors.hevy import HevyConnector

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
        from ..connectors.terra import TerraConnector

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
```

- [ ] **Step 4: Run tests to confirm they pass**

```
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/services/test_sync_service.py -v
```
Expected: 13 tests PASS.

- [ ] **Step 5: Run full suite to confirm no regressions**

```
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/ -x -q
```
Expected: all existing tests still pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/sync_service.py tests/backend/services/test_sync_service.py
git commit -m "feat(phase9): SyncService — centralized Strava/Hevy/Terra sync logic"
```

---

### Task 2: Refactor sync_scheduler.py — delegate to SyncService + add Terra

**Files:**
- Modify: `backend/app/core/sync_scheduler.py`
- Create: `tests/backend/core/test_sync_scheduler.py`

- [ ] **Step 1: Write the failing test**

Create `tests/backend/core/test_sync_scheduler.py`:

```python
"""Tests for sync_scheduler configuration."""
from backend.app.core.sync_scheduler import setup_scheduler


def test_setup_scheduler_registers_three_jobs():
    """Scheduler must have strava_sync, hevy_sync, and terra_sync jobs."""
    scheduler = setup_scheduler()
    try:
        job_ids = {job.id for job in scheduler.get_jobs()}
        assert "strava_sync" in job_ids
        assert "hevy_sync" in job_ids
        assert "terra_sync" in job_ids
    finally:
        scheduler.shutdown(wait=False)


def test_setup_scheduler_all_jobs_run_every_6h():
    """All three jobs must trigger every 6 hours."""
    scheduler = setup_scheduler()
    try:
        for job in scheduler.get_jobs():
            assert job.trigger.interval.total_seconds() == 6 * 3600, \
                f"Job {job.id} interval is not 6h"
    finally:
        scheduler.shutdown(wait=False)
```

- [ ] **Step 2: Run test to confirm it fails**

```
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/core/test_sync_scheduler.py -v
```
Expected: `test_setup_scheduler_registers_three_jobs` FAIL — `terra_sync` not in job_ids.

- [ ] **Step 3: Replace `backend/app/core/sync_scheduler.py`**

```python
"""
Sync scheduler — APScheduler BackgroundScheduler.
Runs sync_all_strava, sync_all_hevy, sync_all_terra every 6 hours.
Each function creates its own DB session (thread-safe).
Delegates all sync logic to SyncService.
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from ..db.database import SessionLocal
from ..db.models import ConnectorCredentialModel
from ..services.sync_service import ConnectorNotFoundError, SyncService

logger = logging.getLogger(__name__)


def sync_all_strava() -> None:
    """Auto-sync Strava for all athletes with active Strava credentials."""
    with SessionLocal() as db:
        creds = db.query(ConnectorCredentialModel).filter_by(provider="strava").all()
        for cred_model in creds:
            try:
                result = SyncService.sync_strava(cred_model.athlete_id, db)
                logger.info(
                    "Strava sync OK: athlete=%s synced=%d skipped=%d",
                    cred_model.athlete_id, result["synced"], result.get("skipped", 0),
                )
            except ConnectorNotFoundError:
                pass
            except Exception:
                logger.warning(
                    "Strava sync failed: athlete=%s", cred_model.athlete_id, exc_info=True
                )


def sync_all_hevy() -> None:
    """Auto-sync Hevy for all athletes with active Hevy API key."""
    with SessionLocal() as db:
        creds = db.query(ConnectorCredentialModel).filter_by(provider="hevy").all()
        for cred_model in creds:
            try:
                result = SyncService.sync_hevy(cred_model.athlete_id, db)
                logger.info(
                    "Hevy sync OK: athlete=%s synced=%d skipped=%d",
                    cred_model.athlete_id, result["synced"], result.get("skipped", 0),
                )
            except ConnectorNotFoundError:
                pass
            except Exception:
                logger.warning(
                    "Hevy sync failed: athlete=%s", cred_model.athlete_id, exc_info=True
                )


def sync_all_terra() -> None:
    """Auto-sync Terra HRV/sleep for all athletes with active Terra credentials."""
    with SessionLocal() as db:
        creds = db.query(ConnectorCredentialModel).filter_by(provider="terra").all()
        for cred_model in creds:
            try:
                result = SyncService.sync_terra(cred_model.athlete_id, db)
                logger.info(
                    "Terra sync OK: athlete=%s hrv=%s sleep=%s",
                    cred_model.athlete_id, result["hrv_rmssd"], result["sleep_hours"],
                )
            except ConnectorNotFoundError:
                pass
            except Exception:
                logger.warning(
                    "Terra sync failed: athlete=%s", cred_model.athlete_id, exc_info=True
                )


def setup_scheduler() -> BackgroundScheduler:
    """Create, configure, and start the BackgroundScheduler."""
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        sync_all_strava, trigger="interval", hours=6,
        id="strava_sync", replace_existing=True, misfire_grace_time=300,
    )
    scheduler.add_job(
        sync_all_hevy, trigger="interval", hours=6,
        id="hevy_sync", replace_existing=True, misfire_grace_time=300,
    )
    scheduler.add_job(
        sync_all_terra, trigger="interval", hours=6,
        id="terra_sync", replace_existing=True, misfire_grace_time=300,
    )
    scheduler.start()
    return scheduler
```

- [ ] **Step 4: Run tests to confirm they pass**

```
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/core/test_sync_scheduler.py -v
```
Expected: 2 tests PASS.

- [ ] **Step 5: Run full suite**

```
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/ -x -q
```
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/sync_scheduler.py tests/backend/core/test_sync_scheduler.py
git commit -m "feat(phase9): scheduler delegates to SyncService + adds Terra auto-sync job"
```

---

### Task 3: Refactor connectors.py + fix schema + add API tests

**Files:**
- Modify: `backend/app/schemas/connector_api.py`
- Modify: `backend/app/routes/connectors.py`
- Create: `tests/backend/api/test_connectors_phase9.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/backend/api/test_connectors_phase9.py`:

```python
"""Phase 9 connector API tests: last_sync in list, delete terra, token refresh."""
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db.models import AthleteModel, Base, ConnectorCredentialModel
from backend.app.main import app
from backend.app.dependencies import get_db, get_current_athlete_id

SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client_and_athlete():
    db = TestingSessionLocal()
    athlete = AthleteModel(
        id="a1", name="Test", email="test@example.com", hashed_password="hash",
        age=30, sex="M", weight_kg=70.0, height_cm=175.0,
        primary_sport="running", hours_per_week=6.0,
        sports_json='["running"]', goals_json='["run 10k"]',
        available_days_json='["monday"]', equipment_json='[]',
        coaching_mode="full",
    )
    db.add(athlete)
    db.commit()
    db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_athlete_id] = lambda: "a1"
    client = TestClient(app)
    yield client, "a1"
    app.dependency_overrides.clear()


def test_list_connectors_includes_last_sync(client_and_athlete):
    """GET /connectors returns last_sync from extra_json."""
    client, athlete_id = client_and_athlete
    db = TestingSessionLocal()
    last_sync_val = datetime.now(timezone.utc).isoformat()
    cred = ConnectorCredentialModel(
        id=str(uuid.uuid4()), athlete_id=athlete_id, provider="strava",
        extra_json=json.dumps({"last_sync": last_sync_val}),
    )
    db.add(cred)
    db.commit()
    db.close()

    resp = client.get(f"/athletes/{athlete_id}/connectors")
    assert resp.status_code == 200
    connectors = resp.json()["connectors"]
    strava = next(c for c in connectors if c["provider"] == "strava")
    assert strava["last_sync"] == last_sync_val


def test_list_connectors_last_sync_none_when_never_synced(client_and_athlete):
    """last_sync is null when extra_json has no last_sync key."""
    client, athlete_id = client_and_athlete
    db = TestingSessionLocal()
    cred = ConnectorCredentialModel(
        id=str(uuid.uuid4()), athlete_id=athlete_id, provider="hevy",
        extra_json='{"api_key": "test"}',
    )
    db.add(cred)
    db.commit()
    db.close()

    resp = client.get(f"/athletes/{athlete_id}/connectors")
    assert resp.status_code == 200
    connectors = resp.json()["connectors"]
    hevy = next(c for c in connectors if c["provider"] == "hevy")
    assert hevy["last_sync"] is None


def test_delete_terra_connector(client_and_athlete):
    """DELETE /connectors/terra returns 204 and removes the credential."""
    client, athlete_id = client_and_athlete
    db = TestingSessionLocal()
    cred = ConnectorCredentialModel(
        id=str(uuid.uuid4()), athlete_id=athlete_id, provider="terra",
        extra_json='{"terra_user_id": "uid-abc"}',
    )
    db.add(cred)
    db.commit()
    db.close()

    resp = client.delete(f"/athletes/{athlete_id}/connectors/terra")
    assert resp.status_code == 204

    db = TestingSessionLocal()
    assert db.query(ConnectorCredentialModel).filter_by(
        athlete_id=athlete_id, provider="terra"
    ).first() is None
    db.close()


def test_manual_strava_sync_delegates_to_sync_service(client_and_athlete):
    """POST /connectors/strava/sync calls SyncService.sync_strava."""
    client, athlete_id = client_and_athlete

    with patch("backend.app.routes.connectors.SyncService") as MockService:
        MockService.sync_strava.return_value = {"synced": 2, "skipped": 0}
        resp = client.post(f"/athletes/{athlete_id}/connectors/strava/sync")

    assert resp.status_code == 200
    assert resp.json()["synced"] == 2
    MockService.sync_strava.assert_called_once_with(athlete_id, pytest.ANY)


def test_manual_hevy_sync_returns_404_when_not_connected(client_and_athlete):
    """POST /connectors/hevy/sync returns 404 when ConnectorNotFoundError raised."""
    client, athlete_id = client_and_athlete
    from backend.app.services.sync_service import ConnectorNotFoundError

    with patch("backend.app.routes.connectors.SyncService") as MockService:
        MockService.sync_hevy.side_effect = ConnectorNotFoundError("not connected")
        resp = client.post(f"/athletes/{athlete_id}/connectors/hevy/sync")

    assert resp.status_code == 404


def test_manual_terra_sync_delegates_to_sync_service(client_and_athlete):
    """POST /connectors/terra/sync calls SyncService.sync_terra."""
    client, athlete_id = client_and_athlete

    with patch("backend.app.routes.connectors.SyncService") as MockService:
        MockService.sync_terra.return_value = {
            "synced": 1, "hrv_rmssd": 55.0, "sleep_hours": 7.5, "sleep_score": 80
        }
        resp = client.post(f"/athletes/{athlete_id}/connectors/terra/sync")

    assert resp.status_code == 200
    assert resp.json()["hrv_rmssd"] == 55.0
```

- [ ] **Step 2: Run tests to confirm they fail**

```
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/api/test_connectors_phase9.py -v
```
Expected: failures — `last_sync` not in ConnectorStatus, terra not in delete literal, sync endpoints don't use SyncService yet.

- [ ] **Step 3: Update `backend/app/schemas/connector_api.py`**

Replace the entire file:

```python
from pydantic import BaseModel, Field


class ConnectorStatus(BaseModel):
    provider: str           # "strava" | "hevy" | "terra"
    connected: bool
    expires_at: int | None = None   # epoch seconds; None for API key providers
    last_sync: str | None = None    # ISO datetime UTC string; None if never synced


class HevyConnectRequest(BaseModel):
    api_key: str = Field(..., min_length=1)


class ConnectorListResponse(BaseModel):
    connectors: list[ConnectorStatus]
```

- [ ] **Step 4: Update `backend/app/routes/connectors.py` — add imports + refactor 3 sync endpoints + fix delete + fix list**

At the top of the file, add these imports after the existing imports:

```python
from ..services.sync_service import ConnectorNotFoundError, SyncService
```

Replace the `hevy_sync` function (lines ~359–441) with:

```python
@router.post("/{athlete_id}/connectors/hevy/sync")
def hevy_sync(
    athlete_id: str,
    db: DB,
    _: Annotated[str, Depends(_require_own)],
) -> dict:
    """Fetch last 7 days of Hevy workouts → map to lifting sessions → SessionLogModel."""
    try:
        return SyncService.sync_hevy(athlete_id, db)
    except ConnectorNotFoundError:
        raise HTTPException(status_code=404, detail="Hevy connector not connected")
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Failed to sync Hevy") from exc
```

Replace the `terra_sync` function (lines ~447–493) with:

```python
@router.post("/{athlete_id}/connectors/terra/sync")
def terra_sync(
    athlete_id: str,
    db: DB,
    _: Annotated[str, Depends(_require_own)],
) -> dict:
    """Fetch today's Terra health data → store HRV/sleep in connector creds."""
    try:
        return SyncService.sync_terra(athlete_id, db)
    except ConnectorNotFoundError:
        raise HTTPException(status_code=404, detail="Terra connector not connected")
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Failed to sync Terra") from exc
```

Replace the `strava_sync` function (lines ~499–585) with:

```python
@router.post("/{athlete_id}/connectors/strava/sync")
def strava_sync(
    athlete_id: str,
    db: DB,
    _: Annotated[str, Depends(_require_own)],
) -> dict:
    """Fetch last 7 days of Strava activities → map to run/bike/swim sessions → SessionLogModel."""
    try:
        return SyncService.sync_strava(athlete_id, db)
    except ConnectorNotFoundError:
        raise HTTPException(status_code=404, detail="Strava connector not connected")
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Failed to sync Strava") from exc
```

In `delete_connector`, change the `provider` parameter type from `Literal["strava", "hevy"]` to `Literal["strava", "hevy", "terra"]`:

```python
@router.delete("/{athlete_id}/connectors/{provider}", status_code=204)
def delete_connector(athlete_id: str, provider: Literal["strava", "hevy", "terra"], db: DB) -> None:
```

In `list_connectors`, update the `ConnectorStatus` construction to include `last_sync`:

```python
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
            last_sync=json.loads(c.extra_json or "{}").get("last_sync"),
        )
        for c in creds
    ])
```

- [ ] **Step 5: Run new tests**

```
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/api/test_connectors_phase9.py -v
```
Expected: 7 tests PASS.

- [ ] **Step 6: Run full suite**

```
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/ -x -q
```
Expected: all tests pass (existing `test_connectors_sync.py` tests still pass because endpoints have same interface).

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/connector_api.py backend/app/routes/connectors.py tests/backend/api/test_connectors_phase9.py
git commit -m "feat(phase9): connectors endpoints delegate to SyncService + last_sync in schema + delete terra"
```

---

### Task 4: Fix Terra → Recovery Coach pipeline in connector_service.py

**Files:**
- Modify: `backend/app/services/connector_service.py`
- Create: `tests/backend/services/test_connector_service_terra.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/backend/services/test_connector_service_terra.py`:

```python
"""Tests for fetch_connector_data terra_health fix."""
import json
import uuid
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db.models import AthleteModel, Base, ConnectorCredentialModel
from backend.app.services.connector_service import fetch_connector_data

SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def _make_athlete(db):
    a = AthleteModel(
        id="a1", name="Test", age=30, sex="M", weight_kg=70.0, height_cm=175.0,
        primary_sport="running", hours_per_week=6.0,
        sports_json='["running"]', goals_json='["run 10k"]',
        available_days_json='["monday"]', equipment_json='[]',
    )
    db.add(a)
    db.commit()


def test_fetch_connector_data_returns_terra_health_when_data_present(db):
    """terra_health is populated from cached extra_json when HRV or sleep is present."""
    _make_athlete(db)
    cred = ConnectorCredentialModel(
        id=str(uuid.uuid4()), athlete_id="a1", provider="terra",
        extra_json=json.dumps({
            "last_hrv_rmssd": 52.0,
            "last_sleep_hours": 7.5,
            "last_sleep_score": 82,
            "last_steps": 8000,
            "last_sync": "2026-04-11T06:00:00+00:00",
        }),
    )
    db.add(cred)
    db.commit()

    result = fetch_connector_data("a1", db)

    assert "terra_health" in result
    assert len(result["terra_health"]) == 1
    terra = result["terra_health"][0]
    assert terra.hrv_rmssd == 52.0
    assert terra.sleep_duration_hours == 7.5
    assert terra.sleep_score == 82


def test_fetch_connector_data_returns_empty_terra_health_when_no_credential(db):
    """terra_health is [] when no Terra credential exists."""
    _make_athlete(db)
    result = fetch_connector_data("a1", db)
    assert result["terra_health"] == []


def test_fetch_connector_data_returns_empty_terra_health_when_no_values(db):
    """terra_health is [] when Terra connected but no HRV/sleep cached yet."""
    _make_athlete(db)
    cred = ConnectorCredentialModel(
        id=str(uuid.uuid4()), athlete_id="a1", provider="terra",
        extra_json=json.dumps({"terra_user_id": "uid-abc"}),
    )
    db.add(cred)
    db.commit()

    result = fetch_connector_data("a1", db)
    assert result["terra_health"] == []


def test_fetch_connector_data_always_has_all_keys(db):
    """Result always contains strava_activities, hevy_workouts, terra_health."""
    _make_athlete(db)
    result = fetch_connector_data("a1", db)
    assert "strava_activities" in result
    assert "hevy_workouts" in result
    assert "terra_health" in result
```

- [ ] **Step 2: Run tests to confirm they fail**

```
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/services/test_connector_service_terra.py -v
```
Expected: `test_fetch_connector_data_returns_terra_health_when_data_present` FAIL — `terra_health` key missing, `test_fetch_connector_data_always_has_all_keys` FAIL.

- [ ] **Step 3: Update `backend/app/services/connector_service.py`**

Add this import at the top of the file (after `from ..schemas.connector import ConnectorCredential, HevyWorkout, StravaActivity`):

```python
from datetime import date as _date
from ..schemas.connector import ConnectorCredential, HevyWorkout, StravaActivity, TerraHealthData
```

Replace the final `return` statement in `fetch_connector_data`:

```python
    # ── Terra (cached from last sync) ─────────────────────────────────────────
    terra_model = (
        db.query(ConnectorCredentialModel)
        .filter_by(athlete_id=athlete_id, provider="terra")
        .first()
    )
    terra_health: list[TerraHealthData] = []
    if terra_model:
        extra = json.loads(terra_model.extra_json or "{}")
        if extra.get("last_hrv_rmssd") is not None or extra.get("last_sleep_hours") is not None:
            terra_health = [TerraHealthData(
                date=_date.today(),
                hrv_rmssd=extra.get("last_hrv_rmssd"),
                sleep_duration_hours=extra.get("last_sleep_hours"),
                sleep_score=extra.get("last_sleep_score"),
                steps=extra.get("last_steps"),
                active_energy_kcal=None,
            )]

    return {
        "strava_activities": strava_activities,
        "hevy_workouts": hevy_workouts,
        "terra_health": terra_health,
    }
```

- [ ] **Step 4: Run tests to confirm they pass**

```
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/backend/services/test_connector_service_terra.py -v
```
Expected: 4 tests PASS.

- [ ] **Step 5: Run full suite**

```
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/ -x -q
```
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/connector_service.py tests/backend/services/test_connector_service_terra.py
git commit -m "fix(phase9): fetch_connector_data returns terra_health — Recovery Coach pipeline fixed"
```

---

### Task 5: Frontend — api.ts + connectors page

**Files:**
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/app/settings/connectors/page.tsx`

- [ ] **Step 1: Update `frontend/src/lib/api.ts`**

Find the `getConnectors` entry and update the return type to include `last_sync`:

```typescript
  getConnectors: (athleteId: string): Promise<{ connectors: Array<{ provider: string; connected: boolean; expires_at?: number | null; last_sync?: string | null }> }> =>
    request(`/athletes/${athleteId}/connectors`),
```

After the existing `connectTerra` entry, add `connectHevy` and `disconnectConnector`:

```typescript
  connectHevy: (athleteId: string, apiKey: string): Promise<{ provider: string; connected: boolean }> =>
    request(`/athletes/${athleteId}/connectors/hevy`, {
      method: 'POST',
      body: JSON.stringify({ api_key: apiKey }),
    }),

  disconnectConnector: (athleteId: string, provider: 'strava' | 'hevy' | 'terra'): Promise<void> =>
    request(`/athletes/${athleteId}/connectors/${provider}`, { method: 'DELETE' }),
```

- [ ] **Step 2: Verify TypeScript compiles**

```
cd C:\Users\simon\resilio-plus\frontend && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 3: Replace `frontend/src/app/settings/connectors/page.tsx`**

```typescript
'use client'
import { useEffect, useState, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth'
import { api, ApiError } from '@/lib/api'
import { ProtectedRoute } from '@/components/protected-route'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

type ConnectorStatus = {
  provider: string
  connected: boolean
  expires_at?: number | null
  last_sync?: string | null
}
type SyncResult = { message: string; ok: boolean }

function formatLastSync(iso: string | null | undefined): string {
  if (!iso) return 'Never'
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'Just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

export default function ConnectorsPage() {
  const { athleteId, logout } = useAuth()
  const router = useRouter()
  const [connectors, setConnectors] = useState<ConnectorStatus[]>([])
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState<string | null>(null)
  const [results, setResults] = useState<Record<string, SyncResult>>({})
  const [hevyKey, setHevyKey] = useState('')
  const [terraUserId, setTerraUserId] = useState('')
  const gpxRef = useRef<HTMLInputElement>(null)
  const fitRef = useRef<HTMLInputElement>(null)

  const loadConnectors = () => {
    if (!athleteId) return
    api.getConnectors(athleteId)
      .then(data => setConnectors(data.connectors))
      .catch(err => {
        if (err instanceof ApiError && err.status === 401) { logout(); router.replace('/login') }
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => { loadConnectors() }, [athleteId]) // eslint-disable-line react-hooks/exhaustive-deps

  const isConnected = (provider: string) =>
    connectors.some(c => c.provider === provider && c.connected)

  const lastSync = (provider: string) =>
    connectors.find(c => c.provider === provider)?.last_sync

  const syncConnector = async (provider: string, action: () => Promise<any>) => {
    if (!athleteId) return
    setSyncing(provider)
    try {
      const result = await action()
      setResults(r => ({
        ...r,
        [provider]: { ok: true, message: `Synced ${result.synced ?? 1} item(s)` },
      }))
      loadConnectors()
    } catch {
      setResults(r => ({ ...r, [provider]: { ok: false, message: 'Sync failed' } }))
    } finally {
      setSyncing(null)
    }
  }

  const disconnectProvider = async (provider: 'strava' | 'hevy' | 'terra') => {
    if (!athleteId) return
    setSyncing(provider)
    try {
      await api.disconnectConnector(athleteId, provider)
      loadConnectors()
      setResults(r => ({ ...r, [provider]: { ok: true, message: 'Disconnected' } }))
    } catch {
      setResults(r => ({ ...r, [provider]: { ok: false, message: 'Disconnect failed' } }))
    } finally {
      setSyncing(null)
    }
  }

  const handleFileUpload = async (
    provider: 'gpx' | 'fit',
    file: File | null | undefined
  ) => {
    if (!file || !athleteId) return
    setSyncing(provider)
    try {
      const result = provider === 'gpx'
        ? await api.uploadGpx(athleteId, file)
        : await api.uploadFit(athleteId, file)
      setResults(r => ({
        ...r,
        [provider]: {
          ok: result.imported,
          message: result.imported
            ? `Imported → session ${result.session_id}`
            : `Not imported: ${(result as any).reason}`,
        },
      }))
    } catch {
      setResults(r => ({ ...r, [provider]: { ok: false, message: 'Upload failed' } }))
    } finally {
      setSyncing(null)
    }
  }

  return (
    <ProtectedRoute>
      <div className="space-y-4">
        <h1 className="text-2xl font-bold">Connected Apps</h1>
        {loading && <p className="animate-pulse text-muted-foreground">Loading…</p>}

        {/* Strava */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">Strava</CardTitle>
              <span className={`text-xs px-2 py-0.5 rounded-full ${isConnected('strava') ? 'bg-emerald-500/20 text-emerald-400' : 'bg-muted text-muted-foreground'}`}>
                {isConnected('strava') ? 'Connected' : 'Not connected'}
              </span>
            </div>
            <p className="text-xs text-muted-foreground">Last synced: {formatLastSync(lastSync('strava'))}</p>
          </CardHeader>
          <CardContent className="flex gap-2 flex-wrap">
            {!isConnected('strava') && athleteId && (
              <Button variant="outline" size="sm" onClick={() =>
                api.stravaAuthorize(athleteId).then(d => window.location.href = d.auth_url)
              }>Connect</Button>
            )}
            {isConnected('strava') && (
              <>
                <Button variant="outline" size="sm" disabled={syncing === 'strava'}
                  onClick={() => syncConnector('strava', () => api.stravaSync(athleteId!))}>
                  {syncing === 'strava' ? 'Syncing…' : 'Sync now'}
                </Button>
                <Button variant="ghost" size="sm" disabled={syncing === 'strava'}
                  onClick={() => disconnectProvider('strava')}>
                  Disconnect
                </Button>
              </>
            )}
            {results.strava && (
              <span className={`text-xs self-center ${results.strava.ok ? 'text-emerald-400' : 'text-destructive'}`}>
                {results.strava.message}
              </span>
            )}
          </CardContent>
        </Card>

        {/* Hevy */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">Hevy</CardTitle>
              <span className={`text-xs px-2 py-0.5 rounded-full ${isConnected('hevy') ? 'bg-purple-500/20 text-purple-400' : 'bg-muted text-muted-foreground'}`}>
                {isConnected('hevy') ? 'Connected' : 'Not connected'}
              </span>
            </div>
            <p className="text-xs text-muted-foreground">Last synced: {formatLastSync(lastSync('hevy'))}</p>
          </CardHeader>
          <CardContent className="flex gap-2 flex-wrap items-center">
            {!isConnected('hevy') && (
              <>
                <Input
                  placeholder="Hevy API key"
                  value={hevyKey}
                  onChange={e => setHevyKey(e.target.value)}
                  className="h-8 text-xs w-48"
                />
                <Button variant="outline" size="sm"
                  disabled={!hevyKey.trim() || syncing === 'hevy'}
                  onClick={async () => {
                    if (!athleteId) return
                    setSyncing('hevy')
                    try {
                      await api.connectHevy(athleteId, hevyKey.trim())
                      setHevyKey('')
                      loadConnectors()
                      setResults(r => ({ ...r, hevy: { ok: true, message: 'Connected' } }))
                    } catch {
                      setResults(r => ({ ...r, hevy: { ok: false, message: 'Connection failed' } }))
                    } finally {
                      setSyncing(null)
                    }
                  }}>
                  {syncing === 'hevy' ? 'Connecting…' : 'Connect'}
                </Button>
              </>
            )}
            {isConnected('hevy') && (
              <>
                <Button variant="outline" size="sm" disabled={syncing === 'hevy'}
                  onClick={() => syncConnector('hevy', () => api.hevySync(athleteId!))}>
                  {syncing === 'hevy' ? 'Syncing…' : 'Sync now'}
                </Button>
                <Button variant="ghost" size="sm" disabled={syncing === 'hevy'}
                  onClick={() => disconnectProvider('hevy')}>
                  Disconnect
                </Button>
              </>
            )}
            {results.hevy && (
              <span className={`text-xs self-center ${results.hevy.ok ? 'text-emerald-400' : 'text-destructive'}`}>
                {results.hevy.message}
              </span>
            )}
          </CardContent>
        </Card>

        {/* Terra */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">Terra (HRV / Sleep)</CardTitle>
              <span className={`text-xs px-2 py-0.5 rounded-full ${isConnected('terra') ? 'bg-blue-500/20 text-blue-400' : 'bg-muted text-muted-foreground'}`}>
                {isConnected('terra') ? 'Connected' : 'Not connected'}
              </span>
            </div>
            <p className="text-xs text-muted-foreground">Last synced: {formatLastSync(lastSync('terra'))}</p>
          </CardHeader>
          <CardContent className="flex gap-2 flex-wrap items-center">
            {!isConnected('terra') && (
              <>
                <Input
                  placeholder="Terra User ID"
                  value={terraUserId}
                  onChange={e => setTerraUserId(e.target.value)}
                  className="h-8 text-xs w-48"
                />
                <Button variant="outline" size="sm"
                  disabled={!terraUserId.trim() || syncing === 'terra'}
                  onClick={async () => {
                    if (!athleteId) return
                    setSyncing('terra')
                    try {
                      await api.connectTerra(athleteId, terraUserId.trim())
                      setTerraUserId('')
                      loadConnectors()
                      setResults(r => ({ ...r, terra: { ok: true, message: 'Connected' } }))
                    } catch {
                      setResults(r => ({ ...r, terra: { ok: false, message: 'Connection failed' } }))
                    } finally {
                      setSyncing(null)
                    }
                  }}>
                  {syncing === 'terra' ? 'Connecting…' : 'Connect'}
                </Button>
              </>
            )}
            {isConnected('terra') && (
              <>
                <Button variant="outline" size="sm" disabled={syncing === 'terra'}
                  onClick={() => syncConnector('terra', () => api.terraSync(athleteId!))}>
                  {syncing === 'terra' ? 'Syncing…' : 'Sync now'}
                </Button>
                <Button variant="ghost" size="sm" disabled={syncing === 'terra'}
                  onClick={() => disconnectProvider('terra')}>
                  Disconnect
                </Button>
              </>
            )}
            {results.terra && (
              <span className={`text-xs self-center ${results.terra.ok ? 'text-emerald-400' : 'text-destructive'}`}>
                {results.terra.message}
              </span>
            )}
          </CardContent>
        </Card>

        {/* Apple Health */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Apple Health</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground mb-2">
              Upload HRV and sleep data from Apple Health JSON export.
            </p>
            <p className="text-xs text-muted-foreground">
              Use the Apple Health export → share as JSON → paste HRV/sleep values below.
            </p>
          </CardContent>
        </Card>

        {/* GPX / FIT */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Import Activity File</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div>
              <p className="text-xs text-muted-foreground mb-2">GPX file (GPS track)</p>
              <input ref={gpxRef} type="file" accept=".gpx" className="hidden"
                onChange={e => handleFileUpload('gpx', e.target.files?.[0])} />
              <Button variant="outline" size="sm" disabled={syncing === 'gpx'}
                onClick={() => gpxRef.current?.click()}>
                {syncing === 'gpx' ? 'Importing…' : 'Upload GPX'}
              </Button>
              {results.gpx && (
                <span className={`text-xs ml-2 ${results.gpx.ok ? 'text-emerald-400' : 'text-destructive'}`}>
                  {results.gpx.message}
                </span>
              )}
            </div>
            <div>
              <p className="text-xs text-muted-foreground mb-2">FIT file (Garmin / Wahoo)</p>
              <input ref={fitRef} type="file" accept=".fit" className="hidden"
                onChange={e => handleFileUpload('fit', e.target.files?.[0])} />
              <Button variant="outline" size="sm" disabled={syncing === 'fit'}
                onClick={() => fitRef.current?.click()}>
                {syncing === 'fit' ? 'Importing…' : 'Upload FIT'}
              </Button>
              {results.fit && (
                <span className={`text-xs ml-2 ${results.fit.ok ? 'text-emerald-400' : 'text-destructive'}`}>
                  {results.fit.message}
                </span>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </ProtectedRoute>
  )
}
```

- [ ] **Step 4: Verify TypeScript compiles**

```
cd C:\Users\simon\resilio-plus\frontend && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 5: Run full backend suite one last time**

```
C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe tests/ -q
```
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/lib/api.ts frontend/src/app/settings/connectors/page.tsx
git commit -m "feat(phase9): connectors UI — Connect forms Hevy/Terra + last_sync display + disconnect buttons"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task |
|---|---|
| SyncService centralisé | Task 1 |
| sync_strava persiste SessionLogModel | Task 1 |
| sync_hevy persiste SessionLogModel | Task 1 |
| sync_terra stocke HRV/sleep dans extra_json | Task 1 |
| Token refresh Strava persisté | Task 1 (sync_strava) |
| last_sync mis à jour après chaque sync | Task 1 (_set_last_sync) |
| Scheduler délègue à SyncService | Task 2 |
| Terra job dans scheduler | Task 2 |
| ConnectorStatus.last_sync | Task 3 |
| delete_connector accepte terra | Task 3 |
| Endpoints manuels délèguent à SyncService | Task 3 |
| fetch_connector_data retourne terra_health | Task 4 |
| Recovery Coach reçoit vraies données HRV | Task 4 (fix indirect) |
| api.ts last_sync type + connectHevy + disconnectConnector | Task 5 |
| Connect form Hevy (API key) | Task 5 |
| Connect form Terra (user ID) | Task 5 |
| Disconnect buttons Hevy + Terra | Task 5 |
| Last synced display dans chaque carte | Task 5 |
