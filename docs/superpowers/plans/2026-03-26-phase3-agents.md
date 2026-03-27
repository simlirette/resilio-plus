# Phase 3 Session 5 — Agent System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the deterministic coaching computation layer: BaseAgent interface, 4 core business-logic modules (ACWR, fatigue aggregation, conflict detection, periodization), HeadCoach orchestrator, and 6 reference data JSON files.

**Architecture:** Option B — `agents/` contains the orchestration interface (BaseAgent, HeadCoach); `core/` contains stateless business logic modules (acwr, fatigue, conflict, periodization) that are independently testable. HeadCoach delegates all computation to core modules. No LLM calls — pure deterministic Python.

**Tech Stack:** Python 3.14, dataclasses, abc, enum, pytest, existing Pydantic schemas (FatigueScore, WorkoutSlot, AthleteProfile, connector DTOs from Phase 1–2)

**Spec:** `docs/superpowers/specs/2026-03-26-phase3-agents-design.md`

---

## File Map

**Create:**
```
backend/app/agents/__init__.py         empty package marker
backend/app/agents/base.py             AgentContext, AgentRecommendation, BaseAgent
backend/app/agents/head_coach.py       WeeklyPlan, HeadCoach
backend/app/core/__init__.py           empty package marker
backend/app/core/acwr.py               ACWRStatus, ACWRResult, compute_acwr()
backend/app/core/fatigue.py            GlobalFatigue, aggregate_fatigue()
backend/app/core/conflict.py           ConflictSeverity, Conflict, detect_conflicts()
backend/app/core/periodization.py      MacroPhase, TIDStrategy, PeriodizationPhase, get_current_phase()
.bmad-core/data/volume-landmarks.json
.bmad-core/data/exercise-database.json
.bmad-core/data/running-zones.json
.bmad-core/data/cycling-zones.json
.bmad-core/data/swimming-benchmarks.json
.bmad-core/data/nutrition-targets.json
tests/backend/agents/__init__.py
tests/backend/agents/conftest.py       MockAgent, sample_context(), sample_recommendation()
tests/backend/agents/test_base.py
tests/backend/agents/test_head_coach.py
tests/backend/core/__init__.py
tests/backend/core/test_acwr.py
tests/backend/core/test_fatigue.py
tests/backend/core/test_conflict.py
tests/backend/core/test_periodization.py
```

**No existing files modified.**

---

## Task 1: Package Scaffolding

**Files:**
- Create: `backend/app/agents/__init__.py`
- Create: `backend/app/core/__init__.py`
- Create: `tests/backend/agents/__init__.py`
- Create: `tests/backend/core/__init__.py`

No TDD needed — these are empty marker files.

- [ ] **Step 1: Create package markers**

```bash
touch /c/Users/simon/resilio-plus/backend/app/agents/__init__.py
touch /c/Users/simon/resilio-plus/backend/app/core/__init__.py
touch /c/Users/simon/resilio-plus/tests/backend/agents/__init__.py
touch /c/Users/simon/resilio-plus/tests/backend/core/__init__.py
```

- [ ] **Step 2: Verify pytest still collects existing tests**

```bash
cd /c/Users/simon/resilio-plus && python -m pytest tests/backend/connectors/test_terra.py tests/backend/schemas/test_fatigue.py -v --no-header
```

Expected: both tests PASS (no import errors from new empty packages)

- [ ] **Step 3: Commit**

```bash
cd /c/Users/simon/resilio-plus && git add backend/app/agents/__init__.py backend/app/core/__init__.py tests/backend/agents/__init__.py tests/backend/core/__init__.py
git commit -m "chore: add agents and core package scaffolding"
```

---

## Task 2: `core/acwr.py` — EWMA ACWR

**Files:**
- Create: `tests/backend/core/test_acwr.py`
- Create: `backend/app/core/acwr.py`

### Step-by-step

- [ ] **Step 1: Write the failing tests**

Create `tests/backend/core/test_acwr.py`:

```python
import pytest
from app.core.acwr import compute_acwr, ACWRStatus, ACWRResult


def test_empty_history_returns_safe_zeros():
    result = compute_acwr([])
    assert result.acute_7d == 0.0
    assert result.chronic_28d == 0.0
    assert result.ratio == 0.0
    assert result.status == ACWRStatus.SAFE
    assert result.max_safe_weekly_load == 0.0


def test_constant_load_ratio_is_one():
    # Constant load → acute EWMA ≈ chronic EWMA → ratio ≈ 1.0 → SAFE
    loads = [50.0] * 56  # 8 weeks of constant load
    result = compute_acwr(loads)
    assert result.status == ACWRStatus.SAFE
    assert abs(result.ratio - 1.0) < 0.05


def test_safe_zone_lower_boundary():
    # ratio just above 0.8 → SAFE
    loads = [50.0] * 27 + [40.0]  # slight drop
    result = compute_acwr(loads)
    assert result.status in (ACWRStatus.SAFE, ACWRStatus.UNDERTRAINED)


def test_undertrained_zone():
    # Very low recent load vs high chronic → ratio < 0.8
    # NOTE: needs several low-load days to pull acute EWMA below 0.8; a single spike doesn't suffice
    loads = [80.0] * 20 + [30.0] * 8
    result = compute_acwr(loads)
    assert result.status == ACWRStatus.UNDERTRAINED


def test_caution_zone_at_boundary():
    # ratio exactly 1.3 → CAUTION (not SAFE)
    # We test the boundary function directly
    from app.core.acwr import _ratio_to_status
    assert _ratio_to_status(1.3) == ACWRStatus.CAUTION
    assert _ratio_to_status(1.299) == ACWRStatus.SAFE


def test_danger_zone():
    # Spike load after very low chronic → ratio > 1.5
    loads = [10.0] * 27 + [200.0]
    result = compute_acwr(loads)
    assert result.status == ACWRStatus.DANGER


def test_10_percent_rule():
    # chronic_28d EWMA ≈ 50 → max_safe ≈ 55
    loads = [50.0] * 56
    result = compute_acwr(loads)
    assert result.max_safe_weekly_load == pytest.approx(result.chronic_28d * 1.1, rel=0.01)


def test_oldest_first_ordering_matters():
    # Different order should produce different EWMA
    loads_a = [10.0, 50.0]
    loads_b = [50.0, 10.0]
    result_a = compute_acwr(loads_a)
    result_b = compute_acwr(loads_b)
    # The two calls must differ (older load matters less in EWMA)
    assert result_a.acute_7d != result_b.acute_7d
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /c/Users/simon/resilio-plus && python -m pytest tests/backend/core/test_acwr.py -v --no-header
```

Expected: `ModuleNotFoundError: No module named 'app.core.acwr'` or `ImportError` — all FAIL

- [ ] **Step 3: Write the implementation**

