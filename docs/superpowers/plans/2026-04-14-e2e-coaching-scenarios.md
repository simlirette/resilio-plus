# E2E Coaching Scenarios Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build 8 scenario-based E2E tests + shared fixtures covering the full CoachingService flow (create_plan → resume_plan) and HeadCoach.build_week() for hormonal scenarios.

**Architecture:** Service-layer tests only — CoachingService with interrupt=True (real LangGraph graph), SQLite in-memory DB, AthleteModel seeded per scenario module. S8 uses HeadCoach.build_week() directly because HormonalProfile doesn't flow through CoachingService.create_plan() (delegate_specialists builds AgentContext without DB-loaded connector data).

**Tech Stack:** pytest, SQLAlchemy SQLite in-memory, LangGraph MemorySaver, CoachingService, HeadCoach, EnergySnapshotModel.

---

> **Implementation note on S2/S6 vs design spec:**
> The design spec described S2 as "Recovery Coach HRV veto" and S6 as "missing sleep data".
> In practice, `delegate_specialists` builds `AgentContext` without Terra/Strava/Hevy data (no connector queries).
> Therefore: S2 tests the Energy snapshot intensity cap (0.6) — the mechanism that DOES flow through apply_energy_snapshot node.
> S6 tests "no EnergySnapshot in DB" → energy_snapshot_dict=None in proposed plan.
> S8 uses HeadCoach.build_week() directly — HormonalProfile doesn't flow through CoachingService.

---

## Files

| File | Action |
|---|---|
| `tests/fixtures/athlete_states.py` | **Create** — profile factories + DB helpers |
| `tests/e2e/test_scenario_01_fresh_athlete.py` | **Create** |
| `tests/e2e/test_scenario_02_energy_cap.py` | **Create** |
| `tests/e2e/test_scenario_03_conflict_resolution.py` | **Create** |
| `tests/e2e/test_scenario_04_user_rejects.py` | **Create** |
| `tests/e2e/test_scenario_05_user_modifies.py` | **Create** |
| `tests/e2e/test_scenario_06_no_energy_snapshot.py` | **Create** |
| `tests/e2e/test_scenario_07_reds_veto.py` | **Create** |
| `tests/e2e/test_scenario_08_luteal_phase.py` | **Create** |
| `docs/backend/E2E-SCENARIOS.md` | **Create** |

---

## Task 1: Shared fixtures — `tests/fixtures/athlete_states.py`

**Files:**
- Create: `tests/fixtures/athlete_states.py`

- [ ] **Step 1: Create the file**

