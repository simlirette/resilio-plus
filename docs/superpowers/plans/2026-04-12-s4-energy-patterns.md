# S-4 Energy Patterns + Proactive Challenges — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `detect_energy_patterns(db)` with 4 energy pattern detectors, a dedicated `head_coach_messages` table for proactive Head Coach messages, and a weekly APScheduler job (Monday mornings).

**Architecture:** New Alembic migration 0005 adds `legs_feeling` + `stress_level` columns to `energy_snapshots` (needed for raw checkin data to detect patterns) and creates `head_coach_messages` table. `EnergyCycleService.submit_checkin()` is updated to persist these raw fields. `detect_energy_patterns(db)` in `sync_scheduler.py` scans last 7 days per athlete and stores messages with 7-day deduplication. Job runs weekly via APScheduler cron trigger on Mondays at 06:00.

**Tech Stack:** Python 3.13, SQLAlchemy 2.0 (sync), Alembic, APScheduler 3.10, pytest, SQLite in-memory for tests.

**Why table dédiée vs JSON field:**
- `head_coach_messages` table enables per-message metadata (is_read, created_at, pattern_type), queryability, unbounded growth without bloating AthleteModel row.
- Consistent with existing time-series tables: `energy_snapshots`, `allostatic_entries`.

---

## File Map

| Action | File | Responsibility |
|---|---|---|
| Create | `alembic/versions/0005_energy_patterns.py` | Migration: add legs_feeling/stress_level to energy_snapshots + create head_coach_messages |
| Modify | `backend/app/models/schemas.py` | Add HeadCoachMessageModel ORM class |
| Modify | `backend/app/db/models.py` | Add head_coach_messages relationship to AthleteModel |
| Modify | `backend/app/services/energy_cycle_service.py` | Persist legs_feeling + stress_level in submit_checkin() |
| Modify | `backend/app/core/sync_scheduler.py` | Add detect_energy_patterns() + weekly Monday job |
| Create | `tests/backend/core/test_energy_patterns.py` | TDD: 4 pattern detectors + scheduler job + dedup |

---

## Task 1: Alembic Migration 0005

**Files:**
- Create: `alembic/versions/0005_energy_patterns.py`

- [ ] **Step 1.1: Write failing migration structure test**

Add to `tests/backend/core/test_energy_patterns.py`:

```python
"""Tests for S-4 energy pattern detection."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.db import models as _db_models  # noqa — registers all ORM models


def _make_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine


def _make_session(engine):
    Session = sessionmaker(bind=engine)
    return Session()


def _make_athlete(session):
    from app.db.models import AthleteModel
    a = AthleteModel(
        id=str(uuid.uuid4()),
        name="PatternTester",
        age=30,
        sex="F",
        weight_kg=60.0,
        height_cm=165.0,
        primary_sport="running",
        hours_per_week=8.0,
        sports_json='["running"]',
        goals_json='[]',
        available_days_json='[0,2,4]',
        equipment_json='[]',
    )
    session.add(a)
    session.commit()
    return a


def test_energy_snapshots_has_legs_feeling_column():
    engine = _make_engine()
    inspector = inspect(engine)
    cols = {c["name"] for c in inspector.get_columns("energy_snapshots")}
    assert "legs_feeling" in cols


def test_energy_snapshots_has_stress_level_column():
    engine = _make_engine()
    inspector = inspect(engine)
    cols = {c["name"] for c in inspector.get_columns("energy_snapshots")}
    assert "stress_level" in cols


def test_head_coach_messages_table_exists():
    engine = _make_engine()
    inspector = inspect(engine)
    assert "head_coach_messages" in inspector.get_table_names()


def test_head_coach_messages_has_required_columns():
    engine = _make_engine()
    inspector = inspect(engine)
    cols = {c["name"] for c in inspector.get_columns("head_coach_messages")}
    assert {"id", "athlete_id", "pattern_type", "message", "created_at", "is_read"} <= cols
```

- [ ] **Step 1.2: Run test to verify it fails**

```bash
cd C:/Users/simon/resilio-plus && C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/backend/core/test_energy_patterns.py -v 2>&1 | tail -20
```

Expected: FAIL — `legs_feeling` not in columns, `head_coach_messages` table not found.

- [ ] **Step 1.3: Create migration file**

Create `alembic/versions/0005_energy_patterns.py`:

```python
"""Add energy pattern detection tables and columns

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-12 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add raw checkin fields to energy_snapshots for pattern analysis
    op.add_column(
        "energy_snapshots",
        sa.Column("legs_feeling", sa.String(), nullable=True),
    )
    op.add_column(
        "energy_snapshots",
        sa.Column("stress_level", sa.String(), nullable=True),
    )
    # Create dedicated head_coach_messages table
    op.create_table(
        "head_coach_messages",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("athlete_id", sa.String(), sa.ForeignKey("athletes.id"), nullable=False),
        sa.Column("pattern_type", sa.String(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("head_coach_messages")
    op.drop_column("energy_snapshots", "stress_level")
    op.drop_column("energy_snapshots", "legs_feeling")
```

- [ ] **Step 1.4: Add HeadCoachMessageModel to schemas.py**

