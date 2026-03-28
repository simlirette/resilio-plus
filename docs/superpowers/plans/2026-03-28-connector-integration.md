# Connector Integration — Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Strava (OAuth2) and Hevy (API key) connector endpoints, a connector service that fetches live data using existing connector classes, and wire it into the plan generation route.

**Architecture:** A new `routes/connectors.py` handles credential CRUD and Strava OAuth flow using the existing `StravaConnector`/`HevyConnector` classes from `backend/app/connectors/`. A new `services/connector_service.py` wraps those connectors to produce `{"strava_activities": [...], "hevy_workouts": [...]}` for `POST /athletes/{id}/plan`. The plan route calls `fetch_connector_data()` before building `AgentContext`.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Pydantic v2, httpx (already used by connectors), respx (already used for tests), SQLite.

**Key codebase facts (read before touching any file):**
- `backend/app/connectors/strava.py` — `StravaConnector(credential, client_id, client_secret)` with `get_auth_url()`, `exchange_code(code)`, `fetch_activities(since, until)`. Uses `httpx` internally.
- `backend/app/connectors/hevy.py` — `HevyConnector(credential, client_id, client_secret)` with `fetch_workouts(since, until)`. API key stored in `credential.extra["api_key"]`.
- `backend/app/connectors/base.py` — `ConnectorError`, `ConnectorAuthError`, `ConnectorAPIError` exceptions.
- `backend/app/schemas/connector.py` — `ConnectorCredential(id: UUID, athlete_id: UUID, provider: str, access_token, refresh_token, expires_at: int|None, extra: dict)`.
- `backend/app/db/models.py` — `ConnectorCredentialModel` with `(id, athlete_id, provider, access_token, refresh_token, expires_at: int|None, extra_json: str)`. Unique on `(athlete_id, provider)`.
- `tests/backend/connectors/` — existing connector tests use `respx` for httpx mocking.
- `tests/backend/api/conftest.py` — has `_make_test_engine()` and `client` fixture (TestClient + StaticPool). Has `athlete_payload()` helper.
- `backend/app/routes/plans.py` — `generate_plan(athlete_id, req, db)` uses variable `athlete` for the deserialized profile.

---

## Task 1: API schemas

**Files:**
- Create: `backend/app/schemas/connector_api.py`
- Test: `tests/backend/schemas/test_connector_api.py`

> `tests/backend/schemas/__init__.py` already exists — no need to create it.

- [ ] **Step 1: Write the failing test**

```python
# tests/backend/schemas/test_connector_api.py
from app.schemas.connector_api import ConnectorStatus, HevyConnectRequest, ConnectorListResponse

def test_connector_status_connected():
    s = ConnectorStatus(provider="strava", connected=True, expires_at=9999999999)
    assert s.provider == "strava"
    assert s.connected is True
    assert s.expires_at == 9999999999

def test_connector_status_api_key_provider_has_no_expiry():
    s = ConnectorStatus(provider="hevy", connected=True, expires_at=None)
    assert s.expires_at is None

def test_hevy_connect_request():
    r = HevyConnectRequest(api_key="abc123")
    assert r.api_key == "abc123"

def test_connector_list_response_empty():
    r = ConnectorListResponse(connectors=[])
    assert r.connectors == []

def test_connector_list_response_with_items():
    r = ConnectorListResponse(connectors=[
        ConnectorStatus(provider="strava", connected=True, expires_at=9999999999),
        ConnectorStatus(provider="hevy", connected=True, expires_at=None),
    ])
    assert len(r.connectors) == 2
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /c/Users/simon/resilio-plus && pytest tests/backend/schemas/test_connector_api.py -v
```
Expected: `ImportError: cannot import name 'ConnectorStatus'`

- [ ] **Step 3: Create the schemas file**

