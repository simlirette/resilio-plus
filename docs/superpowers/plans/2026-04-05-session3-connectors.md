# S3 — Connecteurs : Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire Strava OAuth2 and Hevy API connectors into the FastAPI backend, storing credentials in a new `connector_credentials` table and ingesting activities/workouts into `run_activities`/`lifting_sessions`.

**Architecture:** Pure service layer (`StravaConnector`, `HevyConnector`) with injectable `httpx` transports for testability, mounted on a minimal FastAPI router. DB upserts use PostgreSQL `ON CONFLICT DO UPDATE` for idempotent syncs. No JWT auth in S3 — `athlete_id` as query param throughout.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async, httpx, PostgreSQL (ON CONFLICT), Alembic, pytest-asyncio, httpx.MockTransport.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `models/database.py` | Modify | Add `ConnectorCredential` table + relation on `Athlete`; add `unique=True` to `LiftingSession.hevy_workout_id` |
| `core/config.py` | Modify | Add `HEVY_API_KEY: str = ""` |
| `.env` | Modify | Add real credentials (never committed) |
| `alembic/versions/<hash>_add_connector_credentials.py` | Generate | Migration: new table + unique constraint |
| `tests/conftest.py` | Modify | Add Strava/Hevy env vars for test settings |
| `connectors/__init__.py` | Create | Empty package marker |
| `connectors/strava.py` | Create | `StravaConnector`: OAuth2 flow + activity ingestion |
| `connectors/hevy.py` | Create | `HevyConnector`: API key validation + workout ingestion |
| `api/__init__.py` | Create | Empty package marker |
| `api/v1/__init__.py` | Create | Empty package marker |
| `api/v1/connectors.py` | Create | FastAPI router (9 routes) |
| `api/main.py` | Create | FastAPI app stub |
| `tests/test_strava_connector.py` | Create | 5 unit tests (httpx.MockTransport) |
| `tests/test_hevy_connector.py` | Create | 5 unit tests (httpx.MockTransport) |
| `tests/test_connector_routes.py` | Create | 3 route tests (ASGITransport) |

---

## Task 1: DB model + config + env + migration

**Files:**
- Modify: `models/database.py`
- Modify: `core/config.py`
- Modify: `.env`
- Generate: `alembic/versions/<hash>_add_connector_credentials.py`

- [ ] **Step 1: Add `UniqueConstraint` import and `ConnectorCredential` table to `models/database.py`**

  In `models/database.py`, add `UniqueConstraint` to the existing SQLAlchemy import line:

  ```python
  from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
  ```

  Then add the new table class at the end of the file (after `DecisionLog`):

  ```python
  # ─────────────────────────────────────────────
  # TABLE : connector_credentials
  # Tokens OAuth (Strava) et clés API (Hevy) par athlète
  # Un seul credential par provider par athlète — UniqueConstraint
  # ─────────────────────────────────────────────

  class ConnectorCredential(TimestampMixin, Base):
      __tablename__ = "connector_credentials"

      id: Mapped[uuid.UUID] = mapped_column(
          UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
      )
      athlete_id: Mapped[uuid.UUID] = mapped_column(
          ForeignKey("athletes.id"), nullable=False, index=True
      )
      provider: Mapped[str] = mapped_column(String(50), nullable=False)  # "strava" | "hevy"

      # OAuth tokens (Strava)
      access_token: Mapped[str | None] = mapped_column(Text)
      refresh_token: Mapped[str | None] = mapped_column(Text)
      token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

      # API key (Hevy)
      api_key: Mapped[str | None] = mapped_column(Text)

      # ID externe de l'athlète chez le provider (ex: Strava athlete ID)
      external_athlete_id: Mapped[str | None] = mapped_column(String(100))

      # Un seul credential par provider par athlète
      __table_args__ = (UniqueConstraint("athlete_id", "provider"),)

      # Relation
      athlete: Mapped["Athlete"] = relationship(back_populates="connector_credentials")
  ```

- [ ] **Step 2: Add `connector_credentials` relation on `Athlete` and `unique=True` on `LiftingSession.hevy_workout_id`**

  In the `Athlete` class (around line 122, after the `decision_logs` relation), add:

  ```python
      connector_credentials: Mapped[list["ConnectorCredential"]] = relationship(
          back_populates="athlete"
      )
  ```

  In the `LiftingSession` class, change `hevy_workout_id` (around line 250) from:

  ```python
      hevy_workout_id: Mapped[str | None] = mapped_column(String(100))
  ```

  to:

  ```python
      hevy_workout_id: Mapped[str | None] = mapped_column(String(100), unique=True, index=True)
  ```

- [ ] **Step 3: Add `HEVY_API_KEY` to `core/config.py`**

  In `core/config.py`, after the `USDA_API_KEY` line, add:

  ```python
      # ── Hevy API ─────────────────────────────────
      HEVY_API_KEY: str = ""
  ```

- [ ] **Step 4: Update `.env` with real credentials**

  Open `.env` and add/update:

  ```bash
  # ── Strava OAuth ─────────────────────────────────
  STRAVA_CLIENT_ID=215637
  STRAVA_CLIENT_SECRET=31d0dea45c6a0c9ea7df168b03fbd13beae24fba
  STRAVA_REDIRECT_URI=http://localhost:8000/api/v1/connectors/strava/callback

  # ── Hevy API ─────────────────────────────────────
  HEVY_API_KEY=fe874ad5-90b6-437a-ad0b-81162c850400
  ```

  `.env` is in `.gitignore` — never commit it.

