# Phase 2 — API Connectors Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the connector layer that pulls activity, workout, nutrition, and health data from Strava, Hevy, FatSecret, and Terra into typed Pydantic DTOs that the coaching agents will consume.

**Architecture:** A `BaseConnector` abstract class centralises retry (tenacity inner-function closure pattern — NOT a class decorator), token validity checking, and HTTP client lifecycle. Each provider subclass implements `_do_refresh_token()` and its fetch methods, returning Pydantic DTOs. Per-athlete credentials are persisted in a new `connector_credentials` ORM table with a `(athlete_id, provider)` unique constraint.

**Tech Stack:** `httpx` (sync HTTP client), `tenacity` (retry — already installed), `respx` (httpx mocking in tests — new dev dep), `pydantic` v2, SQLAlchemy 2.x

---

## File Map

**Create:**
- `backend/app/connectors/__init__.py`
- `backend/app/connectors/base.py` — BaseConnector + exception hierarchy
- `backend/app/connectors/strava.py` — Strava OAuth + activity/lap fetch
- `backend/app/connectors/hevy.py` — Hevy API Key + workout fetch
- `backend/app/connectors/fatsecret.py` — FatSecret client credentials + food fetch
- `backend/app/connectors/terra.py` — Terra API Key + daily health fetch
- `backend/app/schemas/connector.py` — ConnectorCredential + all DTOs
- `tests/backend/connectors/__init__.py`
- `tests/backend/connectors/conftest.py` — 4 credential fixtures
- `tests/backend/connectors/fixtures/strava_activities.json`
- `tests/backend/connectors/fixtures/strava_laps.json`
- `tests/backend/connectors/fixtures/hevy_workouts.json`
- `tests/backend/connectors/fixtures/fatsecret_day.json`
- `tests/backend/connectors/fixtures/terra_daily.json`
- `tests/backend/connectors/test_base.py`
- `tests/backend/connectors/test_strava.py`
- `tests/backend/connectors/test_hevy.py`
- `tests/backend/connectors/test_fatsecret.py`
- `tests/backend/connectors/test_terra.py`
- `tests/backend/schemas/test_connector.py`
- `.env.example`

**Modify:**
- `pyproject.toml` — add `respx` to dev deps
- `backend/app/db/models.py` — add `ConnectorCredentialModel`; add `credentials` relationship to `AthleteModel`
- `tests/backend/db/test_models.py` — add 4 `ConnectorCredentialModel` tests

---

## Task 1: Prerequisites

**Files:**
- Modify: `pyproject.toml`
- Create: `.env.example`
- Create: `backend/app/connectors/__init__.py`
- Create: `tests/backend/connectors/__init__.py`

- [ ] **Step 1: Add respx dev dependency**

Edit `pyproject.toml` — append to `[tool.poetry.group.dev.dependencies]`:
```toml
respx = ">=0.21,<1.0"
```

- [ ] **Step 2: Install respx**

```bash
cd C:/Users/simon/resilio-plus && pip install "respx>=0.21,<1.0"
```

Expected: `Successfully installed respx-...`

- [ ] **Step 3: Create .env.example at repo root**

Create `C:/Users/simon/resilio-plus/.env.example`:
```dotenv
# Strava OAuth app credentials
STRAVA_CLIENT_ID=CHANGEME
STRAVA_CLIENT_SECRET=CHANGEME
STRAVA_REDIRECT_URI=http://localhost:8000/auth/strava/callback

# Hevy Pro API key
HEVY_API_KEY=CHANGEME

# FatSecret OAuth2 credentials
FATSECRET_CLIENT_ID=CHANGEME
FATSECRET_CLIENT_SECRET=CHANGEME

# Terra API credentials
TERRA_API_KEY=CHANGEME
TERRA_DEV_ID=CHANGEME
```

- [ ] **Step 4: Create package skeleton files**

Create `backend/app/connectors/__init__.py` (empty).
Create `tests/backend/connectors/__init__.py` (empty).

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml .env.example backend/app/connectors/__init__.py tests/backend/connectors/__init__.py
git commit -m "chore: add respx dev dep, .env.example, connector package skeletons"
```

---

## Task 2: ConnectorCredential Schema + All DTOs

**Files:**
- Create: `backend/app/schemas/connector.py`
- Create: `tests/backend/schemas/test_connector.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/backend/schemas/test_connector.py`:
```python
import pytest
from datetime import date
from uuid import UUID
from app.schemas.connector import (
    ConnectorCredential,
    StravaLap,
    StravaActivity,
    HevySet,
    HevyExercise,
    HevyWorkout,
    FatSecretMeal,
    FatSecretDay,
    TerraHealthData,
)


def test_connector_credential_defaults():
    cred = ConnectorCredential(
        athlete_id="00000000-0000-0000-0000-000000000001",
        provider="strava",
    )
    assert isinstance(cred.id, UUID)
    assert cred.extra == {}
    assert cred.access_token is None
    assert cred.expires_at is None


def test_connector_credential_full():
    cred = ConnectorCredential(
        athlete_id="00000000-0000-0000-0000-000000000001",
        provider="strava",
        access_token="tok",
        refresh_token="ref",
        expires_at=9999999999,
        extra={"scope": "read_all"},
    )
    assert cred.access_token == "tok"
    assert cred.expires_at == 9999999999
    assert cred.extra == {"scope": "read_all"}


def test_strava_lap_round_trip():
    lap = StravaLap(
        lap_index=1,
        elapsed_time_seconds=300,
        distance_meters=1000.0,
        average_hr=142.0,
        pace_per_km="5:00",
    )
    assert lap.lap_index == 1
    assert lap.pace_per_km == "5:00"


def test_strava_activity_with_laps():
    lap = StravaLap(
        lap_index=1,
        elapsed_time_seconds=300,
        distance_meters=1000.0,
        average_hr=None,
        pace_per_km=None,
    )
    activity = StravaActivity(
        id="strava_12345",
        name="Morning Run",
        sport_type="Run",
        date=date(2026, 3, 20),
        duration_seconds=3600,
        distance_meters=10000.0,
        elevation_gain_meters=50.0,
        average_hr=145.0,
        max_hr=165.0,
        perceived_exertion=6,
        laps=[lap],
    )
    assert activity.id == "strava_12345"
    assert len(activity.laps) == 1


def test_strava_activity_optional_fields_default_none():
    activity = StravaActivity(
        id="strava_1",
        name="Test",
        sport_type="Run",
        date=date(2026, 3, 20),
        duration_seconds=1800,
        distance_meters=None,
        elevation_gain_meters=None,
        average_hr=None,
        max_hr=None,
        perceived_exertion=None,
    )
    assert activity.distance_meters is None
    assert activity.laps == []


def test_hevy_set_bodyweight_exercise():
    s = HevySet(reps=8, weight_kg=None, rpe=7.0, set_type="normal")
    assert s.weight_kg is None


def test_hevy_workout_round_trip():
    workout = HevyWorkout(
        id="w1",
        title="Push Day",
        date=date(2026, 3, 20),
        duration_seconds=3900,
        exercises=[
            HevyExercise(
                name="Bench Press",
                sets=[HevySet(reps=10, weight_kg=60.0, rpe=7.0, set_type="normal")],
            )
        ],
    )
    assert workout.title == "Push Day"
    assert workout.exercises[0].name == "Bench Press"