```python
# backend/app/schemas/connector_api.py
from pydantic import BaseModel


class ConnectorStatus(BaseModel):
    provider: str           # "strava" | "hevy"
    connected: bool
    expires_at: int | None  # epoch seconds (int); None for API key providers


class HevyConnectRequest(BaseModel):
    api_key: str


class ConnectorListResponse(BaseModel):
    connectors: list[ConnectorStatus]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/backend/schemas/test_connector_api.py -v
```
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/connector_api.py tests/backend/schemas/test_connector_api.py
git commit -m "feat: add connector API schemas (ConnectorStatus, HevyConnectRequest)"
```

---

## Task 2: Connector service

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/connector_service.py`
- Create: `tests/backend/services/__init__.py`
- Create: `tests/backend/services/conftest.py`
- Create: `tests/backend/services/test_connector_service.py`

### Background: how the connector classes work

`StravaConnector` and `HevyConnector` extend `BaseConnector` from `backend/app/connectors/base.py`. They take a `ConnectorCredential` (from `backend/app/schemas/connector.py`) at construction. `ConnectorCredential` uses `UUID` for both `id` and `athlete_id`, while `ConnectorCredentialModel` stores them as plain strings — conversion is required.

For Hevy, the API key is stored in `credential.extra["api_key"]` (not `access_token`). When storing in `ConnectorCredentialModel`, put it in `extra_json=json.dumps({"api_key": "xxx"})`.

Token refresh happens automatically inside `StravaConnector.fetch_activities()` (via `get_valid_token()` → `_do_refresh_token()`). After fetch, if `connector.credential.access_token != original_access_token`, we persist the refreshed token back to DB.

- [ ] **Step 1: Create `tests/backend/services/` directory files**

```python
# tests/backend/services/__init__.py
# (empty)
```

```python
# tests/backend/services/conftest.py
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db import models  # noqa: F401 — registers ORM models with Base


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )

    @event.listens_for(engine, "connect")
    def set_pragma(conn, _):
        conn.cursor().execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    Session = sessionmaker(engine)
    with Session() as session:
        yield session
    Base.metadata.drop_all(engine)
```

- [ ] **Step 2: Write the failing tests**