Create `backend/app/core/acwr.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ACWRStatus(str, Enum):
    UNDERTRAINED = "undertrained"
    SAFE = "safe"
    CAUTION = "caution"
    DANGER = "danger"


@dataclass
class ACWRResult:
    acute_7d: float
    chronic_28d: float
    ratio: float
    status: ACWRStatus
    max_safe_weekly_load: float


_LAMBDA_ACUTE = 2 / (7 + 1)      # 0.25
_LAMBDA_CHRONIC = 2 / (28 + 1)   # ≈ 0.0690


def _ewma(loads: list[float], lam: float) -> float:
    """Compute EWMA over loads (oldest-first). Seed = first element."""
    if not loads:
        return 0.0
    ewma = loads[0]
    for load in loads[1:]:
        ewma = load * lam + ewma * (1 - lam)
    return ewma


def _ratio_to_status(ratio: float) -> ACWRStatus:
    if ratio < 0.8:
        return ACWRStatus.UNDERTRAINED
    if ratio < 1.3:
        return ACWRStatus.SAFE
    if ratio < 1.5:
        return ACWRStatus.CAUTION
    return ACWRStatus.DANGER


def compute_acwr(daily_loads: list[float]) -> ACWRResult:
    """Compute EWMA-based ACWR from oldest-first daily load history.

    Args:
        daily_loads: List of daily loads in chronological order (index 0 = oldest).
                     Empty list returns safe zero result.
    """
    if not daily_loads:
        return ACWRResult(
            acute_7d=0.0,
            chronic_28d=0.0,
            ratio=0.0,
            status=ACWRStatus.SAFE,
            max_safe_weekly_load=0.0,
        )

    acute = _ewma(daily_loads, _LAMBDA_ACUTE)
    chronic = _ewma(daily_loads, _LAMBDA_CHRONIC)

    ratio = acute / chronic if chronic > 0 else 0.0
    status = _ratio_to_status(ratio)
    max_safe = chronic * 1.1

    return ACWRResult(
        acute_7d=round(acute, 4),
        chronic_28d=round(chronic, 4),
        ratio=round(ratio, 4),
        status=status,
        max_safe_weekly_load=round(max_safe, 4),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /c/Users/simon/resilio-plus && python -m pytest tests/backend/core/test_acwr.py -v --no-header
```

Expected: **8 PASSED**

- [ ] **Step 5: Commit**

```bash
cd /c/Users/simon/resilio-plus && git add backend/app/core/acwr.py tests/backend/core/test_acwr.py
git commit -m "feat: add EWMA ACWR computation with status zones and 10% rule"
```

---

## Task 3: `core/fatigue.py` — FatigueScore Aggregation

**Files:**
- Create: `tests/backend/core/test_fatigue.py`
- Create: `backend/app/core/fatigue.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/backend/core/test_fatigue.py`:

```python
from app.core.fatigue import aggregate_fatigue, GlobalFatigue
from app.schemas.fatigue import FatigueScore


def _make_score(local=0.0, cns=0.0, metabolic=0.0, recovery=0.0, muscles=None):
    return FatigueScore(
        local_muscular=local,
        cns_load=cns,
        metabolic_cost=metabolic,
        recovery_hours=recovery,
        affected_muscles=muscles or [],
    )


def test_empty_list_returns_zeros():
    result = aggregate_fatigue([])
    assert result.total_local_muscular == 0.0
    assert result.total_cns_load == 0.0
    assert result.total_metabolic_cost == 0.0
    assert result.peak_recovery_hours == 0.0
    assert result.all_affected_muscles == []


def test_single_score_passthrough():
    score = _make_score(local=30.0, cns=20.0, metabolic=40.0, recovery=12.0, muscles=["quads"])
    result = aggregate_fatigue([score])
    assert result.total_local_muscular == 30.0
    assert result.total_cns_load == 20.0
    assert result.total_metabolic_cost == 40.0
    assert result.peak_recovery_hours == 12.0
    assert result.all_affected_muscles == ["quads"]


def test_sum_clamped_at_100():
    s1 = _make_score(local=70.0, cns=60.0, metabolic=80.0, recovery=24.0)
    s2 = _make_score(local=60.0, cns=50.0, metabolic=40.0, recovery=12.0)
    result = aggregate_fatigue([s1, s2])
    assert result.total_local_muscular == 100.0  # 70+60 clamped
    assert result.total_cns_load == 100.0        # 60+50 clamped
    assert result.total_metabolic_cost == 100.0  # 80+40 clamped


def test_peak_recovery_hours_is_max():
    s1 = _make_score(recovery=6.0)
    s2 = _make_score(recovery=24.0)
    s3 = _make_score(recovery=12.0)
    result = aggregate_fatigue([s1, s2, s3])
    assert result.peak_recovery_hours == 24.0


def test_muscle_union_deduplicates():
    s1 = _make_score(muscles=["quads", "hamstrings"])
    s2 = _make_score(muscles=["hamstrings", "glutes"])
    result = aggregate_fatigue([s1, s2])
    # Order preserved, no duplicates
    assert result.all_affected_muscles == ["quads", "hamstrings", "glutes"]


def test_muscle_union_preserves_insertion_order():
    s1 = _make_score(muscles=["chest", "triceps"])
    s2 = _make_score(muscles=["back", "biceps"])
    result = aggregate_fatigue([s1, s2])
    assert result.all_affected_muscles == ["chest", "triceps", "back", "biceps"]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /c/Users/simon/resilio-plus && python -m pytest tests/backend/core/test_fatigue.py -v --no-header
```

Expected: `ModuleNotFoundError: No module named 'app.core.fatigue'` — all FAIL

- [ ] **Step 3: Write the implementation**

Create `backend/app/core/fatigue.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field

from app.schemas.fatigue import FatigueScore


@dataclass
class GlobalFatigue:
    total_local_muscular: float
    total_cns_load: float
    total_metabolic_cost: float
    peak_recovery_hours: float
    all_affected_muscles: list[str] = field(default_factory=list)


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def _ordered_union(lists: list[list[str]]) -> list[str]:
    """Return deduplicated union preserving insertion order."""
    seen: set[str] = set()
    result: list[str] = []
    for lst in lists:
        for item in lst:
            if item not in seen:
                seen.add(item)
                result.append(item)
    return result


def aggregate_fatigue(scores: list[FatigueScore]) -> GlobalFatigue:
    """Aggregate multiple FatigueScores into a single GlobalFatigue.

    Empty list returns all-zero GlobalFatigue with empty muscle list.
    Each dimension is summed then clamped to [0, 100].
    peak_recovery_hours = max recovery across all scores.
    all_affected_muscles = ordered union (deduped, insertion order preserved).
    """
    if not scores:
        return GlobalFatigue(0.0, 0.0, 0.0, 0.0, [])

    return GlobalFatigue(
        total_local_muscular=_clamp(sum(s.local_muscular for s in scores)),
        total_cns_load=_clamp(sum(s.cns_load for s in scores)),
        total_metabolic_cost=_clamp(sum(s.metabolic_cost for s in scores)),
        peak_recovery_hours=max(s.recovery_hours for s in scores),
        all_affected_muscles=_ordered_union([s.affected_muscles for s in scores]),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /c/Users/simon/resilio-plus && python -m pytest tests/backend/core/test_fatigue.py -v --no-header
```