def test_fatsecret_day_aggregates():
    day = FatSecretDay(
        date=date(2026, 3, 20),
        calories_total=1800.0,
        carbs_g=220.0,
        protein_g=130.0,
        fat_g=60.0,
        meals=[
            FatSecretMeal(name="Breakfast", calories=600.0, carbs_g=80.0, protein_g=30.0, fat_g=20.0),
            FatSecretMeal(name="Lunch", calories=700.0, carbs_g=80.0, protein_g=50.0, fat_g=20.0),
        ],
    )
    assert day.calories_total == 1800.0
    assert len(day.meals) == 2


def test_terra_health_data_none_hrv():
    data = TerraHealthData(
        date=date(2026, 3, 20),
        hrv_rmssd=None,
        sleep_duration_hours=7.5,
        sleep_score=78.0,
        steps=8500,
        active_energy_kcal=450.0,
    )
    assert data.hrv_rmssd is None
    assert data.steps == 8500
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd C:/Users/simon/resilio-plus && python -m pytest tests/backend/schemas/test_connector.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.schemas.connector'`

- [ ] **Step 3: Implement `backend/app/schemas/connector.py`**

```python
from datetime import date
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


class ConnectorCredential(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    athlete_id: UUID
    provider: str
    access_token: str | None = None
    refresh_token: str | None = None
    expires_at: int | None = None  # Unix timestamp
    extra: dict = Field(default_factory=dict)


class StravaLap(BaseModel):
    lap_index: int
    elapsed_time_seconds: int
    distance_meters: float
    average_hr: float | None
    pace_per_km: str | None  # "5:23"


class StravaActivity(BaseModel):
    id: str  # "strava_{strava_id}"
    name: str
    sport_type: str
    date: date
    duration_seconds: int
    distance_meters: float | None
    elevation_gain_meters: float | None
    average_hr: float | None
    max_hr: float | None
    perceived_exertion: int | None  # RPE 1-10
    laps: list[StravaLap] = Field(default_factory=list)


class HevySet(BaseModel):
    reps: int | None
    weight_kg: float | None
    rpe: float | None  # 1-10
    set_type: str  # "normal", "warmup", "dropset", "failure"


class HevyExercise(BaseModel):
    name: str
    sets: list[HevySet]


class HevyWorkout(BaseModel):
    id: str
    title: str
    date: date
    duration_seconds: int
    exercises: list[HevyExercise]


class FatSecretMeal(BaseModel):
    name: str  # "Breakfast", "Lunch", "Dinner", "Other"
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


class TerraHealthData(BaseModel):
    date: date
    hrv_rmssd: float | None  # ms
    sleep_duration_hours: float | None
    sleep_score: float | None  # 0-100
    steps: int | None
    active_energy_kcal: float | None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd C:/Users/simon/resilio-plus && python -m pytest tests/backend/schemas/test_connector.py -v
```

Expected: 9 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/connector.py tests/backend/schemas/test_connector.py
git commit -m "feat: add ConnectorCredential schema and all connector DTOs"
```

---

## Task 3: ConnectorCredentialModel ORM

**Files:**
- Modify: `backend/app/db/models.py`
- Modify: `tests/backend/db/test_models.py`

**Key constraint:** `UniqueConstraint("athlete_id", "provider")` must be in `__table_args__` — one row per athlete per provider, enforced at DB level.

- [ ] **Step 1: Write the failing tests**

Append to `tests/backend/db/test_models.py`:
```python
def test_connector_credentials_table_created():
    from sqlalchemy import inspect
    engine = make_test_engine()
    setup_db(engine)
    inspector = inspect(engine)
    assert "connector_credentials" in inspector.get_table_names()
    teardown_db(engine)


def test_connector_credential_crud_round_trip():
    from app.db.models import AthleteModel, ConnectorCredentialModel
    import uuid
    engine = make_test_engine()
    Session = setup_db(engine)
    athlete_id = str(uuid.uuid4())
    cred_id = str(uuid.uuid4())
    with Session() as session:
        session.add(AthleteModel(**{**make_athlete_row(), "id": athlete_id}))
        session.add(ConnectorCredentialModel(
            id=cred_id,
            athlete_id=athlete_id,
            provider="strava",
            access_token="tok",
            refresh_token="ref",
            expires_at=9999999999,
            extra_json="{}",
        ))
        session.commit()
        fetched = session.get(ConnectorCredentialModel, cred_id)
        assert fetched.provider == "strava"
        assert fetched.access_token == "tok"
        assert fetched.athlete_id == athlete_id
    teardown_db(engine)


def test_connector_credential_unique_constraint():
    from app.db.models import AthleteModel, ConnectorCredentialModel
    from sqlalchemy.exc import IntegrityError
    import uuid
    engine = make_test_engine()
    Session = setup_db(engine)
    athlete_id = str(uuid.uuid4())
    with Session() as session:
        session.add(AthleteModel(**{**make_athlete_row(), "id": athlete_id}))
        session.add(ConnectorCredentialModel(
            id=str(uuid.uuid4()),
            athlete_id=athlete_id,
            provider="strava",
            extra_json="{}",
        ))
        session.flush()
        session.add(ConnectorCredentialModel(
            id=str(uuid.uuid4()),
            athlete_id=athlete_id,
            provider="strava",  # duplicate (athlete_id, provider)
            extra_json="{}",
        ))
        with pytest.raises(IntegrityError):
            session.commit()
    teardown_db(engine)


def test_athlete_credentials_relationship():
    from app.db.models import AthleteModel, ConnectorCredentialModel
    import uuid
    engine = make_test_engine()
    Session = setup_db(engine)
    athlete_id = str(uuid.uuid4())
    with Session() as session:
        session.add(AthleteModel(**{**make_athlete_row(), "id": athlete_id}))
        session.add(ConnectorCredentialModel(
            id=str(uuid.uuid4()), athlete_id=athlete_id, provider="strava", extra_json="{}",
        ))
        session.add(ConnectorCredentialModel(
            id=str(uuid.uuid4()), athlete_id=athlete_id, provider="hevy", extra_json="{}",
        ))
        session.commit()
        athlete = session.get(AthleteModel, athlete_id)
        assert len(athlete.credentials) == 2
        providers = {c.provider for c in athlete.credentials}
        assert providers == {"strava", "hevy"}
    teardown_db(engine)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd C:/Users/simon/resilio-plus && python -m pytest tests/backend/db/test_models.py::test_connector_credentials_table_created -v
```

Expected: FAIL — `connector_credentials` table not found

- [ ] **Step 3: Modify `backend/app/db/models.py`**

Add `UniqueConstraint` to the existing import line:
```python
from sqlalchemy import Boolean, Column, Date, Float, ForeignKey, Integer, String, Text, UniqueConstraint
```

Add `credentials` relationship to `AthleteModel` (after the existing `reviews` relationship):
```python
    credentials = relationship("ConnectorCredentialModel", back_populates="athlete")