- [ ] **Step 5: Ensure PostgreSQL is running**

  ```bash
  docker compose up db -d
  docker compose ps
  ```

  Expected: `resilio_db` container healthy.

- [ ] **Step 6: Generate Alembic migration**

  ```bash
  poetry run alembic revision --autogenerate -m "add connector credentials"
  ```

  Expected: creates `alembic/versions/<hash>_add_connector_credentials.py` with:
  - `op.create_table('connector_credentials', ...)` with all columns
  - `op.create_unique_constraint(None, 'connector_credentials', ['athlete_id', 'provider'])`
  - `op.create_unique_constraint(None, 'lifting_sessions', ['hevy_workout_id'])`

  If the migration file mentions tables that already exist but aren't in the DB yet, that's because the initial migration `55a168264480` hasn't been applied. Apply it first:
  ```bash
  poetry run alembic upgrade head
  ```

- [ ] **Step 7: Apply migration**

  ```bash
  poetry run alembic upgrade head
  poetry run alembic current
  ```

  Expected: `<new_hash> (head)` — two revisions applied.

- [ ] **Step 8: Verify existing tests still pass**

  ```bash
  poetry run pytest tests/ -v
  ```

  Expected: 29 passed (all S1+S2 tests still green).

- [ ] **Step 9: Commit**

  ```bash
  git add models/database.py core/config.py alembic/versions/
  git commit -m "feat: add connector_credentials table + hevy_workout_id unique constraint"
  ```

---

## Task 2: StravaConnector (TDD)

**Files:**
- Create: `connectors/__init__.py`
- Create: `tests/test_strava_connector.py`
- Create: `connectors/strava.py`
- Modify: `tests/conftest.py`

- [ ] **Step 1: Create `connectors/__init__.py`**

  ```python
  ```

  (Empty file — package marker.)

- [ ] **Step 2: Add Strava/Hevy env vars to `tests/conftest.py`**

  In `tests/conftest.py`, after the existing `os.environ.setdefault("SECRET_KEY", ...)` line, add:

  ```python
  os.environ.setdefault("STRAVA_CLIENT_ID", "215637")
  os.environ.setdefault("STRAVA_CLIENT_SECRET", "test_strava_secret")
  os.environ.setdefault("STRAVA_REDIRECT_URI", "http://localhost:8000/api/v1/connectors/strava/callback")
  os.environ.setdefault("HEVY_API_KEY", "test_hevy_key")
  ```

  These must appear BEFORE any other imports so they are set before `core/config.py` is loaded.

- [ ] **Step 3: Write `tests/test_strava_connector.py` (failing)**

  ```python
  """
  Tests unitaires StravaConnector — httpx.MockTransport, pas de vraies requêtes réseau.
  """

  import math
  from datetime import datetime, timedelta, timezone

  import httpx
  import pytest
  from sqlalchemy import select

  from connectors.strava import StravaConnector
  from models.database import ConnectorCredential, RunActivity


  # ── test_get_authorization_url ────────────────────────────────────────────────

  def test_get_authorization_url():
      connector = StravaConnector()
      url = connector.get_authorization_url()
      assert "client_id=215637" in url
      assert "scope=activity:read_all" in url
      assert "redirect_uri=" in url
      assert url.startswith("https://www.strava.com/oauth/authorize")


  # ── test_exchange_code_stores_credential ─────────────────────────────────────

  async def test_exchange_code_stores_credential(db_session, simon_athlete):
      def mock_handler(request: httpx.Request) -> httpx.Response:
          return httpx.Response(
              200,
              json={
                  "access_token": "acc_token_123",
                  "refresh_token": "ref_token_456",
                  "expires_at": 9999999999,
                  "athlete": {"id": 777},
              },
          )

      connector = StravaConnector(transport=httpx.MockTransport(mock_handler))
      cred = await connector.exchange_code("auth_code_xyz", simon_athlete.id, db_session)

      assert cred.access_token == "acc_token_123"
      assert cred.refresh_token == "ref_token_456"
      assert cred.external_athlete_id == "777"
      assert cred.provider == "strava"
      assert cred.athlete_id == simon_athlete.id


  # ── test_refresh_token_when_expired ──────────────────────────────────────────

  async def test_refresh_token_when_expired(db_session, simon_athlete):
      now = datetime.now(tz=timezone.utc)
      past = now - timedelta(hours=1)

      cred = ConnectorCredential(
          athlete_id=simon_athlete.id,
          provider="strava",
          access_token="old_access",
          refresh_token="old_refresh",
          token_expires_at=past,
      )
      db_session.add(cred)
      await db_session.flush()

      def mock_handler(request: httpx.Request) -> httpx.Response:
          return httpx.Response(
              200,
              json={
                  "access_token": "new_access_token",
                  "refresh_token": "new_refresh_token",
                  "expires_at": int((now + timedelta(hours=6)).timestamp()),
              },
          )

      connector = StravaConnector(transport=httpx.MockTransport(mock_handler))
      refreshed = await connector.refresh_token_if_expired(cred, db_session)

      assert refreshed.access_token == "new_access_token"
      assert refreshed.refresh_token == "new_refresh_token"
      assert refreshed.token_expires_at > now


  # ── test_ingest_activities_upsert ────────────────────────────────────────────

  async def test_ingest_activities_upsert(db_session, simon_athlete):
      activity = {
          "id": 12345,
          "type": "Run",
          "start_date": "2026-01-15T08:00:00Z",
          "distance": 10000,
          "elapsed_time": 3600,
          "average_speed": 2.778,
          "average_heartrate": 155,
          "max_heartrate": 180,
          "total_elevation_gain": 50,
      }

      connector = StravaConnector()
      count1 = await connector.ingest_activities(simon_athlete.id, [activity], db_session)
      count2 = await connector.ingest_activities(simon_athlete.id, [activity], db_session)

      assert count1 == 1
      assert count2 == 1

      result = await db_session.execute(
          select(RunActivity).where(RunActivity.strava_activity_id == "12345")
      )
      activities_in_db = result.scalars().all()
      assert len(activities_in_db) == 1


  # ── test_trimp_calculated_without_hr ─────────────────────────────────────────

  async def test_trimp_calculated_without_hr(db_session, simon_athlete):
      activity = {
          "id": 99999,
          "type": "Run",
          "start_date": "2026-01-16T08:00:00Z",
          "distance": 5000,  # 5 km
          "elapsed_time": 1500,
          # No average_heartrate — fallback: trimp = distance_km * 1.0
      }

      connector = StravaConnector()
      await connector.ingest_activities(simon_athlete.id, [activity], db_session)

      result = await db_session.execute(
          select(RunActivity).where(RunActivity.strava_activity_id == "99999")
      )
      run = result.scalar_one()
      assert run.trimp == pytest.approx(5.0)
  ```