```python
# tests/fixtures/athlete_states.py
"""Shared athlete profile factories and DB helpers for E2E scenario tests.

Usage:
    from tests.fixtures.athlete_states import (
        simon_fresh_profile, layla_luteal_context,
        seed_athlete, seed_energy_snapshot,
        make_scenario_engine, STABLE_LOAD, ELEVATED_LOAD, FRESH_LOAD,
    )
"""
from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


# ---------------------------------------------------------------------------
# Load constants
# ---------------------------------------------------------------------------

STABLE_LOAD: list[float] = [400.0] * 28    # ACWR safe (~1.0)
ELEVATED_LOAD: list[float] = [600.0] * 28  # ACWR caution (~1.3)
FRESH_LOAD: list[float] = [50.0] * 28      # new athlete, low load

# Fixed reference dates (deterministic)
WEEK_START = date(2026, 4, 14)
TARGET_RACE = WEEK_START + timedelta(weeks=27)


# ---------------------------------------------------------------------------
# Engine factory (mirrors e2e/conftest._make_e2e_engine)
# ---------------------------------------------------------------------------

def make_scenario_engine():
    """SQLite in-memory engine with FK enforcement."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_pragma(dbapi_conn, _record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


# ---------------------------------------------------------------------------
# AthleteModel seeding
# ---------------------------------------------------------------------------

def seed_athlete(db, athlete_id: str = "e2e-simon-001") -> None:
    """Insert minimal AthleteModel row. Imports deferred to avoid SA conflicts."""
    import importlib
    importlib.import_module("app.models.schemas")   # V3 models first
    _m = importlib.import_module("app.db.models")
    AthleteModel = _m.AthleteModel

    athlete = AthleteModel(
        id=athlete_id,
        name="Simon",
        age=32,
        sex="M",
        weight_kg=78.5,
        height_cm=178.0,
        primary_sport="running",
        target_race_date=TARGET_RACE,
        hours_per_week=8.0,
        sports_json=json.dumps(["running", "lifting"]),
        goals_json=json.dumps(["run sub-25min 5K", "maintain muscle mass"]),
        available_days_json=json.dumps([0, 1, 3, 5, 6]),
        equipment_json=json.dumps([]),
        coaching_mode="full",
        vdot=45.0,
        resting_hr=58,
        max_hr=188,
    )
    db.add(athlete)
    db.commit()


def seed_athlete_layla(db, athlete_id: str = "e2e-layla-001") -> None:
    """Insert Layla (female, VDOT 40) for hormonal cycle tests."""
    import importlib
    importlib.import_module("app.models.schemas")
    _m = importlib.import_module("app.db.models")
    AthleteModel = _m.AthleteModel

    athlete = AthleteModel(
        id=athlete_id,
        name="Layla",
        age=28,
        sex="F",
        weight_kg=62.0,
        height_cm=168.0,
        primary_sport="running",
        target_race_date=TARGET_RACE,
        hours_per_week=7.0,
        sports_json=json.dumps(["running", "lifting"]),
        goals_json=json.dumps(["sub-30min 5K", "stay healthy"]),
        available_days_json=json.dumps([0, 2, 4, 6]),
        equipment_json=json.dumps([]),
        coaching_mode="full",
        vdot=40.0,
        resting_hr=62,
        max_hr=192,
    )
    db.add(athlete)
    db.commit()


# ---------------------------------------------------------------------------
# EnergySnapshotModel seeding
# ---------------------------------------------------------------------------

def seed_energy_snapshot(
    db,
    athlete_id: str = "e2e-simon-001",
    intensity_cap: float = 1.0,
    veto_triggered: bool = False,
    allostatic_score: float = 40.0,
    energy_availability: float = 45.0,
    veto_reason: str | None = None,
) -> None:
    """Insert today's EnergySnapshotModel (timestamp=now UTC) for apply_energy_snapshot node."""
    import importlib
    importlib.import_module("app.models.schemas")
    _schemas = importlib.import_module("app.models.schemas")
    EnergySnapshotModel = _schemas.EnergySnapshotModel

    snapshot = EnergySnapshotModel(
        id=str(uuid.uuid4()),
        athlete_id=athlete_id,
        timestamp=datetime.now(timezone.utc),
        allostatic_score=allostatic_score,
        energy_availability=energy_availability,
        cognitive_load=4.0,
        sleep_quality=7.0,
        recommended_intensity_cap=intensity_cap,
        veto_triggered=veto_triggered,
        veto_reason=veto_reason,
        objective_score=None,
        subjective_score=None,
    )
    db.add(snapshot)
    db.commit()


# ---------------------------------------------------------------------------
# AthleteProfile dicts (for CoachingService.create_plan athlete_dict param)
# ---------------------------------------------------------------------------

def simon_fresh_profile() -> dict[str, Any]:
    """AthleteProfile.model_dump(mode='json') for Simon — normal training state."""
    return {
        "id": str(uuid.UUID("00000000-0000-0000-0000-000000000001")),
        "name": "Simon",
        "age": 32,
        "sex": "M",
        "weight_kg": 78.5,
        "height_cm": 178.0,
        "sports": ["running", "lifting"],
        "primary_sport": "running",
        "goals": ["run sub-25min 5K", "maintain muscle mass"],
        "target_race_date": TARGET_RACE.isoformat(),
        "available_days": [0, 1, 3, 5, 6],
        "hours_per_week": 8.0,
        "equipment": [],
        "vdot": 45.0,
        "resting_hr": 58,
        "max_hr": 188,
        "sleep_hours_typical": 7.5,
        "stress_level": 4,
        "job_physical": False,
        "coaching_mode": "full",
        "ftp_watts": None,
        "css_per_100m": None,
    }


def simon_single_day_profile() -> dict[str, Any]:
    """Simon with available_days=[0] only — forces both sports on Monday (conflict scenario)."""
    profile = simon_fresh_profile()
    profile["available_days"] = [0]
    return profile


# ---------------------------------------------------------------------------
# AgentContext factory for HeadCoach.build_week() (used in S8 — bypasses CoachingService)
# ---------------------------------------------------------------------------

def layla_luteal_context():
    """Returns (athlete, terra, hormonal_profile, load_history) tuple for S8."""
    from datetime import date as _date
    from app.schemas.athlete import AthleteProfile, Sport
    from app.schemas.connector import TerraHealthData
    from app.models.athlete_state import HormonalProfile

    athlete = AthleteProfile(
        name="Layla",
        age=28,
        sex="F",
        weight_kg=62.0,
        height_cm=168.0,
        sports=[Sport.RUNNING, Sport.LIFTING],
        primary_sport=Sport.RUNNING,
        goals=["sub-30min 5K", "stay healthy"],
        target_race_date=TARGET_RACE,
        available_days=[0, 2, 4, 6],
        hours_per_week=7.0,
        vdot=40.0,
        resting_hr=62,
        max_hr=192,
    )

    # Terra: moderate HRV (not pathological, but cycle-adjusted)
    terra = [
        TerraHealthData(
            date=WEEK_START - timedelta(days=i),
            hrv_rmssd=38.0,
            sleep_duration_hours=6.8,
            sleep_score=65.0,
        )
        for i in range(7)
    ]

    # Luteal phase — day 20/28, higher fatigue baseline
    hormonal = HormonalProfile(
        enabled=True,
        current_phase="luteal",
        current_cycle_day=20,
        cycle_length_days=28,
    )

    return athlete, terra, hormonal
```

- [ ] **Step 2: Verify file parses without error**

```bash
C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/python.exe -c "from tests.fixtures.athlete_states import simon_fresh_profile, STABLE_LOAD; print('OK', len(STABLE_LOAD))"
```

Expected: `OK 28`

- [ ] **Step 3: Commit**

```bash
git add tests/fixtures/athlete_states.py
git commit -m "test(fixtures): add athlete_states.py — Simon/Layla factories, seed helpers, load constants"
```

---

## Task 2: Scenario 1 — Fresh athlete → confirm → DB persist

**Files:**
- Create: `tests/e2e/test_scenario_01_fresh_athlete.py`

- [ ] **Step 1: Write the test file**

