# Strava OAuth 2.0 + Activity Sync Design — Resilio+

**Date:** 2026-04-14  
**Status:** Approved  
**Scope:** Complete Strava OAuth 2.0 flow + incremental activity sync → `strava_activities` table, encrypted token storage, rate limit handling, AthleteState mapping.

---

## Context

Existing `routes/connectors.py` has a partial Strava OAuth implementation:
- Routes at `/{athlete_id}/connectors/strava/authorize|callback` — athlete_id exposed in URL (security anti-pattern)
- Tokens stored in plaintext in `ConnectorCredentialModel.access_token`/`refresh_token`
- `services/sync_service.py` sync uses fixed 7-day window, no rate limit handling, no persistence
- No incremental sync (`last_sync_at`), no activity table

This design replaces that with a production-ready integration module.

---

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Old Strava routes | Replace entirely | Old routes expose `athlete_id` in URL; duplicate OAuth flows = confusion |
| Token storage | New `_enc` columns, drop plaintext | No ambiguity about encryption state; one migration pass |
| Encryption | `cryptography.fernet` | Symmetric, simple, standard for secrets at rest |
| Activity persistence | New `strava_activities` table | CTL/ATL/TSB + ACWR + strain calculations need historical data |
| Sync window | Incremental from `last_sync_at`; NULL → 90-day bootstrap | Efficient; avoids refetching known data |
| Rate limits | `ConnectorRateLimitError` → HTTP 429 + `Retry-After` header | BaseConnector already handles 5xx via tenacity; 429 propagated to client |
| Auth pattern | `get_current_athlete_id` from JWT | Consistent with V3-P; no `athlete_id` path param |
| Callback auth | No JWT (browser redirect) | Strava redirects browser — no Authorization header available; use `state` anti-CSRF |
| STRAVA_ENCRYPTION_KEY | Required — missing → `ConnectorAuthError` | No silent fail on encryption |

---

## File Structure

```
backend/app/integrations/strava/
  __init__.py
  oauth_service.py      — connect() → auth_url, callback(code, state) → save creds,
                          get_valid_credential() → auto-refresh + decrypt
  sync_service.py       — sync(athlete_id, db) → SyncSummary; fetch + upsert activities
  activity_mapper.py    — raw Strava dict → StravaActivityModel

backend/app/schemas/strava.py          — StravaActivity + SyncSummary Pydantic models
backend/app/db/models.py               — add StravaActivityModel; patch ConnectorCredentialModel
alembic/versions/0008_strava_v2.py     — add _enc columns + last_sync_at, drop plaintext,
                                          create strava_activities

backend/app/routes/strava.py           — POST /integrations/strava/connect
                                          GET  /integrations/strava/callback
                                          POST /integrations/strava/sync
backend/app/main.py                    — add strava_router

# Modified:
backend/app/connectors/strava.py       — read _enc columns (decrypt before constructing credential)
backend/app/routes/connectors.py       — remove old Strava OAuth routes (3 functions)
backend/app/services/sync_service.py   — remove sync_strava() (replaced)

tests/backend/integrations/strava/
  __init__.py
  test_oauth_service.py
  test_sync_service.py
  test_activity_mapper.py
tests/backend/api/test_strava.py
# Updated: remove Strava OAuth assertions from affected test files
```

---

## Schemas

```python
# backend/app/schemas/strava.py

class StravaActivity(BaseModel):
    id: str                          # "strava_{strava_id}"
    athlete_id: str
    strava_id: int
    sport_type: str                  # "running" | "biking" | "swimming"
    name: str
    started_at: datetime
    duration_s: int
    distance_m: float | None = None
    elevation_m: float | None = None
    avg_hr: int | None = None
    max_hr: int | None = None
    avg_watts: float | None = None
    perceived_exertion: float | None = None

class SyncSummary(BaseModel):
    synced: int
    skipped: int                     # activities with unrecognized sport_type (not in SPORT_MAP)
    sport_breakdown: dict[str, int]  # {"running": N, "biking": N, "swimming": N}
```

---

## Database Model