```python
# tests/backend/services/test_connector_service.py
import json
import time
import uuid

import httpx
import pytest
import respx

from app.db.models import AthleteModel, ConnectorCredentialModel
from app.services.connector_service import fetch_connector_data


# ─── helpers ───────────────────────────────────────────────────────────────────

def _make_athlete(db_session):
    athlete_id = str(uuid.uuid4())
    db_session.add(AthleteModel(
        id=athlete_id, name="Alice", age=30, sex="F",
        weight_kg=60.0, height_cm=168.0, primary_sport="running",
        hours_per_week=10.0,
        sports_json='["running"]', goals_json='["run fast"]',
        available_days_json='[0,2,4]', equipment_json='[]',
    ))
    db_session.commit()
    return athlete_id


def _add_strava_cred(db_session, athlete_id, expires_at=9999999999):
    db_session.add(ConnectorCredentialModel(
        id=str(uuid.uuid4()), athlete_id=athlete_id, provider="strava",
        access_token="test_access", refresh_token="test_refresh",
        expires_at=expires_at, extra_json="{}",
    ))
    db_session.commit()


def _add_hevy_cred(db_session, athlete_id):
    db_session.add(ConnectorCredentialModel(
        id=str(uuid.uuid4()), athlete_id=athlete_id, provider="hevy",
        access_token=None, refresh_token=None, expires_at=None,
        extra_json=json.dumps({"api_key": "hevy_test_key"}),
    ))
    db_session.commit()


# ─── tests ─────────────────────────────────────────────────────────────────────

def test_fetch_no_credentials_returns_empty_lists(db_session):
    athlete_id = _make_athlete(db_session)
    result = fetch_connector_data(athlete_id, db_session)
    assert result == {"strava_activities": [], "hevy_workouts": []}


@respx.mock
def test_fetch_strava_activities_maps_to_schema(db_session):
    athlete_id = _make_athlete(db_session)
    _add_strava_cred(db_session, athlete_id)

    respx.get("https://www.strava.com/api/v3/athlete/activities").mock(
        return_value=httpx.Response(200, json=[{
            "id": 111,
            "name": "Morning Run",
            "sport_type": "Run",
            "start_date_local": "2026-03-25T07:00:00Z",
            "elapsed_time": 3600,
            "distance": 10000.0,
            "total_elevation_gain": 50.0,
            "average_heartrate": 145.0,
            "max_heartrate": 170.0,
        }])
    )

    result = fetch_connector_data(athlete_id, db_session)
    assert len(result["strava_activities"]) == 1
    act = result["strava_activities"][0]
    assert act.id == "strava_111"
    assert act.name == "Morning Run"
    assert act.duration_seconds == 3600


@respx.mock
def test_fetch_hevy_workouts_maps_to_schema(db_session):
    athlete_id = _make_athlete(db_session)
    _add_hevy_cred(db_session, athlete_id)

    respx.get("https://api.hevyapp.com/v1/workouts").mock(
        return_value=httpx.Response(200, json={
            "page": 1, "page_count": 1,
            "workouts": [{
                "id": "w1",
                "title": "Push Day",
                "start_time": "2026-03-25T08:00:00Z",
                "end_time": "2026-03-25T09:00:00Z",
                "exercises": [],
            }]
        })
    )

    result = fetch_connector_data(athlete_id, db_session)
    assert len(result["hevy_workouts"]) == 1
    w = result["hevy_workouts"][0]
    assert w.id == "w1"
    assert w.title == "Push Day"
    assert w.duration_seconds == 3600


@respx.mock
def test_strava_token_refresh_on_expiry_persisted_to_db(db_session):
    athlete_id = _make_athlete(db_session)
    expired_at = int(time.time()) - 10
    _add_strava_cred(db_session, athlete_id, expires_at=expired_at)

    respx.post("https://www.strava.com/oauth/token").mock(
        return_value=httpx.Response(200, json={
            "access_token": "new_access", "refresh_token": "new_refresh",
            "expires_at": 9999999999,
        })
    )
    respx.get("https://www.strava.com/api/v3/athlete/activities").mock(
        return_value=httpx.Response(200, json=[])
    )

    fetch_connector_data(athlete_id, db_session)

    db_session.expire_all()
    cred = db_session.query(ConnectorCredentialModel).filter_by(
        athlete_id=athlete_id, provider="strava"
    ).first()
    assert cred.access_token == "new_access"
    assert cred.expires_at == 9999999999


def test_fetch_strava_network_error_returns_empty(db_session):
    """A ConnectorError during fetch returns [] without raising."""
    athlete_id = _make_athlete(db_session)
    _add_strava_cred(db_session, athlete_id)

    with respx.mock:
        respx.get("https://www.strava.com/api/v3/athlete/activities").mock(
            side_effect=httpx.ConnectError("timeout")
        )
        result = fetch_connector_data(athlete_id, db_session)

    assert result["strava_activities"] == []
    assert result["hevy_workouts"] == []  # Hevy had no cred, also empty
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
pytest tests/backend/services/test_connector_service.py -v
```
Expected: `ImportError: cannot import name 'fetch_connector_data'`

- [ ] **Step 4: Create service files**

```python
# backend/app/services/__init__.py
# (empty)
```

