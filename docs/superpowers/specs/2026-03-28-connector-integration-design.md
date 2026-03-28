# Connector Integration — Phase 1 Design

## Overview

Add Strava (OAuth2) and Hevy (API key) connector support to the Resilio Plus backend. Credentials are stored per-athlete in the existing `ConnectorCredentialModel`. When a plan is generated, live data is fetched on-demand and injected into `AgentContext`. No authentication or background sync in this phase.

## Scope

**In scope:**
- Strava OAuth2 full flow: authorize redirect + callback + token refresh
- Hevy API key storage and fetch
- Connector CRUD endpoints (list, delete)
- `connector_service.py` — on-demand data fetching for plan generation
- Inject fetched data into `AgentContext` in `POST /athletes/{athlete_id}/plan`

**Out of scope:**
- FatSecret, Terra connectors
- Background / scheduled sync
- Authentication / JWT
- Webhook support

## Architecture

**Option C — Connector service module:**

```
backend/app/
├── routes/
│   └── connectors.py        # Credential CRUD + OAuth2 endpoints
├── schemas/
│   └── connector_api.py     # API request/response schemas (ConnectorStatus etc.)
└── services/
    ├── __init__.py
    └── connector_service.py # fetch_connector_data() — all HTTP calls isolated here
```

`services/connector_service.py` is the only place that makes external HTTP calls. `routes/plans.py` calls `fetch_connector_data()` before building `AgentContext`. All other code stays unchanged.

Note: the existing `backend/app/schemas/connector.py` holds `StravaActivity`, `HevyWorkout` etc. (agent-facing domain schemas with custom field names that do NOT match raw API responses). The new `connector_api.py` holds API-layer schemas only, avoiding naming collision.

## Section 1: Connector Credential Management

### Endpoints

All endpoints follow the `/athletes/{athlete_id}/connectors/...` pattern, consistent with existing routes.

| Method | Path | Status codes | Description |
|--------|------|--------------|-------------|
| `POST` | `/athletes/{athlete_id}/connectors/strava/authorize` | 200, 404 | Returns Strava OAuth2 redirect URL |
| `GET` | `/athletes/{athlete_id}/connectors/strava/callback` | 200, 404, 502 | Exchanges code for tokens, stores credential |
| `POST` | `/athletes/{athlete_id}/connectors/hevy` | 201, 404 | Store Hevy API key |
| `GET` | `/athletes/{athlete_id}/connectors` | 200, 404 | List connected providers (tokens not exposed) |
| `DELETE` | `/athletes/{athlete_id}/connectors/{provider}` | 204, 404 | Revoke / remove credential |

### Router Setup (following existing `athletes.py` / `plans.py` pattern)

```python
# routes/connectors.py
from fastapi import APIRouter
connectors_router = APIRouter(prefix="/athletes", tags=["connectors"])

@connectors_router.post("/{athlete_id}/connectors/strava/authorize")
def strava_authorize(athlete_id: str, db: Session = Depends(get_db)):
    ...
```

In `main.py` — `app.include_router(connectors_router)` with no additional prefix (the router declares its own `prefix="/athletes"`):
```python
from app.routes.connectors import connectors_router
app.include_router(connectors_router)
```

### Schemas (`backend/app/schemas/connector_api.py`)

```python
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

### Strava OAuth2 Flow

**Step 1 — `POST /athletes/{athlete_id}/connectors/strava/authorize`:**
- Validates athlete exists (404 if not)
- Returns `{"auth_url": "https://www.strava.com/oauth/authorize?client_id=...&redirect_uri=...&scope=activity:read_all&state={athlete_id}&response_type=code"}`
- Read env vars with fallback: `os.getenv("STRAVA_CLIENT_ID", "")`, `os.getenv("STRAVA_REDIRECT_URI", "")`
- `state` value in the URL is the `athlete_id` path parameter

**Step 2 — `GET /athletes/{athlete_id}/connectors/strava/callback?code=xxx&state=athlete_id`:**
- Use `athlete_id` from the URL path as the authoritative athlete ID (ignore `state` query param — included for Strava's anti-CSRF requirement but not validated server-side in Phase 1)
- Validate athlete exists (404 if not)
- Exchange `code`: call `POST https://www.strava.com/oauth/token` with fields:
  `client_id` (`os.getenv("STRAVA_CLIENT_ID", "")`), `client_secret` (`os.getenv("STRAVA_CLIENT_SECRET", "")`), `code`, `redirect_uri` (`os.getenv("STRAVA_REDIRECT_URI", "")`), `grant_type=authorization_code`
  - If `requests.post` raises `requests.RequestException` or returns non-200: raise `HTTPException(status_code=502, detail="Strava token exchange failed")`