- [ ] **Step 4: Run tests to verify they fail**

  ```bash
  poetry run pytest tests/test_strava_connector.py -v
  ```

  Expected: `ModuleNotFoundError: No module named 'connectors.strava'` (or `ImportError`).

- [ ] **Step 5: Create `connectors/strava.py`**

  ```python
  """
  Strava connector — OAuth2 flow + activity ingestion.
  Classes de service pures — aucune dépendance FastAPI.
  """

  import math
  import uuid
  from datetime import datetime, timedelta, timezone

  import httpx
  from sqlalchemy import select
  from sqlalchemy.dialects.postgresql import insert as pg_insert
  from sqlalchemy.ext.asyncio import AsyncSession

  from core.config import settings
  from models.database import ConnectorCredential, RunActivity


  class StravaConnector:
      BASE_URL = "https://www.strava.com/api/v3"
      AUTH_URL = "https://www.strava.com/oauth/authorize"
      TOKEN_URL = "https://www.strava.com/oauth/token"

      def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
          self.client_id = settings.STRAVA_CLIENT_ID
          self.client_secret = settings.STRAVA_CLIENT_SECRET
          self.redirect_uri = settings.STRAVA_REDIRECT_URI
          self._transport = transport

      def _client(self) -> httpx.AsyncClient:
          """Crée un AsyncClient — transport injectable pour les tests."""
          return httpx.AsyncClient(transport=self._transport)

      def get_authorization_url(self) -> str:
          """Génère l'URL OAuth Strava pour rediriger l'athlète."""
          params = (
              f"client_id={self.client_id}"
              f"&redirect_uri={self.redirect_uri}"
              f"&response_type=code"
              f"&approval_prompt=auto"
              f"&scope=activity:read_all"
          )
          return f"{self.AUTH_URL}?{params}"

      async def exchange_code(
          self, code: str, athlete_id: uuid.UUID, db: AsyncSession
      ) -> ConnectorCredential:
          """Échange le code d'autorisation contre des tokens. Stocke en DB via upsert."""
          async with self._client() as client:
              resp = await client.post(
                  self.TOKEN_URL,
                  data={
                      "client_id": self.client_id,
                      "client_secret": self.client_secret,
                      "code": code,
                      "grant_type": "authorization_code",
                  },
              )
              resp.raise_for_status()
              data = resp.json()

          return await self._upsert_strava_credential(
              athlete_id=athlete_id,
              db=db,
              access_token=data["access_token"],
              refresh_token=data["refresh_token"],
              token_expires_at=datetime.fromtimestamp(data["expires_at"], tz=timezone.utc),
              external_athlete_id=str(data["athlete"]["id"]),
          )

      async def _upsert_strava_credential(
          self,
          athlete_id: uuid.UUID,
          db: AsyncSession,
          access_token: str,
          refresh_token: str,
          token_expires_at: datetime,
          external_athlete_id: str,
      ) -> ConnectorCredential:
          """Insère ou met à jour le ConnectorCredential Strava."""
          update_set = {
              "access_token": access_token,
              "refresh_token": refresh_token,
              "token_expires_at": token_expires_at,
              "external_athlete_id": external_athlete_id,
          }
          stmt = (
              pg_insert(ConnectorCredential)
              .values(
                  athlete_id=athlete_id,
                  provider="strava",
                  **update_set,
              )
              .on_conflict_do_update(
                  index_elements=["athlete_id", "provider"],
                  set_=update_set,
              )
          )
          await db.execute(stmt)
          await db.flush()
          result = await db.execute(
              select(ConnectorCredential).where(
                  ConnectorCredential.athlete_id == athlete_id,
                  ConnectorCredential.provider == "strava",
              )
          )
          return result.scalar_one()

      async def refresh_token_if_expired(
          self, cred: ConnectorCredential, db: AsyncSession
      ) -> ConnectorCredential:
          """Refresh si le token expire dans moins de 5 minutes."""
          if cred.token_expires_at is None:
              return cred
          threshold = datetime.now(tz=timezone.utc) + timedelta(minutes=5)
          if cred.token_expires_at > threshold:
              return cred

          async with self._client() as client:
              resp = await client.post(
                  self.TOKEN_URL,
                  data={
                      "client_id": self.client_id,
                      "client_secret": self.client_secret,
                      "refresh_token": cred.refresh_token,
                      "grant_type": "refresh_token",
                  },
              )
              resp.raise_for_status()
              data = resp.json()

          cred.access_token = data["access_token"]
          cred.refresh_token = data["refresh_token"]
          cred.token_expires_at = datetime.fromtimestamp(data["expires_at"], tz=timezone.utc)
          await db.flush()
          return cred

      async def fetch_activities(
          self, cred: ConnectorCredential, since: datetime, limit: int = 50
      ) -> list[dict]:
          """GET /athlete/activities depuis `since`. Retourne la liste brute."""
          async with self._client() as client:
              resp = await client.get(
                  f"{self.BASE_URL}/athlete/activities",
                  headers={"Authorization": f"Bearer {cred.access_token}"},
                  params={"after": int(since.timestamp()), "per_page": limit},
              )
              resp.raise_for_status()
              return list(resp.json())

      async def ingest_activities(
          self, athlete_id: uuid.UUID, activities: list[dict], db: AsyncSession
      ) -> int:
          """Convertit et upsert les activités dans run_activities. Retourne le count ingéré."""
          count = 0
          for act in activities:
              if act.get("type") not in ("Run", "Ride", "Swim"):
                  continue

              distance_km = (act.get("distance") or 0) / 1000
              duration_s = act.get("elapsed_time") or 0
              avg_hr = act.get("average_heartrate")
              max_hr_val = act.get("max_heartrate")

              # TRIMP : HR-based si disponible, sinon distance-based
              if avg_hr and max_hr_val:
                  ratio = avg_hr / max_hr_val
                  trimp = (duration_s / 60) * ratio * math.exp(1.92 * ratio)
              else:
                  trimp = distance_km * 1.0

              avg_speed = act.get("average_speed")  # m/s
              avg_pace = (1000 / avg_speed) if avg_speed else None  # sec/km

              start_date_str = act.get("start_date", "")
              activity_date = (
                  datetime.fromisoformat(start_date_str.replace("Z", "+00:00")).date()
                  if start_date_str
                  else None
              )

              values: dict = {
                  "athlete_id": athlete_id,
                  "strava_activity_id": str(act["id"]),
                  "activity_date": activity_date,
                  "activity_type": act.get("type", "Run").lower(),
                  "distance_km": distance_km or None,
                  "duration_seconds": duration_s or None,
                  "avg_pace_sec_per_km": avg_pace,
                  "avg_hr": int(avg_hr) if avg_hr else None,
                  "max_hr": int(max_hr_val) if max_hr_val else None,
                  "elevation_gain_m": act.get("total_elevation_gain"),
                  "trimp": trimp,
                  "strava_raw": act,
              }
              update_set = {k: v for k, v in values.items() if k != "strava_activity_id"}
              stmt = (
                  pg_insert(RunActivity)
                  .values(**values)
                  .on_conflict_do_update(
                      index_elements=["strava_activity_id"],
                      set_=update_set,
                  )
              )
              await db.execute(stmt)
              count += 1

          await db.flush()
          return count
  ```