```

Append the new model class at the end of the file:
```python
class ConnectorCredentialModel(Base):
    __tablename__ = "connector_credentials"

    id = Column(String, primary_key=True)
    athlete_id = Column(String, ForeignKey("athletes.id"), nullable=False)
    provider = Column(String, nullable=False)          # "strava"|"hevy"|"fatsecret"|"terra"
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    expires_at = Column(Integer, nullable=True)        # Unix timestamp
    extra_json = Column(Text, nullable=False, default="{}")
    # Relationships
    athlete = relationship("AthleteModel", back_populates="credentials")

    __table_args__ = (UniqueConstraint("athlete_id", "provider"),)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd C:/Users/simon/resilio-plus && python -m pytest tests/backend/db/test_models.py -v
```

Expected: All 14 tests PASS (10 original + 4 new)

- [ ] **Step 5: Commit**

```bash
git add backend/app/db/models.py tests/backend/db/test_models.py
git commit -m "feat: add ConnectorCredentialModel ORM table with UniqueConstraint"
```

---

## Task 4: BaseConnector + Exceptions

**Files:**
- Create: `backend/app/connectors/base.py`
- Create: `tests/backend/connectors/test_base.py`

**Critical pattern:** The `@retry` decorator from tenacity **cannot** be applied directly to a class instance method (it binds at class definition time, before any instance exists). The correct approach is an inner-function closure inside `_request()` that closes over `self`.

**`_retry_wait` class variable:** Defined as `wait_exponential(multiplier=2, min=2, max=8)` on `BaseConnector`. Test subclasses override with `wait_none()` to eliminate sleep delays.

**429 behaviour:** `ConnectorRateLimitError` is **not** in the retry predicate (`retry_if_exception_type` only covers `ConnectorAPIError` and `httpx.HTTPError`). A 429 raises immediately — the caller is responsible for backing off.

- [ ] **Step 1: Write the failing tests**

Create `tests/backend/connectors/test_base.py`:
```python
import time
import pytest
import respx
import httpx
from tenacity import wait_none

from app.schemas.connector import ConnectorCredential
from app.connectors.base import (
    BaseConnector,
    ConnectorAPIError,
    ConnectorAuthError,
    ConnectorRateLimitError,
)


class FakeConnector(BaseConnector):
    """Test subclass: no-op refresh, instant retry (no sleep)."""
    provider = "fake"
    _retry_wait = wait_none()

    def _do_refresh_token(self) -> ConnectorCredential:
        return self.credential.model_copy(update={
            "access_token": "refreshed_token",
            "expires_at": int(time.time()) + 3600,
        })


@pytest.fixture
def cred():
    return ConnectorCredential(
        athlete_id="00000000-0000-0000-0000-000000000001",
        provider="fake",
        access_token="test_token",
        expires_at=int(time.time()) + 3600,
    )


@pytest.fixture
def connector(cred):
    c = FakeConnector(cred, client_id="cid", client_secret="csecret")
    yield c
    c.close()


TEST_URL = "https://api.fake.test/endpoint"


@respx.mock
def test_retry_succeeds_on_third_attempt(connector):
    route = respx.get(TEST_URL).mock(
        side_effect=[
            httpx.Response(500, json={"error": "server error"}),
            httpx.Response(500, json={"error": "server error"}),
            httpx.Response(200, json={"data": "ok"}),
        ]
    )
    result = connector._request("GET", TEST_URL)
    assert result == {"data": "ok"}
    assert route.call_count == 3


@respx.mock
def test_exhausted_retries_raises_connector_api_error(connector):
    respx.get(TEST_URL).mock(return_value=httpx.Response(500, json={"error": "fail"}))
    with pytest.raises(ConnectorAPIError):
        connector._request("GET", TEST_URL)


@respx.mock
def test_429_raises_rate_limit_immediately(connector):
    route = respx.get(TEST_URL).mock(
        return_value=httpx.Response(429, headers={"Retry-After": "30"}, json={})
    )
    with pytest.raises(ConnectorRateLimitError) as exc_info:
        connector._request("GET", TEST_URL)
    assert exc_info.value.retry_after == 30
    assert route.call_count == 1  # not retried


@respx.mock
def test_401_raises_auth_error(connector):
    respx.get(TEST_URL).mock(return_value=httpx.Response(401, json={"error": "unauthorized"}))
    with pytest.raises(ConnectorAuthError):
        connector._request("GET", TEST_URL)


def test_get_valid_token_no_refresh_when_valid(connector):
    original_token = connector.credential.access_token
    token = connector.get_valid_token()
    assert token == original_token


def test_get_valid_token_refreshes_when_expired(cred):
    expired_cred = cred.model_copy(update={"expires_at": int(time.time()) - 100})
    c = FakeConnector(expired_cred, client_id="cid", client_secret="csecret")
    token = c.get_valid_token()
    assert token == "refreshed_token"
    c.close()


def test_context_manager_closes_client(cred):
    with FakeConnector(cred, client_id="cid", client_secret="csecret") as c:
        assert c._client is not None
    # No assertion needed — just verify no exception on exit
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd C:/Users/simon/resilio-plus && python -m pytest tests/backend/connectors/test_base.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.connectors.base'`

- [ ] **Step 3: Implement `backend/app/connectors/base.py`**

```python
import time
from abc import ABC, abstractmethod

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.schemas.connector import ConnectorCredential


class ConnectorError(Exception):
    def __init__(self, provider: str, message: str) -> None:
        super().__init__(message)
        self.provider = provider


class ConnectorAuthError(ConnectorError):
    pass


class ConnectorRateLimitError(ConnectorError):
    def __init__(self, provider: str, message: str, retry_after: int = 60) -> None:
        super().__init__(provider, message)
        self.retry_after = retry_after


class ConnectorAPIError(ConnectorError):
    def __init__(self, provider: str, message: str, status_code: int = 0) -> None:
        super().__init__(provider, message)
        self.status_code = status_code


class BaseConnector(ABC):
    provider: str
    _retry_wait = wait_exponential(multiplier=2, min=2, max=8)

    def __init__(
        self,
        credential: ConnectorCredential,
        client_id: str,
        client_secret: str,
    ) -> None:
        self.credential = credential
        self.client_id = client_id
        self.client_secret = client_secret
        self._client = httpx.Client(timeout=30.0)

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self) -> "BaseConnector":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def get_valid_token(self) -> str:
        """Return a valid access token, refreshing proactively if expires in < 5 min."""
        expires_at = self.credential.expires_at
        if expires_at is not None and expires_at < (time.time() + 300):
            self.credential = self._do_refresh_token()
        return self.credential.access_token or ""

    @abstractmethod
    def _do_refresh_token(self) -> ConnectorCredential:
        """Provider-specific token refresh. Returns updated credential."""
        ...

    def _request(self, method: str, url: str, **kwargs: object) -> dict:
        """HTTP request with 3-attempt tenacity retry + 429/401 handling.

        NOTE: Uses inner-function closure pattern because @retry cannot be applied
        directly as a class decorator on instance methods — the decorator binds at
        class-definition time before any instance exists.

        429 raises ConnectorRateLimitError immediately (not retried) — caller backs off.
        401 raises ConnectorAuthError immediately (not retried).
        Other HTTP errors become ConnectorAPIError and ARE retried up to 3 times.
        """
        @retry(
            stop=stop_after_attempt(3),
            wait=self._retry_wait,
            retry=retry_if_exception_type((ConnectorAPIError, httpx.HTTPError)),
            reraise=True,
        )
        def _inner() -> dict:
            response = self._client.request(method, url, **kwargs)
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                raise ConnectorRateLimitError(
                    provider=self.provider,
                    message=f"Rate limited by {self.provider}",
                    retry_after=retry_after,
                )
            if response.status_code == 401:
                raise ConnectorAuthError(
                    provider=self.provider,
                    message=f"Authentication failed for {self.provider}",
                )
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                raise ConnectorAPIError(
                    provider=self.provider,
                    message=str(e),
                    status_code=response.status_code,
                ) from e
            return response.json()

        return _inner()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd C:/Users/simon/resilio-plus && python -m pytest tests/backend/connectors/test_base.py -v
```