```python
# backend/app/services/connector_service.py
import json
import logging
import os
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.connectors.base import ConnectorError
from app.connectors.hevy import HevyConnector
from app.connectors.strava import StravaConnector
from app.db.models import ConnectorCredentialModel
from app.schemas.connector import ConnectorCredential, HevyWorkout, StravaActivity

logger = logging.getLogger(__name__)

_WEEK_SECONDS = 7 * 24 * 3600


def _model_to_credential(m: ConnectorCredentialModel) -> ConnectorCredential:
    return ConnectorCredential(
        id=UUID(m.id),
        athlete_id=UUID(m.athlete_id),
        provider=m.provider,
        access_token=m.access_token,
        refresh_token=m.refresh_token,
        expires_at=m.expires_at,
        extra=json.loads(m.extra_json),
    )


def _persist_token_update(
    m: ConnectorCredentialModel, cred: ConnectorCredential, db: Session
) -> None:
    m.access_token = cred.access_token
    m.refresh_token = cred.refresh_token
    m.expires_at = cred.expires_at
    db.commit()


def fetch_connector_data(athlete_id: str, db: Session) -> dict:
    """Fetch live data from all connected providers for the athlete.

    Always returns both keys even on error:
        {"strava_activities": list[StravaActivity], "hevy_workouts": list[HevyWorkout]}
    """
    now = datetime.now(timezone.utc)
    since = datetime.fromtimestamp(now.timestamp() - _WEEK_SECONDS, tz=timezone.utc)

    strava_activities: list[StravaActivity] = []
    hevy_workouts: list[HevyWorkout] = []

    # ── Strava ──────────────────────────────────────────────────────────────
    strava_model = (
        db.query(ConnectorCredentialModel)
        .filter_by(athlete_id=athlete_id, provider="strava")
        .first()
    )
    if strava_model:
        original_token = strava_model.access_token
        cred = _model_to_credential(strava_model)
        client_id = os.getenv("STRAVA_CLIENT_ID", "")
        client_secret = os.getenv("STRAVA_CLIENT_SECRET", "")
        try:
            with StravaConnector(cred, client_id=client_id, client_secret=client_secret) as connector:
                strava_activities = connector.fetch_activities(since=since, until=now)
                if connector.credential.access_token != original_token:
                    _persist_token_update(strava_model, connector.credential, db)
        except Exception:
            logger.warning("Strava fetch failed for athlete %s", athlete_id)

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
            logger.warning("Hevy fetch failed for athlete %s", athlete_id)

    return {"strava_activities": strava_activities, "hevy_workouts": hevy_workouts}
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/backend/services/test_connector_service.py -v
```
Expected: 5 passed

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/ tests/backend/services/
git commit -m "feat: add connector service with Strava and Hevy data fetching"
```

---

## Task 3: Connector credential routes

**Files:**
- Create: `backend/app/routes/connectors.py`
- Modify: `tests/backend/api/conftest.py` — add `client_and_db` fixture
- Create: `tests/backend/api/test_connectors.py`

### Background: how the route uses connectors

`StravaConnector.get_auth_url()` returns a URL *without* `state`. The route appends `&state={athlete_id}`.

`StravaConnector.exchange_code(code)` calls `httpx.Client.post()` with `raise_for_status()` — if Strava returns non-2xx, it raises `httpx.HTTPStatusError`. Catch it and return 502.

For Hevy, the API key goes into `extra_json=json.dumps({"api_key": key})`. `HevyConnector._api_key()` reads `credential.extra.get("api_key")`.

**Upsert pattern** (used for both providers): query existing row by `(athlete_id, provider)`, update in-place if found, add new row if not.

- [ ] **Step 1: Add `client_and_db` fixture to conftest**

Open `tests/backend/api/conftest.py`. It currently ends at line 59. Add after the `client` fixture:

```python
@pytest.fixture()
def client_and_db():
    """Yields (TestClient, Session) sharing the same StaticPool engine.
    Use for tests that inspect DB state after HTTP calls.
    StaticPool ensures all connections see the same in-memory data.
    """
    engine = _make_test_engine()
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(engine)

    def override_get_db():
        with TestSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        with TestSession() as session:
            yield c, session
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
```

- [ ] **Step 2: Write the failing tests**

```python
# tests/backend/api/test_connectors.py
import json
import uuid

import httpx
import pytest
import respx

from app.db.models import AthleteModel, ConnectorCredentialModel


# ─── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def strava_env(monkeypatch):
    """Set Strava env vars for all tests in this file."""
    monkeypatch.setenv("STRAVA_CLIENT_ID", "test_client_id")
    monkeypatch.setenv("STRAVA_CLIENT_SECRET", "test_secret")
    monkeypatch.setenv("STRAVA_REDIRECT_URI", "http://localhost/callback")


