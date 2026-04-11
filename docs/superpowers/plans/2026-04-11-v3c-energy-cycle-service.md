# V3-C Energy Cycle Service Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the standalone EnergyCycleService with its 4 API routes (POST /checkin, GET /readiness, GET /energy/history, PATCH /hormonal-profile) that work independently of any coaching mode.

**Architecture:** Pure Python service (no LangGraph). `EnergyCycleService` reads/writes `EnergySnapshotModel` and `HormonalProfileModel` via SQLAlchemy. Readiness = blend of objective score (100 − allostatic, computed from work+stress+check-in) and subjective score (legs_feeling + energy_global). Migration 0004 adds `objective_score` and `subjective_score` columns to `energy_snapshots`. No connector data required — V3-C is self-contained.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy 2 (sync), Alembic, pytest + SQLite in-memory.

---

## File Map

**Create:**
- `alembic/versions/0004_energy_snapshot_scores.py` — add objective_score + subjective_score to energy_snapshots
- `backend/app/schemas/checkin.py` — CheckInInput, ReadinessResponse, HormonalProfileUpdate
- `backend/app/services/energy_cycle_service.py` — EnergyCycleService (5 methods)
- `backend/app/routes/checkin.py` — 4 routes
- `tests/backend/api/test_energy_cycle.py` — full test suite

**Modify:**
- `backend/app/models/schemas.py` — add objective_score + subjective_score to EnergySnapshotModel
- `data/energy_coach_check_in_schema.json` — add legs_feeling + energy_global questions
- `backend/app/main.py` — mount checkin_router

---

## Task 1: Pydantic schemas + check-in JSON schema

**Files:**
- Create: `backend/app/schemas/checkin.py`
- Modify: `data/energy_coach_check_in_schema.json`

- [ ] **Step 1: Write failing tests**

Create `tests/backend/api/test_energy_cycle.py`:

```python
"""Tests for V3-C Energy Cycle Service — schemas, service, routes."""
import pytest
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# Task 1 — Pydantic schemas
# ---------------------------------------------------------------------------

def test_checkin_input_valid():
    from app.schemas.checkin import CheckInInput
    ci = CheckInInput(
        work_intensity="normal",
        stress_level="mild",
        legs_feeling="normal",
        energy_global="ok",
    )
    assert ci.work_intensity == "normal"
    assert ci.legs_feeling == "normal"
    assert ci.cycle_phase is None
    assert ci.comment is None


def test_checkin_input_rejects_invalid_legs():
    from app.schemas.checkin import CheckInInput
    with pytest.raises(ValidationError):
        CheckInInput(
            work_intensity="normal",
            stress_level="none",
            legs_feeling="bad",   # invalid
            energy_global="ok",
        )


def test_checkin_input_rejects_invalid_energy():
    from app.schemas.checkin import CheckInInput
    with pytest.raises(ValidationError):
        CheckInInput(
            work_intensity="normal",
            stress_level="none",
            legs_feeling="fresh",
            energy_global="meh",  # invalid
        )


def test_readiness_response_fields():
    from app.schemas.checkin import ReadinessResponse
    from datetime import date
    r = ReadinessResponse(
        date=date.today(),
        objective_score=70.0,
        subjective_score=40.0,
        final_readiness=52.0,
        divergence=30.0,
        divergence_flag="high",
        traffic_light="yellow",
        allostatic_score=30.0,
        energy_availability=45.0,
        intensity_cap=1.0,
        insights=["HRV normale mais jambes à dead. Ton ressenti compte."],
    )
    assert r.divergence_flag == "high"
    assert r.traffic_light == "yellow"


def test_hormonal_profile_update_valid():
    from app.schemas.checkin import HormonalProfileUpdate
    from datetime import date
    h = HormonalProfileUpdate(
        enabled=True,
        cycle_length_days=28,
        last_period_start=date.today(),
    )
    assert h.enabled is True
    assert h.cycle_length_days == 28
```

- [ ] **Step 2: Run — expect FAIL**

```
C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/backend/api/test_energy_cycle.py -v
```

Expected: ImportError / 5 FAILED

- [ ] **Step 3: Create `backend/app/schemas/checkin.py`**