Expected: **6 PASSED**

- [ ] **Step 5: Commit**

```bash
cd /c/Users/simon/resilio-plus && git add backend/app/core/fatigue.py tests/backend/core/test_fatigue.py
git commit -m "feat: add FatigueScore aggregation with clamping and muscle union"
```

---

## Task 4: `core/periodization.py` — Macro Phase

**Files:**
- Create: `tests/backend/core/test_periodization.py`
- Create: `backend/app/core/periodization.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/backend/core/test_periodization.py`:

```python
from datetime import date, timedelta
from app.core.periodization import get_current_phase, MacroPhase, TIDStrategy


def _race_in(weeks: int) -> date:
    return date.today() + timedelta(weeks=weeks)


def test_no_race_date_defaults_to_general_prep():
    result = get_current_phase(None, date.today())
    assert result.phase == MacroPhase.GENERAL_PREP
    assert result.tid_recommendation == TIDStrategy.PYRAMIDAL
    assert result.volume_modifier == 1.0


def test_more_than_22_weeks_is_general_prep():
    result = get_current_phase(_race_in(30), date.today())
    assert result.phase == MacroPhase.GENERAL_PREP
    assert result.tid_recommendation == TIDStrategy.PYRAMIDAL
    assert result.volume_modifier == 1.0


def test_exactly_22_weeks_is_specific_prep():
    result = get_current_phase(_race_in(22), date.today())
    assert result.phase == MacroPhase.SPECIFIC_PREP


def test_14_to_22_weeks_is_specific_prep():
    result = get_current_phase(_race_in(18), date.today())
    assert result.phase == MacroPhase.SPECIFIC_PREP
    assert result.tid_recommendation == TIDStrategy.MIXED
    assert result.volume_modifier == 0.9


def test_7_to_13_weeks_is_pre_competition():
    result = get_current_phase(_race_in(10), date.today())
    assert result.phase == MacroPhase.PRE_COMPETITION
    assert result.tid_recommendation == TIDStrategy.POLARIZED
    assert result.volume_modifier == 0.8


def test_1_to_6_weeks_is_competition():
    result = get_current_phase(_race_in(3), date.today())
    assert result.phase == MacroPhase.COMPETITION
    assert result.tid_recommendation == TIDStrategy.POLARIZED
    assert result.volume_modifier == 0.5


def test_post_race_is_transition():
    past_race = date.today() - timedelta(weeks=1)
    result = get_current_phase(past_race, date.today())
    assert result.phase == MacroPhase.TRANSITION
    assert result.tid_recommendation == TIDStrategy.MIXED
    assert result.volume_modifier == 0.6


def test_weeks_remaining_computed_correctly():
    race = date.today() + timedelta(days=35)  # exactly 5 weeks
    result = get_current_phase(race, date.today())
    assert result.weeks_remaining == 5
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /c/Users/simon/resilio-plus && python -m pytest tests/backend/core/test_periodization.py -v --no-header
```

Expected: `ModuleNotFoundError: No module named 'app.core.periodization'` — all FAIL

- [ ] **Step 3: Write the implementation**

Create `backend/app/core/periodization.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum


class MacroPhase(str, Enum):
    # week-count thresholds = weeks_remaining until race date
    GENERAL_PREP    = "general_prep"       # > 22 weeks
    SPECIFIC_PREP   = "specific_prep"      # 14–22 weeks
    PRE_COMPETITION = "pre_competition"    # 7–13 weeks
    COMPETITION     = "competition"        # 1–6 weeks
    TRANSITION      = "transition"         # post-race (≤ 0 weeks)


class TIDStrategy(str, Enum):
    PYRAMIDAL = "pyramidal"
    POLARIZED = "polarized"
    MIXED     = "mixed"


@dataclass
class PeriodizationPhase:
    phase: MacroPhase
    weeks_remaining: int
    tid_recommendation: TIDStrategy
    volume_modifier: float


_PHASE_TABLE: list[tuple[int, MacroPhase, TIDStrategy, float]] = [
    # (min_weeks_remaining, phase, tid, volume_modifier) — evaluated top-down
    (23, MacroPhase.GENERAL_PREP,    TIDStrategy.PYRAMIDAL, 1.0),
    (14, MacroPhase.SPECIFIC_PREP,   TIDStrategy.MIXED,     0.9),
    (7,  MacroPhase.PRE_COMPETITION, TIDStrategy.POLARIZED, 0.8),
    (1,  MacroPhase.COMPETITION,     TIDStrategy.POLARIZED, 0.5),
    (0,  MacroPhase.TRANSITION,      TIDStrategy.MIXED,     0.6),
]


def get_current_phase(target_race_date: date | None, today: date) -> PeriodizationPhase:
    """Determine macro-annual training phase from weeks remaining until race.

    If target_race_date is None, defaults to GENERAL_PREP.
    weeks_remaining = (target_race_date - today).days // 7
    """
    if target_race_date is None:
        return PeriodizationPhase(
            phase=MacroPhase.GENERAL_PREP,
            weeks_remaining=-1,
            tid_recommendation=TIDStrategy.PYRAMIDAL,
            volume_modifier=1.0,
        )

    weeks_remaining = (target_race_date - today).days // 7

    for min_weeks, phase, tid, vol in _PHASE_TABLE:
        if weeks_remaining >= min_weeks:
            return PeriodizationPhase(
                phase=phase,
                weeks_remaining=weeks_remaining,
                tid_recommendation=tid,
                volume_modifier=vol,
            )

    # weeks_remaining < 0 (post-race) → TRANSITION
    return PeriodizationPhase(
        phase=MacroPhase.TRANSITION,
        weeks_remaining=weeks_remaining,
        tid_recommendation=TIDStrategy.MIXED,
        volume_modifier=0.6,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /c/Users/simon/resilio-plus && python -m pytest tests/backend/core/test_periodization.py -v --no-header
```

Expected: **8 PASSED**

- [ ] **Step 5: Commit**

```bash
cd /c/Users/simon/resilio-plus && git add backend/app/core/periodization.py tests/backend/core/test_periodization.py
git commit -m "feat: add macro-annual periodization phase computation"
```

---

## Task 5: `agents/base.py` — BaseAgent Interface