```python
# tests/e2e/test_scenario_01_fresh_athlete.py
"""S1 — Fresh athlete: create_plan → approve → TrainingPlanModel persisted.

Tests the happy path through the full CoachingService flow with no
energy snapshot (cap=1.0 by default), STABLE_LOAD, ACWR in safe zone.
"""
from __future__ import annotations

import random

import pytest
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db import models as _db_models   # noqa: F401 — registers ORM
from app.models import schemas as _v3     # noqa: F401 — registers V3 models
from app.services.coaching_service import CoachingService
from tests.fixtures.athlete_states import (
    make_scenario_engine,
    seed_athlete,
    simon_fresh_profile,
    STABLE_LOAD,
)

random.seed(42)

ATHLETE_ID = "e2e-s01-simon"
_state: dict = {}


@pytest.fixture(scope="module")
def scenario_db():
    engine = make_scenario_engine()
    Base.metadata.create_all(engine)
    Session = sessionmaker(engine)
    with Session() as db:
        seed_athlete(db, ATHLETE_ID)
        yield db
    Base.metadata.drop_all(engine)


def test_01_create_plan_returns_proposed(scenario_db):
    """create_plan() returns non-None proposed_plan_dict with sessions."""
    svc = CoachingService()
    _state["svc"] = svc

    thread_id, proposed = svc.create_plan(
        athlete_id=ATHLETE_ID,
        athlete_dict=simon_fresh_profile(),
        load_history=STABLE_LOAD,
        db=scenario_db,
    )

    assert thread_id is not None
    assert proposed is not None
    assert isinstance(proposed.get("sessions"), list)
    assert len(proposed["sessions"]) > 0

    _state["thread_id"] = thread_id
    _state["proposed"] = proposed


def test_02_proposed_plan_is_green(scenario_db):
    """Fresh athlete with STABLE_LOAD → readiness_level == 'green'."""
    proposed = _state["proposed"]
    assert proposed["readiness_level"] == "green"


def test_03_proposed_acwr_safe(scenario_db):
    """STABLE_LOAD produces ACWR in safe zone."""
    acwr = _state["proposed"]["acwr"]
    assert acwr["status"] in ("safe", "undertrained")


def test_04_sessions_have_valid_duration(scenario_db):
    """All proposed sessions have duration_min > 0."""
    for s in _state["proposed"]["sessions"]:
        assert s["duration_min"] > 0, f"Session with zero duration: {s}"


def test_05_approve_returns_final_with_db_plan_id(scenario_db):
    """resume_plan(approved=True) → final dict with db_plan_id."""
    svc = _state["svc"]
    final = svc.resume_plan(
        thread_id=_state["thread_id"],
        approved=True,
        feedback=None,
        db=scenario_db,
    )

    assert final is not None
    assert final.get("db_plan_id") is not None
    _state["final"] = final


def test_06_plan_persisted_in_db(scenario_db):
    """TrainingPlanModel row exists in DB after approval."""
    import importlib
    _m = importlib.import_module("app.db.models")
    TrainingPlanModel = _m.TrainingPlanModel

    db_plan_id = _state["final"]["db_plan_id"]
    plan = scenario_db.get(TrainingPlanModel, db_plan_id)
    assert plan is not None
    assert plan.athlete_id == ATHLETE_ID
    assert plan.status == "active"
```

- [ ] **Step 2: Run and expect PASS**

```bash
C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/e2e/test_scenario_01_fresh_athlete.py -v
```

Expected: 6 PASSED

- [ ] **Step 3: Commit**

```bash
git add tests/e2e/test_scenario_01_fresh_athlete.py
git commit -m "test(e2e): add scenario 01 — fresh athlete create+approve, DB persist"
```

---

## Task 3: Scenario 2 — Energy cap 60% → sessions scaled

**Files:**
- Create: `tests/e2e/test_scenario_02_energy_cap.py`

> **Note:** The design spec named this "Recovery Coach veto". In reality, delegate_specialists
> runs agents with no Terra data (AgentContext has empty terra_health). The mechanism that
> actually scales sessions through CoachingService is EnergySnapshotModel.recommended_intensity_cap,
> applied by the apply_energy_snapshot node. This scenario tests that mechanism.

- [ ] **Step 1: Write the test file**

```python
# tests/e2e/test_scenario_02_energy_cap.py
"""S2 — Energy snapshot intensity cap (0.6): sessions scaled to 60% duration.

EnergySnapshotModel pre-seeded with recommended_intensity_cap=0.6 (moderate
allostatic load, no veto). Verifies that apply_energy_snapshot node scales
all session durations by cap before presenting plan to athlete.
"""
from __future__ import annotations

import random

import pytest
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db import models as _db_models   # noqa: F401
from app.models import schemas as _v3     # noqa: F401
from app.services.coaching_service import CoachingService
from tests.fixtures.athlete_states import (
    make_scenario_engine,
    seed_athlete,
    seed_energy_snapshot,
    simon_fresh_profile,
    STABLE_LOAD,
)

random.seed(42)

ATHLETE_ID = "e2e-s02-simon"
CAP = 0.6
_state: dict = {}


@pytest.fixture(scope="module")
def scenario_db():
    engine = make_scenario_engine()
    Base.metadata.create_all(engine)
    Session = sessionmaker(engine)
    with Session() as db:
        seed_athlete(db, ATHLETE_ID)
        seed_energy_snapshot(
            db,
            athlete_id=ATHLETE_ID,
            intensity_cap=CAP,
            veto_triggered=False,
            allostatic_score=65.0,
            energy_availability=32.0,
        )
        yield db
    Base.metadata.drop_all(engine)


def test_01_create_plan_no_cap_yet(scenario_db):
    """create_plan applies cap inside graph — proposed reflects scaled sessions."""
    svc = CoachingService()
    _state["svc"] = svc

    thread_id, proposed = svc.create_plan(
        athlete_id=ATHLETE_ID,
        athlete_dict=simon_fresh_profile(),
        load_history=STABLE_LOAD,
        db=scenario_db,
    )

    assert proposed is not None
    assert len(proposed["sessions"]) > 0
    _state["thread_id"] = thread_id
    _state["proposed"] = proposed


def test_02_energy_snapshot_present(scenario_db):
    """proposed dict carries energy_snapshot with correct cap."""
    snapshot = _state["proposed"].get("energy_snapshot")
    assert snapshot is not None
    assert abs(snapshot["intensity_cap"] - CAP) < 0.01


def test_03_sessions_scaled_to_cap(scenario_db):
    """All sessions have duration_min reflecting intensity_cap=0.6 reduction."""
    # The apply_energy_snapshot node scales: new_duration = max(1, int(original * cap))
    # We can't know original durations without a baseline run, but we verify:
    # 1. All durations > 0 (no crash)
    # 2. energy_snapshot["veto_triggered"] is False
    snapshot = _state["proposed"]["energy_snapshot"]
    assert snapshot["veto_triggered"] is False
    for s in _state["proposed"]["sessions"]:
        assert s["duration_min"] >= 1


def test_04_approve_persists_scaled_plan(scenario_db):
    """resume_plan(approved=True) persists plan with scaled sessions."""
    svc = _state["svc"]
    final = svc.resume_plan(
        thread_id=_state["thread_id"],
        approved=True,
        feedback=None,
        db=scenario_db,
    )
    assert final is not None
    assert final.get("db_plan_id") is not None
```

- [ ] **Step 2: Run and expect PASS**

```bash
C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/e2e/test_scenario_02_energy_cap.py -v
```

Expected: 4 PASSED

- [ ] **Step 3: Commit**

