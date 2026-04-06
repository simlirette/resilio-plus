# Session 4 — Connecteurs 2 (Apple Health + GPX/FIT + Food Search) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add four new data connectors — Apple Health (JSON → FatigueSnapshot), GPX/FIT file upload (→ RunActivity), and USDA/Open Food Facts food search (→ JSON response) — plus three new FastAPI router files.

**Architecture:** Each connector is a pure service class in `connectors/` with injectable transport for testability. Three new FastAPI routers mount under `/api/v1/connectors/`. A minimal Alembic migration adds the unique constraint needed for Apple Health upserts. No new tables — all data writes to existing `fatigue_snapshots` and `run_activities` tables.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0 async, PostgreSQL, httpx (MockTransport for tests), fitparse (FIT binary parsing), xml.etree.ElementTree (GPX parsing), pytest-asyncio, Alembic.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `pyproject.toml` | Modify | Add `fitparse` dependency |
| `models/database.py` | Modify | Add `UniqueConstraint("athlete_id", "snapshot_date")` to `FatigueSnapshot` |
| `alembic/versions/<hash>_add_fatigue_snapshot_unique_athlete_date.py` | Create (generated) | DB migration for the unique constraint |
| `connectors/apple_health.py` | Create | `AppleHealthConnector` — JSON → FatigueSnapshot upsert |
| `connectors/gpx.py` | Create | `GpxConnector` — GPX XML → RunActivity |
| `connectors/fit.py` | Create | `FitConnector` — FIT binary → RunActivity |
| `connectors/food_search.py` | Create | `FoodSearchConnector` — USDA + Open Food Facts |
| `api/v1/apple_health.py` | Create | Router `POST /apple-health/upload` |
| `api/v1/files.py` | Create | Router `POST /files/gpx`, `POST /files/fit` |
| `api/v1/food.py` | Create | Router `GET /food/search`, `GET /food/barcode/{barcode}` |
| `api/main.py` | Modify | Mount 3 new routers |
| `tests/test_apple_health_connector.py` | Create | 3 unit tests |
| `tests/test_gpx_connector.py` | Create | 3 unit tests |
| `tests/test_fit_connector.py` | Create | 2 unit tests (mock fitparse) |
| `tests/test_food_search_connector.py` | Create | 3 unit tests (MockTransport) |
| `tests/test_file_routes.py` | Create | 3 route tests |

---

## Task 1: Alembic Migration + fitparse Dependency

**Files:**
- Modify: `pyproject.toml`
- Modify: `models/database.py` (lines 189–229, `FatigueSnapshot` class)
- Create (generated): `alembic/versions/<hash>_add_fatigue_snapshot_unique_athlete_date.py`

- [ ] **Step 1: Add fitparse to pyproject.toml**

Open `pyproject.toml`. In `[tool.poetry.dependencies]`, add after the `python-dateutil` line:

```toml
fitparse = "^1.2.0"
```

- [ ] **Step 2: Install fitparse**

```bash
/c/Users/simon/AppData/Local/Python/pythoncore-3.14-64/Scripts/poetry.exe add fitparse
```

Expected: `fitparse` installed successfully.

- [ ] **Step 3: Add UniqueConstraint to FatigueSnapshot**

In `models/database.py`, locate the `FatigueSnapshot` class (line ~189). Add a `__table_args__` attribute **before** the `created_at` column:

```python
    # Relation
    athlete: Mapped["Athlete"] = relationship(back_populates="fatigue_snapshots")
```

becomes:

```python
    __table_args__ = (UniqueConstraint("athlete_id", "snapshot_date"),)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relation
    athlete: Mapped["Athlete"] = relationship(back_populates="fatigue_snapshots")
```

`UniqueConstraint` is already imported at the top of the file.

- [ ] **Step 4: Generate the Alembic migration**

```bash
/c/Users/simon/AppData/Local/Python/pythoncore-3.14-64/Scripts/poetry.exe run alembic revision --autogenerate -m "add fatigue snapshot unique athlete date"
```

Expected: New file created in `alembic/versions/`. Open it and verify it contains:
- `op.create_unique_constraint(...)` on `fatigue_snapshots` for `["athlete_id", "snapshot_date"]`
- A corresponding `op.drop_constraint(...)` in `downgrade()`

- [ ] **Step 5: Apply the migration**

```bash
docker compose up db -d
/c/Users/simon/AppData/Local/Python/pythoncore-3.14-64/Scripts/poetry.exe run alembic upgrade head
```

Expected: `Running upgrade ... -> <hash> (head)`.

- [ ] **Step 6: Verify migration applied**

```bash
/c/Users/simon/AppData/Local/Python/pythoncore-3.14-64/Scripts/poetry.exe run alembic current
```

Expected: `<new hash> (head)`.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml poetry.lock models/database.py alembic/versions/
git commit -m "feat: add fitparse dep + unique constraint on fatigue_snapshots(athlete_id, snapshot_date)"
```

---

## Task 2: AppleHealthConnector + Tests

**Files:**
- Create: `connectors/apple_health.py`
- Create: `tests/test_apple_health_connector.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_apple_health_connector.py`:

```python
"""
Tests unitaires AppleHealthConnector.
Écrit dans fatigue_snapshots via upsert sur (athlete_id, snapshot_date).
"""