```python
"""Pydantic schemas for the Energy Cycle Service (V3-C).

CheckInInput        — 5 questions daily check-in
ReadinessResponse   — full readiness response with reconciliation
HormonalProfileUpdate — PATCH body for hormonal profile
"""
from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Check-in input
# ---------------------------------------------------------------------------

class CheckInInput(BaseModel):
    work_intensity: Literal["light", "normal", "heavy", "exhausting"]
    stress_level: Literal["none", "mild", "significant"]
    legs_feeling: Literal["fresh", "normal", "heavy", "dead"]
    energy_global: Literal["great", "ok", "low", "exhausted"]
    cycle_phase: Optional[Literal["menstrual", "follicular", "ovulation", "luteal"]] = None
    comment: Optional[str] = Field(default=None, max_length=140)


# ---------------------------------------------------------------------------
# Readiness response
# ---------------------------------------------------------------------------

class ReadinessResponse(BaseModel):
    date: date
    objective_score: float = Field(..., ge=0.0, le=100.0)
    subjective_score: float = Field(..., ge=0.0, le=100.0)
    final_readiness: float = Field(..., ge=0.0, le=100.0)
    divergence: float = Field(..., ge=0.0)
    divergence_flag: Literal["none", "moderate", "high"]
    traffic_light: Literal["green", "yellow", "red"]
    allostatic_score: float = Field(..., ge=0.0, le=100.0)
    energy_availability: float
    intensity_cap: float = Field(..., ge=0.0, le=1.0)
    insights: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Hormonal profile update
# ---------------------------------------------------------------------------

class HormonalProfileUpdate(BaseModel):
    enabled: bool
    cycle_length_days: int = Field(default=28, ge=21, le=45)
    last_period_start: Optional[date] = None
    tracking_source: Literal["manual", "apple_health"] = "manual"
    notes: Optional[str] = None
```

- [ ] **Step 4: Update `data/energy_coach_check_in_schema.json`**

Replace the entire file content:

```json
{
  "version": "2.0",
  "questions": [
    {
      "id": "work_intensity",
      "question_fr": "Comment s'est passée ta journée de travail ?",
      "options": ["light", "normal", "heavy", "exhausting"],
      "labels_fr": ["Légère", "Normale", "Intense", "Épuisante"],
      "required": true
    },
    {
      "id": "stress_level",
      "question_fr": "As-tu eu des facteurs de stress importants aujourd'hui ?",
      "options": ["none", "mild", "significant"],
      "labels_fr": ["Non", "Oui, léger", "Oui, significatif"],
      "required": true
    },
    {
      "id": "legs_feeling",
      "question_fr": "Comment se sentent tes jambes ?",
      "options": ["fresh", "normal", "heavy", "dead"],
      "labels_fr": ["Fraîches", "Normales", "Lourdes", "Mortes"],
      "required": true
    },
    {
      "id": "energy_global",
      "question_fr": "Comment est ton énergie globale aujourd'hui ?",
      "options": ["great", "ok", "low", "exhausted"],
      "labels_fr": ["Top", "OK", "Basse", "Épuisé(e)"],
      "required": true
    },
    {
      "id": "cycle_phase",
      "question_fr": "Phase de cycle ?",
      "options": ["menstrual", "follicular", "ovulation", "luteal"],
      "labels_fr": ["Menstruelle", "Folliculaire", "Ovulation", "Lutéale"],
      "required": false,
      "condition": "hormonal_profile.enabled == true"
    }
  ],
  "comment": {
    "optional": true,
    "max_chars": 140
  },
  "estimated_duration_seconds": 45,
  "frequency": "daily",
  "optimal_timing": "morning"
}
```

- [ ] **Step 5: Run tests — expect PASS**

```
C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/backend/api/test_energy_cycle.py -v
```

Expected: 5 PASSED

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/checkin.py data/energy_coach_check_in_schema.json tests/backend/api/test_energy_cycle.py
git commit -m "feat(schemas): CheckInInput + ReadinessResponse + HormonalProfileUpdate (V3-C)"
```

---

## Task 2: Migration 0004 + SQLAlchemy model update

**Files:**
- Create: `alembic/versions/0004_energy_snapshot_scores.py`
- Modify: `backend/app/models/schemas.py` (EnergySnapshotModel)

- [ ] **Step 1: Write failing tests**

Append to `tests/backend/api/test_energy_cycle.py`:

```python
# ---------------------------------------------------------------------------
# Task 2 — ORM columns
# ---------------------------------------------------------------------------

def test_energy_snapshot_has_objective_score():
    from sqlalchemy import create_engine, inspect
    from sqlalchemy.pool import StaticPool
    from app.db.database import Base
    from app.db import models as _models  # noqa

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    cols = {c["name"] for c in inspector.get_columns("energy_snapshots")}
    assert "objective_score" in cols
    assert "subjective_score" in cols