**Files:**
- Create: `tests/backend/agents/conftest.py`
- Create: `tests/backend/agents/test_base.py`
- Create: `backend/app/agents/base.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/backend/agents/conftest.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pytest

from app.agents.base import AgentContext, AgentRecommendation, BaseAgent
from app.schemas.athlete import AthleteProfile, Sport
from app.schemas.fatigue import FatigueScore
from app.schemas.plan import WorkoutSlot
from app.schemas.connector import StravaActivity, HevyWorkout, TerraHealthData, FatSecretDay


def make_fatigue(local=10.0, cns=10.0, metabolic=10.0, recovery=8.0, muscles=None):
    return FatigueScore(
        local_muscular=local,
        cns_load=cns,
        metabolic_cost=metabolic,
        recovery_hours=recovery,
        affected_muscles=muscles or [],
    )


def make_recommendation(
    agent_name="running",
    weekly_load=100.0,
    readiness_modifier=1.0,
    sessions=None,
    notes="",
):
    return AgentRecommendation(
        agent_name=agent_name,
        fatigue_score=make_fatigue(),
        weekly_load=weekly_load,
        suggested_sessions=sessions or [],
        readiness_modifier=readiness_modifier,
        notes=notes,
    )


@pytest.fixture
def sample_athlete():
    return AthleteProfile(
        name="Test Athlete",
        age=30,
        sex="M",
        weight_kg=75.0,
        height_cm=178.0,
        sports=[Sport.RUNNING, Sport.LIFTING],
        primary_sport=Sport.RUNNING,
        goals=["run sub-4h marathon"],
        target_race_date=date(2026, 10, 15),
        available_days=[0, 2, 4, 6],
        hours_per_week=8.0,
    )


@pytest.fixture
def sample_context(sample_athlete):
    return AgentContext(
        athlete=sample_athlete,
        date_range=(date(2026, 4, 7), date(2026, 4, 13)),
        phase="general_prep",
        strava_activities=[],
        hevy_workouts=[],
        terra_health=[],
        fatsecret_days=[],
    )


class MockAgent(BaseAgent):
    def __init__(self, name: str, recommendation: AgentRecommendation):
        self._name = name
        self._recommendation = recommendation

    @property
    def name(self) -> str:
        return self._name

    def analyze(self, context: AgentContext) -> AgentRecommendation:
        return self._recommendation
```

Create `tests/backend/agents/test_base.py`:

```python
import pytest
from app.agents.base import AgentRecommendation, AgentContext
from app.schemas.athlete import AthleteProfile, Sport
from datetime import date
from tests.backend.agents.conftest import make_recommendation, MockAgent, make_fatigue


def test_agent_recommendation_default_readiness_modifier():
    rec = make_recommendation()
    assert rec.readiness_modifier == 1.0


def test_agent_recommendation_readiness_modifier_valid_range():
    # min and max valid values
    rec_low = make_recommendation(readiness_modifier=0.5)
    rec_high = make_recommendation(readiness_modifier=1.5)
    assert rec_low.readiness_modifier == 0.5
    assert rec_high.readiness_modifier == 1.5


def test_agent_recommendation_readiness_modifier_below_range_raises():
    with pytest.raises(ValueError):
        make_recommendation(readiness_modifier=0.4)


def test_agent_recommendation_readiness_modifier_above_range_raises():
    with pytest.raises(ValueError):
        make_recommendation(readiness_modifier=1.6)


def test_mock_agent_name_property():
    rec = make_recommendation("lifting")
    agent = MockAgent("lifting", rec)
    assert agent.name == "lifting"


def test_mock_agent_analyze_returns_recommendation(sample_context):
    rec = make_recommendation("running")
    agent = MockAgent("running", rec)
    result = agent.analyze(sample_context)
    assert result.agent_name == "running"
    assert result.weekly_load == 100.0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /c/Users/simon/resilio-plus && python -m pytest tests/backend/agents/test_base.py -v --no-header
```

Expected: `ModuleNotFoundError: No module named 'app.agents.base'` — all FAIL

- [ ] **Step 3: Write the implementation**

Create `backend/app/agents/base.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date

from app.schemas.athlete import AthleteProfile
from app.schemas.connector import FatSecretDay, HevyWorkout, StravaActivity, TerraHealthData
from app.schemas.fatigue import FatigueScore
from app.schemas.plan import WorkoutSlot


@dataclass
class AgentContext:
    """All data available to specialist agents for a given planning week."""
    athlete: AthleteProfile
    date_range: tuple[date, date]
    phase: str                              # MacroPhase value (string)
    strava_activities: list[StravaActivity] = field(default_factory=list)
    hevy_workouts: list[HevyWorkout] = field(default_factory=list)
    terra_health: list[TerraHealthData] = field(default_factory=list)
    fatsecret_days: list[FatSecretDay] = field(default_factory=list)


@dataclass
class AgentRecommendation:
    """Output of a specialist agent's analysis for a planning week."""
    agent_name: str
    fatigue_score: FatigueScore
    weekly_load: float
    suggested_sessions: list[WorkoutSlot] = field(default_factory=list)
    readiness_modifier: float = 1.0
    notes: str = ""

    def __post_init__(self) -> None:
        if not (0.5 <= self.readiness_modifier <= 1.5):
            raise ValueError(
                f"readiness_modifier must be in [0.5, 1.5], got {self.readiness_modifier}"
            )


class BaseAgent(ABC):
    """Abstract base class for all specialist coaching agents."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this agent, e.g. 'running', 'lifting'."""

    @abstractmethod
    def analyze(self, context: AgentContext) -> AgentRecommendation:
        """Analyze the context and return a recommendation for the week."""
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /c/Users/simon/resilio-plus && python -m pytest tests/backend/agents/test_base.py -v --no-header
```

Expected: **6 PASSED**

- [ ] **Step 5: Commit**

```bash
cd /c/Users/simon/resilio-plus && git add backend/app/agents/base.py tests/backend/agents/conftest.py tests/backend/agents/test_base.py
git commit -m "feat: add BaseAgent interface with AgentContext and AgentRecommendation"
```

---

## Task 6: `core/conflict.py` — Conflict Detection

**Files:**
- Create: `tests/backend/core/test_conflict.py`
- Create: `backend/app/core/conflict.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/backend/core/test_conflict.py`:

```python
from datetime import date

import pytest

from app.core.conflict import detect_conflicts, Conflict, ConflictSeverity
from app.schemas.athlete import Sport
from app.schemas.fatigue import FatigueScore
from app.schemas.plan import WorkoutSlot
from app.agents.base import AgentRecommendation


def _make_fatigue():
    return FatigueScore(local_muscular=20, cns_load=10, metabolic_cost=30, recovery_hours=8)


def _slot(sport: Sport, workout_type: str, day: date = date(2026, 4, 7)) -> WorkoutSlot:
    return WorkoutSlot(
        date=day,
        sport=sport,
        workout_type=workout_type,
        duration_min=60,
        fatigue_score=_make_fatigue(),
    )


def _rec(agent_name: str, sessions: list[WorkoutSlot]) -> AgentRecommendation:
    return AgentRecommendation(
        agent_name=agent_name,
        fatigue_score=_make_fatigue(),
        weekly_load=100.0,
        suggested_sessions=sessions,
    )


def test_no_conflict_with_single_agent():
    recs = [_rec("running", [_slot(Sport.RUNNING, "easy_z1")])]
    assert detect_conflicts(recs) == []


def test_hiit_and_lifting_same_day_is_critical():
    recs = [
        _rec("running", [_slot(Sport.RUNNING, "hiit_intervals")]),
        _rec("lifting", [_slot(Sport.LIFTING, "upper_body")]),
    ]
    conflicts = detect_conflicts(recs)
    assert any(c.severity == ConflictSeverity.CRITICAL for c in conflicts)
    assert any(c.rule == "hiit_strength_same_session" for c in conflicts)


def test_interval_keyword_also_triggers_hiit_rule():
    recs = [
        _rec("running", [_slot(Sport.RUNNING, "vo2max_intervals")]),
        _rec("lifting", [_slot(Sport.LIFTING, "squat_session")]),
    ]
    conflicts = detect_conflicts(recs)
    assert any(c.rule == "hiit_strength_same_session" for c in conflicts)


def test_z2_running_before_lifting_no_conflict():
    recs = [
        _rec("running", [_slot(Sport.RUNNING, "z2_easy_run")]),
        _rec("lifting", [_slot(Sport.LIFTING, "leg_day")]),
    ]
    conflicts = detect_conflicts(recs)
    # Z2/MICT + lifting → explicitly no conflict per §1.2
    assert conflicts == []


def test_endurance_before_lifting_warning():
    recs = [
        _rec("running", [_slot(Sport.RUNNING, "tempo_run")]),
        _rec("lifting", [_slot(Sport.LIFTING, "full_body")]),
    ]
    conflicts = detect_conflicts(recs)
    assert any(c.severity == ConflictSeverity.WARNING for c in conflicts)
    assert any(c.rule == "endurance_before_strength_gap" for c in conflicts)


def test_swimming_before_lifting_is_warning_not_critical():
    recs = [
        _rec("swimming", [_slot(Sport.SWIMMING, "threshold_set")]),
        _rec("lifting", [_slot(Sport.LIFTING, "upper_body")]),
    ]
    conflicts = detect_conflicts(recs)
    warnings = [c for c in conflicts if c.severity == ConflictSeverity.WARNING]
    criticals = [c for c in conflicts if c.severity == ConflictSeverity.CRITICAL]
    assert len(warnings) >= 1
    assert len(criticals) == 0
    assert any(c.rule == "swimming_before_strength_reduced" for c in conflicts)


def test_different_days_no_conflict():
    day1 = date(2026, 4, 7)
    day2 = date(2026, 4, 8)
    recs = [
        _rec("running", [_slot(Sport.RUNNING, "hiit_intervals", day=day1)]),
        _rec("lifting", [_slot(Sport.LIFTING, "squat_session", day=day2)]),
    ]
    conflicts = detect_conflicts(recs)
    assert conflicts == []


def test_conflict_contains_both_agent_names():
    recs = [
        _rec("running", [_slot(Sport.RUNNING, "hiit_session")]),
        _rec("lifting", [_slot(Sport.LIFTING, "lower_body")]),
    ]
    conflicts = detect_conflicts(recs)
    assert len(conflicts) > 0
    assert "running" in conflicts[0].agents
    assert "lifting" in conflicts[0].agents
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /c/Users/simon/resilio-plus && python -m pytest tests/backend/core/test_conflict.py -v --no-header
```

Expected: `ModuleNotFoundError: No module named 'app.core.conflict'` — all FAIL

- [ ] **Step 3: Write the implementation**

Create `backend/app/core/conflict.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum

from app.agents.base import AgentRecommendation
from app.schemas.plan import WorkoutSlot


class ConflictSeverity(str, Enum):
    WARNING  = "warning"
    CRITICAL = "critical"


@dataclass
class Conflict:
    severity: ConflictSeverity
    rule: str
    agents: list[str] = field(default_factory=list)
    message: str = ""


# workout_type keywords that classify a session as HIIT/interval
_HIIT_KEYWORDS = ("hiit", "interval", "vo2max", "repetition", "speed")
# workout_type prefixes/keywords that classify as Z2/MICT (no interference with strength)
_Z2_KEYWORDS = ("z1", "z2", "easy", "recovery", "mict", "base")


def _is_hiit(workout_type: str) -> bool:
    wt = workout_type.lower()
    return any(k in wt for k in _HIIT_KEYWORDS)


def _is_z2(workout_type: str) -> bool:
    wt = workout_type.lower()
    return any(k in wt for k in _Z2_KEYWORDS)


def _sessions_by_date(recommendations: list[AgentRecommendation]) -> dict[date, list[tuple[str, WorkoutSlot]]]:
    """Group (agent_name, session) pairs by date."""
    by_date: dict[date, list[tuple[str, WorkoutSlot]]] = {}
    for rec in recommendations:
        for session in rec.suggested_sessions:
            by_date.setdefault(session.date, []).append((rec.agent_name, session))
    return by_date


def detect_conflicts(recommendations: list[AgentRecommendation]) -> list[Conflict]:
    """Detect force/endurance scheduling conflicts per Supplement §1.2.

    Rules (checked per day):
    1. HIIT/interval + lifting same day → CRITICAL
    2. Non-swimming endurance (non-Z2) + lifting same day → WARNING
    3. Z2/MICT + lifting same day → no conflict (§1.2 exception)
    4. Swimming + lifting same day → WARNING (reduced severity)
    """
    conflicts: list[Conflict] = []

    by_date = _sessions_by_date(recommendations)

    for day, day_sessions in by_date.items():
        lifting_sessions = [(a, s) for a, s in day_sessions if a == "lifting"]
        endurance_sessions = [
            (a, s) for a, s in day_sessions
            if a in ("running", "biking", "swimming")
        ]

        if not lifting_sessions or not endurance_sessions:
            continue

        for lift_agent, lift_slot in lifting_sessions:
            for end_agent, end_slot in endurance_sessions:
                wt = end_slot.workout_type

                # Rule 1: HIIT + strength → CRITICAL
                if _is_hiit(wt):
                    conflicts.append(Conflict(
                        severity=ConflictSeverity.CRITICAL,
                        rule="hiit_strength_same_session",
                        agents=[end_agent, lift_agent],
                        message=(
                            f"{end_agent} has HIIT session and {lift_agent} is on the same day. "
                            "HIIT + strength training causes maximal interference. "
                            "Separate by at least 24h."
                        ),
                    ))
                    continue

                # Rule 3: Z2/MICT → explicitly no conflict
                if _is_z2(wt):
                    continue

                # Rule 4: Swimming (non-HIIT, non-Z2) → reduced WARNING
                if end_agent == "swimming":
                    conflicts.append(Conflict(
                        severity=ConflictSeverity.WARNING,
                        rule="swimming_before_strength_reduced",
                        agents=[end_agent, lift_agent],
                        message=(
                            f"Swimming and {lift_agent} on the same day. "
                            "Swimming is less inflammatory than running — minor interference risk."
                        ),
                    ))
                    continue

                # Rule 2: Other endurance (tempo, progression, etc.) + strength → WARNING
                conflicts.append(Conflict(
                    severity=ConflictSeverity.WARNING,
                    rule="endurance_before_strength_gap",
                    agents=[end_agent, lift_agent],
                    message=(
                        f"{end_agent} ({wt}) and {lift_agent} on the same day. "
                        "Endurance before strength requires 3h gap to avoid mTOR/AMPK interference."
                    ),
                ))

    return conflicts
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /c/Users/simon/resilio-plus && python -m pytest tests/backend/core/test_conflict.py -v --no-header
```