def _create_athlete(client):
    resp = client.post("/athletes", json={
        "name": "Alice", "age": 30, "sex": "F",
        "weight_kg": 60.0, "height_cm": 168.0,
        "sports": ["running"], "primary_sport": "running",
        "goals": ["run fast"], "available_days": [0, 2, 4],
        "hours_per_week": 10.0,
    })
    assert resp.status_code == 201
    return resp.json()["id"]


# ─── authorize ─────────────────────────────────────────────────────────────────

def test_strava_authorize_returns_auth_url(client):
    athlete_id = _create_athlete(client)
    resp = client.post(f"/athletes/{athlete_id}/connectors/strava/authorize")
    assert resp.status_code == 200
    data = resp.json()
    assert "auth_url" in data
    assert "strava.com" in data["auth_url"]
    assert "test_client_id" in data["auth_url"]
    assert str(athlete_id) in data["auth_url"]  # state param


def test_strava_authorize_unknown_athlete_returns_404(client):
    resp = client.post(f"/athletes/{uuid.uuid4()}/connectors/strava/authorize")
    assert resp.status_code == 404


# ─── callback ──────────────────────────────────────────────────────────────────

@respx.mock
def test_strava_callback_strava_error_returns_502(client):
    athlete_id = _create_athlete(client)
    respx.post("https://www.strava.com/oauth/token").mock(
        return_value=httpx.Response(400, json={"message": "Bad Request"})
    )
    resp = client.get(f"/athletes/{athlete_id}/connectors/strava/callback?code=bad_code")
    assert resp.status_code == 502


def test_strava_callback_unknown_athlete_returns_404(client):
    resp = client.get(
        f"/athletes/{uuid.uuid4()}/connectors/strava/callback?code=abc"
    )
    assert resp.status_code == 404


@respx.mock
def test_strava_callback_stores_credential(client_and_db):
    client, session = client_and_db
    athlete_id = _create_athlete(client)

    respx.post("https://www.strava.com/oauth/token").mock(
        return_value=httpx.Response(200, json={
            "access_token": "tok", "refresh_token": "ref", "expires_at": 9999999999,
        })
    )
    resp = client.get(f"/athletes/{athlete_id}/connectors/strava/callback?code=abc")
    assert resp.status_code == 200
    assert resp.json()["connected"] is True

    session.expire_all()
    cred = session.query(ConnectorCredentialModel).filter_by(
        athlete_id=athlete_id, provider="strava"
    ).first()
    assert cred is not None
    assert cred.access_token == "tok"


@respx.mock
def test_strava_callback_upsert_updates_existing(client_and_db):
    client, session = client_and_db
    athlete_id = _create_athlete(client)

    for token in ("tok_v1", "tok_v2"):
        respx.post("https://www.strava.com/oauth/token").mock(
            return_value=httpx.Response(200, json={
                "access_token": token, "refresh_token": "ref", "expires_at": 9999999999,
            })
        )
        client.get(f"/athletes/{athlete_id}/connectors/strava/callback?code=abc")

    session.expire_all()
    creds = session.query(ConnectorCredentialModel).filter_by(
        athlete_id=athlete_id, provider="strava"
    ).all()
    assert len(creds) == 1
    assert creds[0].access_token == "tok_v2"


# ─── hevy ──────────────────────────────────────────────────────────────────────

