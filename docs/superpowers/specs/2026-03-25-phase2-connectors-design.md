# Phase 2 Design Spec — API Connectors

**Date**: 2026-03-25
**Project**: Resilio Plus — Hybrid Athlete Multi-Agent Coaching Platform
**Scope**: Phase 2 — 4 API connectors: Strava (migration), Hevy, FatSecret, Terra/Apple Health

---

## 1. Context

Phase 1 delivered the complete data layer: 5 Pydantic schemas + 4 SQLAlchemy ORM tables + SQLite engine. Phase 2 builds the connector layer that pulls data from external APIs into the backend. These connectors are the input pipeline for the coaching agents (Phase 3).

Four providers:
- **Strava** — running and cycling activities (OAuth2 PKCE, existing logic in `resilio/core/strava.py`)
- **Hevy** — strength workouts (API Key, Hevy Pro required)
- **FatSecret** — nutrition diary (OAuth2 client credentials)
- **Terra** — Apple Health proxy (API Key, Terra user ID per athlete)

All 4 connectors share a common `BaseConnector` infrastructure (retry, rate limiting, token management).

---

## 2. Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Scope | All 4 connectors in one spec | Share common base infrastructure; designing separately duplicates the foundation |
| Architecture | Abstract base class (`BaseConnector`) | Retry, rate limit, token refresh implemented once, reused by all connectors |
| App credentials | Environment variables | `CLIENT_ID`/`CLIENT_SECRET` are app-level, not user-level |
| User OAuth tokens | `ConnectorCredential` DB table | Per-athlete, per-provider; rotated on each refresh |
| HTTP client | `httpx` (already a dependency) | Sync client matches current codebase style |
| Retry library | `tenacity` (already a dependency) | Already used in legacy Strava connector |
| Test strategy | `respx` mocks + JSON fixtures | No real API calls in tests; fixtures reproduce real responses |

---

## 3. Directory Structure

```
backend/app/connectors/
├── __init__.py
├── base.py          — BaseConnector abstract class + shared exceptions
├── strava.py        — Strava connector (migrated from resilio/core/strava.py)
├── hevy.py          — Hevy connector (new)
├── fatsecret.py     — FatSecret connector (new)
└── terra.py         — Apple Health via Terra API (new)

backend/app/schemas/connector.py   — ConnectorCredential + all DTOs
backend/app/db/models.py           — ConnectorCredentialModel added (ORM table)

tests/backend/connectors/
├── __init__.py
├── fixtures/        — JSON fixture files (anonymized real API responses)
│   ├── strava_activity.json
│   ├── strava_laps.json
│   ├── hevy_workouts.json
│   ├── fatsecret_day.json
│   └── terra_daily.json
├── test_base.py
├── test_strava.py
├── test_hevy.py
├── test_fatsecret.py
└── test_terra.py
```

New dev dependency: `respx>=0.21,<1.0` (httpx mock library).

---

## 4. ConnectorCredential — DB + Schema

### 4.1 ORM Model (`backend/app/db/models.py` — appended)

```python
class ConnectorCredentialModel(Base):
    __tablename__ = "connector_credentials"

    id = Column(String, primary_key=True)
    athlete_id = Column(String, ForeignKey("athletes.id"), nullable=False)
    provider = Column(String, nullable=False)          # "strava"|"hevy"|"fatsecret"|"terra"
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    expires_at = Column(Integer, nullable=True)        # Unix timestamp
    extra_json = Column(Text, nullable=False, default="{}")  # provider-specific extras
    athlete = relationship("AthleteModel", back_populates="credentials")
```

`AthleteModel` gains: `credentials = relationship("ConnectorCredentialModel", back_populates="athlete")`

Unique constraint: `(athlete_id, provider)` — one credential row per athlete per provider.

### 4.2 Pydantic Schema (`backend/app/schemas/connector.py`)

```python
class ConnectorCredential(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    athlete_id: UUID
    provider: str
    access_token: str | None = None
    refresh_token: str | None = None
    expires_at: int | None = None      # Unix timestamp
    extra: dict = Field(default_factory=dict)
```

---

## 5. BaseConnector (`backend/app/connectors/base.py`)

### 5.1 Interface

```python
class BaseConnector(ABC):
    provider: str  # class-level string, set by each subclass

    def __init__(
        self,
        credential: ConnectorCredential,
        client_id: str,
        client_secret: str,
    ) -> None: ...

    def get_valid_token(self) -> str:
        """Return a valid access token, refreshing proactively if expires in < 5 min."""

    @abstractmethod
    def _do_refresh_token(self) -> ConnectorCredential:
        """Provider-specific token refresh. Returns updated credential."""

    def _request(self, method: str, url: str, **kwargs) -> dict:
        """HTTP request with 3-attempt tenacity retry + 429 Retry-After handling."""
```