```

- [ ] **Step 2: Run — expect FAIL**

```
C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/backend/api/test_energy_cycle.py::test_energy_snapshot_has_objective_score -v
```

Expected: FAILED (columns not in ORM model yet)

- [ ] **Step 3: Create migration file**

Create `alembic/versions/0004_energy_snapshot_scores.py`:

```python
"""Add objective_score + subjective_score to energy_snapshots

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-11 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "energy_snapshots",
        sa.Column("objective_score", sa.Float(), nullable=True),
    )
    op.add_column(
        "energy_snapshots",
        sa.Column("subjective_score", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("energy_snapshots", "subjective_score")
    op.drop_column("energy_snapshots", "objective_score")
```

- [ ] **Step 4: Add columns to EnergySnapshotModel in `backend/app/models/schemas.py`**

Open `backend/app/models/schemas.py`. In `EnergySnapshotModel`, add after `veto_reason`:

```python
    veto_reason = Column(Text, nullable=True)
    objective_score = Column(Float, nullable=True)   # ADD
    subjective_score = Column(Float, nullable=True)  # ADD
    created_at = Column(
```

- [ ] **Step 5: Run test — expect PASS**

```
C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/backend/api/test_energy_cycle.py::test_energy_snapshot_has_objective_score -v
```

- [ ] **Step 6: Run full suite — no regressions**

```
C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/ -x -q
```

- [ ] **Step 7: Commit**

```bash
git add alembic/versions/0004_energy_snapshot_scores.py backend/app/models/schemas.py tests/backend/api/test_energy_cycle.py
git commit -m "feat(db): migration 0004 — objective_score + subjective_score on energy_snapshots"
```

---

## Task 3: EnergyCycleService

**Files:**
- Create: `backend/app/services/energy_cycle_service.py`

### Score computation rules (from spec)

**subjective_score (0–100, higher = more tired/loaded):**
```python
_LEG_SCORES    = {"fresh": 0, "normal": 25, "heavy": 60, "dead": 90}
_ENERGY_SCORES = {"great": 0, "ok": 20,    "low": 55,  "exhausted": 85}
subjective_score = (_LEG_SCORES[legs] + _ENERGY_SCORES[energy]) / 2
```

**objective_score (0–100, higher = more loaded):**
```python
# 100 - (100 - allostatic_score) = allostatic_score reversed to "readiness"
# We store allostatic_score as-is and derive:
objective_score = 100.0 - allostatic_score
# allostatic_score uses: hrv_deviation=0.0 (baseline), sleep_quality=50 (neutral),
# work_intensity + stress_level from check-in, cycle_phase if provided, ea_status="optimal"
```

Wait — actually to store it correctly:
- `allostatic_score` = raw allostatic load (0=no load, 100=max)
- `objective_score` = readiness proxy = `100 - allostatic_score` (0=exhausted, 100=fresh)

So `objective_score` stored = `100 - allostatic_score`

**final_readiness (0–100, higher = more ready):**
```python
divergence = abs(objective_score - (100 - subjective_score))  
# Note: subjective_score is 0-100 where 100=max tired, same as objective_score
# So both are on the "load" scale; readiness = 100 - load
# Actually spec says both are 0-100 readiness scale — let me re-read

# From spec: final_readiness = blend of objective_score + subjective_score
# where both are readiness-direction (100 = best)
# subjective_readiness = 100 - subjective_score_load
# So stored subjective_score should be the readiness value (100 - load)
```

Actually let me re-read the spec carefully:

Spec says:
```
objective_score:    float   # 0–100 (HRV, ACWR, sommeil)
subjective_score:   float   # 0–100 (jambes + énergie check-in)
```

And the insight rule: `ACWR ≥ 1.38 + check-in ≤ 4/10` — so check-in is scored 0-10, not 0-100.

But then: `divergence_flag: "none" | "moderate" | "high"` with thresholds:
- `< 15 pts` → "none"
- `15–30 pts` → "moderate"
- `> 30 pts` → "high"

This implies objective_score and subjective_score are on the same 0-100 scale, both representing readiness (higher = more ready).

So the conversion:
```python
# subjective load → readiness (invert)
_LEG_SCORES    = {"fresh": 0, "normal": 25, "heavy": 60, "dead": 90}
_ENERGY_SCORES = {"great": 0, "ok": 20,    "low": 55,  "exhausted": 85}
subjective_load = (_LEG_SCORES[legs] + _ENERGY_SCORES[energy]) / 2
subjective_score = 100.0 - subjective_load  # readiness direction

# objective = 100 - allostatic_score (readiness direction)
objective_score = 100.0 - allostatic_score
```

Reconciliation:
```python
divergence = abs(objective_score - subjective_score)
weight_subjective = 0.55 if divergence > 25 else 0.40
final_readiness = objective_score * (1 - weight_subjective) + subjective_score * weight_subjective
```

Traffic light:
```python
if final_readiness >= 65: "green"
elif final_readiness >= 40: "yellow"
else: "red"
```

- [ ] **Step 1: Write failing service tests**

Append to `tests/backend/api/test_energy_cycle.py`:

```python
# ---------------------------------------------------------------------------
# Task 3 — EnergyCycleService unit tests
# ---------------------------------------------------------------------------

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import uuid
from datetime import date, timedelta

from app.db.database import Base
from app.db import models as _db_models  # noqa


def _make_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine


def _make_athlete(session, sex="M"):
    from app.db.models import AthleteModel
    athlete = AthleteModel(
        id=str(uuid.uuid4()),
        name="Test",
        age=28,
        sex=sex,
        weight_kg=70.0,
        height_cm=175.0,
        primary_sport="running",
        hours_per_week=8.0,
        sports_json='["running"]',
        goals_json='[]',
        available_days_json='[0,2,4]',
        equipment_json='[]',
    )
    session.add(athlete)
    session.commit()
    return athlete


def test_service_submit_checkin_creates_snapshot():
    from app.services.energy_cycle_service import EnergyCycleService
    from app.schemas.checkin import CheckInInput

    engine = _make_engine()
    Session = sessionmaker(bind=engine)
    session = Session()
    athlete = _make_athlete(session)

    svc = EnergyCycleService()
    checkin = CheckInInput(
        work_intensity="normal",
        stress_level="none",
        legs_feeling="fresh",
        energy_global="great",
    )
    result = svc.submit_checkin(athlete.id, session, checkin)

    assert result.final_readiness > 0
    assert result.traffic_light in ("green", "yellow", "red")
    assert result.divergence >= 0
    assert result.divergence_flag in ("none", "moderate", "high")
    session.close()


def test_service_no_duplicate_checkin_same_day():
    from app.services.energy_cycle_service import EnergyCycleService
    from app.schemas.checkin import CheckInInput
    from fastapi import HTTPException

    engine = _make_engine()
    Session = sessionmaker(bind=engine)
    session = Session()
    athlete = _make_athlete(session)

    svc = EnergyCycleService()
    checkin = CheckInInput(
        work_intensity="normal",
        stress_level="none",
        legs_feeling="normal",
        energy_global="ok",
    )
    svc.submit_checkin(athlete.id, session, checkin)

    with pytest.raises(HTTPException) as exc:
        svc.submit_checkin(athlete.id, session, checkin)
    assert exc.value.status_code == 409


def test_service_get_today_snapshot_returns_none_when_no_checkin():
    from app.services.energy_cycle_service import EnergyCycleService

    engine = _make_engine()
    Session = sessionmaker(bind=engine)
    session = Session()
    athlete = _make_athlete(session)

    svc = EnergyCycleService()
    result = svc.get_today_snapshot(athlete.id, session)
    assert result is None
    session.close()


def test_service_get_today_snapshot_returns_snapshot_after_checkin():
    from app.services.energy_cycle_service import EnergyCycleService
    from app.schemas.checkin import CheckInInput

    engine = _make_engine()
    Session = sessionmaker(bind=engine)
    session = Session()
    athlete = _make_athlete(session)

    svc = EnergyCycleService()
    checkin = CheckInInput(
        work_intensity="light",
        stress_level="none",
        legs_feeling="fresh",
        energy_global="great",
    )
    svc.submit_checkin(athlete.id, session, checkin)
    snap = svc.get_today_snapshot(athlete.id, session)
    assert snap is not None
    session.close()


def test_service_get_history_returns_last_n_days():
    from app.services.energy_cycle_service import EnergyCycleService
    from app.models.schemas import EnergySnapshotModel
    from datetime import datetime, timezone

    engine = _make_engine()
    Session = sessionmaker(bind=engine)
    session = Session()
    athlete = _make_athlete(session)

    # Seed 5 snapshots on different days
    for i in range(5):
        snap = EnergySnapshotModel(
            id=str(uuid.uuid4()),
            athlete_id=athlete.id,
            timestamp=datetime.now(timezone.utc).replace(
                day=max(1, datetime.now(timezone.utc).day - i)
            ),
            allostatic_score=30.0,
            cognitive_load=20.0,
            energy_availability=45.0,
            sleep_quality=70.0,
            recommended_intensity_cap=1.0,
            veto_triggered=False,
            objective_score=70.0,
            subjective_score=80.0,
        )
        session.add(snap)
    session.commit()

    svc = EnergyCycleService()
    history = svc.get_history(athlete.id, session, days=7)
    assert len(history) == 5
    session.close()


def test_subjective_score_calculation():
    """Verify subjective_score formula from spec."""
    from app.services.energy_cycle_service import compute_subjective_score
    # fresh + great → load=0, readiness=100
    assert compute_subjective_score("fresh", "great") == 100.0
    # dead + exhausted → load=(90+85)/2=87.5, readiness=12.5
    assert compute_subjective_score("dead", "exhausted") == pytest.approx(12.5)
    # normal + ok → load=(25+20)/2=22.5, readiness=77.5
    assert compute_subjective_score("normal", "ok") == pytest.approx(77.5)


def test_divergence_flag_thresholds():
    """Verify divergence classification from spec."""
    from app.services.energy_cycle_service import classify_divergence
    assert classify_divergence(10.0) == "none"
    assert classify_divergence(20.0) == "moderate"
    assert classify_divergence(35.0) == "high"
```

- [ ] **Step 2: Run — expect FAIL**

```
C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/backend/api/test_energy_cycle.py -k "service or subjective or divergence" -v
```

Expected: ImportError / all FAILED

- [ ] **Step 3: Create `backend/app/services/energy_cycle_service.py`**

```python
"""EnergyCycleService — V3-C.