- Parse response: `token_data = response.json()` → extract `access_token`, `refresh_token`, `expires_at` (int)
- Upsert credential (see Upsert Pattern below, `provider="strava"`)
- Returns `{"connected": True}` with status 200

**Hevy — `POST /athletes/{athlete_id}/connectors/hevy`:**
- Body: `{"api_key": "xxx"}`
- Upsert: `access_token=api_key`, `refresh_token=None`, `expires_at=None`, `extra_json="{}"`
- Returns 201 with `ConnectorStatus(provider="hevy", connected=True, expires_at=None)`

**List — `GET /athletes/{athlete_id}/connectors`:**
- Validate athlete exists (404 if not)
- Query `ConnectorCredentialModel` by `athlete_id`
- Return `ConnectorListResponse` — never include `access_token` or `refresh_token` in response

**Delete — `DELETE /athletes/{athlete_id}/connectors/{provider}`:**
- Query row by `(athlete_id, provider)`; 404 if not found
- `db.delete(row); db.commit()`
- Return 204

### Upsert Pattern (used for both Strava and Hevy)

```python
existing = db.query(ConnectorCredentialModel).filter_by(
    athlete_id=str(athlete_id), provider=provider
).first()
if existing:
    existing.access_token = new_token
    existing.refresh_token = new_refresh  # None for Hevy
    existing.expires_at = new_expires_at  # None for Hevy
    db.commit()
else:
    db.add(ConnectorCredentialModel(
        id=str(uuid.uuid4()),
        athlete_id=str(athlete_id),
        provider=provider,
        access_token=new_token,
        refresh_token=new_refresh,
        expires_at=new_expires_at,
        extra_json="{}",
    ))
    db.commit()
```

## Section 2: Connector Service — Data Fetching

### `backend/app/services/connector_service.py`

```python
def fetch_connector_data(athlete_id: str, db: Session) -> dict:
    """Fetch live data from all connected providers for the athlete.

    Always returns a dict with both keys present:
        {"strava_activities": list[StravaActivity], "hevy_workouts": list[HevyWorkout]}

    If a provider has no credential or its fetch fails, the corresponding list is [].
    Never raises — errors are logged as warnings.
    """
```

Both keys are **unconditionally present** in the returned dict, even when a provider errors or has no credential.

### Strava Fetch

1. Load credential: `db.query(ConnectorCredentialModel).filter_by(athlete_id=athlete_id, provider="strava").first()`; if not found → `strava_activities = []`, skip to return
2. Token refresh: `expires_at` is stored as `int` (epoch seconds). If `int(credential.expires_at) < int(time.time()) + 60`: call `POST https://www.strava.com/oauth/token` with `grant_type=refresh_token`, `client_id` (`os.getenv("STRAVA_CLIENT_ID", "")`), `client_secret` (`os.getenv("STRAVA_CLIENT_SECRET", "")`), `refresh_token`; on success update `credential.access_token`, `credential.refresh_token`, `credential.expires_at` and `db.commit()`; on `requests.RequestException` or non-200 log warning and return `[]` for Strava
3. Fetch last 7 days: `after = int(time.time()) - 7 * 86400`; `GET https://www.strava.com/api/v3/athlete/activities?after={after}&per_page=50` with `Authorization: Bearer {credential.access_token}`
4. Map each activity dict to `StravaActivity` — **manual mapping required** (Strava API field names differ from schema fields):
   ```python
   from datetime import datetime
   def _map_strava_activity(a: dict) -> StravaActivity:
       return StravaActivity(
           id=f"strava_{a['id']}",
           name=a["name"],
           sport_type=a.get("sport_type", a.get("type", "Unknown")),
           date=datetime.fromisoformat(a["start_date"].replace("Z", "+00:00")).date(),
           duration_seconds=a["elapsed_time"],
           distance_meters=a.get("distance"),
           elevation_gain_meters=a.get("total_elevation_gain"),
           average_hr=a.get("average_heartrate"),
           max_hr=a.get("max_heartrate"),
           perceived_exertion=None,
           laps=[],
       )
   ```
5. On any `requests.RequestException` or non-200 response → `logging.warning(...)`, return `[]`

### Hevy Fetch