### 5.2 Retry Strategy

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=8),
    retry=retry_if_exception_type((ConnectorAPIError, httpx.HTTPError)),
    reraise=True,
)
def _request(self, method, url, **kwargs) -> dict:
    response = self._client.request(method, url, **kwargs)
    if response.status_code == 429:
        retry_after = int(response.headers.get("Retry-After", 60))
        raise ConnectorRateLimitError(provider=self.provider, retry_after=retry_after)
    if response.status_code == 401:
        raise ConnectorAuthError(provider=self.provider)
    response.raise_for_status()
    return response.json()
```

### 5.3 Exception Hierarchy

```python
class ConnectorError(Exception):
    def __init__(self, provider: str, message: str): ...

class ConnectorAuthError(ConnectorError): ...         # 401, token invalid
class ConnectorRateLimitError(ConnectorError):         # 429
    retry_after: int                                   # seconds to wait
class ConnectorAPIError(ConnectorError):               # other HTTP errors
    status_code: int
```

---

## 6. Strava Connector (`backend/app/connectors/strava.py`)

### 6.1 Environment Variables
- `STRAVA_CLIENT_ID`
- `STRAVA_CLIENT_SECRET`
- `STRAVA_REDIRECT_URI`

### 6.2 Methods

```python
class StravaConnector(BaseConnector):
    provider = "strava"

    def get_auth_url(self) -> str:
        """Generate OAuth authorization URL with scope activity:read_all,profile:read_all."""

    def exchange_code(self, code: str) -> ConnectorCredential:
        """Exchange auth code for tokens. Returns updated credential."""

    def _do_refresh_token(self) -> ConnectorCredential:
        """POST to https://www.strava.com/oauth/token with refresh_token grant."""

    def fetch_activities(
        self, since: datetime, until: datetime
    ) -> list[StravaActivity]:
        """Paginated fetch (200/page). Stops at since boundary."""

    def fetch_activity_laps(self, activity_id: str) -> list[StravaLap]:
        """GET /activities/{id}/laps. Returns [] if 404."""
```

### 6.3 Migration Notes

The existing `resilio/core/strava.py` contains production-tested logic. The migration:
- Replaces `Config` YAML dependency with `ConnectorCredential` + env vars
- Replaces `RawActivity` return type with `StravaActivity` DTO
- Drops CLI-specific helpers (`create_manual_activity`, `check_duplicate`, sync generator)
- Retains: OAuth flow, proactive token refresh, retry strategy, lap fetching, rate limit handling

`resilio/core/strava.py` remains read-only (legacy CLI still uses it).

---

## 7. Hevy Connector (`backend/app/connectors/hevy.py`)

### 7.1 Environment Variables
- `HEVY_API_KEY` — stored in env; also copied to `ConnectorCredential.extra["api_key"]` for per-athlete override if needed

### 7.2 API Details
- Base URL: `https://api.hevyapp.com/v1/`
- Auth: `api-key: {API_KEY}` header (no OAuth)
- Rate limit: 10 req/min (Hevy Pro)
- Pagination: `page` + `pageCount` params (10 workouts/page default)

### 7.3 Methods

```python
class HevyConnector(BaseConnector):
    provider = "hevy"

    def _do_refresh_token(self) -> ConnectorCredential:
        """No-op — Hevy uses API Key, no refresh needed."""

    def fetch_workouts(
        self, since: datetime, until: datetime
    ) -> list[HevyWorkout]:
        """Paginated fetch of workouts filtered by date range."""
```

---

## 8. FatSecret Connector (`backend/app/connectors/fatsecret.py`)

### 8.1 Environment Variables
- `FATSECRET_CLIENT_ID`
- `FATSECRET_CLIENT_SECRET`

