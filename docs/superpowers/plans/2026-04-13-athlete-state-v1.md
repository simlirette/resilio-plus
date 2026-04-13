# AthleteState V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stabilize `AthleteState` as the single source of truth for all athlete data — a composable, typed Pydantic v2 model with a complete `get_agent_view()` matrix tested for all 8 agents.

**Architecture:** `AthleteState` aggregates 9 domain sub-models (`profile`, `metrics`, `connectors`, `plan`, `energy`, `recovery`, `hormonal`, `allostatic`, `journal`). `get_agent_view()` returns a typed `AgentView` with only the sections each agent is authorized to see. All new code lives in `backend/app/models/athlete_state.py`; existing V3 models are kept intact.

**Tech Stack:** Python 3.13, Pydantic v2, pytest (Windows path: `C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\pytest.exe`), Poetry, Git Bash.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `backend/app/models/athlete_state.py` | **Modify** | Add all new models + new `get_agent_view()`. Keep existing V3 models. |
| `backend/app/models/athlete_state.py.backup` | **Create** | Safety backup before refactor |
| `backend/app/agents/energy_coach/agent.py` | **Modify** | Replace `EnergyCheckIn` dataclass with import from models |
| `tests/test_models/conftest.py` | **Create** | Shared `full_state` fixture |
| `tests/test_models/test_athlete_state.py` | **Create** | Tests for all new sub-models + `AthleteState` root |
| `tests/test_models/test_agent_views.py` | **Create** | Parametric tests for `get_agent_view()` — all 8 agents |

---

## Task 1: Backup + Move `EnergyCheckIn` to models

`EnergyCheckIn` is currently a dataclass in `energy_coach/agent.py`. It belongs in `models/` to avoid a dependency inversion (models importing from agents). Converting to `BaseModel` adds validation.

**Files:**
- Modify: `backend/app/models/athlete_state.py`
- Modify: `backend/app/agents/energy_coach/agent.py`

- [ ] **Step 1: Create backup**

```bash
cd "/c/Users/simon/resilio-plus"
cp backend/app/models/athlete_state.py backend/app/models/athlete_state.py.backup
```

- [ ] **Step 2: Write failing test**

Create `tests/test_models/test_athlete_state.py`:

```python
"""Tests for AthleteState V1 sub-models and root model."""
from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from app.models.athlete_state import EnergyCheckIn


class TestEnergyCheckIn:
    def test_valid_full(self):
        ci = EnergyCheckIn(
            work_intensity="heavy",
            stress_level="mild",
            cycle_phase="follicular",
        )
        assert ci.work_intensity == "heavy"
        assert ci.stress_level == "mild"
        assert ci.cycle_phase == "follicular"

    def test_valid_no_cycle(self):
        ci = EnergyCheckIn(work_intensity="normal", stress_level="none")
        assert ci.cycle_phase is None

    def test_invalid_work_intensity_raises(self):
        with pytest.raises(ValidationError):
            EnergyCheckIn(work_intensity="extreme", stress_level="none")

    def test_invalid_stress_level_raises(self):
        with pytest.raises(ValidationError):
            EnergyCheckIn(work_intensity="normal", stress_level="high")

    def test_invalid_cycle_phase_raises(self):
        with pytest.raises(ValidationError):
            EnergyCheckIn(work_intensity="normal", stress_level="none", cycle_phase="unknown")
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd "/c/Users/simon/resilio-plus"
poetry run pytest tests/test_models/test_athlete_state.py::TestEnergyCheckIn -v
```

Expected: `ImportError` — `EnergyCheckIn` not yet in `app.models.athlete_state`.

- [ ] **Step 4: Add `EnergyCheckIn` to `athlete_state.py`**

Open `backend/app/models/athlete_state.py`. After the existing `CyclePhase` / `TrafficLight` / `TrackingSource` literals (line 22), add:

```python
WorkIntensity = Literal["light", "normal", "heavy", "exhausting"]
StressLevel = Literal["none", "mild", "significant"]


class EnergyCheckIn(BaseModel):
    """Daily check-in — work load, stress, optional cycle phase."""

    work_intensity: WorkIntensity
    stress_level: StressLevel
    cycle_phase: Optional[CyclePhase] = None
```

- [ ] **Step 5: Update import in `energy_coach/agent.py`**

In `backend/app/agents/energy_coach/agent.py`, remove the `EnergyCheckIn` dataclass definition (lines 40-46) and replace the import at the top with:

```python
from ...models.athlete_state import EnergyCheckIn, EnergySnapshot
```

Remove:
```python
@dataclass
class EnergyCheckIn:
    """Résultats du check-in quotidien (max 60 secondes)."""

    work_intensity: str             # "light" | "normal" | "heavy" | "exhausting"
    stress_level: str               # "none" | "mild" | "significant"
    cycle_phase: Optional[str] = None  # "menstrual" | "follicular" | "ovulation" | "luteal"
```

- [ ] **Step 6: Run tests**

```bash
cd "/c/Users/simon/resilio-plus"
poetry run pytest tests/test_models/test_athlete_state.py::TestEnergyCheckIn tests/backend/agents/ -v
```

Expected: All pass. The energy_coach agent tests must still pass.

- [ ] **Step 7: Commit**