from datetime import date

import pytest
from sqlalchemy import select

from connectors.apple_health import AppleHealthConnector
from models.database import FatigueSnapshot


# ── test_ingest_snapshot_creates_fatigue_snapshot ────────────────────────────

async def test_ingest_snapshot_creates_fatigue_snapshot(db_session, simon_athlete):
    connector = AppleHealthConnector()
    data = {
        "snapshot_date": "2026-04-01",
        "hrv_rmssd": 62.4,
        "hr_rest": 54,
        "sleep_hours": 7.5,
        "sleep_quality_subjective": 8,
    }

    snapshot = await connector.ingest_snapshot(simon_athlete.id, data, db_session)

    assert snapshot.athlete_id == simon_athlete.id
    assert snapshot.snapshot_date == date(2026, 4, 1)
    assert snapshot.hrv_rmssd == pytest.approx(62.4)
    assert snapshot.hr_rest == 54
    assert snapshot.sleep_hours == pytest.approx(7.5)
    assert snapshot.sleep_quality_subjective == 8


# ── test_ingest_snapshot_partial_data ────────────────────────────────────────

async def test_ingest_snapshot_partial_data(db_session, simon_athlete):
    connector = AppleHealthConnector()
    data = {
        "snapshot_date": "2026-04-02",
        "sleep_hours": 6.8,
    }

    snapshot = await connector.ingest_snapshot(simon_athlete.id, data, db_session)

    assert snapshot.sleep_hours == pytest.approx(6.8)
    assert snapshot.hrv_rmssd is None
    assert snapshot.hr_rest is None
    assert snapshot.sleep_quality_subjective is None


# ── test_ingest_snapshot_upsert ──────────────────────────────────────────────

async def test_ingest_snapshot_upsert(db_session, simon_athlete):
    connector = AppleHealthConnector()
    target_date = "2026-04-03"

    # First ingestion
    await connector.ingest_snapshot(
        simon_athlete.id,
        {"snapshot_date": target_date, "hrv_rmssd": 55.0},
        db_session,
    )

    # Second ingestion — updates hrv_rmssd, keeps sleep_hours intact
    await connector.ingest_snapshot(
        simon_athlete.id,
        {"snapshot_date": target_date, "hrv_rmssd": 60.0, "sleep_hours": 7.0},
        db_session,
    )

    result = await db_session.execute(
        select(FatigueSnapshot).where(
            FatigueSnapshot.athlete_id == simon_athlete.id,
            FatigueSnapshot.snapshot_date == date(2026, 4, 3),
        )
    )
    rows = result.scalars().all()
    assert len(rows) == 1  # No duplicates
    assert rows[0].hrv_rmssd == pytest.approx(60.0)
    assert rows[0].sleep_hours == pytest.approx(7.0)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
/c/Users/simon/AppData/Local/Python/pythoncore-3.14-64/Scripts/poetry.exe run pytest tests/test_apple_health_connector.py -v
```

Expected: 3 failures with `ModuleNotFoundError: No module named 'connectors.apple_health'`.

- [ ] **Step 3: Implement AppleHealthConnector**

Create `connectors/apple_health.py`:

```python
"""
Apple Health connector — JSON structuré → FatigueSnapshot.
Upsert sur (athlete_id, snapshot_date) — un seul snapshot par athlète par jour.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import FatigueSnapshot

# Champs scalaires Apple Health → FatigueSnapshot
_FIELD_MAP: dict[str, type] = {
    "hrv_rmssd": float,
    "hr_rest": int,
    "sleep_hours": float,
    "sleep_quality_subjective": int,
}


class AppleHealthConnector:
    async def ingest_snapshot(
        self,
        athlete_id: uuid.UUID,
        data: dict,
        db: AsyncSession,
    ) -> FatigueSnapshot:
        """
        Parse les données Apple Health et upsert un FatigueSnapshot.
        Seuls les champs présents et non-None dans `data` sont mis à jour.
        """
        snapshot_date_raw = data.get("snapshot_date")
        if snapshot_date_raw is None:
            raise ValueError("snapshot_date is required")

        if isinstance(snapshot_date_raw, str):
            snapshot_date = date.fromisoformat(snapshot_date_raw)
        elif isinstance(snapshot_date_raw, datetime):
            snapshot_date = snapshot_date_raw.date()
        else:
            snapshot_date = snapshot_date_raw  # assume date object

        # Base values required for INSERT (fatigue_by_muscle is NOT NULL in DB)
        insert_values: dict = {
            "athlete_id": athlete_id,
            "snapshot_date": snapshot_date,
            "fatigue_by_muscle": {},
        }

        # Add only provided non-None Apple Health fields
        for field, cast in _FIELD_MAP.items():
            if field in data and data[field] is not None:
                insert_values[field] = cast(data[field])

        # On conflict: update only the Apple Health fields (not athlete_id,
        # snapshot_date, or fatigue_by_muscle — preserve ACWR calculations)
        update_set = {
            k: v for k, v in insert_values.items()
            if k not in ("athlete_id", "snapshot_date", "fatigue_by_muscle")
        }

        stmt = (
            pg_insert(FatigueSnapshot)
            .values(**insert_values)
            .on_conflict_do_update(
                index_elements=["athlete_id", "snapshot_date"],
                set_=update_set,
            )
        )
        await db.execute(stmt)
        await db.flush()

        result = await db.execute(
            select(FatigueSnapshot).where(
                FatigueSnapshot.athlete_id == athlete_id,
                FatigueSnapshot.snapshot_date == snapshot_date,
            )
        )
        return result.scalar_one()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
/c/Users/simon/AppData/Local/Python/pythoncore-3.14-64/Scripts/poetry.exe run pytest tests/test_apple_health_connector.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Run full suite to check no regressions**

```bash
/c/Users/simon/AppData/Local/Python/pythoncore-3.14-64/Scripts/poetry.exe run pytest tests/ -v
```

Expected: All existing tests + 3 new = 45 passed.

- [ ] **Step 6: Commit**

```bash
git add connectors/apple_health.py tests/test_apple_health_connector.py
git commit -m "feat: add AppleHealthConnector — JSON upload to FatigueSnapshot upsert"
```

---

## Task 3: GpxConnector + Tests

**Files:**
- Create: `connectors/gpx.py`
- Create: `tests/test_gpx_connector.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_gpx_connector.py`:

```python
"""
Tests unitaires GpxConnector.
Parse le XML GPX et insère dans run_activities.
"""

import pytest
from sqlalchemy import select

from connectors.gpx import GpxConnector
from models.database import RunActivity

# Minimal GPX avec 3 trackpoints — durée = 1200s, élévation = 5m de gain
GPX_SAMPLE = b"""<?xml version="1.0"?>
<gpx xmlns="http://www.topografix.com/GPX/1/1" version="1.1">
  <trk>
    <trkseg>
      <trkpt lat="48.8566" lon="2.3522">
        <ele>30.0</ele>
        <time>2026-04-01T08:00:00Z</time>
      </trkpt>
      <trkpt lat="48.8570" lon="2.3530">
        <ele>32.0</ele>
        <time>2026-04-01T08:10:00Z</time>
      </trkpt>
      <trkpt lat="48.8580" lon="2.3545">
        <ele>35.0</ele>
        <time>2026-04-01T08:20:00Z</time>
      </trkpt>
    </trkseg>
  </trk>
