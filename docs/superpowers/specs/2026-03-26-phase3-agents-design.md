# Phase 3 Session 5 — Agent System Design
# BaseAgent + HeadCoach + Core Modules

**Date:** 2026-03-26
**Status:** Approved
**Scope:** Session 5 of Phase 3 — Agent base class, HeadCoach orchestrator, core computation modules, reference data files

---

## Context

Phases 0-2 complete (114 tests passing):
- `backend/app/schemas/` — Pydantic DTOs (Athlete, FatigueScore, WorkoutSlot, TrainingPlan, NutritionPlan, WeeklyReview, connector DTOs)
- `backend/app/db/` — SQLAlchemy ORM (athletes, plans, nutrition, reviews, connector_credentials)
- `backend/app/connectors/` — Strava, Hevy, FatSecret, Terra

Phase 3 builds the coaching computation layer. No LLM calls in Python backend (Phase 3 is pure deterministic Python). The AI coaching emerges in Phase 4/5 via the chat interface (Claude Code + `.agent.md` slash commands consume the structured outputs from this layer).

---

## Architecture Decision

**Option B selected:** Separation of concerns between `agents/` (orchestration interface) and `core/` (business logic modules).

```
backend/app/
├── agents/
│   ├── base.py          # BaseAgent abstract class + AgentContext + AgentRecommendation
│   └── head_coach.py    # HeadCoach — orchestrates agents, delegates to core/
└── core/
    ├── acwr.py          # EWMA ACWR computation
    ├── fatigue.py       # FatigueScore aggregation
    ├── conflict.py      # Force/endurance conflict detection
    └── periodization.py # Macro-annual phase computation
```

The `core/` modules are stateless (pure functions or stateless classes) — independently testable without any agent instantiation.

---

## Section 1 — BaseAgent Interface

**File:** `backend/app/agents/base.py`

### AgentContext

```python
@dataclass
class AgentContext:
    athlete: Athlete
    date_range: tuple[date, date]          # week to plan
    phase: str                             # MacroPhase value
    strava_activities: list[StravaActivity]
    hevy_workouts: list[HevyWorkout]
    terra_health: list[TerraHealthData]
    fatsecret_days: list[FatSecretDay]
```

Each agent takes what it needs from the context and ignores the rest. All connector DTO types already exist in `backend/app/schemas/connector.py`.

### AgentRecommendation

```python
@dataclass
class AgentRecommendation:
    agent_name: str              # "running" | "lifting" | "swimming" | "biking" | "nutrition" | "recovery"
    fatigue_score: FatigueScore  # existing schema
    weekly_load: float           # normalized cross-sport load unit (weighted effort minutes)
    suggested_sessions: list[WorkoutSlot]  # existing schema
    readiness_modifier: float    # 0.5–1.5, default 1.0; Recovery Coach uses HRV here
    notes: str                   # short explanation for Head Coach
```

`weekly_load` is a float in normalized effort-minutes (duration_minutes × intensity_weight). This provides the common unit for cross-sport ACWR computation per Supplement §1.1.

`readiness_modifier` allows Recovery Coach to signal low HRV/poor sleep → HeadCoach scales all sessions down accordingly. It is clamped to [0.5, 1.5] — values outside this range are invalid and raise `ValueError` at construction time.

### BaseAgent

```python
class BaseAgent(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def analyze(self, context: AgentContext) -> AgentRecommendation: ...
```

---

## Section 2 — Core Modules

### `core/acwr.py` — EWMA ACWR

Implements Blueprint §ACWR Rule + Supplement §1.1.

```python
class ACWRStatus(str, Enum):
    UNDERTRAINED = "undertrained"   # ratio < 0.8
    SAFE         = "safe"           # 0.8 ≤ ratio < 1.3
    CAUTION      = "caution"        # 1.3 ≤ ratio < 1.5
    DANGER       = "danger"         # ratio ≥ 1.5

@dataclass
class ACWRResult:
    acute_7d: float
    chronic_28d: float
    ratio: float
    status: ACWRStatus
    max_safe_weekly_load: float    # chronic_28d * 1.1 (10% rule)

def compute_acwr(daily_loads: list[float]) -> ACWRResult:
    ...
```