def test_hevy_connect_stores_api_key(client_and_db):
    client, session = client_and_db
    athlete_id = _create_athlete(client)

    resp = client.post(
        f"/athletes/{athlete_id}/connectors/hevy",
        json={"api_key": "hevy_key_123"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["provider"] == "hevy"
    assert data["connected"] is True

    session.expire_all()
    cred = session.query(ConnectorCredentialModel).filter_by(
        athlete_id=athlete_id, provider="hevy"
    ).first()
    assert cred is not None
    assert json.loads(cred.extra_json)["api_key"] == "hevy_key_123"


def test_hevy_connect_upsert_updates_existing(client_and_db):
    client, session = client_and_db
    athlete_id = _create_athlete(client)

    client.post(f"/athletes/{athlete_id}/connectors/hevy", json={"api_key": "key_v1"})
    client.post(f"/athletes/{athlete_id}/connectors/hevy", json={"api_key": "key_v2"})

    session.expire_all()
    creds = session.query(ConnectorCredentialModel).filter_by(
        athlete_id=athlete_id, provider="hevy"
    ).all()
    assert len(creds) == 1
    assert json.loads(creds[0].extra_json)["api_key"] == "key_v2"


def test_hevy_connect_unknown_athlete_returns_404(client):
    resp = client.post(
        f"/athletes/{uuid.uuid4()}/connectors/hevy",
        json={"api_key": "key"},
    )
    assert resp.status_code == 404


# ─── list ──────────────────────────────────────────────────────────────────────

def test_list_connectors_empty(client):
    athlete_id = _create_athlete(client)
    resp = client.get(f"/athletes/{athlete_id}/connectors")
    assert resp.status_code == 200
    assert resp.json() == {"connectors": []}


def test_list_connectors_after_hevy_connect(client):
    athlete_id = _create_athlete(client)
    client.post(f"/athletes/{athlete_id}/connectors/hevy", json={"api_key": "k"})
    resp = client.get(f"/athletes/{athlete_id}/connectors")
    assert resp.status_code == 200
    connectors = resp.json()["connectors"]
    assert len(connectors) == 1
    assert connectors[0]["provider"] == "hevy"
    assert connectors[0]["connected"] is True


def test_list_connectors_does_not_expose_tokens(client):
    athlete_id = _create_athlete(client)
    client.post(f"/athletes/{athlete_id}/connectors/hevy", json={"api_key": "k"})
    resp = client.get(f"/athletes/{athlete_id}/connectors")
    raw = resp.text
    assert "api_key" not in raw
    assert "access_token" not in raw


def test_list_connectors_unknown_athlete_returns_404(client):
    resp = client.get(f"/athletes/{uuid.uuid4()}/connectors")
    assert resp.status_code == 404


# ─── delete ────────────────────────────────────────────────────────────────────

def test_delete_connector_returns_204(client):
    athlete_id = _create_athlete(client)
    client.post(f"/athletes/{athlete_id}/connectors/hevy", json={"api_key": "k"})
    resp = client.delete(f"/athletes/{athlete_id}/connectors/hevy")
    assert resp.status_code == 204


def test_delete_connector_not_found_returns_404(client):
    athlete_id = _create_athlete(client)
    resp = client.delete(f"/athletes/{athlete_id}/connectors/strava")
    assert resp.status_code == 404
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
pytest tests/backend/api/test_connectors.py -v
```
Expected: `ImportError` or 404 errors (route doesn't exist yet)

- [ ] **Step 4: Create the connectors route**

```python
# backend/app/routes/connectors.py
import json
import os
import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Annotated

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
def strava_callback(athlete_id: str, code: str, db: DB, state: str | None = None) -> dict:
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
    cred = (
        db.query(ConnectorCredentialModel)
        .filter_by(athlete_id=athlete_id, provider=provider)
        .first()
    )
    if cred is None:
        raise HTTPException(status_code=404)
    db.delete(cred)
    db.commit()
```

- [ ] **Step 5: Run tests to verify they fail (route not mounted yet)**

```bash
pytest tests/backend/api/test_connectors.py -v
```
Expected: All 404s (router not registered in `main.py` yet — that's Task 4)

> **Note:** Some tests may fail for different reasons (404 vs 422 vs error). That's expected — just confirm the route file imports correctly.

- [ ] **Step 6: Commit**

```bash
git add backend/app/routes/connectors.py tests/backend/api/conftest.py tests/backend/api/test_connectors.py
git commit -m "feat: add connector routes (Strava OAuth2 + Hevy API key CRUD)"
```

---

## Task 4: Wire up — main.py, plans.py, plan route test

**Files:**
- Modify: `backend/app/main.py` — mount connectors router
- Modify: `backend/app/routes/plans.py` — call `fetch_connector_data`
- Modify: `tests/backend/api/test_plans.py` — add one test

- [ ] **Step 1: Write the failing plan route test**

Open `tests/backend/api/test_plans.py`. Add at the end of the file:

```python
from unittest.mock import ANY, patch


def test_plan_route_calls_connector_service(client):
    # Create athlete
    resp = client.post("/athletes", json={
        "name": "Bob", "age": 28, "sex": "M",
        "weight_kg": 75.0, "height_cm": 180.0,
        "sports": ["running", "lifting"], "primary_sport": "running",
        "goals": ["finish triathlon"], "available_days": [0, 1, 2, 3, 4, 5, 6],
        "hours_per_week": 12.0,
    })
    athlete_id = resp.json()["id"]

    with patch("app.routes.plans.fetch_connector_data") as mock_fetch:
        mock_fetch.return_value = {"strava_activities": [], "hevy_workouts": []}
        resp = client.post(
            f"/athletes/{athlete_id}/plan",
            json={"start_date": "2026-04-07", "end_date": "2026-04-13"},
        )
        assert resp.status_code == 201
        mock_fetch.assert_called_once_with(str(athlete_id), ANY)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/backend/api/test_plans.py::test_plan_route_calls_connector_service -v
```
Expected: FAIL — `fetch_connector_data` is not imported in `plans.py` yet, so mock has no effect and test fails on assertion

- [ ] **Step 3: Mount connectors router in main.py**

Edit `backend/app/main.py`. Add after the existing `from app.routes.plans import router as plans_router`:

```python
from app.routes.connectors import router as connectors_router
```

And after `app.include_router(plans_router)`:

```python
app.include_router(connectors_router)
```

Final `main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.athletes import router as athletes_router
from app.routes.connectors import router as connectors_router
from app.routes.plans import router as plans_router

app = FastAPI(title="Resilio Plus API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(athletes_router)
app.include_router(plans_router)
app.include_router(connectors_router)
```

- [ ] **Step 4: Update plans.py to call fetch_connector_data**

Edit `backend/app/routes/plans.py`. Add import (after existing imports):

```python
from app.services.connector_service import fetch_connector_data
```

Replace the `context = AgentContext(...)` block in `generate_plan()`:

**Before** (lines 49–59):
```python
    context = AgentContext(
        athlete=athlete,
        date_range=(req.start_date, req.end_date),
        phase=phase,
        strava_activities=[],
        hevy_workouts=[],
        terra_health=[],
        fatsecret_days=[],
        week_number=1,
        weeks_remaining=weeks_remaining,
    )
```

**After**:
```python
    connector_data = fetch_connector_data(athlete_id, db)

    context = AgentContext(
        athlete=athlete,
        date_range=(req.start_date, req.end_date),
        phase=phase,
        strava_activities=connector_data["strava_activities"],
        hevy_workouts=connector_data["hevy_workouts"],
        terra_health=[],
        fatsecret_days=[],
        week_number=1,
        weeks_remaining=weeks_remaining,
    )
```

- [ ] **Step 5: Run connector route tests (now mounted)**

```bash
pytest tests/backend/api/test_connectors.py -v
```
Expected: All 17 tests pass

- [ ] **Step 6: Run the new plan test**

```bash
pytest tests/backend/api/test_plans.py::test_plan_route_calls_connector_service -v
```
Expected: PASS

- [ ] **Step 7: Run full test suite**

```bash
pytest tests/backend/ -v --tb=short 2>&1 | tail -20
```
Expected: All existing tests still pass + new tests pass. Total should be ~1130+ passing.

- [ ] **Step 8: Commit**

```bash
git add backend/app/main.py backend/app/routes/plans.py tests/backend/api/test_plans.py
git commit -m "feat: wire connector service into plan route and mount connectors router"
```

---

## Final verification

- [ ] **Run full test suite one last time**

```bash
cd /c/Users/simon/resilio-plus && pytest tests/backend/ --tb=short 2>&1 | tail -5
```
Expected: All new tests pass, no regressions in existing 1112 tests.