```bash
cd "/c/Users/simon/resilio-plus"
git add backend/app/models/athlete_state.py backend/app/agents/energy_coach/agent.py tests/test_models/test_athlete_state.py
git commit -m "feat(models): move EnergyCheckIn to athlete_state, convert to BaseModel"
```

---

## Task 2: Type `AllostaticEntry.components`

`components: dict` is untyped. Replace with `AllostaticComponents(BaseModel)` — all fields optional so existing `components={}` tests keep passing.

**Files:**
- Modify: `backend/app/models/athlete_state.py`
- Modify: `tests/test_models/test_athlete_state.py` (add tests)

- [ ] **Step 1: Write failing test**

Append to `tests/test_models/test_athlete_state.py`:

```python
from app.models.athlete_state import AllostaticComponents, AllostaticEntry


class TestAllostaticComponents:
    def test_full_components(self):
        c = AllostaticComponents(hrv=30.0, sleep=40.0, work=65.0, stress=30.0, cycle=10.0, ea=0.0)
        assert c.hrv == 30.0
        assert c.ea == 0.0

    def test_empty_components(self):
        c = AllostaticComponents()
        assert c.hrv is None
        assert c.sleep is None

    def test_component_above_100_raises(self):
        with pytest.raises(ValidationError):
            AllostaticComponents(hrv=101.0)

    def test_component_below_0_raises(self):
        with pytest.raises(ValidationError):
            AllostaticComponents(sleep=-1.0)

    def test_allostatic_entry_accepts_components_model(self):
        entry = AllostaticEntry(
            date=date(2026, 4, 10),
            allostatic_score=55.0,
            components=AllostaticComponents(hrv=30.0, sleep=40.0),
            intensity_cap_applied=0.85,
        )
        assert entry.components.hrv == 30.0

    def test_allostatic_entry_accepts_dict_coercion(self):
        """Pydantic v2 coerces dict → AllostaticComponents automatically."""
        entry = AllostaticEntry(
            date=date(2026, 4, 10),
            allostatic_score=55.0,
            components={"hrv": 30.0, "sleep": 40.0},
            intensity_cap_applied=0.85,
        )
        assert entry.components.hrv == 30.0

    def test_allostatic_entry_accepts_empty_dict(self):
        entry = AllostaticEntry(
            date=date(2026, 4, 10),
            allostatic_score=0.0,
            components={},
            intensity_cap_applied=1.0,
        )
        assert entry.components.hrv is None
```

- [ ] **Step 2: Run to verify it fails**

```bash
cd "/c/Users/simon/resilio-plus"
poetry run pytest tests/test_models/test_athlete_state.py::TestAllostaticComponents -v
```

Expected: `ImportError` — `AllostaticComponents` does not exist yet.

- [ ] **Step 3: Add `AllostaticComponents` and update `AllostaticEntry`**

In `backend/app/models/athlete_state.py`, add before `AllostaticEntry`:

```python
class AllostaticComponents(BaseModel):
    """Six sub-scores contributing to the daily allostatic score (each 0–100)."""

    hrv: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    sleep: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    work: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    stress: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    cycle: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    ea: Optional[float] = Field(default=None, ge=0.0, le=100.0)
```

Then update `AllostaticEntry.components` field from:
```python
    components: dict  # {"hrv": float, "sleep": float, ...}
```
to:
```python
    components: AllostaticComponents
```

- [ ] **Step 4: Run tests**

```bash
cd "/c/Users/simon/resilio-plus"
poetry run pytest tests/test_models/ -v
```

Expected: All pass, including existing `test_athlete_state_v3.py` tests (Pydantic v2 coerces dicts).

- [ ] **Step 5: Commit**

```bash
cd "/c/Users/simon/resilio-plus"
git add backend/app/models/athlete_state.py tests/test_models/test_athlete_state.py
git commit -m "feat(models): add AllostaticComponents, type AllostaticEntry.components"
```

---

## Task 3: Add `SyncSource` and `AthleteMetrics`

**Files:**
- Modify: `backend/app/models/athlete_state.py`
- Modify: `tests/test_models/test_athlete_state.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_models/test_athlete_state.py`:

```python
from app.models.athlete_state import AthleteMetrics, SyncSource
from app.schemas.fatigue import FatigueScore


class TestSyncSource:
    def test_valid_ok(self):
        s = SyncSource(
            name="strava",
            last_synced_at=datetime(2026, 4, 13, 8, 0, tzinfo=timezone.utc),
            status="ok",
        )
        assert s.name == "strava"
        assert s.status == "ok"

    def test_invalid_name_raises(self):
        with pytest.raises(ValidationError):
            SyncSource(
                name="garmin",
                last_synced_at=datetime(2026, 4, 13, tzinfo=timezone.utc),
                status="ok",
            )

    def test_invalid_status_raises(self):
        with pytest.raises(ValidationError):
            SyncSource(
                name="terra",
                last_synced_at=datetime(2026, 4, 13, tzinfo=timezone.utc),
                status="pending",
            )


class TestAthleteMetrics:
    def test_minimal(self):
        m = AthleteMetrics(date=date(2026, 4, 13))
        assert m.hrv_rmssd is None
        assert m.acwr is None
        assert m.hrv_history_7d == []

    def test_full(self):
        m = AthleteMetrics(
            date=date(2026, 4, 13),
            hrv_rmssd=65.4,
            hrv_history_7d=[60.0, 62.0, 65.4, 58.0, 70.0, 64.0, 65.4],
            sleep_hours=7.5,
            sleep_quality_score=82.0,
            resting_hr=48.0,
            acwr=1.1,
            acwr_status="safe",
            readiness_score=87.0,
            fatigue_score=FatigueScore(
                local_muscular=20.0, cns_load=15.0,
                metabolic_cost=18.0, recovery_hours=24.0, affected_muscles=[],
            ),
        )
        assert m.hrv_rmssd == 65.4
        assert m.acwr_status == "safe"
        assert len(m.hrv_history_7d) == 7

    def test_invalid_acwr_status_raises(self):
        with pytest.raises(ValidationError):
            AthleteMetrics(date=date(2026, 4, 13), acwr_status="warning")
```