Standalone service for the Energy Cycle (Volet 2). Works independently of any
coaching mode or LangGraph. Reads/writes EnergySnapshotModel and
HormonalProfileModel via SQLAlchemy session.

Public API:
    submit_checkin(athlete_id, db, checkin) → ReadinessResponse
    get_today_snapshot(athlete_id, db) → EnergySnapshotModel | None
    get_readiness(athlete_id, db) → ReadinessResponse
    get_history(athlete_id, db, days=28) → list[EnergySnapshotModel]
    update_hormonal_profile(athlete_id, db, data) → HormonalProfileModel

Score conventions (all 0–100, higher = more ready / less loaded):
    subjective_score  = 100 - subjective_load
    objective_score   = 100 - allostatic_score
    final_readiness   = weighted blend (objective 60% / subjective 40%,
                        flips to 45/55 when divergence > 25 pts)
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from ..agents.energy_coach.agent import EnergyCheckIn, EnergyCoach, EnergyInput
from ..db.models import AthleteModel
from ..models.schemas import EnergySnapshotModel, HormonalProfileModel
from ..schemas.checkin import CheckInInput, HormonalProfileUpdate, ReadinessResponse


# ---------------------------------------------------------------------------
# Score helpers (pure functions — exported for unit tests)
# ---------------------------------------------------------------------------