- [ ] **Step 6: Run tests to verify they pass**

  ```bash
  poetry run pytest tests/test_strava_connector.py -v
  ```

  Expected: `5 passed`.

- [ ] **Step 7: Commit**

  ```bash
  git add connectors/__init__.py connectors/strava.py tests/test_strava_connector.py tests/conftest.py
  git commit -m "feat: add StravaConnector — OAuth2 + activity ingestion (TDD)"
  ```

---

## Task 3: HevyConnector (TDD)

**Files:**
- Create: `tests/test_hevy_connector.py`
- Create: `connectors/hevy.py`

- [ ] **Step 1: Write `tests/test_hevy_connector.py` (failing)**

  ```python
  """
  Tests unitaires HevyConnector — httpx.MockTransport, pas de vraies requêtes réseau.
  """

  import pytest
  import httpx
  from sqlalchemy import select

  from connectors.hevy import HevyConnector
  from models.database import LiftingSession, LiftingSet


  # ── test_validate_api_key_valid ───────────────────────────────────────────────

  async def test_validate_api_key_valid():
      def mock_handler(request: httpx.Request) -> httpx.Response:
          return httpx.Response(200, json={"workouts": [], "page_count": 0})

      connector = HevyConnector(transport=httpx.MockTransport(mock_handler))
      result = await connector.validate_api_key("valid_key")
      assert result is True


  # ── test_validate_api_key_invalid ────────────────────────────────────────────

  async def test_validate_api_key_invalid():
      def mock_handler(request: httpx.Request) -> httpx.Response:
          return httpx.Response(401, json={"error": "unauthorized"})

      connector = HevyConnector(transport=httpx.MockTransport(mock_handler))
      result = await connector.validate_api_key("bad_key")
      assert result is False


  # ── test_ingest_workouts_upsert ───────────────────────────────────────────────

  async def test_ingest_workouts_upsert(db_session, simon_athlete):
      workout = {
          "id": "workout_abc",
          "title": "Upper Body",
          "start_time": "2026-01-15T10:00:00Z",
          "end_time": "2026-01-15T11:00:00Z",
          "exercises": [
              {
                  "title": "Bench Press",
                  "sets": [
                      {"index": 0, "type": "normal", "weight_kg": 80, "reps": 8, "rpe": 7},
                  ],
              }
          ],
      }

      connector = HevyConnector()
      count1 = await connector.ingest_workouts(simon_athlete.id, [workout], db_session)
      count2 = await connector.ingest_workouts(simon_athlete.id, [workout], db_session)

      assert count1 == 1
      assert count2 == 1

      result = await db_session.execute(
          select(LiftingSession).where(LiftingSession.hevy_workout_id == "workout_abc")
      )
      sessions_in_db = result.scalars().all()
      assert len(sessions_in_db) == 1


  # ── test_weight_conversion_lbs_to_kg ─────────────────────────────────────────

  async def test_weight_conversion_lbs_to_kg(db_session, simon_athlete):
      workout = {
          "id": "workout_lbs",
          "title": "Lower Body",
          "start_time": "2026-01-16T10:00:00Z",
          "end_time": "2026-01-16T11:00:00Z",
          "exercises": [
              {
                  "title": "Squat",
                  "sets": [
                      {"index": 0, "type": "normal", "weight_lbs": 176.37, "reps": 5},
                  ],
              }
          ],
      }

      connector = HevyConnector()
      await connector.ingest_workouts(simon_athlete.id, [workout], db_session)

      result = await db_session.execute(
          select(LiftingSet)
          .join(LiftingSession)
          .where(LiftingSession.hevy_workout_id == "workout_lbs")
      )
      lifting_set = result.scalar_one()
      # 176.37 lbs × 0.453592 ≈ 80.0 kg
      assert lifting_set.weight_kg == pytest.approx(80.0, abs=0.1)


  # ── test_volume_calculated ───────────────────────────────────────────────────

  async def test_volume_calculated(db_session, simon_athlete):
      workout = {
          "id": "workout_volume",
          "title": "Volume Test",
          "start_time": "2026-01-17T10:00:00Z",
          "end_time": "2026-01-17T11:00:00Z",
          "exercises": [
              {
                  "title": "Deadlift",
                  "sets": [
                      {"index": 0, "type": "normal", "weight_kg": 80, "reps": 8},
                      {"index": 1, "type": "normal", "weight_kg": 80, "reps": 8},
                      {"index": 2, "type": "normal", "weight_kg": 80, "reps": 8},
                  ],
              }
          ],
      }

      connector = HevyConnector()
      await connector.ingest_workouts(simon_athlete.id, [workout], db_session)

      result = await db_session.execute(
          select(LiftingSession).where(LiftingSession.hevy_workout_id == "workout_volume")
      )
      session_obj = result.scalar_one()
      # 3 sets × 80 kg × 8 reps = 1920.0
      assert session_obj.total_volume_kg == pytest.approx(1920.0)
  ```