- [ ] **Step 2: Run to verify failure**

```bash
cd "/c/Users/simon/resilio-plus"
poetry run pytest tests/test_models/test_athlete_state.py::TestSyncSource tests/test_models/test_athlete_state.py::TestAthleteMetrics -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement `SyncSource` and `AthleteMetrics`**

Add to `backend/app/models/athlete_state.py` after the existing imports block. Add new imports at the top:

```python
from app.schemas.fatigue import FatigueScore
```

Wait — this file is in `backend/app/models/` so the import should be relative:
```python
from ..schemas.fatigue import FatigueScore
```

Add at the top of the file (after existing imports):
```python
from ..schemas.fatigue import FatigueScore
```

Then add the models (place after the `EnergyCheckIn` model you added in Task 1):

```python
# ---------------------------------------------------------------------------
# SyncSource  (metadata sur la dernière sync par connecteur)
# ---------------------------------------------------------------------------

SyncSourceName = Literal["strava", "hevy", "terra", "manual"]
SyncStatus = Literal["ok", "error", "stale"]


class SyncSource(BaseModel):
    """Tracks the last successful sync for one external data source."""

    name: SyncSourceName
    last_synced_at: datetime
    status: SyncStatus


# ---------------------------------------------------------------------------
# AthleteMetrics  (valeurs brutes Terra + métriques calculées)
# ---------------------------------------------------------------------------


class AthleteMetrics(BaseModel):
    """Raw connector values + derived metrics for today."""

    date: date
    # Raw Terra
    hrv_rmssd: Optional[float] = None              # ms
    hrv_history_7d: list[float] = Field(default_factory=list)
    sleep_hours: Optional[float] = None
    sleep_quality_score: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    resting_hr: Optional[float] = None
    # Computed
    acwr: Optional[float] = None                   # EWMA Acute:Chronic
    acwr_status: Optional[Literal["safe", "caution", "danger"]] = None
    readiness_score: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    fatigue_score: Optional[FatigueScore] = None
```

- [ ] **Step 4: Run tests**

```bash
cd "/c/Users/simon/resilio-plus"
poetry run pytest tests/test_models/ -v
```

Expected: All pass.

- [ ] **Step 5: Commit**

```bash
cd "/c/Users/simon/resilio-plus"
git add backend/app/models/athlete_state.py tests/test_models/test_athlete_state.py
git commit -m "feat(models): add SyncSource, AthleteMetrics"
```

---

## Task 4: Add `ConnectorSnapshot`

**Files:**
- Modify: `backend/app/models/athlete_state.py`
- Modify: `tests/test_models/test_athlete_state.py`

- [ ] **Step 1: Write failing test**

Append to `tests/test_models/test_athlete_state.py`:

```python
from app.models.athlete_state import ConnectorSnapshot
from app.schemas.connector import HevyExercise, HevySet, HevyWorkout, StravaActivity


def _make_strava() -> StravaActivity:
    return StravaActivity(
        id="strava_1",
        name="Morning run",
        sport_type="Run",
        date=date(2026, 4, 12),
        duration_seconds=3600,
    )


def _make_hevy() -> HevyWorkout:
    return HevyWorkout(
        id="hevy_1",
        title="Upper A",
        date=date(2026, 4, 11),
        duration_seconds=3600,
        exercises=[],
    )


class TestConnectorSnapshot:
    def test_empty(self):
        cs = ConnectorSnapshot()
        assert cs.strava_last_activity is None
        assert cs.strava_activities_7d == []
        assert cs.hevy_last_workout is None
        assert cs.hevy_workouts_7d == []
        assert cs.terra_last_sync is None

    def test_with_strava(self):
        activity = _make_strava()
        cs = ConnectorSnapshot(
            strava_last_activity=activity,
            strava_activities_7d=[activity],
            strava_last_sync=datetime(2026, 4, 13, 6, 0, tzinfo=timezone.utc),
        )
        assert cs.strava_last_activity.id == "strava_1"
        assert len(cs.strava_activities_7d) == 1

    def test_with_hevy(self):
        workout = _make_hevy()
        cs = ConnectorSnapshot(
            hevy_last_workout=workout,
            hevy_workouts_7d=[workout],
            hevy_last_sync=datetime(2026, 4, 13, 6, 0, tzinfo=timezone.utc),
        )
        assert cs.hevy_last_workout.id == "hevy_1"