**EWMA formulas:**
- Input `daily_loads` is **oldest-first chronological order** (index 0 = oldest day)
- `lambda_acute = 2 / (7 + 1) = 0.25`
- `lambda_chronic = 2 / (28 + 1) ≈ 0.069`
- `EWMA[t] = load[t] * lambda + EWMA[t-1] * (1 - lambda)`
- **Cold-start seed:** EWMA is initialized with the first element of `daily_loads` (not zero). If `daily_loads` is empty, return `ACWRResult(0, 0, 0, ACWRStatus.SAFE, 0)`.
- When `len(daily_loads) < 28`, EWMA uses available data — no padding with zeros.

**Boundary conditions (strict):**
- `ratio < 0.8` → UNDERTRAINED
- `0.8 ≤ ratio < 1.3` → SAFE (exactly 1.3 falls into CAUTION)
- `1.3 ≤ ratio < 1.5` → CAUTION
- `ratio ≥ 1.5` → DANGER

**Business rules encoded:**
- Sweet spot: 0.8–1.3 → SAFE
- Danger: ≥1.5 → DANGER (injury risk ×2–4)
- 10% rule: `max_safe = chronic_28d * 1.1`

### `core/fatigue.py` — FatigueScore Aggregation

```python
@dataclass
class GlobalFatigue:
    total_local_muscular: float     # sum, clamped to 100
    total_cns_load: float           # sum, clamped to 100
    total_metabolic_cost: float     # sum, clamped to 100
    peak_recovery_hours: float      # max across all agents
    all_affected_muscles: list[str] # union of all affected_muscles lists

def aggregate_fatigue(scores: list[FatigueScore]) -> GlobalFatigue:
    # Empty list → GlobalFatigue(0.0, 0.0, 0.0, 0.0, [])
    # Sum each dimension, clamp result to [0, 100]
    # peak_recovery_hours = max(recovery_hours) across all scores
    # all_affected_muscles = ordered union (preserves insertion order, deduplicates)
    ...
```

Clamping to 100 prevents unrealistic values when multiple high-fatigue agents overlap.

### `core/conflict.py` — Force/Endurance Conflict Detection

Implements Supplement §1.2 sequencing rules.

```python
class ConflictSeverity(str, Enum):
    WARNING  = "warning"
    CRITICAL = "critical"

@dataclass
class Conflict:
    severity: ConflictSeverity
    rule: str               # rule identifier, e.g. "hiit_strength_same_session"
    agents: list[str]       # e.g. ["running", "lifting"]
    message: str            # human-readable explanation

def detect_conflicts(recommendations: list[AgentRecommendation]) -> list[Conflict]:
    ...
```

**Rules implemented (from Supplement §1.2):**

`WorkoutSlot.date` (existing field) is used to determine same-day co-occurrence.

| Rule | Severity | Condition |
|---|---|---|
| `hiit_strength_same_session` | CRITICAL | HIIT `WorkoutSlot` (workout_type contains "hiit" or "interval") + lifting `WorkoutSlot` on the same date |
| `endurance_before_strength_gap` | WARNING | Non-swimming endurance `WorkoutSlot` + lifting `WorkoutSlot` on the same date (gap assumed < 3h since exact time is not tracked at this layer) |
| `z2_before_strength_no_conflict` | — | Z2/MICT endurance + lifting → explicitly no conflict per §1.2; detector skips this combination |
| `swimming_before_strength_reduced` | WARNING | Swimming `WorkoutSlot` + lifting on same date → WARNING (not CRITICAL; less inflammatory per §1.2) |

`detect_conflicts` receives `List[AgentRecommendation]` — each recommendation carries `agent_name` so the detector can identify which combination triggers a rule.

### `core/periodization.py` — Macro Phase

Implements Supplement §1.3 macro-annual periodization.