_LEG_SCORES: dict[str, float] = {"fresh": 0.0, "normal": 25.0, "heavy": 60.0, "dead": 90.0}
_ENERGY_SCORES: dict[str, float] = {"great": 0.0, "ok": 20.0, "low": 55.0, "exhausted": 85.0}


def compute_subjective_score(legs_feeling: str, energy_global: str) -> float:
    """Return readiness-direction subjective score (0–100, 100 = perfectly fresh)."""
    load = (_LEG_SCORES[legs_feeling] + _ENERGY_SCORES[energy_global]) / 2.0
    return round(100.0 - load, 2)


def classify_divergence(divergence: float) -> str:
    """Classify abs(objective - subjective) per spec thresholds."""
    if divergence < 15.0:
        return "none"
    if divergence <= 30.0:
        return "moderate"
    return "high"


def traffic_light_from_readiness(final_readiness: float) -> str:
    """Map final readiness to traffic light."""
    if final_readiness >= 65.0:
        return "green"
    if final_readiness >= 40.0:
        return "yellow"
    return "red"


def _build_insights(
    divergence_flag: str,
    legs_feeling: str,
    energy_global: str,
    objective_score: float,
    subjective_score: float,
) -> list[str]:
    """Generate factual insight strings per spec rules."""
    insights: list[str] = []

    if divergence_flag == "high" and subjective_score < 40.0:
        insights.append("HRV normale mais jambes à dead. Ton ressenti compte.")

    return insights