In `backend/app/models/schemas.py`, append at the end:

```python
class HeadCoachMessageModel(Base):
    """Proactive Head Coach messages generated by pattern detection."""
    __tablename__ = "head_coach_messages"

    id = Column(String, primary_key=True)
    athlete_id = Column(String, ForeignKey("athletes.id"), nullable=False)
    pattern_type = Column(String, nullable=False)
    # Values: "heavy_legs" | "chronic_stress" | "persistent_divergence" | "reds_signal"
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False,
                        default=lambda: datetime.now(timezone.utc))
    is_read = Column(Boolean, nullable=False, default=False)

    athlete = relationship("AthleteModel", back_populates="head_coach_messages")
```

- [ ] **Step 1.5: Add legs_feeling + stress_level to EnergySnapshotModel**

In `backend/app/models/schemas.py`, in `EnergySnapshotModel` class, after `subjective_score` column:

```python
    legs_feeling = Column(String, nullable=True)    # "fresh"|"normal"|"heavy"|"dead"
    stress_level = Column(String, nullable=True)    # "none"|"mild"|"significant"
```

- [ ] **Step 1.6: Update AthleteModel relationships in db/models.py**

In `backend/app/db/models.py`, in the `AthleteModel` class, add after `external_plans` relationship:

```python
    head_coach_messages = relationship("HeadCoachMessageModel", back_populates="athlete", cascade="all, delete-orphan")
```

In the import block at the bottom, add `HeadCoachMessageModel`:

```python
from app.models.schemas import (  # noqa: E402, F401
    AllostaticEntryModel,
    EnergySnapshotModel,
    HormonalProfileModel,
    ExternalPlanModel,
    ExternalSessionModel,
    HeadCoachMessageModel,
)
```

- [ ] **Step 1.7: Run migration tests — expect PASS**

```bash
cd C:/Users/simon/resilio-plus && C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/backend/core/test_energy_patterns.py::test_energy_snapshots_has_legs_feeling_column tests/backend/core/test_energy_patterns.py::test_energy_snapshots_has_stress_level_column tests/backend/core/test_energy_patterns.py::test_head_coach_messages_table_exists tests/backend/core/test_energy_patterns.py::test_head_coach_messages_has_required_columns -v 2>&1 | tail -20
```

Expected: 4 PASSED

- [ ] **Step 1.8: Commit**

```bash
cd C:/Users/simon/resilio-plus && git add alembic/versions/0005_energy_patterns.py backend/app/models/schemas.py backend/app/db/models.py && git commit -m "feat(s4): migration 0005 — energy_snapshots raw fields + head_coach_messages table"
```

---

## Task 2: Update submit_checkin() to persist raw fields

**Files:**
- Modify: `backend/app/services/energy_cycle_service.py`
- Modify: `backend/app/models/schemas.py` (EnergySnapshotModel — done in Task 1)
- Test: `tests/backend/core/test_energy_patterns.py`

- [ ] **Step 2.1: Write failing test**

Add to `tests/backend/core/test_energy_patterns.py`:

```python
def test_submit_checkin_persists_legs_feeling():
    from app.services.energy_cycle_service import EnergyCycleService
    from app.schemas.checkin import CheckInInput
    from app.models.schemas import EnergySnapshotModel

    engine = _make_engine()
    session = _make_session(engine)
    athlete = _make_athlete(session)

    svc = EnergyCycleService()
    checkin = CheckInInput(
        work_intensity="heavy",
        stress_level="significant",
        legs_feeling="heavy",
        energy_global="low",
    )
    svc.submit_checkin(athlete.id, session, checkin)

    snap = session.query(EnergySnapshotModel).filter_by(athlete_id=athlete.id).first()
    assert snap.legs_feeling == "heavy"
    session.close()


def test_submit_checkin_persists_stress_level():
    from app.services.energy_cycle_service import EnergyCycleService
    from app.schemas.checkin import CheckInInput
    from app.models.schemas import EnergySnapshotModel

    engine = _make_engine()
    session = _make_session(engine)
    athlete = _make_athlete(session)

    svc = EnergyCycleService()
    checkin = CheckInInput(
        work_intensity="normal",
        stress_level="significant",
        legs_feeling="normal",
        energy_global="ok",
    )
    svc.submit_checkin(athlete.id, session, checkin)

    snap = session.query(EnergySnapshotModel).filter_by(athlete_id=athlete.id).first()
    assert snap.stress_level == "significant"
    session.close()
```

- [ ] **Step 2.2: Run test to verify it fails**

```bash
cd C:/Users/simon/resilio-plus && C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/backend/core/test_energy_patterns.py::test_submit_checkin_persists_legs_feeling tests/backend/core/test_energy_patterns.py::test_submit_checkin_persists_stress_level -v 2>&1 | tail -20
```

Expected: FAIL — `snap.legs_feeling` is None (column exists but not set by service).

- [ ] **Step 2.3: Update submit_checkin() in energy_cycle_service.py**

In `backend/app/services/energy_cycle_service.py`, in the `snap_model = EnergySnapshotModel(...)` constructor, add two new fields after `veto_reason`:

```python
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
            legs_feeling=checkin.legs_feeling,
            stress_level=checkin.stress_level,
        )
```

- [ ] **Step 2.4: Run test to verify it passes**

```bash
cd C:/Users/simon/resilio-plus && C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/backend/core/test_energy_patterns.py::test_submit_checkin_persists_legs_feeling tests/backend/core/test_energy_patterns.py::test_submit_checkin_persists_stress_level -v 2>&1 | tail -10
```

Expected: 2 PASSED

- [ ] **Step 2.5: Commit**

```bash
cd C:/Users/simon/resilio-plus && git add backend/app/services/energy_cycle_service.py tests/backend/core/test_energy_patterns.py && git commit -m "feat(s4): persist legs_feeling + stress_level in submit_checkin()"
```

---

## Task 3: Pattern Detectors (pure functions)

**Files:**
- Modify: `backend/app/core/sync_scheduler.py`
- Test: `tests/backend/core/test_energy_patterns.py`

The 4 pattern detectors are pure functions that take a list of `EnergySnapshotModel` and return `bool`. They are defined as module-level helpers in `sync_scheduler.py`.

- [ ] **Step 3.1: Write failing tests for all 4 patterns**

Add to `tests/backend/core/test_energy_patterns.py`:

```python
# ---------------------------------------------------------------------------
# Helpers for pattern tests
# ---------------------------------------------------------------------------

def _make_snapshot(
    session,
    athlete_id: str,
    days_ago: int,
    legs_feeling: str = "normal",
    stress_level: str = "none",
    objective_score: float = 70.0,
    subjective_score: float = 70.0,
    energy_availability: float = 45.0,
):
    from app.models.schemas import EnergySnapshotModel
    snap = EnergySnapshotModel(
        id=str(uuid.uuid4()),
        athlete_id=athlete_id,
        timestamp=datetime.now(timezone.utc) - timedelta(days=days_ago),
        allostatic_score=30.0,
        cognitive_load=20.0,
        energy_availability=energy_availability,
        sleep_quality=70.0,
        recommended_intensity_cap=1.0,
        veto_triggered=False,
        objective_score=objective_score,
        subjective_score=subjective_score,
        legs_feeling=legs_feeling,
        stress_level=stress_level,
    )
    session.add(snap)
    session.commit()
    return snap


# ---------------------------------------------------------------------------
# Pattern 1: Heavy legs ≥3/7 days
# ---------------------------------------------------------------------------

def test_detect_heavy_legs_triggers_at_3_days():
    from app.core.sync_scheduler import _detect_heavy_legs
    from app.models.schemas import EnergySnapshotModel

    engine = _make_engine()
    session = _make_session(engine)
    athlete = _make_athlete(session)

    # 3 heavy-legs days in last 7
    _make_snapshot(session, athlete.id, days_ago=1, legs_feeling="heavy")
    _make_snapshot(session, athlete.id, days_ago=2, legs_feeling="dead")
    _make_snapshot(session, athlete.id, days_ago=3, legs_feeling="heavy")
    _make_snapshot(session, athlete.id, days_ago=4, legs_feeling="normal")

    snaps = session.query(EnergySnapshotModel).filter_by(athlete_id=athlete.id).all()
    assert _detect_heavy_legs(snaps) is True
    session.close()


def test_detect_heavy_legs_no_trigger_below_3_days():
    from app.core.sync_scheduler import _detect_heavy_legs
    from app.models.schemas import EnergySnapshotModel

    engine = _make_engine()
    session = _make_session(engine)
    athlete = _make_athlete(session)

    # Only 2 heavy-legs days
    _make_snapshot(session, athlete.id, days_ago=1, legs_feeling="heavy")
    _make_snapshot(session, athlete.id, days_ago=2, legs_feeling="normal")
    _make_snapshot(session, athlete.id, days_ago=3, legs_feeling="dead")
    _make_snapshot(session, athlete.id, days_ago=4, legs_feeling="fresh")

    snaps = session.query(EnergySnapshotModel).filter_by(athlete_id=athlete.id).all()
    assert _detect_heavy_legs(snaps) is False
    session.close()


def test_detect_heavy_legs_ignores_snapshots_older_than_7_days():
    from app.core.sync_scheduler import _detect_heavy_legs
    from app.models.schemas import EnergySnapshotModel

    engine = _make_engine()
    session = _make_session(engine)
    athlete = _make_athlete(session)

    # 3 heavy days BUT all older than 7 days — must not trigger
    _make_snapshot(session, athlete.id, days_ago=8, legs_feeling="heavy")
    _make_snapshot(session, athlete.id, days_ago=9, legs_feeling="dead")
    _make_snapshot(session, athlete.id, days_ago=10, legs_feeling="heavy")

    snaps = session.query(EnergySnapshotModel).filter_by(athlete_id=athlete.id).all()
    assert _detect_heavy_legs(snaps) is False
    session.close()


# ---------------------------------------------------------------------------
# Pattern 2: Chronic stress ≥4/7 days
# ---------------------------------------------------------------------------

def test_detect_chronic_stress_triggers_at_4_days():
    from app.core.sync_scheduler import _detect_chronic_stress
    from app.models.schemas import EnergySnapshotModel

    engine = _make_engine()
    session = _make_session(engine)
    athlete = _make_athlete(session)

    for i in range(1, 5):  # 4 "significant" days
        _make_snapshot(session, athlete.id, days_ago=i, stress_level="significant")
    _make_snapshot(session, athlete.id, days_ago=5, stress_level="none")

    snaps = session.query(EnergySnapshotModel).filter_by(athlete_id=athlete.id).all()
    assert _detect_chronic_stress(snaps) is True
    session.close()


def test_detect_chronic_stress_no_trigger_below_4_days():
    from app.core.sync_scheduler import _detect_chronic_stress
    from app.models.schemas import EnergySnapshotModel

    engine = _make_engine()
    session = _make_session(engine)
    athlete = _make_athlete(session)

    # Only 3 significant stress days
    for i in range(1, 4):
        _make_snapshot(session, athlete.id, days_ago=i, stress_level="significant")
    _make_snapshot(session, athlete.id, days_ago=4, stress_level="mild")

    snaps = session.query(EnergySnapshotModel).filter_by(athlete_id=athlete.id).all()
    assert _detect_chronic_stress(snaps) is False
    session.close()


# ---------------------------------------------------------------------------
# Pattern 3: Persistent divergence ≥3 consecutive days (high divergence = >30 pts)
# ---------------------------------------------------------------------------

def test_detect_persistent_divergence_triggers_at_3_consecutive():
    from app.core.sync_scheduler import _detect_persistent_divergence
    from app.models.schemas import EnergySnapshotModel

    engine = _make_engine()
    session = _make_session(engine)
    athlete = _make_athlete(session)

    # 3 consecutive days with divergence >30
    _make_snapshot(session, athlete.id, days_ago=1, objective_score=80.0, subjective_score=40.0)
    _make_snapshot(session, athlete.id, days_ago=2, objective_score=75.0, subjective_score=35.0)
    _make_snapshot(session, athlete.id, days_ago=3, objective_score=70.0, subjective_score=30.0)
    _make_snapshot(session, athlete.id, days_ago=4, objective_score=65.0, subjective_score=60.0)  # divergence=5

    snaps = session.query(EnergySnapshotModel).filter_by(athlete_id=athlete.id).all()
    assert _detect_persistent_divergence(snaps) is True
    session.close()


def test_detect_persistent_divergence_no_trigger_if_gap_breaks_streak():
    from app.core.sync_scheduler import _detect_persistent_divergence
    from app.models.schemas import EnergySnapshotModel

    engine = _make_engine()
    session = _make_session(engine)
    athlete = _make_athlete(session)

    # Day 1 + Day 3 have high divergence, but day 2 breaks the streak
    _make_snapshot(session, athlete.id, days_ago=1, objective_score=80.0, subjective_score=40.0)
    _make_snapshot(session, athlete.id, days_ago=2, objective_score=70.0, subjective_score=68.0)  # divergence=2
    _make_snapshot(session, athlete.id, days_ago=3, objective_score=75.0, subjective_score=35.0)

    snaps = session.query(EnergySnapshotModel).filter_by(athlete_id=athlete.id).all()
    assert _detect_persistent_divergence(snaps) is False
    session.close()


# ---------------------------------------------------------------------------
# Pattern 4: RED-S signal — energy_availability < 30 for ≥3/7 days
# ---------------------------------------------------------------------------

def test_detect_reds_signal_triggers_at_3_days():
    from app.core.sync_scheduler import _detect_reds_signal
    from app.models.schemas import EnergySnapshotModel

    engine = _make_engine()
    session = _make_session(engine)
    athlete = _make_athlete(session)

    _make_snapshot(session, athlete.id, days_ago=1, energy_availability=20.0)
    _make_snapshot(session, athlete.id, days_ago=2, energy_availability=25.0)
    _make_snapshot(session, athlete.id, days_ago=3, energy_availability=28.0)
    _make_snapshot(session, athlete.id, days_ago=4, energy_availability=45.0)

    snaps = session.query(EnergySnapshotModel).filter_by(athlete_id=athlete.id).all()
    assert _detect_reds_signal(snaps) is True
    session.close()


def test_detect_reds_signal_no_trigger_below_3_days():
    from app.core.sync_scheduler import _detect_reds_signal
    from app.models.schemas import EnergySnapshotModel

    engine = _make_engine()
    session = _make_session(engine)
    athlete = _make_athlete(session)

    _make_snapshot(session, athlete.id, days_ago=1, energy_availability=20.0)
    _make_snapshot(session, athlete.id, days_ago=2, energy_availability=45.0)
    _make_snapshot(session, athlete.id, days_ago=3, energy_availability=50.0)

    snaps = session.query(EnergySnapshotModel).filter_by(athlete_id=athlete.id).all()
    assert _detect_reds_signal(snaps) is False
    session.close()
```