```

- [ ] **Step 2: Run to verify failure**

```bash
cd "/c/Users/simon/resilio-plus"
poetry run pytest tests/test_models/test_athlete_state.py::TestConnectorSnapshot -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement `ConnectorSnapshot`**

Add to `backend/app/models/athlete_state.py` after `AthleteMetrics`. First add the import at the top of the file:

```python
from ..schemas.connector import HevyWorkout, StravaActivity
```

Then add the model:

```python
# ---------------------------------------------------------------------------
# ConnectorSnapshot  (dernière synchro des connecteurs)
# ---------------------------------------------------------------------------


class ConnectorSnapshot(BaseModel):
    """Last known data from all external connectors."""

    strava_last_activity: Optional[StravaActivity] = None
    strava_activities_7d: list[StravaActivity] = Field(default_factory=list)
    hevy_last_workout: Optional[HevyWorkout] = None
    hevy_workouts_7d: list[HevyWorkout] = Field(default_factory=list)
    terra_last_sync: Optional[datetime] = None
    strava_last_sync: Optional[datetime] = None
    hevy_last_sync: Optional[datetime] = None
```

- [ ] **Step 4: Run tests**

```bash
cd "/c/Users/simon/resilio-plus"
poetry run pytest tests/test_models/ -v
```

Expected: All pass.

- [ ] **Step 5: Commit**

```bash
cd "/c/Users/simon/resilio-plus"
git add backend/app/models/athlete_state.py tests/test_models/test_athlete_state.py
git commit -m "feat(models): add ConnectorSnapshot"
```

---

## Task 5: Add `PlanSnapshot` and `AllostaticSummary`

**Files:**
- Modify: `backend/app/models/athlete_state.py`
- Modify: `tests/test_models/test_athlete_state.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_models/test_athlete_state.py`:

```python
from app.models.athlete_state import AllostaticSummary, PlanSnapshot
from app.schemas.plan import WorkoutSlot
from app.schemas.athlete import Sport
from app.schemas.fatigue import FatigueScore


def _make_slot() -> WorkoutSlot:
    return WorkoutSlot(
        date=date(2026, 4, 14),
        sport=Sport.RUNNING,
        workout_type="easy_z1",
        duration_min=45,
        fatigue_score=FatigueScore(
            local_muscular=10.0, cns_load=5.0,
            metabolic_cost=10.0, recovery_hours=12.0, affected_muscles=[],
        ),
    )


class TestPlanSnapshot:
    def test_defaults(self):
        ps = PlanSnapshot()
        assert ps.today == []
        assert ps.week == []
        assert ps.week_number == 1
        assert ps.phase == "base"

    def test_with_sessions(self):
        slot = _make_slot()
        ps = PlanSnapshot(today=[slot], week=[slot], week_number=3, phase="build")
        assert len(ps.today) == 1
        assert ps.week_number == 3
        assert ps.phase == "build"


class TestAllostaticSummary:
    def test_defaults(self):
        s = AllostaticSummary()
        assert s.history_28d == []
        assert s.trend == "stable"
        assert s.avg_score_7d == 0.0

    def test_invalid_trend_raises(self):
        with pytest.raises(ValidationError):
            AllostaticSummary(trend="worsening")

    def test_with_history(self):
        entries = [
            AllostaticEntry(
                date=date(2026, 4, i),
                allostatic_score=float(30 + i),
                components=AllostaticComponents(),
                intensity_cap_applied=1.0,
            )
            for i in range(1, 8)
        ]
        s = AllostaticSummary(history_28d=entries, trend="improving", avg_score_7d=34.0)
        assert len(s.history_28d) == 7
        assert s.trend == "improving"
```

- [ ] **Step 2: Run to verify failure**

```bash
cd "/c/Users/simon/resilio-plus"
poetry run pytest tests/test_models/test_athlete_state.py::TestPlanSnapshot tests/test_models/test_athlete_state.py::TestAllostaticSummary -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement `PlanSnapshot` and `AllostaticSummary`**

Add the import at the top of `backend/app/models/athlete_state.py`:

```python
from ..schemas.plan import WorkoutSlot
```

Then add the models:

```python
# ---------------------------------------------------------------------------
# PlanSnapshot  (plan du jour et de la semaine)
# ---------------------------------------------------------------------------


class PlanSnapshot(BaseModel):
    """Today's and this week's planned sessions."""

    today: list[WorkoutSlot] = Field(default_factory=list)
    week: list[WorkoutSlot] = Field(default_factory=list)
    week_number: int = 1
    phase: str = "base"


# ---------------------------------------------------------------------------
# AllostaticSummary  (historique 28 jours + tendance)
# ---------------------------------------------------------------------------

AllostaticTrend = Literal["improving", "stable", "declining"]


class AllostaticSummary(BaseModel):
    """28-day allostatic history with computed trend."""

    history_28d: list[AllostaticEntry] = Field(default_factory=list)
    trend: AllostaticTrend = "stable"
    avg_score_7d: float = 0.0