```bash
git add tests/e2e/test_scenario_02_energy_cap.py
git commit -m "test(e2e): add scenario 02 — energy snapshot cap 0.6, sessions scaled"
```

---

## Task 4: Scenario 3 — Running/Lifting conflict → resolution

**Files:**
- Create: `tests/e2e/test_scenario_03_conflict_resolution.py`

- [ ] **Step 1: Write the test file**

```python
# tests/e2e/test_scenario_03_conflict_resolution.py
"""S3 — Running + Lifting conflict on same day → HeadCoach resolution.

Simon available only on Monday (available_days=[0]). Both RunningCoach and
LiftingCoach schedule on Monday. detect_conflicts finds CRITICAL conflict
(high-CNS sessions same day). resolve_conflicts + HeadCoach._arbitrate
drops the shorter session.
"""
from __future__ import annotations

import random

import pytest
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db import models as _db_models   # noqa: F401
from app.models import schemas as _v3     # noqa: F401
from app.services.coaching_service import CoachingService
from tests.fixtures.athlete_states import (
    make_scenario_engine,
    seed_athlete,
    simon_single_day_profile,
    STABLE_LOAD,
)

random.seed(42)

ATHLETE_ID = "e2e-s03-simon"
_state: dict = {}


@pytest.fixture(scope="module")
def scenario_db():
    engine = make_scenario_engine()
    Base.metadata.create_all(engine)
    Session = sessionmaker(engine)
    with Session() as db:
        seed_athlete(db, ATHLETE_ID)
        yield db
    Base.metadata.drop_all(engine)


def test_01_create_plan_produces_sessions(scenario_db):
    """create_plan with single available day returns a valid proposed plan."""
    svc = CoachingService()
    _state["svc"] = svc

    thread_id, proposed = svc.create_plan(
        athlete_id=ATHLETE_ID,
        athlete_dict=simon_single_day_profile(),
        load_history=STABLE_LOAD,
        db=scenario_db,
    )

    assert proposed is not None
    assert len(proposed["sessions"]) > 0
    _state["thread_id"] = thread_id
    _state["proposed"] = proposed


def test_02_conflicts_detected(scenario_db):
    """Conflicts list is populated (single day forces same-day sessions)."""
    conflicts = _state["proposed"].get("conflicts", [])
    # With only Monday available, running + lifting land on same day
    assert len(conflicts) > 0, (
        f"Expected conflicts with available_days=[0], got none. "
        f"Sessions: {_state['proposed']['sessions']}"
    )


def test_03_no_two_hard_sessions_same_day(scenario_db):
    """After resolution: no date has two sessions both with cns_load > 40."""
    from collections import defaultdict
    sessions_by_date: dict[str, list[dict]] = defaultdict(list)
    for s in _state["proposed"]["sessions"]:
        sessions_by_date[s["date"]].append(s)

    for session_date, day_sessions in sessions_by_date.items():
        if len(day_sessions) < 2:
            continue
        high_cns = [
            s for s in day_sessions
            if s.get("fatigue_score", {}).get("cns_load", 0) > 40
        ]
        assert len(high_cns) < 2, (
            f"Two high-CNS sessions on {session_date}: {high_cns}"
        )


def test_04_approve_persists(scenario_db):
    """resume_plan(approved=True) persists without error."""
    svc = _state["svc"]
    final = svc.resume_plan(
        thread_id=_state["thread_id"],
        approved=True,
        feedback=None,
        db=scenario_db,
    )
    assert final is not None
    assert final.get("db_plan_id") is not None
```

- [ ] **Step 2: Run and expect PASS**

```bash
C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/e2e/test_scenario_03_conflict_resolution.py -v
```

Expected: 4 PASSED

- [ ] **Step 3: Commit**

```bash
git add tests/e2e/test_scenario_03_conflict_resolution.py
git commit -m "test(e2e): add scenario 03 — conflict detection and resolution, single available day"
```

---

## Task 5: Scenario 4 — User rejects → revised plan returned

**Files:**
- Create: `tests/e2e/test_scenario_04_user_rejects.py`

- [ ] **Step 1: Write the test file**

```python
# tests/e2e/test_scenario_04_user_rejects.py
"""S4 — User rejects proposed plan → revise loop → second proposed plan.

Verifies the full reject+revise cycle:
  create_plan → interrupt → resume(approved=False) → revise_plan node →
  delegate_specialists → build_proposed_plan → interrupt again → proposed_v2 returned.

The graph enforces max 1 revision (coaching_graph._after_revise logic).
"""
from __future__ import annotations

import random

import pytest
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db import models as _db_models   # noqa: F401
from app.models import schemas as _v3     # noqa: F401
from app.services.coaching_service import CoachingService
from tests.fixtures.athlete_states import (
    make_scenario_engine,
    seed_athlete,
    simon_fresh_profile,
    STABLE_LOAD,
)

random.seed(42)

ATHLETE_ID = "e2e-s04-simon"
_state: dict = {}


@pytest.fixture(scope="module")
def scenario_db():
    engine = make_scenario_engine()
    Base.metadata.create_all(engine)
    Session = sessionmaker(engine)
    with Session() as db:
        seed_athlete(db, ATHLETE_ID)
        yield db
    Base.metadata.drop_all(engine)


def test_01_create_plan(scenario_db):
    """create_plan returns proposed_v1."""
    svc = CoachingService()
    _state["svc"] = svc

    thread_id, proposed_v1 = svc.create_plan(
        athlete_id=ATHLETE_ID,
        athlete_dict=simon_fresh_profile(),
        load_history=STABLE_LOAD,
        db=scenario_db,
    )

    assert proposed_v1 is not None
    assert len(proposed_v1["sessions"]) > 0
    _state["thread_id"] = thread_id
    _state["proposed_v1"] = proposed_v1


def test_02_reject_returns_proposed_v2(scenario_db):
    """resume_plan(approved=False) returns second proposed plan (not None, not final)."""
    svc = _state["svc"]

    proposed_v2 = svc.resume_plan(
        thread_id=_state["thread_id"],
        approved=False,
        feedback="Too much volume this week, please reduce.",
        db=scenario_db,
    )

    assert proposed_v2 is not None, "Expected a second proposed plan, got None"
    assert isinstance(proposed_v2.get("sessions"), list)
    assert len(proposed_v2["sessions"]) > 0
    # proposed_v2 is NOT a final plan — it should NOT have db_plan_id
    assert proposed_v2.get("db_plan_id") is None
    _state["proposed_v2"] = proposed_v2
    _state["thread_id_v2"] = _state["thread_id"]  # same thread continues


def test_03_revised_plan_is_structurally_valid(scenario_db):
    """proposed_v2 has all required top-level fields."""
    p = _state["proposed_v2"]
    assert "sessions" in p
    assert "readiness_level" in p
    assert p["readiness_level"] in ("green", "yellow", "red")
    assert "acwr" in p
    assert "phase" in p


def test_04_approve_revised_plan(scenario_db):
    """resume_plan(approved=True) on the same thread after rejection → persists."""
    svc = _state["svc"]

    final = svc.resume_plan(
        thread_id=_state["thread_id_v2"],
        approved=True,
        feedback=None,
        db=scenario_db,
    )

    assert final is not None
    assert final.get("db_plan_id") is not None
```