</gpx>"""


# ── test_parse_gpx_extracts_distance ─────────────────────────────────────────

def test_parse_gpx_extracts_distance():
    connector = GpxConnector()
    result = connector.parse_gpx(GPX_SAMPLE)

    # 3 points in Paris — distance should be ~0.1-0.5 km
    assert result["distance_km"] is not None
    assert 0.05 < result["distance_km"] < 2.0


# ── test_parse_gpx_extracts_duration ─────────────────────────────────────────

def test_parse_gpx_extracts_duration():
    connector = GpxConnector()
    result = connector.parse_gpx(GPX_SAMPLE)

    # 08:20 - 08:00 = 1200 seconds
    assert result["duration_seconds"] == 1200
    assert result["activity_date"].isoformat() == "2026-04-01"


# ── test_ingest_gpx_creates_run_activity ─────────────────────────────────────

async def test_ingest_gpx_creates_run_activity(db_session, simon_athlete):
    connector = GpxConnector()
    run = await connector.ingest_gpx(simon_athlete.id, GPX_SAMPLE, db_session)

    assert run.athlete_id == simon_athlete.id
    assert run.activity_type == "Run"
    assert run.strava_raw == {"source": "gpx"}
    assert run.distance_km is not None
    assert run.duration_seconds == 1200

    # Verify stored in DB
    result = await db_session.execute(
        select(RunActivity).where(RunActivity.id == run.id)
    )
    stored = result.scalar_one()
    assert stored.activity_type == "Run"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
/c/Users/simon/AppData/Local/Python/pythoncore-3.14-64/Scripts/poetry.exe run pytest tests/test_gpx_connector.py -v
```

Expected: 3 failures with `ModuleNotFoundError: No module named 'connectors.gpx'`.

- [ ] **Step 3: Implement GpxConnector**

Create `connectors/gpx.py`:

```python
"""
GPX connector — fichier XML GPS → RunActivity.
Chaque upload crée une nouvelle RunActivity (pas de déduplication).
"""

import math
import uuid
import xml.etree.ElementTree as ET
from datetime import date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from models.database import RunActivity

_GPX_NS = "http://www.topografix.com/GPX/1/1"


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance en km entre deux points GPS via formule haversine."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.asin(math.sqrt(a))


class GpxConnector:
    def parse_gpx(self, content: bytes) -> dict:
        """
        Parse le XML GPX et retourne les données d'activité.
        Retourne : activity_date, distance_km, duration_seconds,
                   avg_pace_sec_per_km, elevation_gain_m.
        """
        root = ET.fromstring(content)
        ns = {"g": _GPX_NS}

        trackpoints = root.findall(".//g:trkpt", ns)
        if not trackpoints:
            raise ValueError("GPX file contains no trackpoints")

        lats = [float(tp.get("lat", 0)) for tp in trackpoints]
        lons = [float(tp.get("lon", 0)) for tp in trackpoints]
        eles = []
        for tp in trackpoints:
            ele_el = tp.find("g:ele", ns)
            eles.append(float(ele_el.text) if ele_el is not None else None)

        times = []
        for tp in trackpoints:
            time_el = tp.find("g:time", ns)
            if time_el is not None:
                times.append(
                    datetime.fromisoformat(time_el.text.replace("Z", "+00:00"))
                )

        # Distance via haversine
        distance_km = sum(
            _haversine_km(lats[i], lons[i], lats[i + 1], lons[i + 1])
            for i in range(len(lats) - 1)
        )

        # Duration
        duration_seconds: int | None = None
        activity_date: date | None = None
        if len(times) >= 2:
            duration_seconds = int((times[-1] - times[0]).total_seconds())
            activity_date = times[0].date()

        # Avg pace
        avg_pace = (duration_seconds / distance_km) if (distance_km > 0 and duration_seconds) else None

        # Elevation gain (sum of positive increments)
        elevation_gain_m: float | None = None
        valid_eles = [e for e in eles if e is not None]
        if len(valid_eles) >= 2:
            elevation_gain_m = sum(
                max(0.0, valid_eles[i + 1] - valid_eles[i])
                for i in range(len(valid_eles) - 1)
            )

        return {
            "activity_date": activity_date,
            "distance_km": distance_km if distance_km > 0 else None,
            "duration_seconds": duration_seconds,
            "avg_pace_sec_per_km": avg_pace,
            "elevation_gain_m": elevation_gain_m,
        }

    async def ingest_gpx(
        self,
        athlete_id: uuid.UUID,
        content: bytes,
        db: AsyncSession,
    ) -> RunActivity:
        """
        Parse le GPX et insère une RunActivity.
        Pas d'upsert — chaque upload GPX crée une nouvelle activité.
        """
        parsed = self.parse_gpx(content)

        distance_km = parsed.get("distance_km") or 0.0
        duration_s = parsed.get("duration_seconds") or 0

        # TRIMP fallback (pas de HR dans GPX)
        trimp = distance_km * 1.0

        run = RunActivity(
            athlete_id=athlete_id,
            activity_date=parsed["activity_date"],
            activity_type="Run",
            distance_km=parsed.get("distance_km"),
            duration_seconds=parsed.get("duration_seconds"),
            avg_pace_sec_per_km=parsed.get("avg_pace_sec_per_km"),
            elevation_gain_m=parsed.get("elevation_gain_m"),
            trimp=trimp,
            strava_raw={"source": "gpx"},
        )
        db.add(run)
        await db.flush()
        return run
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
/c/Users/simon/AppData/Local/Python/pythoncore-3.14-64/Scripts/poetry.exe run pytest tests/test_gpx_connector.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add connectors/gpx.py tests/test_gpx_connector.py
git commit -m "feat: add GpxConnector — GPX XML file upload to RunActivity"
```

---

## Task 4: FitConnector + Tests

**Files:**
- Create: `connectors/fit.py`
- Create: `tests/test_fit_connector.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_fit_connector.py`:

```python
"""
Tests unitaires FitConnector.
Parse les fichiers FIT binaires Garmin/Polar → RunActivity.
fitparse.FitFile est mocké pour éviter la dépendance à de vrais fichiers FIT.
"""

import math
from datetime import UTC, date, datetime
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import select

from connectors.fit import FitConnector
from models.database import RunActivity


# ── test_parse_fit_session_message ────────────────────────────────────────────

def test_parse_fit_session_message():
    connector = FitConnector()

    # Mock FitFile qui retourne un message session
    mock_message = MagicMock()
    mock_message.get_value.side_effect = lambda key: {
        "start_time": datetime(2026, 4, 1, 8, 0, 0, tzinfo=UTC),
        "total_distance": 10000.0,   # mètres
        "total_elapsed_time": 3600.0,  # secondes
        "avg_heart_rate": 155,
        "max_heart_rate": 180,
        "total_ascent": 120.0,        # mètres
        "sport": "running",
    }.get(key)

    mock_fitfile = MagicMock()
    mock_fitfile.get_messages.return_value = [mock_message]

    with patch("connectors.fit.FitFile", return_value=mock_fitfile):
        result = connector.parse_fit(b"fake_fit_bytes")

    assert result["distance_km"] == pytest.approx(10.0)
    assert result["duration_seconds"] == 3600
    assert result["avg_hr"] == 155
    assert result["max_hr"] == 180
    assert result["elevation_gain_m"] == pytest.approx(120.0)
    assert result["activity_date"] == date(2026, 4, 1)
    assert result["activity_type"] == "running"


# ── test_ingest_fit_creates_run_activity ──────────────────────────────────────

async def test_ingest_fit_creates_run_activity(db_session, simon_athlete):
    connector = FitConnector()
    parsed = {
        "activity_date": date(2026, 4, 1),
        "activity_type": "running",
        "distance_km": 10.0,
        "duration_seconds": 3600,
        "avg_pace_sec_per_km": 360.0,
        "avg_hr": 155,
        "max_hr": 180,
        "elevation_gain_m": 120.0,
    }

    with patch.object(connector, "parse_fit", return_value=parsed):
        run = await connector.ingest_fit(simon_athlete.id, b"fake", db_session)

    assert run.athlete_id == simon_athlete.id
    assert run.distance_km == pytest.approx(10.0)
    assert run.activity_type == "running"
    assert run.strava_raw == {"source": "fit"}
    # TRIMP: HR-based since avg_hr and max_hr are present
    expected_ratio = 155 / 180
    expected_trimp = (3600 / 60) * expected_ratio * math.exp(1.92 * expected_ratio)
    assert run.trimp == pytest.approx(expected_trimp, rel=1e-3)

    # Verify stored in DB
    result = await db_session.execute(
        select(RunActivity).where(RunActivity.id == run.id)
    )
    stored = result.scalar_one()
    assert stored.strava_raw == {"source": "fit"}
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
/c/Users/simon/AppData/Local/Python/pythoncore-3.14-64/Scripts/poetry.exe run pytest tests/test_fit_connector.py -v
```

Expected: 2 failures with `ModuleNotFoundError: No module named 'connectors.fit'`.

- [ ] **Step 3: Implement FitConnector**

Create `connectors/fit.py`:

```python
"""
FIT connector — fichier binaire Garmin/Polar → RunActivity.
Utilise fitparse pour parser le format FIT binaire.
Chaque upload crée une nouvelle RunActivity (pas de déduplication).
"""

import io
import math
import uuid
from datetime import UTC, date, datetime

from fitparse import FitFile
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import RunActivity


class FitConnector:
    def parse_fit(self, content: bytes) -> dict:
        """
        Parse le fichier FIT et retourne les données d'activité.
        Utilise le message 'session' (Garmin summary) si disponible.
        """
        fitfile = FitFile(io.BytesIO(content))
        messages = list(fitfile.get_messages("session"))

        if not messages:
            raise ValueError("FIT file contains no 'session' message")

        msg = messages[0]

        def get(key: str):
            return msg.get_value(key)

        start_time_raw = get("start_time")
        if isinstance(start_time_raw, datetime):
            if start_time_raw.tzinfo is None:
                start_time_raw = start_time_raw.replace(tzinfo=UTC)
            activity_date = start_time_raw.date()
        else:
            activity_date = None

        total_distance = get("total_distance")  # metres
        distance_km = (total_distance / 1000) if total_distance is not None else None

        total_elapsed_time = get("total_elapsed_time")  # seconds
        duration_seconds = int(total_elapsed_time) if total_elapsed_time is not None else None

        avg_hr = get("avg_heart_rate")
        max_hr = get("max_heart_rate")
        elevation_gain_m = get("total_ascent")
        sport = get("sport") or "Run"

        avg_pace: float | None = None
        if distance_km and distance_km > 0 and duration_seconds:
            avg_pace = duration_seconds / distance_km

        return {
            "activity_date": activity_date,
            "activity_type": sport,
            "distance_km": distance_km,
            "duration_seconds": duration_seconds,
            "avg_pace_sec_per_km": avg_pace,
            "avg_hr": int(avg_hr) if avg_hr is not None else None,
            "max_hr": int(max_hr) if max_hr is not None else None,
            "elevation_gain_m": float(elevation_gain_m) if elevation_gain_m is not None else None,
        }

    async def ingest_fit(
        self,
        athlete_id: uuid.UUID,
        content: bytes,
        db: AsyncSession,
    ) -> RunActivity:
        """
        Parse le FIT et insère une RunActivity.
        Calcule le TRIMP HR-based si avg_hr et max_hr disponibles.
        """
        parsed = self.parse_fit(content)

        distance_km = parsed.get("distance_km") or 0.0
        duration_s = parsed.get("duration_seconds") or 0
        avg_hr = parsed.get("avg_hr")
        max_hr = parsed.get("max_hr")

        # TRIMP
        if avg_hr and max_hr:
            ratio = avg_hr / max_hr
            trimp = (duration_s / 60) * ratio * math.exp(1.92 * ratio)
        else:
            trimp = distance_km * 1.0

        run = RunActivity(
            athlete_id=athlete_id,
            activity_date=parsed.get("activity_date"),
            activity_type=parsed.get("activity_type", "Run"),
            distance_km=parsed.get("distance_km"),
            duration_seconds=parsed.get("duration_seconds"),
            avg_pace_sec_per_km=parsed.get("avg_pace_sec_per_km"),
            avg_hr=avg_hr,
            max_hr=max_hr,
            elevation_gain_m=parsed.get("elevation_gain_m"),
            trimp=trimp,
            strava_raw={"source": "fit"},
        )
        db.add(run)
        await db.flush()
        return run
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
/c/Users/simon/AppData/Local/Python/pythoncore-3.14-64/Scripts/poetry.exe run pytest tests/test_fit_connector.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add connectors/fit.py tests/test_fit_connector.py
git commit -m "feat: add FitConnector — FIT binary file upload to RunActivity"
```

---

## Task 5: FoodSearchConnector + Tests

**Files:**
- Create: `connectors/food_search.py`
- Create: `tests/test_food_search_connector.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_food_search_connector.py`:

```python
"""
Tests unitaires FoodSearchConnector.
Tous les appels HTTP sont interceptés via httpx.MockTransport.
"""

import httpx
import pytest

from connectors.food_search import FoodSearchConnector


# ── test_search_usda_returns_results ─────────────────────────────────────────

async def test_search_usda_returns_results():
    usda_response = {
        "foods": [
            {
                "fdcId": 171705,
                "description": "Chicken, broilers or fryers, breast",
                "foodNutrients": [
                    {"nutrientId": 1008, "value": 165.0},  # calories
                    {"nutrientId": 1003, "value": 31.0},    # protein
                    {"nutrientId": 1004, "value": 3.6},     # fat
                    {"nutrientId": 1005, "value": 0.0},     # carbs
                ],
            }
        ]
    }

    def mock_handler(request: httpx.Request) -> httpx.Response:
        assert "foods/search" in str(request.url)
        return httpx.Response(200, json=usda_response)

    connector = FoodSearchConnector(transport=httpx.MockTransport(mock_handler))
    results = await connector.search_usda("chicken")

    assert len(results) == 1
    assert results[0]["fdcId"] == 171705
    assert results[0]["description"] == "Chicken, broilers or fryers, breast"
    assert results[0]["nutrients"]["protein_g"] == pytest.approx(31.0)
    assert results[0]["nutrients"]["calories"] == pytest.approx(165.0)
    assert results[0]["nutrients"]["fat_g"] == pytest.approx(3.6)
    assert results[0]["nutrients"]["carbs_g"] == pytest.approx(0.0)


# ── test_search_barcode_found ─────────────────────────────────────────────────

async def test_search_barcode_found():
    off_response = {
        "status": 1,
        "product": {
            "product_name": "Nutella",
            "nutriments": {
                "energy-kcal_100g": 539.0,
                "proteins_100g": 6.3,
                "fat_100g": 30.9,
                "carbohydrates_100g": 57.5,
            },
        },
    }

    def mock_handler(request: httpx.Request) -> httpx.Response:
        assert "3017624010701" in str(request.url)
        return httpx.Response(200, json=off_response)

    connector = FoodSearchConnector(transport=httpx.MockTransport(mock_handler))
    result = await connector.search_barcode("3017624010701")

    assert result is not None
    assert result["name"] == "Nutella"
    assert result["nutrients"]["calories"] == pytest.approx(539.0)
    assert result["nutrients"]["protein_g"] == pytest.approx(6.3)
    assert result["nutrients"]["fat_g"] == pytest.approx(30.9)
    assert result["nutrients"]["carbs_g"] == pytest.approx(57.5)


# ── test_search_barcode_not_found ─────────────────────────────────────────────

async def test_search_barcode_not_found():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": 0, "product": {}})

    connector = FoodSearchConnector(transport=httpx.MockTransport(mock_handler))
    result = await connector.search_barcode("0000000000000")

    assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
/c/Users/simon/AppData/Local/Python/pythoncore-3.14-64/Scripts/poetry.exe run pytest tests/test_food_search_connector.py -v
```

Expected: 3 failures with `ModuleNotFoundError: No module named 'connectors.food_search'`.

- [ ] **Step 3: Implement FoodSearchConnector**

Create `connectors/food_search.py`:

```python
"""
Food search connector — USDA FoodData Central + Open Food Facts.
Pas de stockage en DB en S4 — retour JSON uniquement.
"""

import httpx

from core.config import settings

# USDA nutrient IDs (par 100g)
_NUTRIENT_IDS = {
    1008: "calories",
    1003: "protein_g",
    1004: "fat_g",
    1005: "carbs_g",
}


class FoodSearchConnector:
    USDA_BASE_URL = "https://api.nal.usda.gov/fdc/v1"
    OFF_BASE_URL = "https://world.openfoodfacts.org/api/v2"

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._transport = transport

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=self._transport)

    async def search_usda(self, query: str, page_size: int = 5) -> list[dict]:
        """
        Recherche USDA FoodData Central par texte.
        Retourne une liste de { fdcId, description, nutrients }.
        """
        async with self._client() as client:
            resp = await client.get(
                f"{self.USDA_BASE_URL}/foods/search",
                params={
                    "query": query,
                    "pageSize": page_size,
                    "api_key": settings.USDA_API_KEY or "DEMO_KEY",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        results = []
        for food in data.get("foods", []):
            nutrients: dict[str, float] = {v: 0.0 for v in _NUTRIENT_IDS.values()}
            for nutrient in food.get("foodNutrients", []):
                nid = nutrient.get("nutrientId")
                if nid in _NUTRIENT_IDS:
                    nutrients[_NUTRIENT_IDS[nid]] = float(nutrient.get("value", 0))
            results.append({
                "fdcId": food.get("fdcId"),
                "description": food.get("description", ""),
                "nutrients": nutrients,
            })
        return results

    async def search_barcode(self, barcode: str) -> dict | None:
        """
        Recherche Open Food Facts par code-barres.
        Retourne { name, nutrients } ou None si non trouvé.
        """
        async with self._client() as client:
            resp = await client.get(
                f"{self.OFF_BASE_URL}/product/{barcode}",
                params={"fields": "nutriments,product_name"},
            )
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            data = resp.json()

        if data.get("status") != 1:
            return None

        product = data.get("product", {})
        nutriments = product.get("nutriments", {})

        return {
            "name": product.get("product_name", ""),
            "nutrients": {
                "calories": float(nutriments.get("energy-kcal_100g", 0)),
                "protein_g": float(nutriments.get("proteins_100g", 0)),
                "fat_g": float(nutriments.get("fat_100g", 0)),
                "carbs_g": float(nutriments.get("carbohydrates_100g", 0)),
            },
        }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
/c/Users/simon/AppData/Local/Python/pythoncore-3.14-64/Scripts/poetry.exe run pytest tests/test_food_search_connector.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add connectors/food_search.py tests/test_food_search_connector.py
git commit -m "feat: add FoodSearchConnector — USDA text search + Open Food Facts barcode"
```

---

## Task 6: FastAPI Routers + Route Tests

**Files:**
- Create: `api/v1/apple_health.py`
- Create: `api/v1/files.py`
- Create: `api/v1/food.py`
- Modify: `api/main.py`
- Create: `tests/test_file_routes.py`

- [ ] **Step 1: Write the failing route tests**

Create `tests/test_file_routes.py`:

```python
"""
Tests des nouvelles routes FastAPI S4 :
- POST /apple-health/upload
- POST /files/gpx
- POST /files/fit
- GET  /food/search
- GET  /food/barcode/{barcode}
"""

from unittest.mock import AsyncMock, MagicMock, patch

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


# GPX sample minimal pour le test d'upload
GPX_BYTES = b"""<?xml version="1.0"?>
<gpx xmlns="http://www.topografix.com/GPX/1/1" version="1.1">
  <trk><trkseg>
    <trkpt lat="48.8566" lon="2.3522"><ele>30.0</ele><time>2026-04-01T08:00:00Z</time></trkpt>
    <trkpt lat="48.8580" lon="2.3545"><ele>35.0</ele><time>2026-04-01T08:20:00Z</time></trkpt>
  </trkseg></trk>