- [ ] **Step 3.2: Run test to verify it fails**

```bash
cd C:/Users/simon/resilio-plus && C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/backend/core/test_energy_patterns.py -k "detect_" -v 2>&1 | tail -30
```

Expected: ImportError — `_detect_heavy_legs` not found in `sync_scheduler`.

- [ ] **Step 3.3: Add pattern detector functions to sync_scheduler.py**

Add these functions to `backend/app/core/sync_scheduler.py` after the imports, before `sync_all_strava`:

```python
from datetime import datetime, timedelta, timezone

from ..models.schemas import EnergySnapshotModel


# ---------------------------------------------------------------------------
# Pattern detector helpers (pure functions — testable without DB)
# ---------------------------------------------------------------------------

def _last_7_days(snapshots: list) -> list:
    """Filter snapshots to those within the last 7 days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    return [s for s in snapshots if s.timestamp >= cutoff]


def _detect_heavy_legs(snapshots: list) -> bool:
    """Pattern 1: legs_feeling heavy/dead on ≥3 of last 7 days."""
    recent = _last_7_days(snapshots)
    count = sum(1 for s in recent if s.legs_feeling in ("heavy", "dead"))
    return count >= 3


def _detect_chronic_stress(snapshots: list) -> bool:
    """Pattern 2: stress_level == 'significant' on ≥4 of last 7 days."""
    recent = _last_7_days(snapshots)
    count = sum(1 for s in recent if s.stress_level == "significant")
    return count >= 4


def _detect_persistent_divergence(snapshots: list) -> bool:
    """Pattern 3: divergence >30 pts for ≥3 consecutive days (most recent first)."""
    recent = sorted(_last_7_days(snapshots), key=lambda s: s.timestamp, reverse=True)
    consecutive = 0
    for snap in recent:
        obj = float(snap.objective_score) if snap.objective_score is not None else 50.0
        subj = float(snap.subjective_score) if snap.subjective_score is not None else 50.0
        if abs(obj - subj) > 30.0:
            consecutive += 1
            if consecutive >= 3:
                return True
        else:
            consecutive = 0  # streak broken
    return False


def _detect_reds_signal(snapshots: list) -> bool:
    """Pattern 4: energy_availability < 30.0 on ≥3 of last 7 days (RED-S risk)."""
    recent = _last_7_days(snapshots)
    count = sum(1 for s in recent if float(s.energy_availability) < 30.0)
    return count >= 3
```