Expected: 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/connectors/base.py tests/backend/connectors/test_base.py
git commit -m "feat: add BaseConnector with tenacity inner-function retry pattern"
```

---

## Task 5: JSON Fixtures + conftest.py

**Files:**
- Create: `tests/backend/connectors/conftest.py`
- Create: `tests/backend/connectors/fixtures/strava_activities.json`
- Create: `tests/backend/connectors/fixtures/strava_laps.json`
- Create: `tests/backend/connectors/fixtures/hevy_workouts.json`
- Create: `tests/backend/connectors/fixtures/fatsecret_day.json`
- Create: `tests/backend/connectors/fixtures/terra_daily.json`

No TDD cycle needed — this task creates shared test infrastructure.

- [ ] **Step 1: Create conftest.py**

Create `tests/backend/connectors/conftest.py`:
```python
import pytest
from app.schemas.connector import ConnectorCredential


@pytest.fixture
def strava_credential():
    return ConnectorCredential(
        athlete_id="00000000-0000-0000-0000-000000000001",
        provider="strava",
        access_token="test_access_token",
        refresh_token="test_refresh_token",
        expires_at=9999999999,  # far future — valid token
    )


@pytest.fixture
def hevy_credential():
    # Hevy uses API Key — no access/refresh tokens; key lives in extra
    return ConnectorCredential(
        athlete_id="00000000-0000-0000-0000-000000000001",
        provider="hevy",
        extra={"api_key": "test_hevy_key"},
    )


@pytest.fixture
def fatsecret_credential():
    # FatSecret uses app-level Bearer token (client credentials grant)
    return ConnectorCredential(
        athlete_id="00000000-0000-0000-0000-000000000001",
        provider="fatsecret",
        access_token="test_bearer_token",
        expires_at=9999999999,
    )


@pytest.fixture
def terra_credential():
    # Terra uses API Key (env) + per-athlete terra_user_id in extra
    return ConnectorCredential(
        athlete_id="00000000-0000-0000-0000-000000000001",
        provider="terra",
        extra={"terra_user_id": "test_terra_user_123"},
    )
```

- [ ] **Step 2: Create strava_activities.json**

Create `tests/backend/connectors/fixtures/strava_activities.json`:
```json
[
  {
    "id": 11111111111,
    "name": "Morning Run",
    "sport_type": "Run",
    "start_date_local": "2026-03-20T07:00:00Z",
    "elapsed_time": 3600,
    "distance": 10000.0,
    "total_elevation_gain": 50.0,
    "average_heartrate": 145.0,
    "max_heartrate": 165.0,
    "perceived_exertion": 6
  },
  {
    "id": 22222222222,
    "name": "Evening Ride",
    "sport_type": "Ride",
    "start_date_local": "2026-03-21T18:00:00Z",
    "elapsed_time": 5400,
    "distance": 45000.0,
    "total_elevation_gain": 300.0,
    "average_heartrate": 138.0,
    "max_heartrate": 158.0,
    "perceived_exertion": null
  }
]
```

- [ ] **Step 3: Create strava_laps.json**

Create `tests/backend/connectors/fixtures/strava_laps.json`:
```json
[
  {
    "lap_index": 1,
    "elapsed_time": 360,
    "distance": 1000.0,
    "average_heartrate": 140.0,
    "average_speed": 2.78
  },
  {
    "lap_index": 2,
    "elapsed_time": 355,
    "distance": 1000.0,
    "average_heartrate": 143.0,
    "average_speed": 2.82
  }
]
```

- [ ] **Step 4: Create hevy_workouts.json**

Create `tests/backend/connectors/fixtures/hevy_workouts.json`:
```json
{
  "workouts": [
    {
      "id": "workout1",
      "title": "Push Day",
      "start_time": "2026-03-20T10:00:00Z",
      "end_time": "2026-03-20T11:05:00Z",
      "exercises": [
        {
          "title": "Bench Press (Barbell)",
          "sets": [
            {"reps": 10, "weight_kg": 60.0, "rpe": 7.0, "set_type": "normal"},
            {"reps": 8, "weight_kg": 65.0, "rpe": 8.0, "set_type": "normal"}
          ]
        },
        {
          "title": "Pull-up",
          "sets": [
            {"reps": 8, "weight_kg": null, "rpe": 7.0, "set_type": "normal"},
            {"reps": 7, "weight_kg": null, "rpe": 8.0, "set_type": "normal"}
          ]
        }
      ]
    }
  ],
  "page": 1,
  "page_count": 1
}
```

- [ ] **Step 5: Create fatsecret_day.json**

Create `tests/backend/connectors/fixtures/fatsecret_day.json`:
```json
{
  "food_entries": {
    "food_entry": [
      {
        "food_entry_id": "1001",
        "food_entry_name": "Oatmeal with Banana",
        "meal": "breakfast",
        "calories": "350",
        "carbohydrate": "65",
        "protein": "10",
        "fat": "6"
      },
      {
        "food_entry_id": "1002",
        "food_entry_name": "Grilled Chicken Breast",
        "meal": "lunch",
        "calories": "280",
        "carbohydrate": "0",
        "protein": "55",
        "fat": "5"
      },
      {
        "food_entry_id": "1003",
        "food_entry_name": "Salmon with Rice",
        "meal": "dinner",
        "calories": "550",
        "carbohydrate": "60",
        "protein": "40",
        "fat": "15"
      }
    ]
  }
}
```

Totals: 1180 cal, 125g carbs, 105g protein, 26g fat.

- [ ] **Step 6: Create terra_daily.json**

Create `tests/backend/connectors/fixtures/terra_daily.json`:
```json
{
  "status": "ok",
  "data": [
    {
      "user": {"user_id": "test_terra_user_123"},
      "metadata": {
        "start_time": "2026-03-20T00:00:00+00:00",
        "end_time": "2026-03-20T23:59:59+00:00"
      },
      "heart_rate_data": {
        "summary": {
          "hrv_rmssd_data": [{"hrv_rmssd": 45.2}]
        }
      },
      "sleep_durations_data": {
        "total_sleep_time": 27000
      },
      "daily_movement": {
        "steps": 8500,
        "active_energy_burned_cal": 450.0
      },
      "sleep_score": 78.0
    }
  ]
}
```

`total_sleep_time` = 27000 seconds = 7.5 hours.

- [ ] **Step 7: Verify conftest fixtures are importable**

```bash
cd C:/Users/simon/resilio-plus && python -m pytest tests/backend/connectors/conftest.py --collect-only
```

Expected: no collection errors

- [ ] **Step 8: Commit**

```bash
git add tests/backend/connectors/conftest.py tests/backend/connectors/fixtures/
git commit -m "test: add connector fixtures and conftest credential fixtures"
```

---

## Task 6: StravaConnector

**Files:**
- Create: `backend/app/connectors/strava.py`
- Create: `tests/backend/connectors/test_strava.py`

**Migration notes:** The legacy `resilio/core/strava.py` is read-only. New connector replaces `Config` YAML with `ConnectorCredential` + env vars, and replaces `RawActivity` with `StravaActivity` DTO.

- [ ] **Step 1: Write the failing tests**

Create `tests/backend/connectors/test_strava.py`:
```python
import json
import pytest
import respx
import httpx
from pathlib import Path
from datetime import datetime, timezone, date