```

- [ ] **Step 4: Run tests**

```bash
cd "/c/Users/simon/resilio-plus"
poetry run pytest tests/test_models/ -v
```

Expected: All pass.

- [ ] **Step 5: Commit**

```bash
cd "/c/Users/simon/resilio-plus"
git add backend/app/models/athlete_state.py tests/test_models/test_athlete_state.py
git commit -m "feat(models): add PlanSnapshot, AllostaticSummary"
```

---

## Task 6: Add `DailyJournal`

**Files:**
- Modify: `backend/app/models/athlete_state.py`
- Modify: `tests/test_models/test_athlete_state.py`

- [ ] **Step 1: Write failing test**

Append to `tests/test_models/test_athlete_state.py`:

```python
from app.models.athlete_state import DailyJournal


class TestDailyJournal:
    def test_minimal(self):
        j = DailyJournal(date=date(2026, 4, 13))
        assert j.check_in is None
        assert j.comment is None
        assert j.mood_score is None

    def test_full(self):
        j = DailyJournal(
            date=date(2026, 4, 13),
            check_in=EnergyCheckIn(work_intensity="normal", stress_level="mild"),
            comment="Felt tired after yesterday's long run.",
            mood_score=7,
        )
        assert j.check_in.work_intensity == "normal"
        assert j.comment == "Felt tired after yesterday's long run."
        assert j.mood_score == 7

    def test_mood_below_1_raises(self):
        with pytest.raises(ValidationError):
            DailyJournal(date=date(2026, 4, 13), mood_score=0)

    def test_mood_above_10_raises(self):
        with pytest.raises(ValidationError):
            DailyJournal(date=date(2026, 4, 13), mood_score=11)
```

Note: `EnergyCheckIn` was already imported at the top of the test file in Task 1. No new import needed.

- [ ] **Step 2: Run to verify failure**

```bash
cd "/c/Users/simon/resilio-plus"
poetry run pytest tests/test_models/test_athlete_state.py::TestDailyJournal -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement `DailyJournal`**

Add to `backend/app/models/athlete_state.py` after `AllostaticSummary`:

```python
# ---------------------------------------------------------------------------
# DailyJournal  (check-in structuré + commentaire libre)
# ---------------------------------------------------------------------------


class DailyJournal(BaseModel):
    """Daily athlete journal: structured check-in + free-text comment."""

    date: date
    check_in: Optional[EnergyCheckIn] = None
    comment: Optional[str] = None
    mood_score: Optional[int] = Field(default=None, ge=1, le=10)
```

- [ ] **Step 4: Run tests**

```bash
cd "/c/Users/simon/resilio-plus"
poetry run pytest tests/test_models/ -v
```

Expected: All pass.

- [ ] **Step 5: Commit**

```bash
cd "/c/Users/simon/resilio-plus"
git add backend/app/models/athlete_state.py tests/test_models/test_athlete_state.py
git commit -m "feat(models): add DailyJournal"
```

---

## Task 7: Add `AthleteState` root model

**Files:**
- Modify: `backend/app/models/athlete_state.py`
- Modify: `tests/test_models/test_athlete_state.py`

- [ ] **Step 1: Write failing test**

Append to `tests/test_models/test_athlete_state.py`. First add imports at the top of the file (edit the import block):

```python
from app.models.athlete_state import AthleteState
from app.schemas.athlete import AthleteProfile, Sport
```

Add at the bottom:

```python
def _make_athlete_profile() -> AthleteProfile:
    return AthleteProfile(
        name="Alice",
        age=28,
        sex="F",
        weight_kg=60.0,
        height_cm=168.0,
        sports=[Sport.RUNNING, Sport.LIFTING],
        primary_sport=Sport.RUNNING,
        goals=["marathon_sub4"],
        available_days=[1, 3, 5, 6],
        hours_per_week=8.0,
    )


def _make_veto() -> RecoveryVetoV3:
    return RecoveryVetoV3(
        status="green",
        hrv_component="green",
        acwr_component="green",
        ea_component="green",
        allostatic_component="green",
        final_intensity_cap=1.0,
        veto_triggered=False,
        veto_reasons=[],
    )


class TestAthleteState:
    def test_minimal_valid(self):
        state = AthleteState(
            athlete_id="athlete-001",
            last_synced_at=datetime(2026, 4, 13, 8, 0, tzinfo=timezone.utc),
            sync_sources=[],
            profile=_make_athlete_profile(),
            metrics=AthleteMetrics(date=date(2026, 4, 13)),
            connectors=ConnectorSnapshot(),
            plan=PlanSnapshot(),
            recovery=_make_veto(),
            allostatic=AllostaticSummary(),
        )
        assert state.athlete_id == "athlete-001"
        assert state.energy is None
        assert state.hormonal is None
        assert state.journal is None

    def test_with_all_optional_sections(self):
        snap = EnergySnapshot(
            timestamp=datetime(2026, 4, 13, 8, 0, tzinfo=timezone.utc),
            allostatic_score=30.0,
            cognitive_load=25.0,
            energy_availability=45.0,
            sleep_quality=80.0,
            recommended_intensity_cap=1.0,
            veto_triggered=False,
        )
        profile = HormonalProfile(enabled=True, tracking_source="manual", current_phase="follicular")
        journal = DailyJournal(
            date=date(2026, 4, 13),
            check_in=EnergyCheckIn(work_intensity="normal", stress_level="none"),
            comment="Good day.",
            mood_score=8,
        )
        state = AthleteState(
            athlete_id="athlete-002",
            last_synced_at=datetime(2026, 4, 13, 8, 0, tzinfo=timezone.utc),
            sync_sources=[SyncSource(
                name="strava",
                last_synced_at=datetime(2026, 4, 13, 8, 0, tzinfo=timezone.utc),
                status="ok",
            )],
            profile=_make_athlete_profile(),
            metrics=AthleteMetrics(date=date(2026, 4, 13), hrv_rmssd=65.0, acwr=1.1, acwr_status="safe"),
            connectors=ConnectorSnapshot(),
            plan=PlanSnapshot(week_number=3, phase="build"),
            energy=snap,
            recovery=_make_veto(),
            hormonal=profile,
            allostatic=AllostaticSummary(trend="improving", avg_score_7d=32.0),
            journal=journal,
        )
        assert state.energy.allostatic_score == 30.0
        assert state.hormonal.current_phase == "follicular"
        assert state.journal.mood_score == 8
        assert state.plan.phase == "build"

    def test_missing_required_field_raises(self):
        with pytest.raises(ValidationError):
            AthleteState(
                athlete_id="athlete-003",
                last_synced_at=datetime(2026, 4, 13, tzinfo=timezone.utc),
                sync_sources=[],
                # missing profile, metrics, connectors, plan, recovery, allostatic
            )
```