- [ ] **Step 3.4: Run pattern detector tests — expect PASS**

```bash
cd C:/Users/simon/resilio-plus && C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/backend/core/test_energy_patterns.py -k "detect_" -v 2>&1 | tail -30
```

Expected: 10 PASSED

- [ ] **Step 3.5: Commit**

```bash
cd C:/Users/simon/resilio-plus && git add backend/app/core/sync_scheduler.py tests/backend/core/test_energy_patterns.py && git commit -m "feat(s4): add 4 energy pattern detector functions with TDD"
```

---

## Task 4: detect_energy_patterns() — DB scanning + message creation

**Files:**
- Modify: `backend/app/core/sync_scheduler.py`
- Test: `tests/backend/core/test_energy_patterns.py`

- [ ] **Step 4.1: Write failing tests**

Add to `tests/backend/core/test_energy_patterns.py`:

```python
# ---------------------------------------------------------------------------
# detect_energy_patterns() integration tests
# ---------------------------------------------------------------------------

def test_detect_energy_patterns_creates_heavy_legs_message():
    from app.core.sync_scheduler import detect_energy_patterns
    from app.models.schemas import HeadCoachMessageModel

    engine = _make_engine()
    session = _make_session(engine)
    athlete = _make_athlete(session)

    # 3 heavy-legs days
    for i in range(1, 4):
        _make_snapshot(session, athlete.id, days_ago=i, legs_feeling="heavy")

    detect_energy_patterns(session)

    msgs = session.query(HeadCoachMessageModel).filter_by(
        athlete_id=athlete.id, pattern_type="heavy_legs"
    ).all()
    assert len(msgs) == 1
    assert msgs[0].is_read is False
    session.close()


def test_detect_energy_patterns_creates_chronic_stress_message():
    from app.core.sync_scheduler import detect_energy_patterns
    from app.models.schemas import HeadCoachMessageModel

    engine = _make_engine()
    session = _make_session(engine)
    athlete = _make_athlete(session)

    for i in range(1, 5):
        _make_snapshot(session, athlete.id, days_ago=i, stress_level="significant")

    detect_energy_patterns(session)

    msgs = session.query(HeadCoachMessageModel).filter_by(
        athlete_id=athlete.id, pattern_type="chronic_stress"
    ).all()
    assert len(msgs) == 1
    session.close()


def test_detect_energy_patterns_no_duplicate_message_within_7_days():
    from app.core.sync_scheduler import detect_energy_patterns
    from app.models.schemas import HeadCoachMessageModel

    engine = _make_engine()
    session = _make_session(engine)
    athlete = _make_athlete(session)

    # 3 heavy-legs days
    for i in range(1, 4):
        _make_snapshot(session, athlete.id, days_ago=i, legs_feeling="heavy")

    # Run detect twice — should still produce only 1 message
    detect_energy_patterns(session)
    detect_energy_patterns(session)

    msgs = session.query(HeadCoachMessageModel).filter_by(
        athlete_id=athlete.id, pattern_type="heavy_legs"
    ).all()
    assert len(msgs) == 1
    session.close()


def test_detect_energy_patterns_no_message_when_no_pattern():
    from app.core.sync_scheduler import detect_energy_patterns
    from app.models.schemas import HeadCoachMessageModel

    engine = _make_engine()
    session = _make_session(engine)
    athlete = _make_athlete(session)

    # Only 1 heavy day — no pattern
    _make_snapshot(session, athlete.id, days_ago=1, legs_feeling="heavy")
    _make_snapshot(session, athlete.id, days_ago=2, legs_feeling="normal")

    detect_energy_patterns(session)

    msgs = session.query(HeadCoachMessageModel).filter_by(athlete_id=athlete.id).all()
    assert len(msgs) == 0
    session.close()


def test_detect_energy_patterns_creates_reds_message():
    from app.core.sync_scheduler import detect_energy_patterns
    from app.models.schemas import HeadCoachMessageModel

    engine = _make_engine()
    session = _make_session(engine)
    athlete = _make_athlete(session)

    for i in range(1, 4):
        _make_snapshot(session, athlete.id, days_ago=i, energy_availability=20.0)

    detect_energy_patterns(session)

    msgs = session.query(HeadCoachMessageModel).filter_by(
        athlete_id=athlete.id, pattern_type="reds_signal"
    ).all()
    assert len(msgs) == 1
    session.close()
```