from app.connectors.strava import StravaConnector
from app.schemas.connector import ConnectorCredential, StravaActivity, StravaLap

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def connector(strava_credential):
    c = StravaConnector(
        strava_credential,
        client_id="test_client_id",
        client_secret="test_client_secret",
    )
    yield c
    c.close()


def test_get_auth_url_contains_scope_and_client_id(connector):
    url = connector.get_auth_url()
    assert "activity:read_all" in url
    assert "profile:read_all" in url
    assert "test_client_id" in url
    assert "response_type=code" in url


@respx.mock
def test_exchange_code_returns_populated_credential(connector):
    respx.post("https://www.strava.com/oauth/token").mock(
        return_value=httpx.Response(200, json={
            "access_token": "new_access",
            "refresh_token": "new_refresh",
            "expires_at": 9999999999,
            "athlete": {"id": 12345},
        })
    )
    cred = connector.exchange_code("auth_code_123")
    assert cred.access_token == "new_access"
    assert cred.refresh_token == "new_refresh"
    assert cred.expires_at == 9999999999


@respx.mock
def test_fetch_activities_parses_fixture(connector):
    fixture = json.loads((FIXTURES_DIR / "strava_activities.json").read_text())
    respx.get("https://www.strava.com/api/v3/athlete/activities").mock(
        side_effect=[
            httpx.Response(200, json=fixture),
            httpx.Response(200, json=[]),  # second page empty — stops pagination
        ]
    )
    since = datetime(2026, 3, 1, tzinfo=timezone.utc)
    until = datetime(2026, 3, 31, tzinfo=timezone.utc)
    activities = connector.fetch_activities(since, until)
    assert len(activities) == 2
    assert isinstance(activities[0], StravaActivity)
    assert activities[0].id == "strava_11111111111"
    assert activities[0].sport_type == "Run"
    assert activities[0].date == date(2026, 3, 20)
    assert activities[1].id == "strava_22222222222"
    assert activities[1].perceived_exertion is None


@respx.mock
def test_fetch_activity_laps_parses_fixture(connector):
    fixture = json.loads((FIXTURES_DIR / "strava_laps.json").read_text())
    respx.get("https://www.strava.com/api/v3/activities/11111111111/laps").mock(
        return_value=httpx.Response(200, json=fixture)
    )
    laps = connector.fetch_activity_laps("11111111111")
    assert len(laps) == 2
    assert isinstance(laps[0], StravaLap)
    assert laps[0].lap_index == 1
    assert laps[0].distance_meters == 1000.0
    assert laps[0].pace_per_km is not None  # computed from average_speed


@respx.mock
def test_fetch_activity_laps_returns_empty_on_404(connector):
    respx.get("https://www.strava.com/api/v3/activities/99999/laps").mock(
        return_value=httpx.Response(404, json={"message": "Not Found"})
    )
    laps = connector.fetch_activity_laps("99999")
    assert laps == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd C:/Users/simon/resilio-plus && python -m pytest tests/backend/connectors/test_strava.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.connectors.strava'`

- [ ] **Step 3: Implement `backend/app/connectors/strava.py`**

```python
import os
from datetime import datetime, date
from urllib.parse import urlencode

import httpx

from app.connectors.base import BaseConnector, ConnectorAPIError
from app.schemas.connector import ConnectorCredential, StravaActivity, StravaLap

STRAVA_BASE = "https://www.strava.com/api/v3"
STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"
STRAVA_AUTH_URL = "https://www.strava.com/oauth/authorize"
STRAVA_SCOPE = "activity:read_all,profile:read_all"
PAGE_SIZE = 200


def _speed_to_pace_per_km(speed_mps: float | None) -> str | None:
    if not speed_mps or speed_mps <= 0:
        return None
    total_secs = 1000 / speed_mps
    mins = int(total_secs // 60)
    secs = int(total_secs % 60)
    return f"{mins}:{secs:02d}"


def _parse_activity(item: dict) -> StravaActivity:
    raw_date = item["start_date_local"][:10]  # "YYYY-MM-DD"
    return StravaActivity(
        id=f"strava_{item['id']}",
        name=item["name"],
        sport_type=item.get("sport_type") or item.get("type", "Unknown"),
        date=date.fromisoformat(raw_date),
        duration_seconds=item["elapsed_time"],
        distance_meters=item.get("distance"),
        elevation_gain_meters=item.get("total_elevation_gain"),
        average_hr=item.get("average_heartrate"),
        max_hr=item.get("max_heartrate"),
        perceived_exertion=item.get("perceived_exertion"),
    )


def _parse_lap(item: dict) -> StravaLap:
    return StravaLap(
        lap_index=item["lap_index"],
        elapsed_time_seconds=item["elapsed_time"],
        distance_meters=item["distance"],
        average_hr=item.get("average_heartrate"),
        pace_per_km=_speed_to_pace_per_km(item.get("average_speed")),
    )


class StravaConnector(BaseConnector):
    provider = "strava"

    def get_auth_url(self) -> str:
        redirect_uri = os.getenv(
            "STRAVA_REDIRECT_URI",
            "http://localhost:8000/auth/strava/callback",
        )
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "approval_prompt": "force",
            "scope": STRAVA_SCOPE,
        }
        return f"{STRAVA_AUTH_URL}?{urlencode(params)}"

    def exchange_code(self, code: str) -> ConnectorCredential:
        response = self._client.post(
            STRAVA_TOKEN_URL,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": code,
                "grant_type": "authorization_code",
            },
        )
        response.raise_for_status()
        data = response.json()
        return self.credential.model_copy(update={
            "access_token": data["access_token"],
            "refresh_token": data["refresh_token"],
            "expires_at": data["expires_at"],
        })

    def _do_refresh_token(self) -> ConnectorCredential:
        response = self._client.post(
            STRAVA_TOKEN_URL,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self.credential.refresh_token,
                "grant_type": "refresh_token",
            },
        )
        response.raise_for_status()
        data = response.json()
        return self.credential.model_copy(update={
            "access_token": data["access_token"],
            "refresh_token": data["refresh_token"],
            "expires_at": data["expires_at"],
        })

    def fetch_activities(
        self, since: datetime, until: datetime
    ) -> list[StravaActivity]:
        token = self.get_valid_token()
        headers = {"Authorization": f"Bearer {token}"}
        activities: list[StravaActivity] = []
        page = 1
        while True:
            data = self._request(
                "GET",
                f"{STRAVA_BASE}/athlete/activities",
                headers=headers,
                params={
                    "after": int(since.timestamp()),
                    "before": int(until.timestamp()),
                    "per_page": PAGE_SIZE,
                    "page": page,
                },
            )
            if not data:
                break
            for item in data:
                activities.append(_parse_activity(item))
            if len(data) < PAGE_SIZE:
                break
            page += 1
        return activities

    def fetch_activity_laps(self, activity_id: str) -> list[StravaLap]:
        token = self.get_valid_token()
        try:
            data = self._request(
                "GET",
                f"{STRAVA_BASE}/activities/{activity_id}/laps",
                headers={"Authorization": f"Bearer {token}"},
            )
        except ConnectorAPIError as e:
            if e.status_code == 404:
                return []
            raise
        return [_parse_lap(lap) for lap in data]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd C:/Users/simon/resilio-plus && python -m pytest tests/backend/connectors/test_strava.py -v
```