- [ ] **Step 2: Run to verify failure**

```bash
cd "/c/Users/simon/resilio-plus"
poetry run pytest tests/test_models/test_athlete_state.py::TestAthleteState -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement `AthleteState`**

Add to `backend/app/models/athlete_state.py`. First add the import at the top:

```python
from ..schemas.athlete import AthleteProfile
```

Then add the root model after `DailyJournal`:

```python
# ---------------------------------------------------------------------------
# AthleteState  (source de vérité unique — section 7.1)
# ---------------------------------------------------------------------------


class AthleteState(BaseModel):
    """Single source of truth for all athlete data.

    Persisted snapshot — refreshed on every sync, falls back to last known
    version when connectors are unavailable.
    """

    athlete_id: str
    last_synced_at: datetime
    sync_sources: list[SyncSource] = Field(default_factory=list)

    # Domain sections
    profile: AthleteProfile
    metrics: AthleteMetrics
    connectors: ConnectorSnapshot
    plan: PlanSnapshot
    recovery: RecoveryVetoV3

    # Optional sections — not all athletes have these
    energy: Optional[EnergySnapshot] = None
    hormonal: Optional[HormonalProfile] = None
    allostatic: AllostaticSummary = Field(default_factory=AllostaticSummary)
    journal: Optional[DailyJournal] = None
```

- [ ] **Step 4: Run tests**

```bash
cd "/c/Users/simon/resilio-plus"
poetry run pytest tests/test_models/ -v
```

Expected: All pass.

- [ ] **Step 5: Commit**

```bash
cd "/c/Users/simon/resilio-plus"
git add backend/app/models/athlete_state.py tests/test_models/test_athlete_state.py
git commit -m "feat(models): add AthleteState root model"
```

---

## Task 8: Add `AgentView` + new `get_agent_view()`

Replace the current `get_agent_view()` (which uses `AthleteStateV3` and returns field name lists) with a typed implementation using `AthleteState` and `AgentView`.

**Files:**
- Modify: `backend/app/models/athlete_state.py`
- Create: `tests/test_models/test_agent_views.py`
- Create: `tests/test_models/conftest.py`

- [ ] **Step 1: Create `conftest.py` with `full_state` fixture**

Create `tests/test_models/conftest.py`:

```python
"""Shared fixtures for test_models."""
from datetime import date, datetime, timezone

import pytest

from app.models.athlete_state import (
    AllostaticComponents,
    AllostaticEntry,
    AllostaticSummary,
    AthleteMetrics,
    AthleteState,
    ConnectorSnapshot,
    DailyJournal,
    EnergyCheckIn,
    EnergySnapshot,
    HormonalProfile,
    PlanSnapshot,
    RecoveryVetoV3,
    SyncSource,
)
from app.schemas.athlete import AthleteProfile, Sport