### 8.2 API Details
- Base URL: `https://platform.fatsecret.com/rest/server.api`
- Auth: OAuth2 client credentials flow (Bearer token, expires in 86400s)
- No per-user OAuth — accesses a shared diary (the authenticated client's own diary)
- Date param: integer `date_int` = days since 1970-01-01

### 8.3 Methods

```python
class FatSecretConnector(BaseConnector):
    provider = "fatsecret"

    def _do_refresh_token(self) -> ConnectorCredential:
        """POST client_credentials grant to get new Bearer token."""

    def fetch_food_entries(self, date: date) -> FatSecretDay:
        """GET food/entries.get for a given date. Returns FatSecretDay with aggregated macros."""
```

---

## 9. Terra Connector (`backend/app/connectors/terra.py`)

### 9.1 Environment Variables
- `TERRA_API_KEY`
- `TERRA_DEV_ID`

### 9.2 API Details
- Base URL: `https://api.tryterra.co/v2/`
- Auth: `x-api-key` + `dev-id` headers
- Per-athlete: Terra `user_id` stored in `ConnectorCredential.extra["terra_user_id"]`
- Apple Health data flows through Terra widget (user connects once in frontend)

### 9.3 Methods

```python
class TerraConnector(BaseConnector):
    provider = "terra"

    def _do_refresh_token(self) -> ConnectorCredential:
        """No-op — Terra uses API Key + user_id, no OAuth refresh."""

    def fetch_daily(self, date: date) -> TerraHealthData:
        """GET /daily for HRV, sleep, steps, active energy for a given date."""
```

---

## 10. Data Transfer Objects (`backend/app/schemas/connector.py`)

```python
# --- Strava ---
class StravaLap(BaseModel):
    lap_index: int
    elapsed_time_seconds: int
    distance_meters: float
    average_hr: float | None
    pace_per_km: str | None         # "5:23"

class StravaActivity(BaseModel):
    id: str                         # "strava_{strava_id}"
    name: str
    sport_type: str                 # "Run", "Ride", "TrailRun", etc.
    date: date
    duration_seconds: int
    distance_meters: float | None
    elevation_gain_meters: float | None
    average_hr: float | None
    max_hr: float | None
    perceived_exertion: int | None  # RPE 1-10
    laps: list[StravaLap] = Field(default_factory=list)

# --- Hevy ---
class HevySet(BaseModel):
    reps: int | None
    weight_kg: float | None
    rpe: float | None               # 1-10
    set_type: str                   # "normal", "warmup", "dropset", "failure"

class HevyExercise(BaseModel):
    name: str
    sets: list[HevySet]

class HevyWorkout(BaseModel):
    id: str
    title: str
    date: date
    duration_seconds: int
    exercises: list[HevyExercise]

# --- FatSecret ---
class FatSecretMeal(BaseModel):
    name: str                       # "Breakfast", "Lunch", "Dinner", "Other"
    calories: float
    carbs_g: float
    protein_g: float
    fat_g: float

class FatSecretDay(BaseModel):
    date: date
    calories_total: float
    carbs_g: float
    protein_g: float
    fat_g: float
    meals: list[FatSecretMeal]

# --- Terra ---
class TerraHealthData(BaseModel):
    date: date
    hrv_rmssd: float | None         # ms — key signal for Recovery Coach
    sleep_duration_hours: float | None
    sleep_score: float | None       # 0-100 if available
    steps: int | None
    active_energy_kcal: float | None
```

---

## 11. Testing Strategy

### 11.1 Dependencies
Add to `[tool.poetry.group.dev.dependencies]`:
```toml
respx = ">=0.21,<1.0"
```

### 11.2 Fixtures
`tests/backend/connectors/fixtures/` contains anonymized JSON files matching real API responses:
- `strava_activity.json` — single activity response from GET /activities/{id}
- `strava_laps.json` — laps response from GET /activities/{id}/laps
- `hevy_workouts.json` — page 1 workouts list response
- `fatsecret_day.json` — food entries response for one day
- `terra_daily.json` — daily endpoint response with HRV + sleep

### 11.3 Test Coverage Per Module

**`test_base.py`** (BaseConnector):
- Retry: 3 attempts on `ConnectorAPIError`, backoff respected
- Rate limit: 429 response raises `ConnectorRateLimitError` with correct `retry_after`
- Auth error: 401 raises `ConnectorAuthError`
- Token refresh: `get_valid_token()` calls `_do_refresh_token()` when `expires_at < now + 5min`
- Token valid: no refresh when token still valid

**`test_strava.py`**:
- `get_auth_url()` returns URL with correct scope
- `exchange_code()` returns populated `ConnectorCredential`
- `fetch_activities()` parses fixture into `list[StravaActivity]`
- `fetch_activity_laps()` parses lap fixture into `list[StravaLap]`
- `fetch_activity_laps()` returns `[]` on 404

**`test_hevy.py`**:
- `fetch_workouts()` parses fixture into `list[HevyWorkout]`
- Pagination: second page fetched when `pageCount > 1`
- Sets with `None` weight (bodyweight exercises) parse correctly

**`test_fatsecret.py`**:
- `_do_refresh_token()` fetches new Bearer token via client credentials
- `fetch_food_entries()` aggregates meal macros into `FatSecretDay`
- Missing meal (e.g., no dinner logged) does not raise

**`test_terra.py`**:
- `fetch_daily()` parses HRV RMSSD from nested Terra response
- Missing HRV data returns `hrv_rmssd=None` (not an error)
- Sleep duration parsed from `sleep_durations_data`

---

## 12. Environment Variables Summary

| Variable | Provider | Description |
|---|---|---|
| `STRAVA_CLIENT_ID` | Strava | OAuth app client ID |
| `STRAVA_CLIENT_SECRET` | Strava | OAuth app client secret |
| `STRAVA_REDIRECT_URI` | Strava | OAuth callback URL |
| `HEVY_API_KEY` | Hevy | Pro API key |
| `FATSECRET_CLIENT_ID` | FatSecret | OAuth2 client ID |
| `FATSECRET_CLIENT_SECRET` | FatSecret | OAuth2 client secret |
| `TERRA_API_KEY` | Terra | API key |
| `TERRA_DEV_ID` | Terra | Developer ID |

A `.env.example` file will be created at the repo root listing all variables with placeholder values.

---

## 13. Out of Scope for Phase 2

- FastAPI routes exposing connector data (Phase 4)
- Frontend OAuth callback handling (Phase 4/5)
- Agent consumption of connector DTOs (Phase 3)
- Real integration tests against live APIs (Phase 6)
- Strava webhook for real-time activity push
- FatSecret user-level OAuth (diary access via client credentials is sufficient for MVP)