```python
# ConnectorCredentialModel — patched (migration 0008)
# DROPPED: access_token, refresh_token
# ADDED:
access_token_enc  = Column(Text, nullable=True)
refresh_token_enc = Column(Text, nullable=True)
last_sync_at      = Column(DateTime(timezone=True), nullable=True)  # NULL = never synced

class StravaActivityModel(Base):
    __tablename__ = "strava_activities"

    id            = Column(String, primary_key=True)       # "strava_{strava_id}"
    athlete_id    = Column(String, ForeignKey("athletes.id"), nullable=False)
    strava_id     = Column(BigInteger, nullable=False, unique=True)
    sport_type    = Column(String, nullable=False)
    name          = Column(String, nullable=False)
    started_at    = Column(DateTime(timezone=True), nullable=False)
    duration_s    = Column(Integer, nullable=False)
    distance_m    = Column(Float, nullable=True)
    elevation_m   = Column(Float, nullable=True)
    avg_hr        = Column(Integer, nullable=True)
    max_hr        = Column(Integer, nullable=True)
    avg_watts     = Column(Float, nullable=True)
    perceived_exertion = Column(Float, nullable=True)
    raw_json      = Column(Text, nullable=False, default="{}")
```

---

## OAuth Flow

### POST /integrations/strava/connect
```
1. get_current_athlete_id() → athlete_id (JWT)
2. Verify athlete exists → 404 if not
3. state = secrets.token_urlsafe(16)
4. Store state in ConnectorCredentialModel.extra_json (upsert)
5. Build auth_url via StravaConnector.get_auth_url() + &state=<state>
   scope: activity:read_all,profile:read_all
6. Return {"auth_url": str}
```

### GET /integrations/strava/callback?code=&state=
```
1. Lookup ConnectorCredentialModel WHERE extra_json contains state → 400 if not found
   (no JWT — browser redirect, no Authorization header)
2. StravaConnector.exchange_code(code) → ConnectorCredential
3. encrypt_token(access_token, STRAVA_ENCRYPTION_KEY) → access_token_enc
   encrypt_token(refresh_token, STRAVA_ENCRYPTION_KEY) → refresh_token_enc
4. Upsert ConnectorCredentialModel:
     access_token_enc, refresh_token_enc, expires_at, last_sync_at=NULL
     Clear state from extra_json
5. Return {"connected": True}
```

### get_valid_credential(athlete_id, db) → ConnectorCredential
```
1. Load ConnectorCredentialModel for athlete + provider="strava"
2. decrypt_token(access_token_enc) → plain access token
3. If expires_at < now + 300s:
     StravaConnector._do_refresh_token() → new tokens
     encrypt + upsert _enc columns
4. Return ConnectorCredential (plaintext in memory only — never logged)
```

---

## Sync Flow

### POST /integrations/strava/sync
```
1. get_current_athlete_id() → athlete_id (JWT)
2. oauth_service.get_valid_credential(athlete_id, db) → credential
3. Read last_sync_at from ConnectorCredentialModel
   If NULL → since = now - 90 days (initial bootstrap)
4. StravaConnector.fetch_activities(since=last_sync_at) → list[dict]
5. For each activity:
     activity_mapper.to_model(raw, athlete_id) → StravaActivityModel
     db.merge() — upsert by strava_id (idempotent)
     Increment sport_breakdown[sport_type]
6. Update last_sync_at = now
7. Return SyncSummary{synced, skipped, sport_breakdown}
```

### Rate limit handling
```python
# sync_service.py
except ConnectorRateLimitError as e:
    raise HTTPException(
        status_code=429,
        headers={"Retry-After": str(e.retry_after)},
        detail="Strava rate limit reached",
    )
# ConnectorAPIError (5xx) → tenacity 3× exponential backoff (BaseConnector)
```

---

## activity_mapper.py