def _snapshot_to_readiness(
    snapshot: EnergySnapshotModel,
    legs_feeling: Optional[str] = None,
    energy_global: Optional[str] = None,
) -> ReadinessResponse:
    """Convert an EnergySnapshotModel → ReadinessResponse."""
    obj = float(snapshot.objective_score) if snapshot.objective_score is not None else 50.0
    subj = float(snapshot.subjective_score) if snapshot.subjective_score is not None else 50.0

    divergence = abs(obj - subj)
    divergence_flag = classify_divergence(divergence)

    weight_subj = 0.55 if divergence > 25.0 else 0.40
    final = round(obj * (1.0 - weight_subj) + subj * weight_subj, 2)

    insights = _build_insights(
        divergence_flag=divergence_flag,
        legs_feeling=legs_feeling or "normal",
        energy_global=energy_global or "ok",
        objective_score=obj,
        subjective_score=subj,
    )

    return ReadinessResponse(
        date=snapshot.timestamp.date(),
        objective_score=round(obj, 2),
        subjective_score=round(subj, 2),
        final_readiness=final,
        divergence=round(divergence, 2),
        divergence_flag=divergence_flag,
        traffic_light=traffic_light_from_readiness(final),
        allostatic_score=round(snapshot.allostatic_score, 2),
        energy_availability=round(snapshot.energy_availability, 2),
        intensity_cap=round(snapshot.recommended_intensity_cap, 2),
        insights=insights,
    )


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class EnergyCycleService:
    """Standalone service — no LangGraph dependency, no coaching mode check."""

    _coach = EnergyCoach()

    def submit_checkin(
        self,
        athlete_id: str,
        db: Session,
        checkin: CheckInInput,
    ) -> ReadinessResponse:
        """Create an EnergySnapshot from the daily check-in.

        Raises 409 if a check-in already exists for today.
        Raises 404 if athlete not found.
        """
        athlete = db.get(AthleteModel, athlete_id)
        if not athlete:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Athlete not found")

        # Duplicate check — one per calendar day
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        existing = (
            db.query(EnergySnapshotModel)
            .filter(
                EnergySnapshotModel.athlete_id == athlete_id,
                EnergySnapshotModel.timestamp >= today_start,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Check-in already submitted for today",
            )

        # --- Compute scores ---

        # Subjective: from legs + energy (readiness direction)
        subjective_score = compute_subjective_score(checkin.legs_feeling, checkin.energy_global)

        # Objective: derive from allostatic (readiness direction = 100 - allostatic_load)
        # Use neutral values for sensor data not yet available (connectors = Phase 9)
        energy_input = EnergyInput(
            hrv_deviation=0.0,          # baseline (no Terra connector yet)
            sleep_quality=50.0,         # neutral
            caloric_intake=2000.0,      # neutral assumption → EA ≈ optimal
            exercise_energy=0.0,
            ffm_kg=max(1.0, athlete.weight_kg * 0.80),  # rough estimate
            check_in=EnergyCheckIn(
                work_intensity=checkin.work_intensity,
                stress_level=checkin.stress_level,
                cycle_phase=checkin.cycle_phase,
            ),
            sex=athlete.sex,
        )
        energy_snapshot = self._coach.create_snapshot(energy_input)
        objective_score = round(100.0 - energy_snapshot.allostatic_score, 2)

        # --- Persist ---
        snap_model = EnergySnapshotModel(
            id=str(uuid.uuid4()),
            athlete_id=athlete_id,
            timestamp=datetime.now(timezone.utc),
            allostatic_score=round(energy_snapshot.allostatic_score, 4),
            cognitive_load=round(energy_snapshot.cognitive_load, 4),
            energy_availability=round(energy_snapshot.energy_availability, 4),
            cycle_phase=checkin.cycle_phase,
            sleep_quality=energy_snapshot.sleep_quality,
            recommended_intensity_cap=energy_snapshot.recommended_intensity_cap,
            veto_triggered=energy_snapshot.veto_triggered,
            veto_reason=energy_snapshot.veto_reason,
            objective_score=objective_score,
            subjective_score=round(subjective_score, 2),
        )
        db.add(snap_model)
        db.commit()
        db.refresh(snap_model)

        return _snapshot_to_readiness(
            snap_model,
            legs_feeling=checkin.legs_feeling,
            energy_global=checkin.energy_global,
        )

    def get_today_snapshot(
        self,
        athlete_id: str,
        db: Session,
    ) -> Optional[EnergySnapshotModel]:
        """Return today's EnergySnapshotModel or None if no check-in today."""
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        return (
            db.query(EnergySnapshotModel)
            .filter(
                EnergySnapshotModel.athlete_id == athlete_id,
                EnergySnapshotModel.timestamp >= today_start,
            )
            .first()
        )

    def get_readiness(
        self,
        athlete_id: str,
        db: Session,
    ) -> ReadinessResponse:
        """Return readiness for today, or the most recent snapshot if none today.

        Raises 404 if no snapshots exist at all.
        """
        snapshot = self.get_today_snapshot(athlete_id, db)

        if snapshot is None:
            # Fall back to most recent
            snapshot = (
                db.query(EnergySnapshotModel)
                .filter(EnergySnapshotModel.athlete_id == athlete_id)
                .order_by(EnergySnapshotModel.timestamp.desc())
                .first()
            )

        if snapshot is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No check-in data found. Submit a check-in first.",
            )

        return _snapshot_to_readiness(snapshot)

    def get_history(
        self,
        athlete_id: str,
        db: Session,
        days: int = 28,
    ) -> list[EnergySnapshotModel]:
        """Return EnergySnapshotModels for the last N days, newest first."""
        since = datetime.now(timezone.utc) - timedelta(days=days)
        return (
            db.query(EnergySnapshotModel)
            .filter(
                EnergySnapshotModel.athlete_id == athlete_id,
                EnergySnapshotModel.timestamp >= since,
            )
            .order_by(EnergySnapshotModel.timestamp.desc())
            .all()
        )

    def update_hormonal_profile(
        self,
        athlete_id: str,
        db: Session,
        data: HormonalProfileUpdate,
    ) -> HormonalProfileModel:
        """Upsert the hormonal profile for the athlete."""
        profile = (
            db.query(HormonalProfileModel)
            .filter(HormonalProfileModel.athlete_id == athlete_id)
            .first()
        )

        if profile is None:
            profile = HormonalProfileModel(
                id=str(uuid.uuid4()),
                athlete_id=athlete_id,
            )
            db.add(profile)

        profile.enabled = data.enabled
        profile.cycle_length_days = data.cycle_length_days
        profile.last_period_start = data.last_period_start
        profile.tracking_source = data.tracking_source
        profile.notes = data.notes

        db.commit()
        db.refresh(profile)
        return profile
