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

`readiness_modifier` allows Recovery Coach to signal low HRV/poor sleep → HeadCoach scales all sessions down accordingly.

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
    SAFE         = "safe"           # 0.8 – 1.3
    CAUTION      = "caution"        # 1.3 – 1.5
    DANGER       = "danger"         # > 1.5

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
- `lambda_acute = 2 / (7 + 1) = 0.25`
- `lambda_chronic = 2 / (28 + 1) ≈ 0.069`
- `EWMA[t] = load[t] * lambda + EWMA[t-1] * (1 - lambda)`

Requires minimum 1 data point; handles empty list gracefully (returns SAFE with zero loads).

**Business rules encoded:**
- Sweet spot: 0.8–1.3 → SAFE
- Danger: >1.5 → DANGER (injury risk ×2–4)
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
    ...
```

Clamping to 100 prevents unrealistic values when multiple high-fatigue agents overlap.

### `core/conflict.py` — Force/Endurance Conflict Detection

Implements Supplement §1.2 sequencing rules.

```python
@dataclass
class Conflict:
    severity: str           # "warning" | "critical"
    rule: str               # rule identifier, e.g. "hiit_strength_same_session"
    agents: list[str]       # e.g. ["running", "lifting"]
    message: str            # human-readable explanation

def detect_conflicts(recommendations: list[AgentRecommendation]) -> list[Conflict]:
    ...
```

**Rules implemented (from Supplement §1.2):**

| Rule | Severity | Condition |
|---|---|---|
| `hiit_strength_same_session` | critical | HIIT session + lifting session on same day |
| `endurance_before_strength_gap` | warning | Endurance before strength with < 3h gap |
| `z2_before_strength_no_conflict` | — | Z2/MICT before strength → no conflict (§1.2) |
| `swimming_before_strength_reduced` | warning (reduced) | Swimming before strength → minor warning only |

`detect_conflicts` receives `List[AgentRecommendation]` — each recommendation carries `agent_name` so the detector can identify which combination triggers a rule.

### `core/periodization.py` — Macro Phase

Implements Supplement §1.3 macro-annual periodization.

```python
class MacroPhase(str, Enum):
    GENERAL_PREP    = "general_prep"       # 8-12 weeks: pyramidal TID, high volume
    SPECIFIC_PREP   = "specific_prep"      # 6-8 weeks: mixed→polarized TID
    PRE_COMPETITION = "pre_competition"    # 3-4 weeks: polarized, strength maintenance
    COMPETITION     = "competition"        # 1-3 weeks: tapering -40-60% volume
    TRANSITION      = "transition"         # 2-4 weeks: active recovery

@dataclass
class PeriodizationPhase:
    phase: MacroPhase
    weeks_remaining: int
    tid_recommendation: str     # "pyramidal" | "polarized" | "mixed"
    volume_modifier: float      # 0.4–1.0 multiplier for target volume

def get_current_phase(target_race_date: date | None, today: date) -> PeriodizationPhase:
    # If no race date: default to GENERAL_PREP
    # weeks_remaining drives phase selection:
    #   > 22w → general_prep
    #   14-22w → specific_prep
    #   7-14w → pre_competition
    #   1-7w  → competition
    #   post-race → transition
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
        readiness_modifier = min(r.readiness_modifier for r in recommendations)
        readiness_level = _modifier_to_level(readiness_modifier)

        # 7. Arbitrate final session list
        all_sessions = [s for r in recommendations for s in r.suggested_sessions]
        sessions = self._arbitrate(all_sessions, conflicts, acwr, readiness_modifier)

        return WeeklyPlan(phase, acwr, global_fatigue, conflicts, sessions, readiness_level, notes)

    def _arbitrate(
        self,
        sessions: list[WorkoutSlot],
        conflicts: list[Conflict],
        acwr: ACWRResult,
        readiness_modifier: float,
    ) -> list[WorkoutSlot]:
        # Rules applied in order:
        # 1. If ACWR DANGER: reduce total volume by 20-30% (scale durations)
        # 2. If conflict critical: remove lower-priority session of conflicting pair
        # 3. If readiness RED (modifier < 0.6): convert all sessions to Z1
        # 4. If proposed weekly load > acwr.max_safe_weekly_load: trim sessions
```

**Arbitration priority order (when dropping sessions):**
1. Keep: long run, main lifting session, key interval session
2. Drop first: supplementary/accessory sessions, extra volume days

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