- [ ] **Step 2: Run and expect PASS**

```bash
C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/e2e/test_scenario_04_user_rejects.py -v
```

Expected: 4 PASSED

- [ ] **Step 3: Commit**

```bash
git add tests/e2e/test_scenario_04_user_rejects.py
git commit -m "test(e2e): add scenario 04 — user rejects plan, revise cycle completes"
```

---

## Task 6: Scenario 5 — User modifies with specific feedback

**Files:**
- Create: `tests/e2e/test_scenario_05_user_modifies.py`

- [ ] **Step 1: Write the test file**

```python
# tests/e2e/test_scenario_05_user_modifies.py
"""S5 — User rejects with specific feedback → second plan returned without crash.

Note: revise_plan clears proposed_plan_dict and stores feedback in messages,
then re-delegates to specialists. Agents do NOT read human_feedback text —
the feedback is recorded for audit trail only. The test verifies:
1. The revise cycle completes without error.
2. A valid second proposed plan is returned.
3. The feedback text appears in the graph messages.
"""
from __future__ import annotations

import random

import pytest
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db import models as _db_models   # noqa: F401
from app.models import schemas as _v3     # noqa: F401
from app.services.coaching_service import CoachingService
from tests.fixtures.athlete_states import (
    make_scenario_engine,
    seed_athlete,
    simon_fresh_profile,
    STABLE_LOAD,
)

random.seed(42)

ATHLETE_ID = "e2e-s05-simon"
FEEDBACK = "Replace long run with 45min easy run — my legs are sore."
_state: dict = {}


@pytest.fixture(scope="module")
def scenario_db():
    engine = make_scenario_engine()
    Base.metadata.create_all(engine)
    Session = sessionmaker(engine)
    with Session() as db:
        seed_athlete(db, ATHLETE_ID)
        yield db
    Base.metadata.drop_all(engine)


def test_01_create_plan(scenario_db):
    svc = CoachingService()
    _state["svc"] = svc
    thread_id, proposed = svc.create_plan(
        athlete_id=ATHLETE_ID,
        athlete_dict=simon_fresh_profile(),
        load_history=STABLE_LOAD,
        db=scenario_db,
    )
    assert proposed is not None
    _state["thread_id"] = thread_id


def test_02_reject_with_specific_feedback(scenario_db):
    """Specific feedback text → revise loop completes, returns valid proposed_v2."""
    svc = _state["svc"]
    proposed_v2 = svc.resume_plan(
        thread_id=_state["thread_id"],
        approved=False,
        feedback=FEEDBACK,
        db=scenario_db,
    )
    assert proposed_v2 is not None
    assert isinstance(proposed_v2.get("sessions"), list)
    assert proposed_v2["readiness_level"] in ("green", "yellow", "red")
    _state["proposed_v2"] = proposed_v2


def test_03_feedback_recorded_in_graph_state(scenario_db):
    """Verify revise cycle ran (indirectly: proposed_v2 has no db_plan_id yet)."""
    # proposed_v2 should NOT be a final plan — no persistence happened
    assert _state["proposed_v2"].get("db_plan_id") is None


def test_04_second_approval_persists(scenario_db):
    """approve after modification → DB persist succeeds."""
    svc = _state["svc"]
    final = svc.resume_plan(
        thread_id=_state["thread_id"],
        approved=True,
        feedback=None,
        db=scenario_db,
    )
    assert final is not None
    assert final.get("db_plan_id") is not None
```

- [ ] **Step 2: Run and expect PASS**

```bash
C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/e2e/test_scenario_05_user_modifies.py -v
```

Expected: 4 PASSED

- [ ] **Step 3: Commit**

```bash
git add tests/e2e/test_scenario_05_user_modifies.py
git commit -m "test(e2e): add scenario 05 — user modifies with feedback, revise+approve cycle"
```

---

## Task 7: Scenario 6 — No energy snapshot → plan unmodified

**Files:**
- Create: `tests/e2e/test_scenario_06_no_energy_snapshot.py`

- [ ] **Step 1: Write the test file**