```

- [ ] **Step 4: Run service tests — expect PASS**

```
C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/backend/api/test_energy_cycle.py -k "service or subjective or divergence" -v
```

Expected: 8 PASSED

- [ ] **Step 5: Run full suite**

```
C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/ -x -q
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/energy_cycle_service.py tests/backend/api/test_energy_cycle.py
git commit -m "feat(service): EnergyCycleService — submit_checkin, readiness, history, hormonal profile"
```

---

## Task 4: Routes

**Files:**
- Create: `backend/app/routes/checkin.py`

- [ ] **Step 1: Write failing integration tests**

Append to `tests/backend/api/test_energy_cycle.py`:

```python
# ---------------------------------------------------------------------------
# Task 4 — Route integration tests
# ---------------------------------------------------------------------------

def test_post_checkin_creates_readiness(authed_client):
    client, athlete_id = authed_client
    resp = client.post(
        f"/athletes/{athlete_id}/checkin",
        json={
            "work_intensity": "normal",
            "stress_level": "none",
            "legs_feeling": "fresh",
            "energy_global": "great",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert "final_readiness" in body
    assert "traffic_light" in body
    assert body["traffic_light"] in ("green", "yellow", "red")
    assert "intensity_cap" in body


def test_post_checkin_rejects_duplicate(authed_client):
    client, athlete_id = authed_client
    payload = {
        "work_intensity": "normal",
        "stress_level": "none",
        "legs_feeling": "normal",
        "energy_global": "ok",
    }
    client.post(f"/athletes/{athlete_id}/checkin", json=payload)
    resp = client.post(f"/athletes/{athlete_id}/checkin", json=payload)
    assert resp.status_code == 409


def test_post_checkin_requires_auth(client):
    resp = client.post(
        "/athletes/some-id/checkin",
        json={
            "work_intensity": "normal",
            "stress_level": "none",
            "legs_feeling": "normal",
            "energy_global": "ok",
        },
    )
    assert resp.status_code == 401


def test_get_readiness_returns_404_when_no_checkin(authed_client):
    client, athlete_id = authed_client
    resp = client.get(f"/athletes/{athlete_id}/readiness")
    assert resp.status_code == 404


def test_get_readiness_returns_data_after_checkin(authed_client):
    client, athlete_id = authed_client
    client.post(
        f"/athletes/{athlete_id}/checkin",
        json={
            "work_intensity": "light",
            "stress_level": "none",
            "legs_feeling": "fresh",
            "energy_global": "great",
        },
    )
    resp = client.get(f"/athletes/{athlete_id}/readiness")
    assert resp.status_code == 200
    assert "final_readiness" in resp.json()


def test_get_energy_history_returns_list(authed_client):
    client, athlete_id = authed_client
    client.post(
        f"/athletes/{athlete_id}/checkin",
        json={
            "work_intensity": "heavy",
            "stress_level": "significant",
            "legs_feeling": "heavy",
            "energy_global": "low",
        },
    )
    resp = client.get(f"/athletes/{athlete_id}/energy/history")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) == 1


def test_patch_hormonal_profile(authed_client):
    client, athlete_id = authed_client
    from datetime import date
    resp = client.patch(
        f"/athletes/{athlete_id}/hormonal-profile",
        json={
            "enabled": True,
            "cycle_length_days": 28,
            "last_period_start": str(date.today()),
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["enabled"] is True
    assert body["cycle_length_days"] == 28


def test_checkin_with_cycle_phase(authed_client):
    client, athlete_id = authed_client
    resp = client.post(
        f"/athletes/{athlete_id}/checkin",
        json={
            "work_intensity": "normal",
            "stress_level": "mild",
            "legs_feeling": "normal",
            "energy_global": "ok",
            "cycle_phase": "follicular",
        },
    )
    assert resp.status_code == 201


def test_checkin_rejects_invalid_legs_value(authed_client):
    client, athlete_id = authed_client
    resp = client.post(
        f"/athletes/{athlete_id}/checkin",
        json={
            "work_intensity": "normal",
            "stress_level": "none",
            "legs_feeling": "terrible",  # invalid
            "energy_global": "ok",
        },
    )
    assert resp.status_code == 422
```

- [ ] **Step 2: Run — expect FAIL (routes don't exist)**

```
C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/backend/api/test_energy_cycle.py -k "checkin or readiness or history or hormonal" -v
```

Expected: 404/405 errors

- [ ] **Step 3: Create `backend/app/routes/checkin.py`**

```python
"""Energy Cycle routes — V3-C.

Routes (no mode restriction — available to all athletes):
    POST  /athletes/{id}/checkin
    GET   /athletes/{id}/readiness
    GET   /athletes/{id}/energy/history?days=28
    PATCH /athletes/{id}/hormonal-profile
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..dependencies import get_db, get_current_athlete_id
from ..models.schemas import HormonalProfileModel
from ..schemas.checkin import CheckInInput, HormonalProfileUpdate, ReadinessResponse
from ..services.energy_cycle_service import EnergyCycleService

router = APIRouter(prefix="/athletes", tags=["energy"])

DB = Annotated[Session, Depends(get_db)]
_svc = EnergyCycleService()


def _require_own(
    athlete_id: str,
    current_id: Annotated[str, Depends(get_current_athlete_id)],
) -> str:
    from fastapi import HTTPException
    if current_id != athlete_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return athlete_id


class HormonalProfileResponse(BaseModel):
    athlete_id: str
    enabled: bool
    cycle_length_days: int
    last_period_start: str | None
    tracking_source: str
    notes: str | None


class EnergySnapshotSummary(BaseModel):
    date: str
    objective_score: float | None
    subjective_score: float | None
    allostatic_score: float
    energy_availability: float
    intensity_cap: float
    veto_triggered: bool
    traffic_light: str


@router.post(
    "/{athlete_id}/checkin",
    response_model=ReadinessResponse,
    status_code=201,
)
def submit_checkin(
    athlete_id: str,
    body: CheckInInput,
    db: DB,
    _: Annotated[str, Depends(_require_own)],
) -> ReadinessResponse:
    return _svc.submit_checkin(athlete_id, db, body)


@router.get("/{athlete_id}/readiness", response_model=ReadinessResponse)
def get_readiness(
    athlete_id: str,
    db: DB,
    _: Annotated[str, Depends(_require_own)],
) -> ReadinessResponse:
    return _svc.get_readiness(athlete_id, db)


@router.get("/{athlete_id}/energy/history", response_model=list[EnergySnapshotSummary])
def get_energy_history(
    athlete_id: str,
    db: DB,
    _: Annotated[str, Depends(_require_own)],
    days: int = Query(default=28, ge=1, le=90),
) -> list[EnergySnapshotSummary]:
    from app.services.energy_cycle_service import (
        classify_divergence,
        traffic_light_from_readiness,
    )
    snapshots = _svc.get_history(athlete_id, db, days=days)
    result = []
    for s in snapshots:
        obj = s.objective_score or 50.0
        subj = s.subjective_score or 50.0
        div = abs(obj - subj)
        w = 0.55 if div > 25 else 0.40
        final = obj * (1 - w) + subj * w
        result.append(
            EnergySnapshotSummary(
                date=str(s.timestamp.date()),
                objective_score=s.objective_score,
                subjective_score=s.subjective_score,
                allostatic_score=round(s.allostatic_score, 2),
                energy_availability=round(s.energy_availability, 2),
                intensity_cap=round(s.recommended_intensity_cap, 2),
                veto_triggered=s.veto_triggered,
                traffic_light=traffic_light_from_readiness(final),
            )
        )
    return result


@router.patch(
    "/{athlete_id}/hormonal-profile",
    response_model=HormonalProfileResponse,
)
def update_hormonal_profile(
    athlete_id: str,
    body: HormonalProfileUpdate,
    db: DB,
    _: Annotated[str, Depends(_require_own)],
) -> HormonalProfileResponse:
    profile = _svc.update_hormonal_profile(athlete_id, db, body)
    return HormonalProfileResponse(
        athlete_id=profile.athlete_id,
        enabled=profile.enabled,
        cycle_length_days=profile.cycle_length_days,
        last_period_start=(
            str(profile.last_period_start) if profile.last_period_start else None
        ),
        tracking_source=profile.tracking_source,
        notes=profile.notes,
    )
```

- [ ] **Step 4: Mount checkin_router in main.py**

Add import after the other route imports:
```python
from .routes.checkin import router as checkin_router
```

Add at the end of router registrations:
```python
app.include_router(checkin_router)
```

- [ ] **Step 5: Run integration tests — expect PASS**

```
C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/backend/api/test_energy_cycle.py -v
```

Expected: all PASSED

- [ ] **Step 6: Run full suite**

```
C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/ -x -q
```

Expected: ≥1645 passing, no regressions.

- [ ] **Step 7: Commit**

```bash
git add backend/app/routes/checkin.py backend/app/main.py tests/backend/api/test_energy_cycle.py
git commit -m "feat(routes): Energy Cycle — POST /checkin, GET /readiness, GET /energy/history, PATCH /hormonal-profile"
```

---

## Done ✓

After Task 4, V3-C is complete:
- `EnergyCycleService` with 5 methods
- 4 API routes working independently of coaching mode
- `objective_score` + `subjective_score` stored per snapshot
- Readiness reconciliation (60/40 → 45/55 on divergence > 25)
- Traffic light (green/yellow/red)
- Insights rules (spec-compliant)
- All tests passing, no regressions

**Next plan:** V3-D — LangGraph coaching graph (11 nodes, 2 human-in-loop interrupts)