- [ ] **Step 2: Run tests to verify they fail**

  ```bash
  poetry run pytest tests/test_hevy_connector.py -v
  ```

  Expected: `ModuleNotFoundError: No module named 'connectors.hevy'`.

- [ ] **Step 3: Create `connectors/hevy.py`**

  ```python
  """
  Hevy connector — validation de clé API + ingestion workouts.
  Classes de service pures — aucune dépendance FastAPI.
  """

  import uuid
  from datetime import datetime, timezone

  import httpx
  from sqlalchemy import delete, select
  from sqlalchemy.dialects.postgresql import insert as pg_insert
  from sqlalchemy.ext.asyncio import AsyncSession

  from models.database import LiftingSession, LiftingSet, SetType


  class HevyConnector:
      BASE_URL = "https://api.hevyapp.com"

      def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
          self._transport = transport

      def _client(self) -> httpx.AsyncClient:
          """Crée un AsyncClient — transport injectable pour les tests."""
          return httpx.AsyncClient(transport=self._transport)

      async def validate_api_key(self, api_key: str) -> bool:
          """GET /v1/workouts?page=1&pageSize=1 — 200 = valide, 401 = invalide."""
          async with self._client() as client:
              resp = await client.get(
                  f"{self.BASE_URL}/v1/workouts",
                  headers={"api-key": api_key},
                  params={"page": 1, "pageSize": 1},
              )
              return resp.status_code == 200

      async def fetch_workouts(
          self, api_key: str, page: int = 1, page_size: int = 10
      ) -> list[dict]:
          """GET /v1/workouts — retourne les workouts paginés."""
          async with self._client() as client:
              resp = await client.get(
                  f"{self.BASE_URL}/v1/workouts",
                  headers={"api-key": api_key},
                  params={"page": page, "pageSize": page_size},
              )
              resp.raise_for_status()
              return list(resp.json().get("workouts", []))

      async def fetch_all_since(self, api_key: str, since: datetime) -> list[dict]:
          """Pagine jusqu'à ce que updated_at < since ou page vide."""
          all_workouts: list[dict] = []
          page = 1
          while True:
              workouts = await self.fetch_workouts(api_key=api_key, page=page, page_size=10)
              if not workouts:
                  break
              done = False
              for w in workouts:
                  updated_at_str = w.get("updated_at", "")
                  if updated_at_str:
                      updated_at = datetime.fromisoformat(
                          updated_at_str.replace("Z", "+00:00")
                      )
                      if updated_at.replace(tzinfo=timezone.utc) < since:
                          done = True
                          break
                  all_workouts.append(w)
              if done:
                  break
              page += 1
          return all_workouts

      async def ingest_workouts(
          self, athlete_id: uuid.UUID, workouts: list[dict], db: AsyncSession
      ) -> int:
          """Convertit et upsert les workouts dans lifting_sessions + lifting_sets."""
          count = 0
          for w in workouts:
              start_dt = (
                  datetime.fromisoformat(w["start_time"].replace("Z", "+00:00"))
                  if w.get("start_time")
                  else None
              )
              end_dt = (
                  datetime.fromisoformat(w["end_time"].replace("Z", "+00:00"))
                  if w.get("end_time")
                  else None
              )

              duration_minutes = None
              if start_dt and end_dt:
                  duration_minutes = int((end_dt - start_dt).total_seconds() / 60)

              exercises = w.get("exercises", [])
              all_sets = [s for ex in exercises for s in ex.get("sets", [])]

              total_sets = len(all_sets)
              total_volume_kg = sum(
                  (
                      s.get("weight_kg")
                      if s.get("weight_kg") is not None
                      else (s.get("weight_lbs", 0) * 0.453592)
                  )
                  * (s.get("reps") or 0)
                  for s in all_sets
              )

              session_values: dict = {
                  "athlete_id": athlete_id,
                  "hevy_workout_id": str(w["id"]),
                  "hevy_title": w.get("title", ""),
                  "session_date": start_dt.date() if start_dt else None,
                  "start_time": start_dt,
                  "end_time": end_dt,
                  "duration_minutes": duration_minutes,
                  "source": "hevy_api",
                  "total_volume_kg": total_volume_kg,
                  "total_sets": total_sets,
              }
              update_set = {k: v for k, v in session_values.items() if k != "hevy_workout_id"}

              # Upsert LiftingSession sur hevy_workout_id
              stmt = (
                  pg_insert(LiftingSession)
                  .values(**session_values)
                  .on_conflict_do_update(
                      index_elements=["hevy_workout_id"],
                      set_=update_set,
                  )
                  .returning(LiftingSession.id)
              )
              result = await db.execute(stmt)
              session_id = result.scalar_one()

              # Supprime et recrée les sets (garantit la cohérence)
              await db.execute(
                  delete(LiftingSet).where(LiftingSet.session_id == session_id)
              )

              for ex in exercises:
                  for i, s in enumerate(ex.get("sets", [])):
                      weight_kg = s.get("weight_kg")
                      if weight_kg is None and s.get("weight_lbs") is not None:
                          weight_kg = s["weight_lbs"] * 0.453592

                      set_type_str = s.get("type", "normal")
                      try:
                          set_type = SetType(set_type_str)
                      except ValueError:
                          set_type = SetType.normal

                      db.add(
                          LiftingSet(
                              session_id=session_id,
                              exercise_title=ex.get("title", ""),
                              set_index=i,
                              set_type=set_type,
                              weight_kg=weight_kg,
                              reps=s.get("reps"),
                              rpe=s.get("rpe"),
                          )
                      )

              count += 1

          await db.flush()
          return count
  ```

