# Connector Integration — Phase 1 Design

## Overview

Add Strava (OAuth2) and Hevy (API key) connector support to the Resilio Plus backend. Credentials are stored per-athlete in the existing `ConnectorCredentialModel`. When a plan is generated, live data is fetched on-demand and injected into `AgentContext`. No authentication or background sync in this phase.

## Scope

**In scope:**
- Strava OAuth2 full flow: authorize redirect + callback + token refresh
- Hevy API key storage and fetch
- Connector CRUD endpoints (list, delete)
- `connector_service.py` — on-demand data fetching for plan generation
- Inject fetched data into `AgentContext` in `POST /athletes/{id}/plan`

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

Note: the existing `backend/app/schemas/connector.py` holds `StravaActivity`, `HevyWorkout` etc. (agent-facing domain schemas). The new `connector_api.py` holds API-layer schemas only, avoiding naming collision.

## Section 1: Connector Credential Management

### Endpoints

| Method | Path | Status codes | Description |
|--------|------|--------------|-------------|
| `POST` | `/athletes/{id}/connectors/strava/authorize` | 200, 404 | Returns Strava OAuth2 redirect URL |
| `GET` | `/athletes/{id}/connectors/strava/callback` | 200, 404 | Exchanges code for tokens, stores credential |
| `POST` | `/athletes/{id}/connectors/hevy` | 201, 404 | Store Hevy API key |
| `GET` | `/athletes/{id}/connectors` | 200, 404 | List connected providers (tokens not exposed) |
| `DELETE` | `/athletes/{id}/connectors/{provider}` | 204, 404 | Revoke / remove credential |

### Schemas (`backend/app/schemas/connector_api.py`)

```python
from pydantic import BaseModel

class ConnectorStatus(BaseModel):
    provider: str           # "strava" | "hevy"
    connected: bool
    expires_at: int | None  # epoch seconds; None for API key providers

class HevyConnectRequest(BaseModel):
    api_key: str

class ConnectorListResponse(BaseModel):
    connectors: list[ConnectorStatus]
```

### Strava OAuth2 Flow

**Step 1 — `POST /athletes/{id}/connectors/strava/authorize`:**
- Validates athlete exists (404 if not)
- Returns `{"auth_url": "https://www.strava.com/oauth/authorize?client_id=...&redirect_uri=...&scope=activity:read_all&state={athlete_id}&response_type=code"}`
- `STRAVA_CLIENT_ID` and `STRAVA_REDIRECT_URI` read from environment variables

**Step 2 — `GET /athletes/{id}/connectors/strava/callback?code=xxx&state=athlete_id`:**
- Exchanges `code` via `POST https://www.strava.com/oauth/token` with `grant_type=authorization_code`
- Stores `access_token`, `refresh_token`, `expires_at` in `ConnectorCredentialModel`
- On re-auth: upsert (update existing row if provider already connected)
- Returns `{"connected": true}`

**Hevy — `POST /athletes/{id}/connectors/hevy`:**
- Body: `{"api_key": "xxx"}`
- Stored as `access_token` in `ConnectorCredentialModel`; `refresh_token=None`, `expires_at=None`
- Returns 201 with `ConnectorStatus`

**List — `GET /athletes/{id}/connectors`:**
- Query `ConnectorCredentialModel` by `athlete_id`
- Return `ConnectorListResponse` — never expose raw tokens

**Delete — `DELETE /athletes/{id}/connectors/{provider}`:**
- Delete matching row; 404 if not found

## Section 2: Connector Service — Data Fetching

### `backend/app/services/connector_service.py`

```python
def fetch_connector_data(athlete_id: str, db: Session) -> dict:
    """Fetch live data from all connected providers for the athlete.
    Returns {"strava_activities": [...], "hevy_workouts": [...]}
    On any fetch error, returns empty list for that provider.
    """
```