</gpx>"""


# ── test_upload_gpx_returns_activity ─────────────────────────────────────────

async def test_upload_gpx_returns_activity(api_client, simon_athlete):
    response = await api_client.post(
        "/api/v1/connectors/files/gpx",
        params={"athlete_id": str(simon_athlete.id)},
        files={"file": ("run.gpx", GPX_BYTES, "application/gpx+xml")},
    )

    assert response.status_code == 200
    data = response.json()
    assert "activity_date" in data
    assert data["activity_date"] == "2026-04-01"
    assert "distance_km" in data
    assert "duration_seconds" in data


# ── test_upload_fit_returns_activity ─────────────────────────────────────────

async def test_upload_fit_returns_activity(api_client, simon_athlete):
    from datetime import date
    parsed_mock = {
        "activity_date": date(2026, 4, 2),
        "activity_type": "running",
        "distance_km": 5.0,
        "duration_seconds": 1800,
        "avg_pace_sec_per_km": 360.0,
        "avg_hr": 150,
        "max_hr": 175,
        "elevation_gain_m": 50.0,
    }

    with patch("api.v1.files._fit.parse_fit", return_value=parsed_mock):
        response = await api_client.post(
            "/api/v1/connectors/files/fit",
            params={"athlete_id": str(simon_athlete.id)},
            files={"file": ("activity.fit", b"fake_fit_content", "application/octet-stream")},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["activity_date"] == "2026-04-02"
    assert data["distance_km"] == 5.0


# ── test_food_search_returns_list ─────────────────────────────────────────────

async def test_food_search_returns_list(api_client):
    mock_results = [
        {"fdcId": 1, "description": "Chicken breast", "nutrients": {"calories": 165.0, "protein_g": 31.0, "fat_g": 3.6, "carbs_g": 0.0}}
    ]

    with patch(
        "api.v1.food._food.search_usda",
        new=AsyncMock(return_value=mock_results),
    ):
        response = await api_client.get(
            "/api/v1/connectors/food/search",
            params={"q": "chicken"},
        )

    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert len(data["results"]) == 1
    assert data["results"][0]["description"] == "Chicken breast"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
/c/Users/simon/AppData/Local/Python/pythoncore-3.14-64/Scripts/poetry.exe run pytest tests/test_file_routes.py -v
```

Expected: failures with `ModuleNotFoundError` for the new routers.

- [ ] **Step 3: Create api/v1/apple_health.py**

```python
"""
FastAPI router — Apple Health JSON upload → FatigueSnapshot.
auth: athlete_id en query param (JWT en S11).
"""

import uuid

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from connectors.apple_health import AppleHealthConnector
from models.database import Athlete
from models.db_session import get_db

router = APIRouter()
_apple_health = AppleHealthConnector()


async def _get_athlete_or_404(athlete_id: uuid.UUID, db: AsyncSession) -> Athlete:
    result = await db.execute(select(Athlete).where(Athlete.id == athlete_id))
    athlete = result.scalar_one_or_none()
    if athlete is None:
        raise HTTPException(status_code=404, detail=f"Athlete {athlete_id} not found")
    return athlete


@router.post("/apple-health/upload")
async def apple_health_upload(
    data: dict = Body(...),
    athlete_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Upload JSON Apple Health → upsert FatigueSnapshot."""
    await _get_athlete_or_404(athlete_id, db)
    try:
        snapshot = await _apple_health.ingest_snapshot(athlete_id, data, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "snapshot_date": snapshot.snapshot_date.isoformat(),
        "hrv_rmssd": snapshot.hrv_rmssd,
        "hr_rest": snapshot.hr_rest,
        "sleep_hours": snapshot.sleep_hours,
        "sleep_quality_subjective": snapshot.sleep_quality_subjective,
    }