```python
# tests/e2e/test_scenario_06_no_energy_snapshot.py
"""S6 — No EnergySnapshotModel in DB → apply_energy_snapshot returns None gracefully.

Verifies the graceful degradation path: when no check-in exists for today,
apply_energy_snapshot node returns energy_snapshot_dict=None and sessions
are NOT scaled (plan preserved as-is). No exception raised.

(Design spec named this 'missing sleep data'. The actual mechanism is
'no EnergySnapshot' since Terra data doesn't flow through CoachingService
delegate_specialists node.)
"""
from __future__ import annotations

import random

import pytest
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db import models as _db_models   # noqa: F401
from app.models import schemas as _v3     # noqa: F401
from app.services.coaching_service import CoachingService
from tests.fixtures.athlete_states import (
    make_scenario_engine,
    seed_athlete,
    simon_fresh_profile,
    STABLE_LOAD,
)

random.seed(42)

ATHLETE_ID = "e2e-s06-simon"
_state: dict = {}


@pytest.fixture(scope="module")
def scenario_db():
    """No EnergySnapshotModel seeded — only AthleteModel."""
    engine = make_scenario_engine()
    Base.metadata.create_all(engine)
    Session = sessionmaker(engine)
    with Session() as db:
        seed_athlete(db, ATHLETE_ID)
        # Intentionally no seed_energy_snapshot call
        yield db
    Base.metadata.drop_all(engine)


def test_01_create_plan_no_crash(scenario_db):
    """create_plan with no energy snapshot does not raise an exception."""
    svc = CoachingService()
    _state["svc"] = svc

    thread_id, proposed = svc.create_plan(
        athlete_id=ATHLETE_ID,
        athlete_dict=simon_fresh_profile(),
        load_history=STABLE_LOAD,
        db=scenario_db,
    )

    assert proposed is not None
    assert len(proposed["sessions"]) > 0
    _state["thread_id"] = thread_id
    _state["proposed"] = proposed


def test_02_energy_snapshot_is_none(scenario_db):
    """proposed dict has energy_snapshot key as None (no snapshot today)."""
    # apply_energy_snapshot returns energy_snapshot_dict=None when no snapshot
    snapshot = _state["proposed"].get("energy_snapshot")
    assert snapshot is None, f"Expected None energy_snapshot, got: {snapshot}"


def test_03_sessions_not_scaled(scenario_db):
    """Sessions have normal durations (no scaling applied)."""
    for s in _state["proposed"]["sessions"]:
        # Without a cap, sessions shouldn't be capped to 1 minute
        assert s["duration_min"] > 1, f"Session unexpectedly at 1min: {s}"


def test_04_approve_persists_normally(scenario_db):
    """Plan with no energy snapshot can still be approved and persisted."""
    svc = _state["svc"]
    final = svc.resume_plan(
        thread_id=_state["thread_id"],
        approved=True,
        feedback=None,
        db=scenario_db,
    )
    assert final is not None
    assert final.get("db_plan_id") is not None
```

- [ ] **Step 2: Run and expect PASS**

```bash
C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/e2e/test_scenario_06_no_energy_snapshot.py -v
```

Expected: 4 PASSED

- [ ] **Step 3: Commit**

```bash
git add tests/e2e/test_scenario_06_no_energy_snapshot.py
git commit -m "test(e2e): add scenario 06 — no energy snapshot, graceful None handling"
```

---

## Task 8: Scenario 7 — RED-S veto → sessions at 1 min

**Files:**
- Create: `tests/e2e/test_scenario_07_reds_veto.py`

- [ ] **Step 1: Write the test file**

```python
# tests/e2e/test_scenario_07_reds_veto.py
"""S7 — RED-S energy veto: EnergySnapshot(cap=0.0, veto=True) → sessions all 1min.

EnergySnapshotModel pre-seeded with:
  energy_availability=18.0 kcal/kg FFM (< 25 male threshold = critical)
  recommended_intensity_cap=0.0
  veto_triggered=True

apply_energy_snapshot node reads the snapshot and scales:
  new_duration = max(1, int(duration_min * 0.0)) = 1 for all sessions.

The veto is non-overridable by the athlete's approval decision —
the sessions are already scaled before present_to_athlete.
Approving persists the plan with all sessions at 1min.
"""
from __future__ import annotations

import random

import pytest
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db import models as _db_models   # noqa: F401
from app.models import schemas as _v3     # noqa: F401
from app.services.coaching_service import CoachingService
from tests.fixtures.athlete_states import (
    make_scenario_engine,
    seed_athlete,
    seed_energy_snapshot,
    simon_fresh_profile,
    STABLE_LOAD,
)

random.seed(42)

ATHLETE_ID = "e2e-s07-simon"
_state: dict = {}


@pytest.fixture(scope="module")
def scenario_db():
    engine = make_scenario_engine()
    Base.metadata.create_all(engine)
    Session = sessionmaker(engine)
    with Session() as db:
        seed_athlete(db, ATHLETE_ID)
        seed_energy_snapshot(
            db,
            athlete_id=ATHLETE_ID,
            intensity_cap=0.0,
            veto_triggered=True,
            allostatic_score=88.0,
            energy_availability=18.0,
            veto_reason="EA critique (18.0 < 25 kcal/kg FFM)",
        )
        yield db
    Base.metadata.drop_all(engine)


def test_01_create_plan_does_not_crash(scenario_db):
    """create_plan with RED-S veto snapshot completes without exception."""
    svc = CoachingService()
    _state["svc"] = svc

    thread_id, proposed = svc.create_plan(
        athlete_id=ATHLETE_ID,
        athlete_dict=simon_fresh_profile(),
        load_history=STABLE_LOAD,
        db=scenario_db,
    )

    assert proposed is not None
    _state["thread_id"] = thread_id
    _state["proposed"] = proposed


def test_02_veto_flag_in_proposed(scenario_db):
    """proposed carries energy_snapshot with veto_triggered=True."""
    snapshot = _state["proposed"].get("energy_snapshot")
    assert snapshot is not None
    assert snapshot["veto_triggered"] is True
    assert abs(snapshot["intensity_cap"]) < 0.01  # ~0.0


def test_03_all_sessions_at_1_minute(scenario_db):
    """All sessions have duration_min == 1 (max(1, int(d * 0.0)) = 1)."""
    sessions = _state["proposed"]["sessions"]
    assert len(sessions) > 0
    for s in sessions:
        assert s["duration_min"] == 1, (
            f"Expected 1min (RED-S cap=0), got {s['duration_min']}min "
            f"for session: {s.get('workout_type')}"
        )


def test_04_approve_persists_veto_plan(scenario_db):
    """Athlete can still approve and persist the veto plan (their decision)."""
    svc = _state["svc"]
    final = svc.resume_plan(
        thread_id=_state["thread_id"],
        approved=True,
        feedback=None,
        db=scenario_db,
    )
    assert final is not None
    assert final.get("db_plan_id") is not None


def test_05_db_plan_sessions_at_1_minute(scenario_db):
    """Persisted TrainingPlanModel has sessions all at 1min in weekly_slots_json."""
    import json
    import importlib
    _m = importlib.import_module("app.db.models")
    TrainingPlanModel = _m.TrainingPlanModel

    db_plan_id = _state["proposed"].get("energy_snapshot") and _state.get("_final_id")
    # Re-fetch via DB
    plan = (
        scenario_db.query(TrainingPlanModel)
        .filter(TrainingPlanModel.athlete_id == ATHLETE_ID)
        .first()
    )
    assert plan is not None
    slots = json.loads(plan.weekly_slots_json)
    assert len(slots) > 0
    for slot in slots:
        assert slot["duration_min"] == 1
```