1. Load credential by `(athlete_id, provider="hevy")`; if not found → `hevy_workouts = []`, skip to return
2. `GET https://api.hevyapp.com/v1/workouts?page=1&pageSize=10` with header `api-key: {credential.access_token}`
3. Response envelope: `{"page": 1, "page_count": N, "workouts": [...]}` — iterate `response.json()["workouts"]`
4. Map each workout to `HevyWorkout` — manual mapping required:
   ```python
   def _map_hevy_workout(w: dict) -> HevyWorkout:
       start = datetime.fromisoformat(w["start_time"])
       end = datetime.fromisoformat(w["end_time"])
       return HevyWorkout(
           id=w["id"],
           title=w["title"],
           date=start.date(),
           duration_seconds=int((end - start).total_seconds()),
           exercises=[
               HevyExercise(
                   name=ex["title"],
                   sets=[
                       HevySet(
                           reps=s.get("reps"),
                           weight_kg=s.get("weight_kg"),
                           rpe=s.get("rpe"),
                           set_type=s.get("indicator", "normal"),
                           # set_type is required (no default); "normal" fallback covers missing "indicator"
                       )
                       for s in ex.get("sets", [])
                   ],
               )
               for ex in w.get("exercises", [])
           ],
       )
   ```
5. On any error → `logging.warning(...)`, return `[]`

### Implementation Notes

- Fully synchronous — uses `requests` library (consistent with sync FastAPI app)
- All env vars via `os.getenv(key, "")` — never raise `KeyError`
- No retry logic in Phase 1

## Section 3: Plan Route Integration & Testing

### `routes/plans.py` change

Variable names follow the existing file (`athlete` for the deserialized profile, `athlete_id` for the path param):

```python
from app.services.connector_service import fetch_connector_data

# Inside generate_plan(), after: athlete = athlete_model_to_response(athlete_model)
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

### Mocking External HTTP Calls in Tests

Use `unittest.mock.patch` at the import site (where the name is used, not where it is defined).

All mock targets use full dotted module paths:
- Routes mock target: `app.routes.connectors.requests.post` / `app.routes.connectors.requests.get`
- Service mock target: `app.services.connector_service.requests.post` / `app.services.connector_service.requests.get`

```python
from unittest.mock import patch, MagicMock, ANY

# Single patch — route-level token exchange:
with patch("app.routes.connectors.requests.post") as mock_post:
    mock_post.return_value = MagicMock(
        status_code=200,
        json=lambda: {"access_token": "tok", "refresh_token": "ref", "expires_at": 9999999999}
    )
    response = client.get(f"/athletes/{athlete_id}/connectors/strava/callback?code=abc")

# Stacked patches — service refresh + activities fetch (use @patch decorators or nested with):
with patch("app.services.connector_service.requests.post") as mock_refresh, \
     patch("app.services.connector_service.requests.get") as mock_get:
    mock_refresh.return_value = MagicMock(
        status_code=200,
        json=lambda: {"access_token": "new_tok", "refresh_token": "new_ref", "expires_at": 9999999999}
    )
    mock_get.return_value = MagicMock(status_code=200, json=lambda: [])
    result = fetch_connector_data(athlete_id, db_session)

# Mocking fetch_connector_data in plan route tests:
with patch("app.routes.plans.fetch_connector_data") as mock_fetch:
    mock_fetch.return_value = {"strava_activities": [], "hevy_workouts": []}
    response = client.post(...)
    mock_fetch.assert_called_once_with(str(athlete_id), ANY)