Expected: **8 PASSED**

- [ ] **Step 5: Commit**

```bash
cd /c/Users/simon/resilio-plus && git add backend/app/core/conflict.py tests/backend/core/test_conflict.py
git commit -m "feat: add force/endurance conflict detection with §1.2 sequencing rules"
```

---

## Task 7: `agents/head_coach.py` — HeadCoach Orchestrator

**Files:**
- Create: `tests/backend/agents/test_head_coach.py`
- Create: `backend/app/agents/head_coach.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/backend/agents/test_head_coach.py`:

```python
from datetime import date

import pytest

from app.agents.head_coach import HeadCoach, WeeklyPlan
from app.core.acwr import ACWRStatus
from app.core.conflict import ConflictSeverity
from app.schemas.athlete import Sport
from app.schemas.fatigue import FatigueScore
from app.schemas.plan import WorkoutSlot
from tests.backend.agents.conftest import (
    MockAgent,
    make_recommendation,
    make_fatigue,
    sample_context,
    sample_athlete,
)


def _slot(sport: Sport, workout_type: str, duration: int = 60) -> WorkoutSlot:
    return WorkoutSlot(
        date=date(2026, 4, 7),
        sport=sport,
        workout_type=workout_type,
        duration_min=duration,
        fatigue_score=make_fatigue(),
    )


def test_empty_agents_returns_empty_plan(sample_context):
    hc = HeadCoach([])
    plan = hc.build_week(sample_context, [])
    assert plan.sessions == []
    assert plan.readiness_level == "green"
    assert plan.notes == []


def test_single_agent_sessions_pass_through(sample_context):
    session = _slot(Sport.RUNNING, "easy_z1")
    rec = make_recommendation("running", sessions=[session], weekly_load=80.0)
    hc = HeadCoach([MockAgent("running", rec)])
    plan = hc.build_week(sample_context, [50.0] * 28)
    assert len(plan.sessions) == 1


def test_readiness_green_when_modifier_above_0_9(sample_context):
    rec = make_recommendation("running", readiness_modifier=1.0)
    hc = HeadCoach([MockAgent("running", rec)])
    plan = hc.build_week(sample_context, [50.0] * 28)
    assert plan.readiness_level == "green"


def test_readiness_yellow_when_modifier_between_0_6_and_0_9(sample_context):
    rec = make_recommendation("recovery", readiness_modifier=0.75)
    hc = HeadCoach([MockAgent("recovery", rec)])
    plan = hc.build_week(sample_context, [50.0] * 28)
    assert plan.readiness_level == "yellow"


def test_readiness_red_converts_sessions_to_z1(sample_context):
    session = _slot(Sport.RUNNING, "tempo_run")
    rec = make_recommendation("running", readiness_modifier=0.5, sessions=[session])
    hc = HeadCoach([MockAgent("running", rec)])
    plan = hc.build_week(sample_context, [50.0] * 28)
    assert plan.readiness_level == "red"
    assert all(s.workout_type == "easy_z1" for s in plan.sessions)


def test_danger_acwr_scales_sessions_by_75_percent(sample_context):
    session = _slot(Sport.RUNNING, "long_run", duration=120)
    # Very high weekly load to trigger DANGER
    rec = make_recommendation("running", weekly_load=500.0, sessions=[session])
    hc = HeadCoach([MockAgent("running", rec)])
    plan = hc.build_week(sample_context, [10.0] * 28)
    assert plan.acwr.status == ACWRStatus.DANGER
    # Duration should be scaled to 120 * 0.75 = 90
    assert plan.sessions[0].duration_min == 90


def test_notes_collected_from_agents(sample_context):
    rec = make_recommendation("running", notes="Easy week — deload")
    hc = HeadCoach([MockAgent("running", rec)])
    plan = hc.build_week(sample_context, [50.0] * 28)
    assert "Easy week — deload" in plan.notes


def test_acwr_computed_from_load_history(sample_context):
    rec = make_recommendation("running", weekly_load=50.0)
    hc = HeadCoach([MockAgent("running", rec)])
    plan = hc.build_week(sample_context, [50.0] * 28)
    assert plan.acwr.status == ACWRStatus.SAFE
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /c/Users/simon/resilio-plus && python -m pytest tests/backend/agents/test_head_coach.py -v --no-header
```

Expected: `ModuleNotFoundError: No module named 'app.agents.head_coach'` — all FAIL

- [ ] **Step 3: Write the implementation**

Create `backend/app/agents/head_coach.py`:

```python
from __future__ import annotations

import copy
from dataclasses import dataclass, field

from app.agents.base import AgentContext, AgentRecommendation, BaseAgent
from app.core.acwr import ACWRResult, ACWRStatus, compute_acwr
from app.core.conflict import Conflict, detect_conflicts
from app.core.fatigue import GlobalFatigue, aggregate_fatigue
from app.core.periodization import PeriodizationPhase, get_current_phase
from app.schemas.plan import WorkoutSlot


@dataclass
class WeeklyPlan:
    phase: PeriodizationPhase
    acwr: ACWRResult
    global_fatigue: GlobalFatigue
    conflicts: list[Conflict]
    sessions: list[WorkoutSlot]
    readiness_level: str            # "green" | "yellow" | "red"
    notes: list[str] = field(default_factory=list)


class HeadCoach:
    """Orchestrates specialist agents and arbitrates a coherent weekly training plan."""

    def __init__(self, agents: list[BaseAgent]) -> None:
        self.agents = agents

    def build_week(
        self,
        context: AgentContext,
        load_history: list[float],
    ) -> WeeklyPlan:
        """Build a weekly training plan by orchestrating all specialist agents.

        Args:
            context: Planning context including athlete profile and connector data.
            load_history: Daily loads in oldest-first chronological order (from DB).
                          HeadCoach appends the new week's total load before computing ACWR.
        """
        # 1. Invoke all specialist agents
        recommendations: list[AgentRecommendation] = [
            a.analyze(context) for a in self.agents
        ]

        # 2. Compute unified cross-sport ACWR
        weekly_load = sum(r.weekly_load for r in recommendations)
        acwr = compute_acwr(load_history + [weekly_load])

        # 3. Aggregate FatigueScores
        global_fatigue = aggregate_fatigue([r.fatigue_score for r in recommendations])

        # 4. Determine macro phase
        phase = get_current_phase(
            context.athlete.target_race_date,
            context.date_range[0],
        )

        # 5. Detect inter-agent conflicts
        conflicts = detect_conflicts(recommendations)

        # 6. Compute global readiness (minimum modifier drives decisions)
        readiness_modifier = (
            min(r.readiness_modifier for r in recommendations)
            if recommendations
            else 1.0
        )
        readiness_level = self._modifier_to_level(readiness_modifier)

        # 7. Collect agent notes
        notes = [r.notes for r in recommendations if r.notes]

        # 8. Arbitrate final session list
        all_sessions = [s for r in recommendations for s in r.suggested_sessions]
        sessions = self._arbitrate(all_sessions, conflicts, acwr, readiness_modifier)

        return WeeklyPlan(
            phase=phase,
            acwr=acwr,
            global_fatigue=global_fatigue,
            conflicts=conflicts,
            sessions=sessions,
            readiness_level=readiness_level,
            notes=notes,
        )

    def _modifier_to_level(self, modifier: float) -> str:
        if modifier >= 0.9:
            return "green"
        if modifier >= 0.6:
            return "yellow"
        return "red"

    def _arbitrate(
        self,
        sessions: list[WorkoutSlot],
        conflicts: list[Conflict],
        acwr: ACWRResult,
        readiness_modifier: float,
    ) -> list[WorkoutSlot]:
        # Work on copies to avoid mutating inputs
        result = [copy.replace(s) for s in sessions]

        # Rule 1: RED readiness → convert all sessions to Z1
        if readiness_modifier < 0.6:
            result = [
                copy.replace(s, workout_type="easy_z1") for s in result
            ]
            return result  # No further arbitration needed on Z1 sessions

        # Rule 2: DANGER ACWR → scale all session durations by 0.75 (25% reduction)
        if acwr.status == ACWRStatus.DANGER:
            result = [
                copy.replace(s, duration_min=max(1, int(s.duration_min * 0.75)))
                for s in result
            ]

        # Rule 3: CRITICAL conflicts → drop shorter session of conflicting pair
        from app.core.conflict import ConflictSeverity
        for conflict in conflicts:
            if conflict.severity != ConflictSeverity.CRITICAL:
                continue
            # Find sessions belonging to the conflicting agents on the same date
            conflicting = [
                s for s in result
                # We identify the agent via sport mapping — running→running, lifting→lifting
                # Simpler: match by workout sessions that overlap with conflict agents
            ]
            # Find all sessions from each conflicting agent pair
            agents_in_conflict = set(conflict.agents)
            candidate_sessions = [s for s in result if s.sport.value in agents_in_conflict
                                   or any(a in s.workout_type for a in agents_in_conflict)]
            if len(candidate_sessions) >= 2:
                # Drop shorter session (tiebreaker: alphabetically later sport name)
                to_drop = min(
                    candidate_sessions,
                    key=lambda s: (s.duration_min, [-ord(c) for c in s.sport.value]),
                )
                result = [s for s in result if s is not to_drop]

        # Rule 4: Total load > max_safe → trim shortest sessions first
        if acwr.max_safe_weekly_load > 0:
            while (
                sum(s.duration_min for s in result) > acwr.max_safe_weekly_load
                and result
            ):
                result.sort(key=lambda s: s.duration_min)
                result.pop(0)

        return result
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /c/Users/simon/resilio-plus && python -m pytest tests/backend/agents/test_head_coach.py -v --no-header
```

Expected: **8 PASSED**

- [ ] **Step 5: Commit**

```bash
cd /c/Users/simon/resilio-plus && git add backend/app/agents/head_coach.py tests/backend/agents/test_head_coach.py
git commit -m "feat: add HeadCoach orchestrator with ACWR, conflict arbitration, and readiness"
```

---

## Task 8: Reference Data Files (`.bmad-core/data/`)

**Files:** 6 JSON files — no TDD needed (static reference data)

- [ ] **Step 1: Create `volume-landmarks.json`**

Create `.bmad-core/data/volume-landmarks.json`:

```json
{
  "_source": "Blueprint §5.2 + Renaissance Periodization (Israetel) MEV/MAV/MRV",
  "_note": "hybrid_reduction = fraction to reduce MRV when running volume is high",
  "quads":      {"MEV": 8,  "MAV": 14, "MRV": 20, "hybrid_reduction": 0.4},
  "hamstrings": {"MEV": 6,  "MAV": 10, "MRV": 16, "hybrid_reduction": 0.3},
  "glutes":     {"MEV": 4,  "MAV": 8,  "MRV": 16, "hybrid_reduction": 0.2},
  "calves":     {"MEV": 8,  "MAV": 14, "MRV": 22, "hybrid_reduction": 0.2},
  "chest":      {"MEV": 8,  "MAV": 14, "MRV": 22, "hybrid_reduction": 0.0},
  "back":       {"MEV": 10, "MAV": 16, "MRV": 25, "hybrid_reduction": 0.0},
  "shoulders":  {"MEV": 8,  "MAV": 14, "MRV": 22, "hybrid_reduction": 0.0},
  "biceps":     {"MEV": 6,  "MAV": 10, "MRV": 20, "hybrid_reduction": 0.0},
  "triceps":    {"MEV": 6,  "MAV": 10, "MRV": 20, "hybrid_reduction": 0.0},
  "core":       {"MEV": 6,  "MAV": 10, "MRV": 16, "hybrid_reduction": 0.1}
}
```

- [ ] **Step 2: Create `exercise-database.json`**

Create `.bmad-core/data/exercise-database.json`:

```json
{
  "_source": "Supplement §3.3 — SFR (Stimulus-to-Fatigue Ratio) tiers",
  "_note": "In high running volume phases, prefer Tier 1. Tier 3 reserved for off-season.",
  "tier_1_high_sfr_low_cns": [
    "Machine Leg Press", "Hack Squat Machine", "Seated Leg Curl",
    "Lat Pulldown", "Cable Row", "Machine Chest Press",
    "Cable Lateral Raise", "Overhead Cable Tricep Extension",
    "Incline Dumbbell Curl", "Leg Extension"
  ],
  "tier_2_moderate_sfr_moderate_cns": [
    "Romanian Deadlift (DB)", "Bulgarian Split Squat",
    "Dumbbell Bench Press", "Barbell Row", "Overhead Press (DB)",
    "Pull-ups", "Dips"
  ],
  "tier_3_low_sfr_high_cns_use_sparingly": [
    "Barbell Back Squat", "Conventional Deadlift", "Barbell Bench Press",
    "Barbell Overhead Press", "Power Clean"
  ]
}
```

- [ ] **Step 3: Create `running-zones.json`**

Create `.bmad-core/data/running-zones.json`:

```json
{
  "_source": "Supplement §2.1 — Daniels/Seiler hybrid zones",
  "zones": {
    "Z1_easy": {
      "description": "Endurance fondamentale, conversation facile",
      "hr_percent_max": [60, 74],
      "pace_reference": "Easy pace (Daniels)",
      "lactate_mmol": [0.8, 2.0],
      "volume_percent_weekly": [75, 80],
      "purpose": "Base aérobie, récupération active, adaptation mitochondriale"
    },
    "Z2_tempo": {
      "description": "Seuil lactique, confortablement difficile",
      "hr_percent_max": [80, 88],
      "pace_reference": "Tempo/Threshold pace (Daniels T-pace)",
      "lactate_mmol": [2.0, 4.0],
      "volume_percent_weekly": [5, 10],
      "purpose": "Amélioration seuil lactique, économie de course"
    },
    "Z3_vo2max": {
      "description": "Intervalles durs, respiration lourde",
      "hr_percent_max": [95, 100],
      "pace_reference": "Interval pace (Daniels I-pace)",
      "lactate_mmol": [6.0, 10.0],
      "volume_percent_weekly": [5, 8],
      "purpose": "VO2max, capacité aérobie maximale"
    },
    "Z4_repetition": {
      "description": "Sprints courts, vitesse pure",
      "hr_percent_max": null,
      "pace_reference": "Repetition pace (Daniels R-pace)",
      "volume_percent_weekly": [2, 5],
      "purpose": "Économie de course, recrutement fibres rapides"
    }
  }
}
```