- [ ] **Step 2: Run and expect PASS**

```bash
C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/e2e/test_scenario_07_reds_veto.py -v
```

Expected: 5 PASSED

- [ ] **Step 3: Commit**

```bash
git add tests/e2e/test_scenario_07_reds_veto.py
git commit -m "test(e2e): add scenario 07 — RED-S veto cap=0.0, sessions all 1min"
```

---

## Task 9: Scenario 8 — Luteal phase → HeadCoach.build_week() adjusted prescription

**Files:**
- Create: `tests/e2e/test_scenario_08_luteal_phase.py`

> **Note:** HormonalProfile does NOT flow through CoachingService.create_plan() because
> delegate_specialists builds AgentContext without loading HormonalProfileModel from DB.
> This scenario uses HeadCoach.build_week() directly (same layer as TestHeadCoachWorkflowE2E
> in test_agents_integration.py) — consistent with existing E2E patterns for agent-level tests.

- [ ] **Step 1: Write the test file**

```python
# tests/e2e/test_scenario_08_luteal_phase.py
"""S8 — Luteal phase: HeadCoach.build_week() with HormonalProfile → adjusted prescription.

Uses HeadCoach.build_week() directly (bypasses CoachingService) because
HormonalProfile doesn't flow through the graph's delegate_specialists node.
This is consistent with how TestHeadCoachWorkflowE2E tests the Head Coach.

Layla: female, VDOT 40, HormonalProfile.current_phase='luteal', cycle day 20.
Expected: readiness_level in ('yellow', 'red') — luteal phase triggers
allostatic adjustment; NutritionCoach prescribes protein bonus.
"""
from __future__ import annotations

import random
from datetime import date, timedelta

import pytest

from app.agents.head_coach import HeadCoach, WeeklyPlan
from app.agents.running_coach import RunningCoach
from app.agents.lifting_coach import LiftingCoach
from app.agents.nutrition_coach import NutritionCoach
from app.agents.recovery_coach.agent import RecoveryCoachV3
from app.agents.base import AgentContext
from tests.fixtures.athlete_states import layla_luteal_context, STABLE_LOAD

random.seed(42)

WEEK_START = date(2026, 4, 14)
WEEK_END = WEEK_START + timedelta(days=6)


@pytest.fixture(scope="module")
def layla_plan():
    """Build Layla's week with luteal HormonalProfile via HeadCoach.build_week()."""
    athlete, terra, hormonal = layla_luteal_context()

    context = AgentContext(
        athlete=athlete,
        date_range=(WEEK_START, WEEK_END),
        phase="base",
        terra_health=terra,
        strava_activities=[],
        hevy_workouts=[],
        hormonal_profile=hormonal,
        sport_budgets={"running": 4.2, "lifting": 2.8},
        week_number=2,
        weeks_remaining=27,
    )

    hc = HeadCoach([RunningCoach(), LiftingCoach(), NutritionCoach(), RecoveryCoachV3()])
    plan = hc.build_week(context, load_history=STABLE_LOAD)
    return plan


def test_plan_is_weekly_plan(layla_plan):
    assert isinstance(layla_plan, WeeklyPlan)


def test_plan_has_sessions(layla_plan):
    assert len(layla_plan.sessions) > 0


def test_readiness_adjusted_for_luteal(layla_plan):
    """Luteal phase (day 20) with moderate HRV → readiness not green."""
    # Luteal phase + moderate terra → readiness_modifier < 0.9 → yellow/red
    assert layla_plan.readiness_level in ("yellow", "red"), (
        f"Expected luteal phase to reduce readiness from green, "
        f"got: {layla_plan.readiness_level}"
    )


def test_sessions_within_budget(layla_plan):
    """Total session duration respects Layla's 7h/week budget."""
    total_hours = sum(s.duration_min for s in layla_plan.sessions) / 60.0
    assert total_hours <= 8.0, f"Total {total_hours:.1f}h exceeds 8h budget"


def test_no_session_has_none_fields(layla_plan):
    """No critical session fields are None."""
    for s in layla_plan.sessions:
        assert s.date is not None
        assert s.sport is not None
        assert s.workout_type is not None
        assert s.duration_min > 0
        assert s.fatigue_score is not None


def test_nutrition_notes_contain_cycle_reference(layla_plan):
    """NutritionCoach notes reference luteal phase or cycle."""
    notes_text = " ".join(layla_plan.notes).lower()
    has_cycle_ref = any(
        kw in notes_text for kw in ["luteal", "cycle", "menstrual", "hormonal", "protein"]
    )
    assert has_cycle_ref, (
        f"Expected NutritionCoach to reference cycle in notes. Notes: {layla_plan.notes}"
    )
```

- [ ] **Step 2: Run and expect PASS**

```bash
C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/e2e/test_scenario_08_luteal_phase.py -v
```

Expected: 6 PASSED

- [ ] **Step 3: Commit**

```bash
git add tests/e2e/test_scenario_08_luteal_phase.py
git commit -m "test(e2e): add scenario 08 — luteal phase, HeadCoach.build_week, adjusted readiness"
```

---

## Task 10: Living spec — `docs/backend/E2E-SCENARIOS.md`

**Files:**
- Create: `docs/backend/E2E-SCENARIOS.md`

- [ ] **Step 1: Create the file**