```python
class MacroPhase(str, Enum):
    # Note: week-count thresholds below refer to weeks_remaining until race,
    # not the prose duration of each phase. E.g., GENERAL_PREP covers all weeks
    # > 22 remaining (could be many months out).
    GENERAL_PREP    = "general_prep"       # > 22 weeks to race: pyramidal TID, high volume
    SPECIFIC_PREP   = "specific_prep"      # 14–22 weeks to race: mixed→polarized TID
    PRE_COMPETITION = "pre_competition"    # 7–13 weeks to race: polarized, strength maintenance
    COMPETITION     = "competition"        # 1–6 weeks to race: tapering -40-60% volume
    TRANSITION      = "transition"         # post-race (≤ 0 weeks): active recovery

class TIDStrategy(str, Enum):
    PYRAMIDAL = "pyramidal"
    POLARIZED = "polarized"
    MIXED     = "mixed"

@dataclass
class PeriodizationPhase:
    phase: MacroPhase
    weeks_remaining: int
    tid_recommendation: TIDStrategy
    volume_modifier: float      # 0.4–1.0 multiplier for target volume

def get_current_phase(target_race_date: date | None, today: date) -> PeriodizationPhase:
    # If no race date: default to GENERAL_PREP (tid=PYRAMIDAL, volume_modifier=1.0)
    # weeks_remaining = (target_race_date - today).days // 7
    # Phase selection (strict boundaries, evaluated top-down):
    #   weeks_remaining > 22  → GENERAL_PREP  (tid=PYRAMIDAL, volume_modifier=1.0)
    #   weeks_remaining >= 14 → SPECIFIC_PREP (tid=MIXED,     volume_modifier=0.9)
    #   weeks_remaining >= 7  → PRE_COMPETITION (tid=POLARIZED, volume_modifier=0.8)
    #   weeks_remaining >= 1  → COMPETITION   (tid=POLARIZED, volume_modifier=0.5)
    #   weeks_remaining <= 0  → TRANSITION    (tid=MIXED,     volume_modifier=0.6)
```

---

## Section 3 — HeadCoach

**File:** `backend/app/agents/head_coach.py`

```python
@dataclass
class WeeklyPlan:
    phase: PeriodizationPhase
    acwr: ACWRResult
    global_fatigue: GlobalFatigue
    conflicts: list[Conflict]
    sessions: list[WorkoutSlot]        # arbitrated final plan (7 days)
    readiness_level: str               # "green" | "yellow" | "red"
    notes: list[str]                   # messages for the athlete

class HeadCoach:
    def __init__(self, agents: list[BaseAgent]):
        self.agents = agents

    def build_week(
        self,
        context: AgentContext,
        load_history: list[float],     # 28 days of daily loads from DB
    ) -> WeeklyPlan:
        # 1. Invoke all specialist agents
        recommendations = [a.analyze(context) for a in self.agents]

        # 2. Compute unified cross-sport ACWR
        weekly_load = sum(r.weekly_load for r in recommendations)
        acwr = compute_acwr(load_history + [weekly_load])

        # 3. Aggregate FatigueScores
        global_fatigue = aggregate_fatigue([r.fatigue_score for r in recommendations])

        # 4. Determine macro phase
        phase = get_current_phase(context.athlete.target_race_date, context.date_range[0])

        # 5. Detect inter-agent conflicts
        conflicts = detect_conflicts(recommendations)

        # 6. Compute global readiness
        # min() over all readiness_modifiers (Recovery Coach drives this when HRV is low)
        readiness_modifier = min(r.readiness_modifier for r in recommendations) if recommendations else 1.0
        # _modifier_to_level thresholds: green ≥ 0.9, yellow [0.6, 0.9), red < 0.6
        readiness_level = self._modifier_to_level(readiness_modifier)

        # 7. Collect notes from all agents
        notes = [r.notes for r in recommendations if r.notes]

        # 8. Arbitrate final session list
        all_sessions = [s for r in recommendations for s in r.suggested_sessions]
        sessions = self._arbitrate(all_sessions, conflicts, acwr, readiness_modifier)

        return WeeklyPlan(phase, acwr, global_fatigue, conflicts, sessions, readiness_level, notes)

    def _modifier_to_level(self, modifier: float) -> str:
        # modifier ≥ 0.9 → "green"
        # 0.6 ≤ modifier < 0.9 → "yellow"
        # modifier < 0.6 → "red"

    def _arbitrate(
        self,
        sessions: list[WorkoutSlot],
        conflicts: list[Conflict],
        acwr: ACWRResult,
        readiness_modifier: float,
    ) -> list[WorkoutSlot]:
        # Rules applied in order:
        # 1. If readiness RED (modifier < 0.6): convert all sessions to Z1
        #    (set workout_type = "easy_z1", duration unchanged)
        # 2. If ACWR DANGER: scale all session durations by 0.75 (25% reduction)
        # 3. If conflict CRITICAL: drop the shorter session (by duration_min) of the
        #    conflicting pair. Tiebreaker: drop the session from the agent with
        #    alphabetically later name. This is deterministic.
        # 4. If total weekly load > acwr.max_safe_weekly_load:
        #    trim sessions by dropping shortest sessions first until within budget.
        #    Note: rule 4 operates on post-rule-2 session durations (after any 25% scale).
```