Expected: 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/connectors/strava.py tests/backend/connectors/test_strava.py
git commit -m "feat: add StravaConnector with OAuth flow and activity/lap fetch"
```

---

## Task 7: HevyConnector

**Files:**
- Create: `backend/app/connectors/hevy.py`
- Create: `tests/backend/connectors/test_hevy.py`

**API Key source:** `self.credential.extra.get("api_key")` takes priority; falls back to `self.client_id` (which maps to `HEVY_API_KEY` env var in production).

- [ ] **Step 1: Write the failing tests**

Create `tests/backend/connectors/test_hevy.py`:
```python
import json
import pytest
import respx
import httpx
from pathlib import Path
from datetime import datetime, timezone

from app.connectors.hevy import HevyConnector
from app.schemas.connector import HevyWorkout

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def connector(hevy_credential):
    c = HevyConnector(hevy_credential, client_id="", client_secret="")
    yield c
    c.close()


@respx.mock
def test_fetch_workouts_parses_fixture(connector):
    fixture = json.loads((FIXTURES_DIR / "hevy_workouts.json").read_text())
    respx.get("https://api.hevyapp.com/v1/workouts").mock(
        return_value=httpx.Response(200, json=fixture)
    )
    since = datetime(2026, 3, 1, tzinfo=timezone.utc)
    until = datetime(2026, 3, 31, tzinfo=timezone.utc)
    workouts = connector.fetch_workouts(since, until)
    assert len(workouts) == 1
    assert isinstance(workouts[0], HevyWorkout)
    assert workouts[0].title == "Push Day"
    assert workouts[0].duration_seconds == 3900  # 65 min = 3900 s


@respx.mock
def test_fetch_workouts_bodyweight_sets_parse_correctly(connector):
    fixture = json.loads((FIXTURES_DIR / "hevy_workouts.json").read_text())
    respx.get("https://api.hevyapp.com/v1/workouts").mock(
        return_value=httpx.Response(200, json=fixture)
    )
    since = datetime(2026, 3, 1, tzinfo=timezone.utc)
    until = datetime(2026, 3, 31, tzinfo=timezone.utc)
    workouts = connector.fetch_workouts(since, until)
    pullup_exercise = workouts[0].exercises[1]  # Pull-up (index 1)
    assert pullup_exercise.name == "Pull-up"
    assert pullup_exercise.sets[0].weight_kg is None


@respx.mock
def test_fetch_workouts_pagination_stops_at_since_boundary(hevy_credential):
    page1 = {
        "workouts": [{
            "id": "w1", "title": "In Range",
            "start_time": "2026-03-20T10:00:00Z",
            "end_time": "2026-03-20T11:00:00Z",
            "exercises": [],
        }],
        "page": 1, "page_count": 2,
    }
    page2 = {
        "workouts": [{
            "id": "w2", "title": "Before Range",
            "start_time": "2026-03-19T10:00:00Z",
            "end_time": "2026-03-19T11:00:00Z",
            "exercises": [],
        }],
        "page": 2, "page_count": 2,
    }
    route = respx.get("https://api.hevyapp.com/v1/workouts").mock(
        side_effect=[
            httpx.Response(200, json=page1),
            httpx.Response(200, json=page2),
        ]
    )
    c = HevyConnector(hevy_credential, client_id="", client_secret="")
    since = datetime(2026, 3, 20, tzinfo=timezone.utc)  # midnight March 20
    until = datetime(2026, 3, 31, tzinfo=timezone.utc)
    workouts = c.fetch_workouts(since, until)
    assert route.call_count == 2  # fetched page 2 before finding cutoff
    assert len(workouts) == 1  # w2 is before since, not included
    c.close()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd C:/Users/simon/resilio-plus && python -m pytest tests/backend/connectors/test_hevy.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.connectors.hevy'`

- [ ] **Step 3: Implement `backend/app/connectors/hevy.py`**

```python
from datetime import datetime, timezone

from app.connectors.base import BaseConnector
from app.schemas.connector import ConnectorCredential, HevyExercise, HevySet, HevyWorkout

HEVY_BASE = "https://api.hevyapp.com/v1"
PAGE_SIZE = 10


def _parse_set(item: dict) -> HevySet:
    return HevySet(
        reps=item.get("reps"),
        weight_kg=item.get("weight_kg"),
        rpe=item.get("rpe"),
        set_type=item.get("set_type", "normal"),
    )


def _parse_exercise(item: dict) -> HevyExercise:
    return HevyExercise(
        name=item["title"],
        sets=[_parse_set(s) for s in item.get("sets", [])],
    )


def _parse_workout(item: dict) -> HevyWorkout:
    start = datetime.fromisoformat(item["start_time"].replace("Z", "+00:00"))
    end = datetime.fromisoformat(item["end_time"].replace("Z", "+00:00"))
    duration_seconds = int((end - start).total_seconds())
    return HevyWorkout(
        id=item["id"],
        title=item["title"],
        date=start.date(),
        duration_seconds=duration_seconds,
        exercises=[_parse_exercise(ex) for ex in item.get("exercises", [])],
    )


class HevyConnector(BaseConnector):
    provider = "hevy"

    def _do_refresh_token(self) -> ConnectorCredential:
        return self.credential  # API Key never expires

    def _api_key(self) -> str:
        return self.credential.extra.get("api_key") or self.client_id

    def fetch_workouts(
        self, since: datetime, until: datetime
    ) -> list[HevyWorkout]:
        headers = {"api-key": self._api_key()}
        workouts: list[HevyWorkout] = []
        page = 1
        while True:
            data = self._request(
                "GET",
                f"{HEVY_BASE}/workouts",
                headers=headers,
                params={"page": page, "pageCount": PAGE_SIZE},
            )
            for item in data.get("workouts", []):
                start = datetime.fromisoformat(
                    item["start_time"].replace("Z", "+00:00")
                )
                if start < since:
                    return workouts  # past the date range — stop
                if start <= until:
                    workouts.append(_parse_workout(item))
            total_pages = data.get("page_count", 1)
            if page >= total_pages:
                break
            page += 1
        return workouts
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd C:/Users/simon/resilio-plus && python -m pytest tests/backend/connectors/test_hevy.py -v
```

Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/connectors/hevy.py tests/backend/connectors/test_hevy.py
git commit -m "feat: add HevyConnector with paginated workout fetch"
```

---

## Task 8: FatSecretConnector

**Files:**
- Create: `backend/app/connectors/fatsecret.py`
- Create: `tests/backend/connectors/test_fatsecret.py`

**Date encoding:** FatSecret uses `date_int` = days since 1970-01-01. Python: `(query_date - date(1970, 1, 1)).days`

**Single-entry edge case:** When only one food entry exists for a date, FatSecret returns a `dict` (not a `list`) under `food_entry`. The parser must handle both.

- [ ] **Step 1: Write the failing tests**

Create `tests/backend/connectors/test_fatsecret.py`:
```python
import json
import pytest
import respx
import httpx
from pathlib import Path
from datetime import date