- [ ] **Step 4: Run tests to verify they pass**

  ```bash
  poetry run pytest tests/test_hevy_connector.py -v
  ```

  Expected: `5 passed`.

- [ ] **Step 5: Commit**

  ```bash
  git add connectors/hevy.py tests/test_hevy_connector.py
  git commit -m "feat: add HevyConnector — API key validation + workout ingestion (TDD)"
  ```

---

## Task 4: FastAPI router + app (TDD)

**Files:**
- Create: `api/__init__.py`
- Create: `api/v1/__init__.py`
- Create: `tests/test_connector_routes.py`
- Create: `api/v1/connectors.py`
- Create: `api/main.py`
- Modify: `CLAUDE.md` (update session status at end)

- [ ] **Step 1: Create package markers**

  Create `api/__init__.py` — empty file.
  Create `api/v1/__init__.py` — empty file.

- [ ] **Step 2: Write `tests/test_connector_routes.py` (failing)**

  ```python
  """
  Tests des routes FastAPI connecteurs.
  Utilise httpx.AsyncClient avec ASGITransport pour rester in-process.
  La session DB de test est injectée via override de la dépendance get_db.
  """

  from unittest.mock import AsyncMock, patch

  import pytest
  import pytest_asyncio
  from httpx import ASGITransport, AsyncClient
  from sqlalchemy.ext.asyncio import AsyncSession

  from api.main import app
  from models.db_session import get_db


  @pytest_asyncio.fixture
  async def api_client(db_session: AsyncSession):
      """AsyncClient avec override DB — isole les tests de la vraie DB."""

      async def override_get_db():
          yield db_session

      app.dependency_overrides[get_db] = override_get_db
      async with AsyncClient(
          transport=ASGITransport(app=app), base_url="http://test"
      ) as client:
          yield client
      app.dependency_overrides.clear()


  # ── test_strava_auth_returns_url ──────────────────────────────────────────────

  async def test_strava_auth_returns_url(api_client):
      response = await api_client.get("/api/v1/connectors/strava/auth")
      assert response.status_code == 200
      data = response.json()
      assert "authorization_url" in data
      assert "strava.com" in data["authorization_url"]
      assert "scope=activity:read_all" in data["authorization_url"]


  # ── test_hevy_connect_stores_credential ──────────────────────────────────────

  async def test_hevy_connect_stores_credential(api_client, simon_athlete, db_session):
      with patch(
          "api.v1.connectors._hevy.validate_api_key",
          new=AsyncMock(return_value=True),
      ):
          response = await api_client.post(
              "/api/v1/connectors/hevy/connect",
              params={"athlete_id": str(simon_athlete.id)},
              json={"api_key": "my_hevy_key"},
          )

      assert response.status_code == 200
      assert response.json()["connected"] is True


  # ── test_hevy_status_not_connected ────────────────────────────────────────────

  async def test_hevy_status_not_connected(api_client, simon_athlete):
      response = await api_client.get(
          "/api/v1/connectors/hevy/status",
          params={"athlete_id": str(simon_athlete.id)},
      )
      assert response.status_code == 200
      data = response.json()
      assert data["connected"] is False
  ```