```python
SPORT_MAP = {
    "Run": "running", "TrailRun": "running", "VirtualRun": "running",
    "Ride": "biking", "VirtualRide": "biking", "EBikeRide": "biking",
    "Swim": "swimming",
}

def to_model(raw: dict, athlete_id: str) -> StravaActivityModel:
    sport = SPORT_MAP.get(raw["sport_type"], raw["sport_type"].lower())
    return StravaActivityModel(
        id=f"strava_{raw['id']}",
        athlete_id=athlete_id,
        strava_id=raw["id"],
        sport_type=sport,
        name=raw["name"],
        started_at=datetime.fromisoformat(raw["start_date"]),
        duration_s=raw["elapsed_time"],
        distance_m=raw.get("distance"),
        elevation_m=raw.get("total_elevation_gain"),
        avg_hr=raw.get("average_heartrate"),
        max_hr=raw.get("max_heartrate"),
        avg_watts=raw.get("average_watts"),
        perceived_exertion=raw.get("perceived_exertion"),
        raw_json=json.dumps(raw),
    )
```

---

## Endpoints

```
POST /integrations/strava/connect
  Authorization: Bearer <token>
  → 200: {"auth_url": str}
  → 401: unauthenticated
  → 404: athlete not found

GET /integrations/strava/callback?code=<str>&state=<str>
  Authorization: none (browser redirect)
  → 200: {"connected": True}
  → 400: invalid or missing state
  → 502: Strava token exchange failed

POST /integrations/strava/sync
  Authorization: Bearer <token>
  → 200: SyncSummary
  → 401: unauthenticated
  → 429: rate limited (Retry-After header)
  → 502: Strava API error
```

---

## Environment Variables

```bash
# Added to .env.example
STRAVA_ENCRYPTION_KEY=<fernet-base64-key>  # Generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Existing (unchanged):
STRAVA_CLIENT_ID=your_client_id
STRAVA_CLIENT_SECRET=your_client_secret
STRAVA_REDIRECT_URI=http://localhost:8000/integrations/strava/callback
```

Missing `STRAVA_ENCRYPTION_KEY` → `ConnectorAuthError` raised at connect time (no silent fail).

---

## Testing Strategy

```
test_oauth_service.py — SQLite in-memory + respx
  - connect() returns auth_url containing state
  - callback() encrypts tokens + upserts to DB
  - callback() with invalid state → ValueError
  - get_valid_credential() returns plaintext (not ciphertext)
  - get_valid_credential() auto-refreshes if expires_at < now+300

test_sync_service.py — SQLite in-memory + respx
  - sync with NULL last_sync_at → since = now-90d
  - incremental sync from last_sync_at
  - upsert is idempotent (2× sync = same count)
  - ConnectorRateLimitError propagated correctly
  - sport_breakdown counts by type

test_activity_mapper.py
  - Run → "running", VirtualRide → "biking", Swim → "swimming"
  - unknown sport_type → lowercased fallback
  - optional fields None when absent (avg_hr, avg_watts, etc.)
  - raw_json contains original payload

test_strava.py — API level
  - POST /integrations/strava/connect → 200 + auth_url
  - POST /integrations/strava/connect unauthenticated → 401
  - GET /integrations/strava/callback?code=x&state=valid → 200
  - GET /integrations/strava/callback?state=invalid → 400
  - POST /integrations/strava/sync → 200 + SyncSummary
  - POST /integrations/strava/sync unauthenticated → 401
```

---

## Migration

`alembic/versions/0008_strava_v2.py`:
- Add `access_token_enc`, `refresh_token_enc` (Text, nullable) to `connector_credentials`
- Add `last_sync_at` (DateTime with timezone, nullable) to `connector_credentials`
- Drop `access_token`, `refresh_token` from `connector_credentials`
- Create `strava_activities` table

Existing Strava credentials are invalidated by migration (plaintext columns dropped). Athletes must re-authorize — acceptable for a pre-launch app.

---

## Tokens — Security Rules

- **Never log** `access_token`, `refresh_token`, or `STRAVA_ENCRYPTION_KEY`
- Plaintext tokens exist **in memory only** for the duration of a request
- `get_valid_credential()` is the single entry point — all callers go through it
- `STRAVA_ENCRYPTION_KEY` read from env at call time (not stored in any model)

---

## V2 Roadmap (out of scope)

- Webhook-based real-time sync (Strava push events)
- Per-athlete sync scheduling (cron)
- Lap data ingestion (`fetch_activity_laps`)
- AthleteState field updates from persisted activities (CTL/ATL/TSB recalculation)