- [ ] **Step 4: Create `cycling-zones.json`**

Create `.bmad-core/data/cycling-zones.json`:

```json
{
  "_source": "Supplement §4.1 — Coggan power zones",
  "zones": {
    "Z1_active_recovery": {"percent_ftp": [0,   55],  "description": "Récupération active"},
    "Z2_endurance":        {"percent_ftp": [56,  75],  "description": "Endurance, conversation possible"},
    "Z3_tempo":            {"percent_ftp": [76,  90],  "description": "Tempo, effort soutenu"},
    "Z4_threshold":        {"percent_ftp": [91,  105], "description": "Seuil lactique, ~60min soutenable"},
    "Z5_vo2max":           {"percent_ftp": [106, 120], "description": "VO2max, 3-8min"},
    "Z6_anaerobic":        {"percent_ftp": [121, 150], "description": "Capacité anaérobie, 30s-3min"},
    "Z7_neuromuscular":    {"percent_ftp": [150, 9999],"description": "Sprint, <30s"}
  },
  "ftp_test_protocols": {
    "20min_test": "20min all-out, FTP = 95% of average power",
    "ramp_test":  "Increments of 25W/min, FTP = 75% of peak power reached",
    "retest_interval_weeks": 6
  }
}
```

- [ ] **Step 5: Create `swimming-benchmarks.json`**

Create `.bmad-core/data/swimming-benchmarks.json`:

```json
{
  "_source": "Supplement §5.1 — CSS-based swimming zones",
  "css_formula": "(distance_400m - distance_200m) / (time_400s - time_200s)",
  "css_description": "Critical Swim Speed = lactate threshold in swimming",
  "zones": {
    "Z1_technique":  {"percent_css": [0,   85],  "description": "Technique, échauffement, récupération"},
    "Z2_endurance":  {"percent_css": [85,  95],  "description": "Endurance aérobie"},
    "Z3_threshold":  {"percent_css": [95,  100], "description": "Seuil CSS pace"},
    "Z4_vo2max":     {"percent_css": [100, 105], "description": "VO2max natation"},
    "Z5_sprint":     {"percent_css": [105, 9999],"description": "Sprint, vitesse pure"}
  },
  "swolf_description": "SWOLF = strokes per length + time per length (lower = more efficient)",
  "key_sessions": {
    "threshold_set": "5-10 × 200m @ CSS pace, 15-20s rest",
    "vo2max_set": "8 × 100m @ Z4, 20s rest",
    "pull_set": "With paddles, focus on DPS improvement",
    "drill_set": "Technique drills (catch-up, finger drag, fist drill)"
  }
}
```

- [ ] **Step 6: Create `nutrition-targets.json`**

Create `.bmad-core/data/nutrition-targets.json`:

```json
{
  "_source": "Blueprint §5.6 + Supplement §6",
  "carbs_g_per_kg": {
    "strength_day":    [4, 5],
    "endurance_short": [5, 6],
    "endurance_long":  [6, 7],
    "rest":            [3, 4]
  },
  "protein_g_per_kg": {
    "daily": 1.8,
    "dose_frequency_hours": [3, 4],
    "dose_size_g": [20, 40],
    "pre_sleep_casein_g": [30, 40]
  },
  "intra_effort": {
    "under_60min_g_per_h": 0,
    "60_to_150min_g_per_h": [30, 60],
    "over_150min_g_per_h": [60, 90],
    "over_150min_note": "Use glucose:fructose 2:1 ratio. Requires gut training.",
    "over_3h_sodium_mg_per_h": [500, 1000]
  },
  "hydration": {
    "baseline_ml_per_kg_day": [35, 40],
    "pre_exercise_ml_per_kg_2_4h_before": [5, 7],
    "during_ml_per_h": [400, 800],
    "post_exercise_ml_per_kg_lost": 1500
  },
  "supplements_evidence_level_A": [
    {"name": "creatine_monohydrate", "dose": "3-5g/day", "timing": "any"},
    {"name": "caffeine", "dose": "3-6mg/kg", "timing": "30-60min pre-effort"},
    {"name": "beta_alanine", "dose": "3.2-6.4g/day split", "timing": "with meals"},
    {"name": "nitrate_beetroot", "dose": "6-8mmol", "timing": "2-3h pre-effort"},
    {"name": "omega3", "dose": "2-4g EPA+DHA/day", "timing": "with meals"},
    {"name": "vitamin_d", "dose": "1000-2000 IU/day if deficient", "timing": "any"}
  ]
}
```

- [ ] **Step 7: Verify JSON files are valid**

```bash
cd /c/Users/simon/resilio-plus && python -c "
import json, pathlib
for f in pathlib.Path('.bmad-core/data').glob('*.json'):
    json.loads(f.read_text())
    print(f'  OK: {f.name}')
print('All JSON files valid.')
"
```

Expected output:
```
  OK: volume-landmarks.json
  OK: exercise-database.json
  OK: running-zones.json
  OK: cycling-zones.json
  OK: swimming-benchmarks.json
  OK: nutrition-targets.json
All JSON files valid.
```

- [ ] **Step 8: Commit**

```bash
cd /c/Users/simon/resilio-plus && git add .bmad-core/data/
git commit -m "feat: add 6 reference data JSON files for specialist agents (Sessions 6-7)"
```

---

## Task 9: Final Verification

**Files:** None — run only

- [ ] **Step 1: Run the Phase 3 agent + core test suite**

```bash
cd /c/Users/simon/resilio-plus && python -m pytest tests/backend/agents/ tests/backend/core/ -v --no-header
```

Expected: **~41 tests PASSED**, 0 failed

- [ ] **Step 2: Run the full backend test suite (no regressions)**

```bash
cd /c/Users/simon/resilio-plus && python -m pytest tests/backend/agents/ tests/backend/core/ tests/backend/connectors/ tests/backend/schemas/ tests/backend/db/test_models.py -v --no-header 2>&1 | tail -10
```

Expected: All Phase 1+2+3 tests PASS (~155 total). No regressions.

- [ ] **Step 3: Verify CLI still works**

```bash
cd /c/Users/simon/resilio-plus && poetry run resilio --help
```

Expected: CLI help text printed without errors

- [ ] **Step 4: Final commit (if any cleanup needed)**

```bash
cd /c/Users/simon/resilio-plus && git add -A
git commit -m "chore: Phase 3 Session 5 complete — BaseAgent, HeadCoach, 4 core modules, 6 data files (~41 tests)"
```