- [ ] **Step 3: Run tests to verify they fail**

  ```bash
  poetry run pytest tests/test_connector_routes.py -v
  ```

  Expected: `ModuleNotFoundError: No module named 'api.main'`.

- [ ] **Step 4: Create `api/v1/connectors.py`**

  ```python
  """
  FastAPI router — gestion des credentials connecteurs.
  Strava OAuth2 + Hevy API key CRUD.
  auth: athlete_id en query param (JWT en S11).
  """

  import uuid
  from datetime import datetime, timedelta, timezone

  from fastapi import APIRouter, Body, Depends, HTTPException, Query
  from pydantic import BaseModel
  from sqlalchemy import select
  from sqlalchemy.dialects.postgresql import insert as pg_insert
  from sqlalchemy.ext.asyncio import AsyncSession

  from connectors.hevy import HevyConnector
  from connectors.strava import StravaConnector
  from models.database import Athlete, ConnectorCredential
  from models.db_session import get_db

  router = APIRouter()
  _strava = StravaConnector()
  _hevy = HevyConnector()


  # ── Helpers ───────────────────────────────────────────────────────────────────

  async def _get_athlete_or_404(athlete_id: uuid.UUID, db: AsyncSession) -> Athlete:
      result = await db.execute(select(Athlete).where(Athlete.id == athlete_id))
      athlete = result.scalar_one_or_none()
      if athlete is None:
          raise HTTPException(status_code=404, detail=f"Athlete {athlete_id} not found")
      return athlete


  async def _get_credential(
      athlete_id: uuid.UUID, provider: str, db: AsyncSession
  ) -> ConnectorCredential | None:
      result = await db.execute(
          select(ConnectorCredential).where(
              ConnectorCredential.athlete_id == athlete_id,
              ConnectorCredential.provider == provider,
          )
      )
      return result.scalar_one_or_none()


  # ── Strava ────────────────────────────────────────────────────────────────────

  @router.get("/strava/auth")
  async def strava_auth() -> dict:
      return {"authorization_url": _strava.get_authorization_url()}


  @router.get("/strava/callback")
  async def strava_callback(
      code: str = Query(...),
      athlete_id: uuid.UUID = Query(...),
      db: AsyncSession = Depends(get_db),
  ) -> dict:
      await _get_athlete_or_404(athlete_id, db)
      cred = await _strava.exchange_code(code, athlete_id, db)
      return {"connected": True, "strava_athlete_id": cred.external_athlete_id}


  @router.post("/strava/sync")
  async def strava_sync(
      athlete_id: uuid.UUID = Query(...),
      days: int = Query(default=30),
      db: AsyncSession = Depends(get_db),
  ) -> dict:
      await _get_athlete_or_404(athlete_id, db)
      cred = await _get_credential(athlete_id, "strava", db)
      if cred is None:
          raise HTTPException(status_code=404, detail="Strava not connected for this athlete")
      cred = await _strava.refresh_token_if_expired(cred, db)
      since = datetime.now(tz=timezone.utc) - timedelta(days=days)
      activities = await _strava.fetch_activities(cred, since)
      synced = await _strava.ingest_activities(athlete_id, activities, db)
      return {"synced": synced}


  @router.get("/strava/status")
  async def strava_status(
      athlete_id: uuid.UUID = Query(...),
      db: AsyncSession = Depends(get_db),
  ) -> dict:
      await _get_athlete_or_404(athlete_id, db)
      cred = await _get_credential(athlete_id, "strava", db)
      if cred is None:
          return {"connected": False, "last_sync": None, "token_expires_at": None}
      return {
          "connected": True,
          "last_sync": cred.updated_at.isoformat() if cred.updated_at else None,
          "token_expires_at": (
              cred.token_expires_at.isoformat() if cred.token_expires_at else None
          ),
      }


  @router.delete("/strava/disconnect")
  async def strava_disconnect(
      athlete_id: uuid.UUID = Query(...),
      db: AsyncSession = Depends(get_db),
  ) -> dict:
      await _get_athlete_or_404(athlete_id, db)
      cred = await _get_credential(athlete_id, "strava", db)
      if cred is not None:
          await db.delete(cred)
      return {"disconnected": True}


  # ── Hevy ──────────────────────────────────────────────────────────────────────

  class HevyConnectBody(BaseModel):
      api_key: str


  @router.post("/hevy/connect")
  async def hevy_connect(
      athlete_id: uuid.UUID = Query(...),
      body: HevyConnectBody = Body(...),
      db: AsyncSession = Depends(get_db),
  ) -> dict:
      await _get_athlete_or_404(athlete_id, db)
      if not await _hevy.validate_api_key(body.api_key):
          raise HTTPException(status_code=400, detail="Invalid Hevy API key")
      stmt = (
          pg_insert(ConnectorCredential)
          .values(athlete_id=athlete_id, provider="hevy", api_key=body.api_key)
          .on_conflict_do_update(
              index_elements=["athlete_id", "provider"],
              set_={"api_key": body.api_key},
          )
      )
      await db.execute(stmt)
      return {"connected": True}


  @router.post("/hevy/sync")
  async def hevy_sync(
      athlete_id: uuid.UUID = Query(...),
      days: int = Query(default=30),
      db: AsyncSession = Depends(get_db),
  ) -> dict:
      await _get_athlete_or_404(athlete_id, db)
      cred = await _get_credential(athlete_id, "hevy", db)
      if cred is None:
          raise HTTPException(status_code=404, detail="Hevy not connected for this athlete")
      since = datetime.now(tz=timezone.utc) - timedelta(days=days)
      workouts = await _hevy.fetch_all_since(cred.api_key, since)
      synced = await _hevy.ingest_workouts(athlete_id, workouts, db)
      return {"synced": synced}


  @router.get("/hevy/status")
  async def hevy_status(
      athlete_id: uuid.UUID = Query(...),
      db: AsyncSession = Depends(get_db),
  ) -> dict:
      await _get_athlete_or_404(athlete_id, db)
      cred = await _get_credential(athlete_id, "hevy", db)
      if cred is None:
          return {"connected": False, "last_sync": None}
      return {
          "connected": True,
          "last_sync": cred.updated_at.isoformat() if cred.updated_at else None,
      }


  @router.delete("/hevy/disconnect")
  async def hevy_disconnect(
      athlete_id: uuid.UUID = Query(...),
      db: AsyncSession = Depends(get_db),
  ) -> dict:
      await _get_athlete_or_404(athlete_id, db)
      cred = await _get_credential(athlete_id, "hevy", db)
      if cred is not None:
          await db.delete(cred)
      return {"disconnected": True}
  ```