```

- [ ] **Step 4: Create api/v1/files.py**

```python
"""
FastAPI router — upload fichiers GPX/FIT → RunActivity.
auth: athlete_id en query param (JWT en S11).
"""

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from connectors.fit import FitConnector
from connectors.gpx import GpxConnector
from models.database import Athlete
from models.db_session import get_db

router = APIRouter()
_gpx = GpxConnector()
_fit = FitConnector()


async def _get_athlete_or_404(athlete_id: uuid.UUID, db: AsyncSession) -> Athlete:
    result = await db.execute(select(Athlete).where(Athlete.id == athlete_id))
    athlete = result.scalar_one_or_none()
    if athlete is None:
        raise HTTPException(status_code=404, detail=f"Athlete {athlete_id} not found")
    return athlete


@router.post("/files/gpx")
async def upload_gpx(
    file: UploadFile = File(...),
    athlete_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Upload fichier GPX → RunActivity."""
    await _get_athlete_or_404(athlete_id, db)
    content = await file.read()
    try:
        run = await _gpx.ingest_gpx(athlete_id, content, db)
    except (ValueError, Exception) as e:
        raise HTTPException(status_code=400, detail=f"Invalid GPX file: {e}")
    return {
        "activity_date": run.activity_date.isoformat() if run.activity_date else None,
        "distance_km": run.distance_km,
        "duration_seconds": run.duration_seconds,
    }


@router.post("/files/fit")
async def upload_fit(
    file: UploadFile = File(...),
    athlete_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Upload fichier FIT binaire → RunActivity."""
    await _get_athlete_or_404(athlete_id, db)
    content = await file.read()
    try:
        run = await _fit.ingest_fit(athlete_id, content, db)
    except (ValueError, Exception) as e:
        raise HTTPException(status_code=400, detail=f"Invalid FIT file: {e}")
    return {
        "activity_date": run.activity_date.isoformat() if run.activity_date else None,
        "distance_km": run.distance_km,
        "duration_seconds": run.duration_seconds,
    }
```

- [ ] **Step 5: Create api/v1/food.py**

```python
"""
FastAPI router — recherche alimentaire USDA + Open Food Facts.
Pas d'auth requise — données publiques (JWT en S11 si nécessaire).
"""

from fastapi import APIRouter, HTTPException, Query

from connectors.food_search import FoodSearchConnector

router = APIRouter()
_food = FoodSearchConnector()


@router.get("/food/search")
async def food_search(
    q: str = Query(..., min_length=1),
    page_size: int = Query(default=5, ge=1, le=20),
) -> dict:
    """Recherche USDA FoodData Central par texte libre."""
    results = await _food.search_usda(q, page_size=page_size)
    return {"results": results}


@router.get("/food/barcode/{barcode}")
async def food_barcode(barcode: str) -> dict:
    """Recherche Open Food Facts par code-barres EAN."""
    result = await _food.search_barcode(barcode)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Product with barcode {barcode} not found")
    return result
```

- [ ] **Step 6: Update api/main.py**

Replace the contents of `api/main.py`:

```python
"""
FastAPI application stub — Resilio+
S11 complétera : auth JWT, middleware CORS, autres routers.
"""

from fastapi import FastAPI

from api.v1.apple_health import router as apple_health_router
from api.v1.connectors import router as connectors_router
from api.v1.files import router as files_router
from api.v1.food import router as food_router

app = FastAPI(title="Resilio+", version="0.1.0")

app.include_router(
    connectors_router,
    prefix="/api/v1/connectors",
    tags=["connectors"],
)
app.include_router(
    apple_health_router,
    prefix="/api/v1/connectors",
    tags=["apple-health"],
)
app.include_router(
    files_router,
    prefix="/api/v1/connectors",
    tags=["files"],
)
app.include_router(
    food_router,
    prefix="/api/v1/connectors",
    tags=["food"],
)
```

- [ ] **Step 7: Run the new route tests**

```bash
/c/Users/simon/AppData/Local/Python/pythoncore-3.14-64/Scripts/poetry.exe run pytest tests/test_file_routes.py -v
```

Expected: 3 passed.

- [ ] **Step 8: Run full test suite**

```bash
/c/Users/simon/AppData/Local/Python/pythoncore-3.14-64/Scripts/poetry.exe run pytest tests/ -v
```

Expected: ~55 passed (42 S3 + 13 S4).

- [ ] **Step 9: Run ruff linter**

```bash
/c/Users/simon/AppData/Local/Python/pythoncore-3.14-64/Scripts/poetry.exe run ruff check .
```

Expected: No errors. Fix any reported issues before committing.

- [ ] **Step 10: Commit**

```bash
git add api/v1/apple_health.py api/v1/files.py api/v1/food.py api/main.py tests/test_file_routes.py
git commit -m "feat: add S4 routers — apple-health upload, GPX/FIT file upload, food search"
```

---

## Verification Summary

After all 6 tasks:

```bash
# Suite complète
/c/Users/simon/AppData/Local/Python/pythoncore-3.14-64/Scripts/poetry.exe run pytest tests/ -v
# Expected: ~55 passed

# Linter
/c/Users/simon/AppData/Local/Python/pythoncore-3.14-64/Scripts/poetry.exe run ruff check .
# Expected: No errors

# Migration à jour
/c/Users/simon/AppData/Local/Python/pythoncore-3.14-64/Scripts/poetry.exe run alembic current
# Expected: <latest hash> (head)
```