- [ ] **Step 4.2: Run tests to verify they fail**

```bash
cd C:/Users/simon/resilio-plus && C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/backend/core/test_energy_patterns.py -k "detect_energy_patterns" -v 2>&1 | tail -20
```

Expected: ImportError or AttributeError — `detect_energy_patterns` not defined.

- [ ] **Step 4.3: Implement detect_energy_patterns() in sync_scheduler.py**

Add this function and its helpers to `backend/app/core/sync_scheduler.py`, after the pattern detector helpers and before `sync_all_strava`:

```python
_PATTERN_MESSAGES: dict[str, str] = {
    "heavy_legs": (
        "Tes jambes sont lourdes depuis 3 jours ou plus. "
        "Ton Head Coach recommande une séance de récupération active ou un jour de repos complet."
    ),
    "chronic_stress": (
        "Ton niveau de stress est élevé depuis 4 jours ou plus. "
        "Ton Head Coach recommande de réduire l'intensité et de prioriser le sommeil."
    ),
    "persistent_divergence": (
        "Tes données objectives et subjectives divergent fortement depuis 3 jours consécutifs. "
        "Ton ressenti compte — ton Head Coach ajuste l'intensité à la baisse."
    ),
    "reds_signal": (
        "Ta disponibilité énergétique est basse depuis 3 jours ou plus. "
        "Ton Head Coach recommande d'augmenter les apports caloriques et de réduire le volume."
    ),
}


def _has_recent_message(athlete_id: str, pattern_type: str, db) -> bool:
    """Return True if a message of this pattern_type was created in the last 7 days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    existing = (
        db.query(HeadCoachMessageModel)
        .filter(
            HeadCoachMessageModel.athlete_id == athlete_id,
            HeadCoachMessageModel.pattern_type == pattern_type,
            HeadCoachMessageModel.created_at >= cutoff,
        )
        .first()
    )
    return existing is not None


def _maybe_create_message(athlete_id: str, pattern_type: str, db) -> bool:
    """Create a Head Coach message if no duplicate exists in last 7 days. Returns True if created."""
    if _has_recent_message(athlete_id, pattern_type, db):
        return False
    msg = HeadCoachMessageModel(
        id=str(uuid.uuid4()),
        athlete_id=athlete_id,
        pattern_type=pattern_type,
        message=_PATTERN_MESSAGES[pattern_type],
        created_at=datetime.now(timezone.utc),
        is_read=False,
    )
    db.add(msg)
    return True


def detect_energy_patterns(db) -> dict:
    """
    Scan all athletes' energy snapshots for the last 7 days.
    Detect 4 patterns and store proactive Head Coach messages.
    Called by the weekly APScheduler job (Mondays at 06:00).
    Returns summary dict: {"athletes_scanned": N, "messages_created": M}.
    """
    from ..db.models import AthleteModel

    athletes = db.query(AthleteModel).all()
    athletes_scanned = 0
    messages_created = 0

    for athlete in athletes:
        athletes_scanned += 1
        snaps = (
            db.query(EnergySnapshotModel)
            .filter(EnergySnapshotModel.athlete_id == athlete.id)
            .all()
        )
        if not snaps:
            continue

        pattern_checks = [
            ("heavy_legs", _detect_heavy_legs(snaps)),
            ("chronic_stress", _detect_chronic_stress(snaps)),
            ("persistent_divergence", _detect_persistent_divergence(snaps)),
            ("reds_signal", _detect_reds_signal(snaps)),
        ]
        for pattern_type, triggered in pattern_checks:
            if triggered:
                created = _maybe_create_message(athlete.id, pattern_type, db)
                if created:
                    messages_created += 1

    db.commit()
    return {"athletes_scanned": athletes_scanned, "messages_created": messages_created}
```