- [ ] **Step 5: Create `api/main.py`**

  ```python
  """
  FastAPI application stub — Resilio+
  S11 complétera : auth JWT, middleware CORS, autres routers.
  """

  from fastapi import FastAPI

  from api.v1.connectors import router as connectors_router

  app = FastAPI(title="Resilio+", version="0.1.0")

  app.include_router(
      connectors_router,
      prefix="/api/v1/connectors",
      tags=["connectors"],
  )
  ```

- [ ] **Step 6: Run connector route tests to verify they pass**

  ```bash
  poetry run pytest tests/test_connector_routes.py -v
  ```

  Expected: `3 passed`.

- [ ] **Step 7: Run the full test suite**

  ```bash
  poetry run pytest tests/ -v
  ```

  Expected: `42 passed` (29 S1+S2 + 13 S3).

  If any S1+S2 tests fail, diagnose before continuing — never ignore regressions.

- [ ] **Step 8: Run ruff**

  ```bash
  poetry run ruff check .
  ```

  Expected: no violations. If there are violations, fix them before committing.

- [ ] **Step 9: Update `CLAUDE.md` — mark S3 complete**

  In `CLAUDE.md`, change the S3 row:

  ```markdown
  | **S3** | Connecteurs | Strava OAuth + Hevy (API ou CSV fallback) | ⬜ À FAIRE |
  ```

  to:

  ```markdown
  | **S3** | Connecteurs | Strava OAuth + Hevy (API ou CSV fallback) | ✅ FAIT |
  ```

  Also update the `STRUCTURE DU REPO` section to reflect the new files:

  - Under `connectors/`, change `← ⬜ S3-S4` to `← ✅ S3 — StravaConnector + HevyConnector`
  - Under `api/`, change `(api/main.py → S11)` to `← ✅ S3 — FastAPI stub + connectors router`

- [ ] **Step 10: Final commit**

  ```bash
  git add api/__init__.py api/v1/__init__.py api/v1/connectors.py api/main.py \
          tests/test_connector_routes.py CLAUDE.md
  git commit -m "feat: add connector routes (Strava OAuth2 + Hevy) + FastAPI app stub (TDD)"
  ```

---

## Verification post-S3

```bash
# Suite complète — 42 tests
poetry run pytest tests/ -v
# Expected: 42 passed

# Linter
poetry run ruff check .
# Expected: no violations

# Migration appliquée
poetry run alembic current
# Expected: <hash_s3> (head)

# Démarrage optionnel
docker compose up db -d
poetry run uvicorn api.main:app --reload
# Test: GET http://localhost:8000/api/v1/connectors/strava/auth
# → { "authorization_url": "https://www.strava.com/oauth/authorize?client_id=215637&..." }
```

---

## Known edge cases

- `httpx.MockTransport` takes a **sync** handler even for async clients — this is correct and expected.
- `on_conflict_do_update(index_elements=["athlete_id", "provider"])` requires the `UniqueConstraint` from Task 1 to be applied to the DB before connector tests run — run `alembic upgrade head` first.
- `on_conflict_do_update(index_elements=["hevy_workout_id"])` requires `unique=True` on `LiftingSession.hevy_workout_id` — also covered by the Task 1 migration.
- The `db_session` test fixture does a rollback at the end of each test. In route tests, `get_db` is overridden to yield the same `db_session` — changes are visible within the test but rolled back after.