**`_modifier_to_level` thresholds:**
- `modifier ≥ 0.9` → `"green"` (train as planned)
- `0.6 ≤ modifier < 0.9` → `"yellow"` (reduce intensity 10–20%)
- `modifier < 0.6` → `"red"` (Z1 only)

`load_history` is sourced externally (from DB) by the API layer in Phase 4. HeadCoach has no DB dependency.

---

## Section 4 — Reference Data Files

**Location:** `.bmad-core/data/`

| File | Used by | Source |
|---|---|---|
| `volume-landmarks.json` | Lifting Coach (Session 6) | Blueprint §5.2, RP methodology |
| `exercise-database.json` | Lifting Coach (Session 6) | Supplement §3.3 SFR tiers |
| `running-zones.json` | Running Coach (Session 6) | Supplement §2.1 Daniels/Seiler hybrid |
| `cycling-zones.json` | Biking Coach (Session 7) | Supplement §4.1 Coggan zones |
| `swimming-benchmarks.json` | Swimming Coach (Session 7) | Supplement §5.1 CSS zones |
| `nutrition-targets.json` | Nutrition Coach (Session 7) | Blueprint §5.6 + Supplement §6 |

These files are static reference tables loaded via `json.load()` — no Pydantic schema needed.

---

## Section 5 — Testing Strategy

**Structure:**
```
tests/backend/agents/
├── __init__.py
├── conftest.py           # MockAgent, sample AgentContext, sample AgentRecommendation
├── test_base.py          # AgentRecommendation validation, BaseAgent contract
└── test_head_coach.py    # HeadCoach.build_week() end-to-end with mock agents

tests/backend/core/
├── __init__.py
├── test_acwr.py          # compute_acwr — safe zone, danger zone, 10% rule, edge cases
├── test_fatigue.py       # aggregate_fatigue — clamping, muscle union, empty list
├── test_conflict.py      # detect_conflicts — all §1.2 rules
└── test_periodization.py # get_current_phase — all 5 phases, no race date fallback
```

**Target: ~41 tests**

| File | Count |
|---|---|
| `test_base.py` | ~6 |
| `test_head_coach.py` | ~8 |
| `test_acwr.py` | ~7 |
| `test_fatigue.py` | ~6 |
| `test_conflict.py` | ~8 |
| `test_periodization.py` | ~6 |

**Key test cases:**
- ACWR safe/caution/danger/undertrained zones
- ACWR with empty history (cold start graceful handling)
- 10% rule enforcement
- FatigueScore clamping at 100
- HIIT + lifting → critical conflict
- Z2 + lifting → no conflict (§1.2 exception)
- HeadCoach reduces volume on DANGER ACWR
- HeadCoach converts sessions to Z1 on red readiness
- HeadCoach with no agents returns empty plan gracefully

---

## File Map Summary

**Create:**
- `backend/app/agents/__init__.py`
- `backend/app/agents/base.py`
- `backend/app/agents/head_coach.py`
- `backend/app/core/__init__.py`
- `backend/app/core/acwr.py`
- `backend/app/core/fatigue.py`
- `backend/app/core/conflict.py`
- `backend/app/core/periodization.py`
- `.bmad-core/data/volume-landmarks.json`
- `.bmad-core/data/exercise-database.json`
- `.bmad-core/data/running-zones.json`
- `.bmad-core/data/cycling-zones.json`
- `.bmad-core/data/swimming-benchmarks.json`
- `.bmad-core/data/nutrition-targets.json`
- `tests/backend/agents/__init__.py`
- `tests/backend/agents/conftest.py`
- `tests/backend/agents/test_base.py`
- `tests/backend/agents/test_head_coach.py`
- `tests/backend/core/__init__.py`
- `tests/backend/core/test_acwr.py`
- `tests/backend/core/test_fatigue.py`
- `tests/backend/core/test_conflict.py`
- `tests/backend/core/test_periodization.py`

**No existing files modified.**

---

## Invariants (verified after every task)

- `python -m pytest tests/backend/agents/ tests/backend/core/ -v` → all pass
- `python -m pytest tests/backend/ -v` → no regressions (Phase 1+2 tests still pass)
- `poetry run resilio --help` → CLI still responds