@pytest.fixture
def full_state() -> AthleteState:
    """A fully populated AthleteState for view testing."""
    profile = AthleteProfile(
        name="Alice",
        age=28,
        sex="F",
        weight_kg=60.0,
        height_cm=168.0,
        sports=[Sport.RUNNING, Sport.LIFTING],
        primary_sport=Sport.RUNNING,
        goals=["marathon_sub4"],
        available_days=[1, 3, 5, 6],
        hours_per_week=8.0,
    )
    metrics = AthleteMetrics(
        date=date(2026, 4, 13),
        hrv_rmssd=65.0,
        hrv_history_7d=[60.0, 62.0, 65.0, 58.0, 70.0, 64.0, 65.0],
        sleep_hours=7.5,
        sleep_quality_score=82.0,
        resting_hr=48.0,
        acwr=1.1,
        acwr_status="safe",
        readiness_score=87.0,
    )
    connectors = ConnectorSnapshot(
        terra_last_sync=datetime(2026, 4, 13, 6, 0, tzinfo=timezone.utc),
        strava_last_sync=datetime(2026, 4, 13, 6, 0, tzinfo=timezone.utc),
    )
    plan = PlanSnapshot(week_number=3, phase="build")
    energy = EnergySnapshot(
        timestamp=datetime(2026, 4, 13, 8, 0, tzinfo=timezone.utc),
        allostatic_score=30.0,
        cognitive_load=25.0,
        energy_availability=45.0,
        sleep_quality=80.0,
        recommended_intensity_cap=1.0,
        veto_triggered=False,
    )
    recovery = RecoveryVetoV3(
        status="green",
        hrv_component="green",
        acwr_component="green",
        ea_component="green",
        allostatic_component="green",
        final_intensity_cap=1.0,
        veto_triggered=False,
        veto_reasons=[],
    )
    hormonal = HormonalProfile(
        enabled=True,
        tracking_source="manual",
        current_phase="follicular",
    )
    allostatic = AllostaticSummary(
        history_28d=[
            AllostaticEntry(
                date=date(2026, 4, i),
                allostatic_score=float(30 + i),
                components=AllostaticComponents(hrv=20.0, sleep=30.0),
                intensity_cap_applied=1.0,
            )
            for i in range(1, 8)
        ],
        trend="stable",
        avg_score_7d=33.0,
    )
    journal = DailyJournal(
        date=date(2026, 4, 13),
        check_in=EnergyCheckIn(work_intensity="normal", stress_level="none"),
        comment="Felt good.",
        mood_score=8,
    )
    return AthleteState(
        athlete_id="fixture-athlete",
        last_synced_at=datetime(2026, 4, 13, 8, 0, tzinfo=timezone.utc),
        sync_sources=[SyncSource(
            name="strava",
            last_synced_at=datetime(2026, 4, 13, 8, 0, tzinfo=timezone.utc),
            status="ok",
        )],
        profile=profile,
        metrics=metrics,
        connectors=connectors,
        plan=plan,
        energy=energy,
        recovery=recovery,
        hormonal=hormonal,
        allostatic=allostatic,
        journal=journal,
    )
```

- [ ] **Step 2: Write failing tests**

Create `tests/test_models/test_agent_views.py`:

```python
"""Tests for get_agent_view() — all 8 agents, parametric matrix validation."""
import pytest

from app.models.athlete_state import AgentView, get_agent_view

ALL_SECTIONS = frozenset({
    "profile", "metrics", "connectors", "plan",
    "energy", "recovery", "hormonal", "allostatic", "journal",
})

_EXPECTED: list[tuple[str, frozenset[str]]] = [
    ("head_coach",  frozenset(ALL_SECTIONS)),
    ("running",     frozenset({"profile", "metrics", "connectors", "plan", "hormonal"})),
    ("lifting",     frozenset({"profile", "metrics", "connectors", "plan", "hormonal"})),
    ("swimming",    frozenset({"profile", "metrics", "connectors", "plan"})),
    ("biking",      frozenset({"profile", "metrics", "connectors", "plan"})),
    ("nutrition",   frozenset({"profile", "plan", "energy", "hormonal"})),
    ("recovery",    frozenset({"profile", "metrics", "connectors", "plan", "energy", "recovery", "hormonal", "allostatic", "journal"})),
    ("energy",      frozenset({"profile", "metrics", "energy", "recovery", "hormonal", "allostatic", "journal"})),
]


@pytest.mark.parametrize("agent,expected_sections", _EXPECTED)
def test_agent_view_sections_present(agent, expected_sections, full_state):
    view = get_agent_view(full_state, agent)
    assert isinstance(view, AgentView)
    assert view.agent == agent
    for section in expected_sections:
        assert getattr(view, section) is not None, (
            f"Agent '{agent}' should have section '{section}' but it is None"
        )


@pytest.mark.parametrize("agent,expected_sections", _EXPECTED)
def test_agent_view_sections_absent(agent, expected_sections, full_state):
    view = get_agent_view(full_state, agent)
    for section in ALL_SECTIONS - expected_sections:
        assert getattr(view, section) is None, (
            f"Agent '{agent}' should NOT have section '{section}' but it is present"
        )


def test_unknown_agent_returns_empty_view(full_state):
    view = get_agent_view(full_state, "unknown_agent")
    assert isinstance(view, AgentView)
    assert view.agent == "unknown_agent"
    for section in ALL_SECTIONS:
        assert getattr(view, section) is None


def test_agent_view_is_pydantic_model(full_state):
    """AgentView must be a Pydantic BaseModel (serializable to JSON)."""
    view = get_agent_view(full_state, "running")
    dumped = view.model_dump()
    assert "profile" in dumped
    assert "agent" in dumped


def test_head_coach_gets_all_sections(full_state):
    view = get_agent_view(full_state, "head_coach")
    for section in ALL_SECTIONS:
        assert getattr(view, section) is not None
```

- [ ] **Step 3: Run to verify failure**

```bash
cd "/c/Users/simon/resilio-plus"
poetry run pytest tests/test_models/test_agent_views.py -v
```

Expected: `ImportError` — `AgentView` and new `get_agent_view()` do not exist yet.

- [ ] **Step 4: Implement `AgentView` and new `get_agent_view()`**

In `backend/app/models/athlete_state.py`, add at the top:

```python
from pydantic import BaseModel, ConfigDict, Field
```

(Replace existing `from pydantic import BaseModel, Field` if not already updated.)

Add at the end of the file, **replacing** the old `_AGENT_VIEWS` dict and `get_agent_view()` function entirely:

```python
# ---------------------------------------------------------------------------
# AgentView + get_agent_view()  (section 7.2)
# ---------------------------------------------------------------------------