Also add these imports at the top of `sync_scheduler.py`:

```python
import uuid
from datetime import datetime, timedelta, timezone

from ..models.schemas import EnergySnapshotModel, HeadCoachMessageModel
```

(Replace the existing `from datetime import datetime, timedelta, timezone` line added in Task 3.)

- [ ] **Step 4.4: Run tests — expect PASS**

```bash
cd C:/Users/simon/resilio-plus && C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/backend/core/test_energy_patterns.py -k "detect_energy_patterns" -v 2>&1 | tail -20
```

Expected: 5 PASSED

- [ ] **Step 4.5: Commit**

```bash
cd C:/Users/simon/resilio-plus && git add backend/app/core/sync_scheduler.py tests/backend/core/test_energy_patterns.py && git commit -m "feat(s4): implement detect_energy_patterns() with deduplication"
```

---

## Task 5: APScheduler weekly job (Monday at 06:00)

**Files:**
- Modify: `backend/app/core/sync_scheduler.py`
- Test: `tests/backend/core/test_energy_patterns.py`

- [ ] **Step 5.1: Write failing test**

Add to `tests/backend/core/test_energy_patterns.py`:

```python
def test_setup_scheduler_has_energy_patterns_job():
    from app.core.sync_scheduler import setup_scheduler
    from apscheduler.schedulers.background import BackgroundScheduler

    scheduler = setup_scheduler()
    try:
        job_ids = [job.id for job in scheduler.get_jobs()]
        assert "energy_patterns_weekly" in job_ids
    finally:
        scheduler.shutdown(wait=False)


def test_energy_patterns_job_runs_weekly_on_monday():
    from app.core.sync_scheduler import setup_scheduler

    scheduler = setup_scheduler()
    try:
        job = next(j for j in scheduler.get_jobs() if j.id == "energy_patterns_weekly")
        # CronTrigger — check fields
        trigger = job.trigger
        assert trigger.__class__.__name__ == "CronTrigger"
        # day_of_week=0 means Monday in APScheduler (0=Mon...6=Sun)
        field_names = [f.name for f in trigger.fields]
        assert "day_of_week" in field_names
    finally:
        scheduler.shutdown(wait=False)
```

- [ ] **Step 5.2: Run test to verify it fails**

```bash
cd C:/Users/simon/resilio-plus && C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/backend/core/test_energy_patterns.py::test_setup_scheduler_has_energy_patterns_job tests/backend/core/test_energy_patterns.py::test_energy_patterns_job_runs_weekly_on_monday -v 2>&1 | tail -15
```

Expected: FAIL — `energy_patterns_weekly` not in job_ids.

- [ ] **Step 5.3: Add weekly job wrapper + scheduler registration**

In `backend/app/core/sync_scheduler.py`, add this wrapper function before `setup_scheduler()`:

```python
def run_energy_patterns_weekly() -> None:
    """Weekly job: detect energy patterns for all athletes and store proactive messages."""
    with SessionLocal() as db:
        try:
            result = detect_energy_patterns(db)
            logger.info(
                "Energy patterns scan: athletes=%d messages_created=%d",
                result["athletes_scanned"], result["messages_created"],
            )
        except Exception:
            logger.warning("Energy patterns scan failed", exc_info=True)
```

In `setup_scheduler()`, add this job registration after the existing 3 jobs (before `scheduler.start()`):

```python
    scheduler.add_job(
        run_energy_patterns_weekly,
        trigger="cron",
        day_of_week="mon",
        hour=6,
        minute=0,
        id="energy_patterns_weekly",
        replace_existing=True,
        misfire_grace_time=3600,
    )
```

Note: import `CronTrigger` is not needed — APScheduler resolves `trigger="cron"` internally.

- [ ] **Step 5.4: Run tests — expect PASS**

```bash
cd C:/Users/simon/resilio-plus && C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/backend/core/test_energy_patterns.py::test_setup_scheduler_has_energy_patterns_job tests/backend/core/test_energy_patterns.py::test_energy_patterns_job_runs_weekly_on_monday -v 2>&1 | tail -15
```

Expected: 2 PASSED

- [ ] **Step 5.5: Commit**

```bash
cd C:/Users/simon/resilio-plus && git add backend/app/core/sync_scheduler.py tests/backend/core/test_energy_patterns.py && git commit -m "feat(s4): add weekly APScheduler job for energy pattern detection (Monday 06:00)"
```

---

## Task 6: Full test suite invariant check + existing scheduler tests

- [ ] **Step 6.1: Run the existing scheduler tests to verify nothing broke**

```bash
cd C:/Users/simon/resilio-plus && C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/backend/core/test_sync_scheduler.py -v 2>&1 | tail -20
```

Expected: All existing tests pass. Note: `test_setup_scheduler_all_jobs_every_6h` may now fail because the new job is a CronTrigger (not an IntervalTrigger). If it fails, fix the test to skip non-interval jobs.

The fix for `test_setup_scheduler_all_jobs_every_6h` in `tests/backend/core/test_sync_scheduler.py`:

```python
def test_setup_scheduler_all_jobs_every_6h():
    scheduler = setup_scheduler()
    try:
        for job in scheduler.get_jobs():
            # Only check interval-based jobs (skip cron jobs like energy_patterns_weekly)
            if job.trigger.__class__.__name__ == "IntervalTrigger":
                assert job.trigger.interval.total_seconds() == 6 * 3600, \
                    f"Job {job.id} interval is not 6h"
    finally:
        scheduler.shutdown(wait=False)
```

- [ ] **Step 6.2: Run all energy pattern tests together**

```bash
cd C:/Users/simon/resilio-plus && C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/backend/core/test_energy_patterns.py -v 2>&1 | tail -30
```

Expected: All tests PASS (≥17 new tests).

- [ ] **Step 6.3: Run full test suite — verify invariant ≥ 1243**

```bash
cd C:/Users/simon/resilio-plus && C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe tests/ --tb=short -q 2>&1 | tail -20
```

Expected: All tests pass, total count ≥ 1243.

- [ ] **Step 6.4: Final commit for test fixes**

```bash
cd C:/Users/simon/resilio-plus && git add tests/backend/core/test_sync_scheduler.py tests/backend/core/test_energy_patterns.py && git commit -m "test(s4): fix interval-only assertion + full suite green"
```

---

## Task 7: Update resilio-master-v3.md + SESSION_REPORT.md + push

- [ ] **Step 7.1: Update resilio-master-v3.md**

In `resilio-master-v3.md`, section 8 (APScheduler block), replace:
```
# detect_energy_patterns() : NON IMPLÉMENTÉ (V3-F)
```
with:
```
scheduler.add_job(run_energy_patterns_weekly, trigger="cron", day_of_week="mon", hour=6)
# → stores messages in head_coach_messages table
```

In section 11 (État d'implémentation), move S-4 items from NON IMPLÉMENTÉ to IMPLÉMENTÉ:
```
| detect_energy_patterns() APScheduler | `core/sync_scheduler.py` | S-4 ✅ |
| Challenges proactifs (messages Head Coach) | `models/schemas.py` (HeadCoachMessageModel) | S-4 ✅ |
```

In CLAUDE.md, update Phase status: `V3-F | detect_energy_patterns() + challenges proactifs | ✅ Complete`

- [ ] **Step 7.2: Append S-4 section to SESSION_REPORT.md**

Append to `SESSION_REPORT.md`:

```markdown
---

## Session S-4 — detect_energy_patterns() + Challenges Proactifs

**Date :** 2026-04-12
**Branche :** session/s4-energy-patterns

### Ce qui a été fait

#### Migration 0005
- Ajout de `legs_feeling` (String, nullable) et `stress_level` (String, nullable) sur `energy_snapshots`
- Création de la table `head_coach_messages` (id, athlete_id, pattern_type, message, created_at, is_read)
- Downgrade fonctionnel : DROP TABLE head_coach_messages + DROP COLUMN

#### HeadCoachMessageModel (backend/app/models/schemas.py)
- Nouveau modèle ORM avec relationship vers AthleteModel
- Relation ajoutée sur AthleteModel.head_coach_messages

#### EnergyCycleService.submit_checkin()
- Persiste maintenant `legs_feeling` et `stress_level` dans EnergySnapshotModel

#### detect_energy_patterns(db) — backend/app/core/sync_scheduler.py
- 4 fonctions détecteur pures : `_detect_heavy_legs`, `_detect_chronic_stress`, `_detect_persistent_divergence`, `_detect_reds_signal`
- Déduplication : pas de message créé si le même pattern_type existe dans les 7 derniers jours
- Retourne `{"athletes_scanned": N, "messages_created": M}`

#### APScheduler weekly job
- `run_energy_patterns_weekly()` wrapper avec SessionLocal()
- Job `energy_patterns_weekly` : cron, day_of_week="mon", hour=6, misfire_grace_time=3600

### Décision architecturale documentée : table dédiée vs JSON

**Choix : table `head_coach_messages`**

Justification : les messages sont une donnée time-series (un message par pattern par semaine par athlète). Un champ JSON sur AthleteModel grandissait sans borne, sans métadonnées par message (lu/non lu, pattern_type, created_at), et sans capacité de requête. La table dédiée est cohérente avec `energy_snapshots` et `allostatic_entries` qui suivent le même pattern.

### Tests ajoutés
- `tests/backend/core/test_energy_patterns.py` — 17+ tests TDD couvrant les 4 patterns, la déduplication, et le scheduler job
- `tests/backend/core/test_sync_scheduler.py` — test existant `test_setup_scheduler_all_jobs_every_6h` corrigé pour ignorer les CronTrigger

### Invariants vérifiés
- pytest ≥ 1243 tests passing ✅
- Branche poussée : session/s4-energy-patterns ✅
```

- [ ] **Step 7.3: Commit docs + push**

```bash
cd C:/Users/simon/resilio-plus && git add SESSION_REPORT.md resilio-master-v3.md CLAUDE.md && git commit -m "docs(s4): update SESSION_REPORT, resilio-master-v3, CLAUDE.md"

git push -u origin session/s4-energy-patterns
```