from app.connectors.fatsecret import FatSecretConnector
from app.schemas.connector import FatSecretDay

FIXTURES_DIR = Path(__file__).parent / "fixtures"

FATSECRET_API_URL = "https://platform.fatsecret.com/rest/server.api"
FATSECRET_TOKEN_URL = "https://oauth.fatsecret.com/connect/token"


@pytest.fixture
def connector(fatsecret_credential):
    c = FatSecretConnector(
        fatsecret_credential,
        client_id="test_fs_id",
        client_secret="test_fs_secret",
    )
    yield c
    c.close()


@respx.mock
def test_do_refresh_token_fetches_new_bearer(fatsecret_credential):
    respx.post(FATSECRET_TOKEN_URL).mock(
        return_value=httpx.Response(200, json={
            "access_token": "new_bearer_token",
            "expires_in": 86400,
            "token_type": "Bearer",
        })
    )
    c = FatSecretConnector(fatsecret_credential, client_id="cid", client_secret="csecret")
    updated_cred = c._do_refresh_token()
    assert updated_cred.access_token == "new_bearer_token"
    c.close()


@respx.mock
def test_fetch_food_entries_parses_fixture(connector):
    fixture = json.loads((FIXTURES_DIR / "fatsecret_day.json").read_text())
    respx.get(FATSECRET_API_URL).mock(return_value=httpx.Response(200, json=fixture))
    result = connector.fetch_food_entries(date(2026, 3, 20))
    assert isinstance(result, FatSecretDay)
    assert result.date == date(2026, 3, 20)
    assert result.calories_total == pytest.approx(1180.0)  # 350 + 280 + 550
    assert result.protein_g == pytest.approx(105.0)  # 10 + 55 + 40
    assert result.carbs_g == pytest.approx(125.0)   # 65 + 0 + 60
    assert len(result.meals) == 3
    assert result.meals[0].name == "Breakfast"


@respx.mock
def test_fetch_food_entries_missing_meals_does_not_raise(connector):
    partial_fixture = {
        "food_entries": {
            "food_entry": [
                {
                    "food_entry_id": "1", "food_entry_name": "Oatmeal",
                    "meal": "breakfast", "calories": "300",
                    "carbohydrate": "50", "protein": "10", "fat": "5",
                }
            ]
        }
    }
    respx.get(FATSECRET_API_URL).mock(return_value=httpx.Response(200, json=partial_fixture))
    result = connector.fetch_food_entries(date(2026, 3, 20))
    assert result.calories_total == pytest.approx(300.0)
    assert len(result.meals) == 1


@respx.mock
def test_fetch_food_entries_single_entry_as_dict(connector):
    # FatSecret returns food_entry as a dict (not list) when only one entry exists
    single_entry_fixture = {
        "food_entries": {
            "food_entry": {
                "food_entry_id": "1", "food_entry_name": "Protein Bar",
                "meal": "other", "calories": "200",
                "carbohydrate": "20", "protein": "25", "fat": "8",
            }
        }
    }
    respx.get(FATSECRET_API_URL).mock(return_value=httpx.Response(200, json=single_entry_fixture))
    result = connector.fetch_food_entries(date(2026, 3, 20))
    assert result.calories_total == pytest.approx(200.0)
    assert len(result.meals) == 1
    assert result.meals[0].name == "Other"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd C:/Users/simon/resilio-plus && python -m pytest tests/backend/connectors/test_fatsecret.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.connectors.fatsecret'`

- [ ] **Step 3: Implement `backend/app/connectors/fatsecret.py`**

```python
import time
from datetime import date

from app.connectors.base import BaseConnector
from app.schemas.connector import ConnectorCredential, FatSecretDay, FatSecretMeal

FATSECRET_API_URL = "https://platform.fatsecret.com/rest/server.api"
FATSECRET_TOKEN_URL = "https://oauth.fatsecret.com/connect/token"
_EPOCH = date(1970, 1, 1)


def _to_date_int(d: date) -> int:
    return (d - _EPOCH).days


def _parse_day(data: dict, query_date: date) -> FatSecretDay:
    entries_data = data.get("food_entries", {})
    raw_entries = entries_data.get("food_entry", [])
    # FatSecret returns a dict (not list) when there is only one entry
    if isinstance(raw_entries, dict):
        raw_entries = [raw_entries]

    meals: list[FatSecretMeal] = []
    total_cal = total_carbs = total_protein = total_fat = 0.0

    for entry in raw_entries:
        meal_name = entry.get("meal", "other").title()
        cal = float(entry.get("calories", 0))
        carbs = float(entry.get("carbohydrate", 0))
        protein = float(entry.get("protein", 0))
        fat = float(entry.get("fat", 0))
        meals.append(
            FatSecretMeal(
                name=meal_name,
                calories=cal,
                carbs_g=carbs,
                protein_g=protein,
                fat_g=fat,
            )
        )
        total_cal += cal
        total_carbs += carbs
        total_protein += protein
        total_fat += fat

    return FatSecretDay(
        date=query_date,
        calories_total=total_cal,
        carbs_g=total_carbs,
        protein_g=total_protein,
        fat_g=total_fat,
        meals=meals,
    )


class FatSecretConnector(BaseConnector):
    provider = "fatsecret"

    def _do_refresh_token(self) -> ConnectorCredential:
        response = self._client.post(
            FATSECRET_TOKEN_URL,
            data={"grant_type": "client_credentials", "scope": "basic"},
            auth=(self.client_id, self.client_secret),
        )
        response.raise_for_status()
        data = response.json()
        return self.credential.model_copy(update={
            "access_token": data["access_token"],
            "expires_at": int(time.time()) + data.get("expires_in", 86400),
        })

    def fetch_food_entries(self, query_date: date) -> FatSecretDay:
        token = self.get_valid_token()
        data = self._request(
            "GET",
            FATSECRET_API_URL,
            headers={"Authorization": f"Bearer {token}"},
            params={
                "method": "food_entries.get",
                "date": _to_date_int(query_date),
                "format": "json",
            },
        )
        return _parse_day(data, query_date)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd C:/Users/simon/resilio-plus && python -m pytest tests/backend/connectors/test_fatsecret.py -v
```

Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/connectors/fatsecret.py tests/backend/connectors/test_fatsecret.py
git commit -m "feat: add FatSecretConnector with client credentials token refresh"
```

---

## Task 9: TerraConnector

**Files:**
- Create: `backend/app/connectors/terra.py`
- Create: `tests/backend/connectors/test_terra.py`

**Auth mapping:** `client_id` = `TERRA_API_KEY` (sent as `x-api-key` header), `client_secret` = `TERRA_DEV_ID` (sent as `dev-id` header). Per-athlete `terra_user_id` lives in `credential.extra["terra_user_id"]`.

**HRV path:** `data[0].heart_rate_data.summary.hrv_rmssd_data[0].hrv_rmssd` — absent at any level → `None` (not an error).

- [ ] **Step 1: Write the failing tests**

Create `tests/backend/connectors/test_terra.py`:
```python
import json
import pytest
import respx
import httpx
from pathlib import Path
from datetime import date