**Strava fetch:**
1. Load credential from DB; if not found → return `[]`
2. Token refresh: if `expires_at < time.time() + 60`, call `POST https://www.strava.com/oauth/token` with `grant_type=refresh_token`; update `access_token`, `refresh_token`, `expires_at` in DB
3. Fetch last 7 days: `GET https://www.strava.com/api/v3/athlete/activities?after={epoch}&per_page=50` with `Authorization: Bearer {token}`
4. Map each activity dict → `StravaActivity` schema object
5. On any `requests` exception or non-200 response → log warning, return `[]`

**Hevy fetch:**
1. Load credential; if not found → return `[]`
2. `GET https://api.hevyapp.com/v1/workouts?page=1&pageSize=10` with `api-key: {access_token}` header
3. Map response → `HevyWorkout` schema objects
4. On error → log warning, return `[]`

**Implementation notes:**
- Fully synchronous — uses `requests` library (consistent with sync FastAPI app)
- `STRAVA_CLIENT_ID`, `STRAVA_CLIENT_SECRET` read from `os.environ`
- No retry logic in Phase 1

## Section 3: Plan Route Integration & Testing

### `routes/plans.py` change

```python
from app.services.connector_service import fetch_connector_data

# Inside POST /athletes/{id}/plan, after loading athlete:
connector_data = fetch_connector_data(str(id), db)

context = AgentContext(
    athlete=athlete_profile,
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

### Test Files

**`tests/backend/api/test_connectors.py`** (~10 tests):
- `test_strava_authorize_returns_auth_url` — assert response contains `auth_url` with `strava.com`
- `test_strava_authorize_unknown_athlete_returns_404`
- `test_strava_callback_stores_credential` — mock `requests.post` token exchange, assert `ConnectorCredentialModel` row created
- `test_hevy_connect_stores_api_key` — POST `{"api_key": "xxx"}`, assert credential stored, returns 201
- `test_hevy_connect_unknown_athlete_returns_404`
- `test_list_connectors_empty` — no credentials → `{"connectors": []}`
- `test_list_connectors_after_connect` — after hevy connect → `connected: True`
- `test_list_connectors_does_not_expose_tokens` — assert no `access_token` field in response
- `test_delete_connector_returns_204`
- `test_delete_connector_not_found_returns_404`

**`tests/backend/services/test_connector_service.py`** (~6 tests):
- `test_fetch_no_credentials_returns_empty_lists`
- `test_fetch_strava_activities_maps_to_schema` — mock `requests.get`, assert `StravaActivity` objects returned
- `test_fetch_hevy_workouts_maps_to_schema` — mock `requests.get`
- `test_strava_token_refresh_on_expiry` — expired token → `requests.post` refresh called → new token stored in DB
- `test_fetch_strava_network_error_returns_empty` — `requests.get` raises `requests.RequestException` → returns `[]`
- `test_plan_route_uses_connector_data` — mock `fetch_connector_data`, assert `AgentContext` receives the lists

## File Summary

| File | Action |
|------|--------|
| `backend/app/routes/connectors.py` | Create |
| `backend/app/schemas/connector_api.py` | Create |
| `backend/app/services/__init__.py` | Create |
| `backend/app/services/connector_service.py` | Create |
| `backend/app/main.py` | Modify — mount connectors router |
| `backend/app/routes/plans.py` | Modify — call `fetch_connector_data` |
| `tests/backend/api/test_connectors.py` | Create |
| `tests/backend/services/__init__.py` | Create |
| `tests/backend/services/test_connector_service.py` | Create |

## Dependencies

`requests` — already present in the project (check `requirements.txt`; add if missing).

Environment variables required (can be empty strings for tests):
- `STRAVA_CLIENT_ID`
- `STRAVA_CLIENT_SECRET`
- `STRAVA_REDIRECT_URI`

## Error Handling

- **404**: athlete not found on all connector endpoints
- **404**: credential not found on DELETE
- **Fetch errors**: logged as warnings, return empty list — plan generation continues
- **422**: FastAPI/Pydantic handles malformed request bodies automatically