```

Note: in stacked `with patch(...)` blocks, inner patches bind to variables left-to-right; with `@patch` decorators the order is reversed (bottom decorator = first argument). Use `with` blocks to avoid confusion.

### Test Fixtures

**`tests/backend/api/conftest.py` — add `client_and_db` fixture** (alongside existing `client` fixture):

```python
@pytest.fixture()
def client_and_db():
    """Yields (TestClient, Session) sharing the same StaticPool engine.
    Use this for tests that need to inspect DB state after HTTP calls.
    StaticPool ensures all connections share the same in-memory data.
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

**`tests/backend/services/conftest.py` — new file** (in `tests/backend/services/`):

```python
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from app.db.database import Base
from app.db import models  # noqa: F401 — registers ORM models

@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def set_pragma(conn, _):
        conn.cursor().execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    Session = sessionmaker(engine)
    with Session() as session:
        yield session
    Base.metadata.drop_all(engine)
```

### Test Files

**`tests/backend/api/test_connectors.py`** (~14 tests):

Define the `strava_env` fixture at the **top of `test_connectors.py`** (not in `conftest.py` — scope is intentionally limited to this file):

```python
@pytest.fixture(autouse=True)
def strava_env(monkeypatch):
    monkeypatch.setenv("STRAVA_CLIENT_ID", "test_client_id")
    monkeypatch.setenv("STRAVA_CLIENT_SECRET", "test_secret")
    monkeypatch.setenv("STRAVA_REDIRECT_URI", "http://localhost/callback")
```

Tests using `client` fixture (HTTP assertions only):
- `test_strava_authorize_returns_auth_url` — assert `"strava.com"` in `response.json()["auth_url"]`
- `test_strava_authorize_unknown_athlete_returns_404`
- `test_strava_callback_strava_error_returns_502` — patch `"app.routes.connectors.requests.post"` to return `status_code=400`, assert 502
- `test_strava_callback_unknown_athlete_returns_404`
- `test_hevy_connect_stores_api_key` — POST `{"api_key": "xxx"}`, assert 201 and `provider="hevy"` in response
- `test_hevy_connect_unknown_athlete_returns_404`
- `test_list_connectors_empty` — `{"connectors": []}`
- `test_list_connectors_after_connect` — after hevy connect, `connected: True`
- `test_list_connectors_does_not_expose_tokens` — assert no `access_token` key in any item
- `test_delete_connector_returns_204`
- `test_delete_connector_not_found_returns_404`

Tests using `client_and_db` fixture (HTTP call + DB verification):
- `test_strava_callback_stores_credential` — patch `"app.routes.connectors.requests.post"`, call callback, query `ConnectorCredentialModel` via the yielded `session` to assert row exists
- `test_strava_callback_upsert_updates_existing` — call callback twice (both patched), assert only one row in DB
- `test_hevy_connect_upsert_updates_existing` — POST twice with different keys, assert only one row, second key is stored

**`tests/backend/services/test_connector_service.py`** (~5 tests using `db_session` fixture):

- `test_fetch_no_credentials_returns_empty_lists` — assert `result == {"strava_activities": [], "hevy_workouts": []}`
- `test_fetch_strava_activities_maps_to_schema` — insert Strava credential (non-expired), patch `"app.services.connector_service.requests.get"` with a mock Strava activities list response, assert `result["strava_activities"]` is a non-empty `list[StravaActivity]`
- `test_fetch_hevy_workouts_maps_to_schema` — insert Hevy credential, patch `"app.services.connector_service.requests.get"` with mock Hevy response
- `test_strava_token_refresh_on_expiry` — insert credential with `expires_at=int(time.time()) - 10`; patch both `"app.services.connector_service.requests.post"` (refresh) and `"app.services.connector_service.requests.get"` (activities) using stacked `with patch(...)` blocks (see mock example above); assert `credential.access_token` updated in DB
- `test_fetch_strava_network_error_returns_empty` — insert credential, patch `"app.services.connector_service.requests.get"` to raise `requests.RequestException`, assert `result["strava_activities"] == []` and no exception propagates

**`tests/backend/api/test_plans.py`** — add one test to the existing file (uses existing `client` fixture):

- `test_plan_route_calls_connector_service` — patch `"app.routes.plans.fetch_connector_data"` to return `{"strava_activities": [], "hevy_workouts": []}`, call `POST /athletes/{id}/plan`, assert `mock_fetch.assert_called_once_with(ANY, ANY)`

## File Summary

| File | Action |
|------|--------|
| `backend/app/routes/connectors.py` | Create |
| `backend/app/schemas/connector_api.py` | Create |
| `backend/app/services/__init__.py` | Create |
| `backend/app/services/connector_service.py` | Create |
| `backend/app/main.py` | Modify — `app.include_router(connectors_router)` (router declares `prefix="/athletes"`) |
| `backend/app/routes/plans.py` | Modify — import and call `fetch_connector_data` |
| `tests/backend/api/conftest.py` | Modify — add `client_and_db` fixture |
| `tests/backend/api/test_connectors.py` | Create (`tests/backend/api/__init__.py` already exists) |
| `tests/backend/services/__init__.py` | Create (new directory) |
| `tests/backend/services/conftest.py` | Create — `db_session` fixture |
| `tests/backend/services/test_connector_service.py` | Create |
| `tests/backend/api/test_plans.py` | Modify — add `test_plan_route_calls_connector_service` |

## Dependencies

`requests` — already present in the project (check `requirements.txt`; add if missing).

Environment variables (all via `os.getenv(key, "")` — never raise `KeyError`):
- `STRAVA_CLIENT_ID`
- `STRAVA_CLIENT_SECRET`
- `STRAVA_REDIRECT_URI`

In tests: set via `monkeypatch.setenv(...)` in the `strava_env` fixture defined in `test_connectors.py`; empty string default is acceptable for tests that don't exercise Strava URL construction.

## Error Handling

- **404**: athlete not found on all connector endpoints
- **404**: credential not found on DELETE
- **502**: Strava token exchange returned non-200 or raised — `HTTPException(status_code=502, detail="Strava token exchange failed")`
- **Fetch errors in connector_service**: logged as warnings, return `[]` for that provider — plan generation continues
- **422**: FastAPI/Pydantic handles malformed request bodies automatically