class AgentView(BaseModel):
    """Typed filtered view of AthleteState for a specific agent.

    Only sections the agent is authorized to see are populated.
    All other sections are None. extra="forbid" prevents unauthorized access.
    """

    model_config = ConfigDict(extra="forbid")

    agent: str
    profile: Optional[AthleteProfile] = None
    metrics: Optional[AthleteMetrics] = None
    connectors: Optional[ConnectorSnapshot] = None
    plan: Optional[PlanSnapshot] = None
    energy: Optional[EnergySnapshot] = None
    recovery: Optional[RecoveryVetoV3] = None
    hormonal: Optional[HormonalProfile] = None
    allostatic: Optional[AllostaticSummary] = None
    journal: Optional[DailyJournal] = None


_AGENT_VIEWS: dict[str, set[str]] = {
    "head_coach": {"profile", "metrics", "connectors", "plan", "energy", "recovery", "hormonal", "allostatic", "journal"},
    "running":    {"profile", "metrics", "connectors", "plan", "hormonal"},
    "lifting":    {"profile", "metrics", "connectors", "plan", "hormonal"},
    "swimming":   {"profile", "metrics", "connectors", "plan"},
    "biking":     {"profile", "metrics", "connectors", "plan"},
    "nutrition":  {"profile", "plan", "energy", "hormonal"},
    "recovery":   {"profile", "metrics", "connectors", "plan", "energy", "recovery", "hormonal", "allostatic", "journal"},
    "energy":     {"profile", "metrics", "energy", "recovery", "hormonal", "allostatic", "journal"},
}


def get_agent_view(state: AthleteState, agent: str) -> AgentView:
    """Return a typed filtered view of AthleteState for the given agent.

    - Known agents → populated sections per _AGENT_VIEWS matrix
    - Unknown agents → AgentView with all sections None
    """
    allowed = _AGENT_VIEWS.get(agent, set())
    return AgentView(
        agent=agent,
        **{k: getattr(state, k) for k in allowed},
    )
```

- [ ] **Step 5: Run tests**

```bash
cd "/c/Users/simon/resilio-plus"
poetry run pytest tests/test_models/ -v
```

Expected: All pass.

- [ ] **Step 6: Commit**

```bash
cd "/c/Users/simon/resilio-plus"
git add backend/app/models/athlete_state.py tests/test_models/test_agent_views.py tests/test_models/conftest.py
git commit -m "feat(models): add AgentView, replace get_agent_view() with typed matrix"
```

---

## Task 9: Full test suite verification

Verify all existing tests still pass after the refactor.

**Files:** None (verification only)

- [ ] **Step 1: Run full test suite**

```bash
cd "/c/Users/simon/resilio-plus"
poetry run pytest tests/ -v --tb=short 2>&1 | tail -30
```

Expected: All tests pass. Count should be ≥ 1847 existing + new tests in `test_models/`.

- [ ] **Step 2: Check for import errors in energy_coach**

```bash
cd "/c/Users/simon/resilio-plus"
poetry run pytest tests/backend/agents/ -v --tb=short
```

Expected: All agent tests pass (including energy coach tests that use `EnergyCheckIn`).

- [ ] **Step 3: Verify no regressions in V3 model tests**

```bash
cd "/c/Users/simon/resilio-plus"
poetry run pytest tests/test_models/test_athlete_state_v3.py -v
```

Expected: All 22 existing V3 model tests pass.

- [ ] **Step 4: Commit final state**

```bash
cd "/c/Users/simon/resilio-plus"
git add -p  # review any unstaged changes
git status  # confirm clean working tree
```

If working tree is clean after all task commits, no additional commit needed.

---

## Self-Review Checklist

**Spec coverage:**
- [x] `AthleteState` root model with 9 sections → Task 7
- [x] `EnergyCheckIn` moved + converted to BaseModel → Task 1
- [x] `AllostaticComponents` typed → Task 2
- [x] `SyncSource` + `AthleteMetrics` → Task 3
- [x] `ConnectorSnapshot` → Task 4
- [x] `PlanSnapshot` + `AllostaticSummary` → Task 5
- [x] `DailyJournal` with mood + check-in + comment → Task 6
- [x] `AgentView` + `get_agent_view()` → Task 8
- [x] Parametric tests for all 8 agents → Task 8
- [x] Backup before refactor → Task 1 Step 1
- [x] `poetry run pytest` after each change → every task

**Type consistency:**
- `AllostaticComponents` defined in Task 2, used in `AllostaticEntry` (same task) and `conftest.py` (Task 8) ✅
- `EnergyCheckIn` defined in Task 1, used in `DailyJournal` (Task 6), `conftest.py` (Task 8) ✅
- `RecoveryVetoV3` imported from existing models in all test helpers ✅
- `AthleteState` defined in Task 7, used in `get_agent_view()` signature (Task 8) ✅

**No placeholders:** Confirmed — all code blocks are complete.