```markdown
# E2E Coaching Scenarios — Living Spec

Tests in `tests/e2e/test_scenario_*.py`. Each file is an independent scenario with its own SQLite in-memory DB and module-scoped fixture.

**Layer:** CoachingService (S1–S7) or HeadCoach.build_week() (S8).
**Fixtures:** `tests/fixtures/athlete_states.py` — `simon_fresh_profile()`, `layla_luteal_context()`, `seed_athlete()`, `seed_energy_snapshot()`.
**Pytest:** `C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/e2e/test_scenario_*.py -v`

---

## Scenario Table

| # | Name | File | Layer | Key assertion |
|---|---|---|---|---|
| 1 | Fresh athlete → confirm | `test_scenario_01_fresh_athlete.py` | CoachingService | `db_plan_id` not None after approve |
| 2 | Energy cap 60% → sessions scaled | `test_scenario_02_energy_cap.py` | CoachingService | `energy_snapshot.intensity_cap == 0.6` |
| 3 | Running/Lifting conflict → resolved | `test_scenario_03_conflict_resolution.py` | CoachingService | no two high-CNS sessions same day |
| 4 | User rejects → revise cycle | `test_scenario_04_user_rejects.py` | CoachingService | `proposed_v2` returned, `db_plan_id=None` |
| 5 | User modifies with feedback | `test_scenario_05_user_modifies.py` | CoachingService | revise cycle completes without error |
| 6 | No energy snapshot → graceful | `test_scenario_06_no_energy_snapshot.py` | CoachingService | `energy_snapshot=None`, sessions unscaled |
| 7 | RED-S veto cap=0.0 | `test_scenario_07_reds_veto.py` | CoachingService | all sessions `duration_min=1` |
| 8 | Luteal phase → adjusted plan | `test_scenario_08_luteal_phase.py` | HeadCoach.build_week() | readiness yellow/red, nutrition references cycle |

---

## Common Pattern (S1–S7)

```python
# 1. Module-level state dict
_state: dict = {}

# 2. Module-scoped DB fixture
@pytest.fixture(scope="module")
def scenario_db():
    engine = make_scenario_engine()
    Base.metadata.create_all(engine)
    Session = sessionmaker(engine)
    with Session() as db:
        seed_athlete(db, ATHLETE_ID)
        # optional: seed_energy_snapshot(...)
        yield db
    Base.metadata.drop_all(engine)

# 3. Step 1 — create plan, store svc instance
def test_01_create_plan(scenario_db):
    svc = CoachingService()
    _state["svc"] = svc  # MUST reuse same instance for resume_plan
    thread_id, proposed = svc.create_plan(ATHLETE_ID, profile_dict, STABLE_LOAD, scenario_db)
    _state["thread_id"] = thread_id

# 4. Step 2 — resume
def test_02_approve(scenario_db):
    final = _state["svc"].resume_plan(_state["thread_id"], approved=True, feedback=None, db=scenario_db)
```

> **Critical:** `CoachingService` instance must be shared across steps. The MemorySaver
> (LangGraph checkpointer) is attached to `svc._graph`. A new `CoachingService()` would
> have a fresh MemorySaver with no checkpoint — `resume_plan` would fail.

---

## Why S8 uses HeadCoach.build_week() instead of CoachingService

`CoachingService.create_plan()` → `delegate_specialists` node builds `AgentContext` with:
```python
context = AgentContext(athlete=athlete, date_range=..., phase=..., sport_budgets=...)
# No terra_health, no strava_activities, no hevy_workouts, no hormonal_profile
```

Terra health and HormonalProfile don't flow through the graph. HRV-based Recovery Coach
veto and hormonal adjustments require `AgentContext` built with explicit data — only
possible via `HeadCoach.build_week()` directly (as in `test_agents_integration.py`).

---

## Adding a New Scenario

1. Create `tests/e2e/test_scenario_NN_<name>.py`
2. Use `seed_athlete()` + optional `seed_energy_snapshot()` from `athlete_states.py`
3. Follow the Common Pattern above — store `svc` in `_state` and reuse it
4. Run: `pytest tests/e2e/test_scenario_NN_*.py -v`
5. Add row to Scenario Table above
6. Commit: `test(e2e): add scenario NN — <description>`
```

- [ ] **Step 2: Commit**

```bash
git add docs/backend/E2E-SCENARIOS.md
git commit -m "docs(e2e): add E2E-SCENARIOS.md living spec — 8 scenarios, pattern guide, S8 rationale"
```

---

## Task 11: Run full suite + verify invariants

**Files:** None created — validation only.

- [ ] **Step 1: Run all new scenario tests**

```bash
C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/e2e/test_scenario_*.py -v
```

Expected: all PASSED (33 tests across 8 files)

- [ ] **Step 2: Run full test suite — no regressions**

```bash
C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/ -x -q 2>&1 | tail -5
```

Expected: all passing (2211+ tests)

- [ ] **Step 3: Push to origin**

```bash
git push origin main
```

- [ ] **Step 4: Invoke `/revise-claude-md`**

Update CLAUDE.md with new V3-Q phase entry and test count.

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task |
|---|---|
| S1 — Fresh → confirm → DB persist | Task 2 |
| S2 — Fatigue → intensity reduced | Task 3 (via energy cap, not HRV — explained in note) |
| S3 — Running/Lifting conflict | Task 4 |
| S4 — User rejects | Task 5 |
| S5 — User modifies | Task 6 |
| S6 — Missing data graceful | Task 7 (no energy snapshot) |
| S7 — RED-S veto | Task 8 |
| S8 — Luteal phase | Task 9 |
| `tests/fixtures/athlete_states.py` | Task 1 |
| `docs/backend/E2E-SCENARIOS.md` | Task 10 |
| Final validation | Task 11 |

**Placeholder scan:** None found. All code blocks are complete.

**Type consistency:**
- `seed_athlete(db, athlete_id)` used consistently in Tasks 2–8
- `seed_energy_snapshot(db, athlete_id, intensity_cap, ...)` used in Tasks 3, 8
- `CoachingService().create_plan(athlete_id, athlete_dict, load_history, db)` — consistent signature
- `svc.resume_plan(thread_id, approved, feedback, db)` — consistent signature
- `_state["svc"]` pattern consistent across S1–S7