from app.connectors.terra import TerraConnector
from app.schemas.connector import TerraHealthData

FIXTURES_DIR = Path(__file__).parent / "fixtures"

TERRA_DAILY_URL = "https://api.tryterra.co/v2/daily"


@pytest.fixture
def connector(terra_credential):
    c = TerraConnector(
        terra_credential,
        client_id="test_terra_key",
        client_secret="test_dev_id",
    )
    yield c
    c.close()


@respx.mock
def test_fetch_daily_parses_fixture(connector):
    fixture = json.loads((FIXTURES_DIR / "terra_daily.json").read_text())
    respx.get(TERRA_DAILY_URL).mock(return_value=httpx.Response(200, json=fixture))
    result = connector.fetch_daily(date(2026, 3, 20))
    assert isinstance(result, TerraHealthData)
    assert result.hrv_rmssd == pytest.approx(45.2)
    assert result.sleep_duration_hours == pytest.approx(7.5)
    assert result.steps == 8500
    assert result.active_energy_kcal == pytest.approx(450.0)
    assert result.sleep_score == pytest.approx(78.0)


@respx.mock
def test_fetch_daily_missing_hrv_returns_none(connector):
    no_hrv = {
        "status": "ok",
        "data": [{
            "user": {"user_id": "test_terra_user_123"},
            "metadata": {"start_time": "2026-03-20T00:00:00+00:00"},
            "heart_rate_data": {"summary": {}},
            "sleep_durations_data": {"total_sleep_time": 25200},
            "daily_movement": {"steps": 5000, "active_energy_burned_cal": 300.0},
        }]
    }
    respx.get(TERRA_DAILY_URL).mock(return_value=httpx.Response(200, json=no_hrv))
    result = connector.fetch_daily(date(2026, 3, 20))
    assert result.hrv_rmssd is None
    assert result.steps == 5000


@respx.mock
def test_fetch_daily_empty_data_returns_all_none(connector):
    respx.get(TERRA_DAILY_URL).mock(
        return_value=httpx.Response(200, json={"status": "ok", "data": []})
    )
    result = connector.fetch_daily(date(2026, 3, 20))
    assert result.hrv_rmssd is None
    assert result.sleep_duration_hours is None
    assert result.steps is None
    assert result.date == date(2026, 3, 20)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd C:/Users/simon/resilio-plus && python -m pytest tests/backend/connectors/test_terra.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.connectors.terra'`

- [ ] **Step 3: Implement `backend/app/connectors/terra.py`**

```python
from datetime import date

from app.connectors.base import BaseConnector
from app.schemas.connector import ConnectorCredential, TerraHealthData

TERRA_BASE = "https://api.tryterra.co/v2"


def _parse_daily(data: dict, query_date: date) -> TerraHealthData:
    items = data.get("data", [])
    if not items:
        return TerraHealthData(
            date=query_date,
            hrv_rmssd=None,
            sleep_duration_hours=None,
            sleep_score=None,
            steps=None,
            active_energy_kcal=None,
        )
    item = items[0]

    # HRV RMSSD — deeply nested; absent at any level → None
    hrv_rmssd = None
    hr_data = item.get("heart_rate_data", {})
    hrv_data = hr_data.get("summary", {}).get("hrv_rmssd_data", [])
    if hrv_data:
        hrv_rmssd = hrv_data[0].get("hrv_rmssd")

    # Sleep
    sleep_secs = item.get("sleep_durations_data", {}).get("total_sleep_time")
    sleep_hours = round(sleep_secs / 3600, 2) if sleep_secs else None

    # Movement
    movement = item.get("daily_movement", {})
    steps = movement.get("steps")
    active_kcal = movement.get("active_energy_burned_cal")

    sleep_score = item.get("sleep_score")

    return TerraHealthData(
        date=query_date,
        hrv_rmssd=hrv_rmssd,
        sleep_duration_hours=sleep_hours,
        sleep_score=sleep_score,
        steps=steps,
        active_energy_kcal=active_kcal,
    )


class TerraConnector(BaseConnector):
    provider = "terra"

    def _do_refresh_token(self) -> ConnectorCredential:
        return self.credential  # API Key never expires

    def _headers(self) -> dict:
        return {
            "x-api-key": self.client_id,    # TERRA_API_KEY
            "dev-id": self.client_secret,    # TERRA_DEV_ID
        }

    def fetch_daily(self, query_date: date) -> TerraHealthData:
        terra_user_id = self.credential.extra.get("terra_user_id", "")
        data = self._request(
            "GET",
            f"{TERRA_BASE}/daily",
            headers=self._headers(),
            params={
                "user_id": terra_user_id,
                "start_date": query_date.isoformat(),
                "end_date": query_date.isoformat(),
                "to_webhook": "false",
            },
        )
        return _parse_daily(data, query_date)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd C:/Users/simon/resilio-plus && python -m pytest tests/backend/connectors/test_terra.py -v
```

Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/connectors/terra.py tests/backend/connectors/test_terra.py
git commit -m "feat: add TerraConnector with HRV, sleep, and activity parsing"
```

---

## Task 10: Final Verification

**Files:** none (run only)

- [ ] **Step 1: Run the full connector test suite**

```bash
cd C:/Users/simon/resilio-plus && python -m pytest tests/backend/connectors/ tests/backend/schemas/test_connector.py tests/backend/db/test_models.py -v
```

Expected: All tests PASS. Count should be approximately:
- `test_base.py`: 7 tests
- `test_strava.py`: 5 tests
- `test_hevy.py`: 3 tests
- `test_fatsecret.py`: 4 tests
- `test_terra.py`: 3 tests
- `test_connector.py` (schemas): 9 tests
- `test_models.py` (ORM + ConnectorCredential): 14 tests
- **Total: ~45 tests**

- [ ] **Step 2: Run the full test suite (sanity check)**

```bash
cd C:/Users/simon/resilio-plus && python -m pytest tests/backend/ -v --tb=short
```

Expected: All backend tests PASS (no regressions in Phase 1 tests)

- [ ] **Step 3: Final commit (if any cleanup needed)**

```bash
git add -A
git commit -m "chore: Phase 2 complete — 4 API connectors with full TDD coverage"
```
