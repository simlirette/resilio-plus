# Phase 7 — Agents manquants Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter les 4 agents manquants (BikingCoach, SwimmingCoach, NutritionCoach, RecoveryCoach) et remplacer le budget horaire hardcodé par une allocation dynamique pilotée par les goals de l'athlète.

**Architecture:** Nouveau module `goal_analysis.py` interprète les goals textuels → `dict[Sport, float]`. Ce dict est injecté dans `AgentContext.sport_budgets` par le HeadCoach avant d'appeler les agents. Chaque agent lit `context.sport_budgets.get(self.name, 0.0)` pour son budget. Les 4 nouveaux agents suivent le même pattern que RunningCoach/LiftingCoach : `core/X_logic.py` (logique stateless) + `agents/X_coach.py` (wrapper thin).

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy, pytest. Données depuis `.bmad-core/data/cycling-zones.json`, `swimming-benchmarks.json`, `nutrition-targets.json` (déjà présents). pytest venv : `C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts\python.exe`

---

## File Map

| Fichier | Action | Rôle |
|---------|--------|------|
| `backend/app/core/goal_analysis.py` | Créer | Goals text → sport budget dict |
| `backend/app/core/biking_logic.py` | Créer | FTP fallback, sessions vélo, fatigue |
| `backend/app/core/swimming_logic.py` | Créer | CSS fallback, sessions natation, fatigue |
| `backend/app/core/nutrition_logic.py` | Créer | Directives macro par DayType |
| `backend/app/core/recovery_logic.py` | Créer | RecoveryStatus, sleep banking, HRV trend |
| `backend/app/agents/biking_coach.py` | Créer | BikingCoach(BaseAgent) |
| `backend/app/agents/swimming_coach.py` | Créer | SwimmingCoach(BaseAgent) |
| `backend/app/agents/nutrition_coach.py` | Créer | NutritionCoach(BaseAgent) |
| `backend/app/agents/recovery_coach.py` | Créer | RecoveryCoach(BaseAgent) |
| `backend/app/routes/_agent_factory.py` | Créer | build_agents(athlete) → list[BaseAgent] |
| `backend/app/routes/nutrition.py` | Créer | GET /athletes/{id}/nutrition-directives |
| `backend/app/routes/recovery.py` | Créer | GET /athletes/{id}/recovery-status |
| `backend/app/agents/base.py` | Modifier | Ajouter sport_budgets dans AgentContext |
| `backend/app/agents/head_coach.py` | Modifier | Appeler analyze_goals() avant agents |
| `backend/app/agents/running_coach.py` | Modifier | Lire sport_budgets au lieu de hardcode |
| `backend/app/agents/lifting_coach.py` | Modifier | Lire sport_budgets au lieu de hardcode |
| `backend/app/routes/onboarding.py` | Modifier | Utiliser build_agents() |
| `backend/app/routes/plans.py` | Modifier | Utiliser build_agents() |
| `backend/app/main.py` | Modifier | Inclure nutrition + recovery routers |
| `tests/backend/core/test_goal_analysis.py` | Créer | Tests goal → budget |
| `tests/backend/core/test_biking_logic.py` | Créer | Tests FTP, sessions, fatigue |
| `tests/backend/core/test_swimming_logic.py` | Créer | Tests CSS, sessions, fatigue |
| `tests/backend/core/test_nutrition_logic.py` | Créer | Tests macros par DayType |
| `tests/backend/core/test_recovery_logic.py` | Créer | Tests RecoveryStatus |
| `tests/backend/agents/test_biking_coach.py` | Créer | Tests BikingCoach.analyze() |
| `tests/backend/agents/test_swimming_coach.py` | Créer | Tests SwimmingCoach.analyze() |
| `tests/backend/agents/test_nutrition_coach.py` | Créer | Tests NutritionCoach.analyze() |
| `tests/backend/agents/test_recovery_coach.py` | Créer | Tests RecoveryCoach.analyze() |

---

## Task 1: goal_analysis.py

**Files:**
- Create: `backend/app/core/goal_analysis.py`
- Create: `tests/backend/core/test_goal_analysis.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/backend/core/test_goal_analysis.py`:

```python
from datetime import date, timedelta
import pytest
from app.core.goal_analysis import analyze_goals
from app.schemas.athlete import AthleteProfile, Sport


def _athlete(goals, sports, primary, hours=10.0, race_date=None):
    return AthleteProfile(
        name="Test", age=28, sex="M", weight_kg=75, height_cm=180,
        sports=sports, primary_sport=primary,
        goals=goals, target_race_date=race_date,
        available_days=[0, 2, 4, 6], hours_per_week=hours,
    )


def test_single_sport_gets_all_hours():
    athlete = _athlete(["finish a 10K"], [Sport.RUNNING], Sport.RUNNING, hours=8.0)
    budgets = analyze_goals(athlete)
    assert abs(budgets[Sport.RUNNING] - 8.0) < 0.01


def test_sum_equals_hours_per_week():
    athlete = _athlete(
        ["marathon preparation"], [Sport.RUNNING, Sport.LIFTING], Sport.RUNNING, hours=10.0
    )
    budgets = analyze_goals(athlete)
    assert abs(sum(budgets.values()) - 10.0) < 0.01


def test_running_goal_boosts_running():
    athlete = _athlete(
        ["préparer un marathon"], [Sport.RUNNING, Sport.LIFTING], Sport.RUNNING, hours=10.0
    )
    budgets = analyze_goals(athlete)
    assert budgets[Sport.RUNNING] > budgets[Sport.LIFTING]


def test_biking_keyword_boosts_biking():
    athlete = _athlete(
        ["améliorer mon FTP vélo"], [Sport.RUNNING, Sport.BIKING], Sport.BIKING, hours=9.0
    )
    budgets = analyze_goals(athlete)
    assert budgets[Sport.BIKING] > budgets[Sport.RUNNING]


def test_all_sports_get_positive_budget():
    athlete = _athlete(
        ["triathlon sprint"], [Sport.RUNNING, Sport.BIKING, Sport.SWIMMING, Sport.LIFTING],
        Sport.RUNNING, hours=12.0,
    )
    budgets = analyze_goals(athlete)
    for sport in [Sport.RUNNING, Sport.BIKING, Sport.SWIMMING, Sport.LIFTING]:
        assert budgets[sport] >= 0.33  # floor: min 20min


def test_only_active_sports_in_output():
    athlete = _athlete(["trail running"], [Sport.RUNNING], Sport.RUNNING, hours=8.0)
    budgets = analyze_goals(athlete)
    assert set(budgets.keys()) == {Sport.RUNNING}


def test_near_race_boosts_detected_sport():
    near_race = date.today() + timedelta(weeks=6)
    athlete = _athlete(
        ["course 10K"],
        [Sport.RUNNING, Sport.LIFTING], Sport.RUNNING,
        hours=10.0, race_date=near_race,
    )
    far_athlete = _athlete(
        ["course 10K"],
        [Sport.RUNNING, Sport.LIFTING], Sport.RUNNING,
        hours=10.0, race_date=date.today() + timedelta(weeks=30),
    )
    near_budgets = analyze_goals(athlete)
    far_budgets = analyze_goals(far_athlete)
    assert near_budgets[Sport.RUNNING] >= far_budgets[Sport.RUNNING]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
"/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe" tests/backend/core/test_goal_analysis.py -v
```

Expected: `ImportError` ou `ModuleNotFoundError` — `goal_analysis` n'existe pas encore.

- [ ] **Step 3: Implement `goal_analysis.py`**

Create `backend/app/core/goal_analysis.py`:

```python
from __future__ import annotations

from datetime import date

from ..schemas.athlete import AthleteProfile, Sport

# Keyword → sport weight multiplier
_KEYWORD_WEIGHTS: list[tuple[list[str], Sport, float]] = [
    (["marathon", "5k", "10k", "trail", "course", "running", "run"], Sport.RUNNING, 2.0),
    (["ftp", "vélo", "velo", "biking", "gravel", "cycling", "triathlon"], Sport.BIKING, 2.0),
    (["force", "squat", "hypertrophie", "musculation", "lifting", "deadlift"], Sport.LIFTING, 2.0),
    (["natation", "swimming", "nager", "open water", "swim"], Sport.SWIMMING, 2.0),
]

_NEAR_RACE_WEEKS = 12  # boost if race within this many weeks


def analyze_goals(athlete: AthleteProfile) -> dict[Sport, float]:
    """Interpret athlete goals and return hourly budget per sport.

    Returns dict with exactly the sports in athlete.sports.
    Guarantee: sum(values) == athlete.hours_per_week (within float precision).
    Floor: each active sport receives at least 0.33h (20 min).
    """
    active_sports = list(athlete.sports)
    if not active_sports:
        return {}

    if len(active_sports) == 1:
        return {active_sports[0]: athlete.hours_per_week}

    # 1. Base weights: each sport starts at 1.0
    weights: dict[Sport, float] = {s: 1.0 for s in active_sports}

    # 2. Apply keyword boosts from goals
    goals_lower = " ".join(athlete.goals).lower()
    for keywords, sport, multiplier in _KEYWORD_WEIGHTS:
        if sport not in weights:
            continue
        if any(kw in goals_lower for kw in keywords):
            weights[sport] *= multiplier

    # 3. Near-race boost: if race within _NEAR_RACE_WEEKS, boost detected sport × 1.5
    if athlete.target_race_date:
        weeks_remaining = (athlete.target_race_date - date.today()).days // 7
        if 0 < weeks_remaining <= _NEAR_RACE_WEEKS:
            for keywords, sport, _ in _KEYWORD_WEIGHTS:
                if sport in weights and any(kw in goals_lower for kw in keywords):
                    weights[sport] *= 1.5

    # 4. Normalize to hours_per_week with floor
    floor_h = 0.33  # 20 min minimum per active sport
    total_floor = floor_h * len(active_sports)
    distributable = max(0.0, athlete.hours_per_week - total_floor)

    total_weight = sum(weights.values())
    budgets: dict[Sport, float] = {}
    for sport in active_sports:
        budgets[sport] = floor_h + distributable * (weights[sport] / total_weight)

    # 5. Correct floating-point drift — assign remainder to heaviest sport
    diff = athlete.hours_per_week - sum(budgets.values())
    if abs(diff) > 1e-9:
        heaviest = max(budgets, key=lambda s: budgets[s])
        budgets[heaviest] += diff

    return budgets
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
"/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe" tests/backend/core/test_goal_analysis.py -v
```

Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/goal_analysis.py tests/backend/core/test_goal_analysis.py
git commit -m "feat: add goal_analysis — goals text → sport budget allocation"
```

---

## Task 2: AgentContext + HeadCoach + budget migration

**Files:**
- Modify: `backend/app/agents/base.py`
- Modify: `backend/app/agents/head_coach.py`
- Modify: `backend/app/agents/running_coach.py`
- Modify: `backend/app/agents/lifting_coach.py`

- [ ] **Step 1: Add `sport_budgets` to AgentContext**

In `backend/app/agents/base.py`, add one field to `AgentContext`:

```python
@dataclass
class AgentContext:
    """All data available to specialist agents for a given planning week."""
    athlete: AthleteProfile
    date_range: tuple[date, date]
    phase: str
    strava_activities: list[StravaActivity] = field(default_factory=list)
    hevy_workouts: list[HevyWorkout] = field(default_factory=list)
    terra_health: list[TerraHealthData] = field(default_factory=list)
    fatsecret_days: list[FatSecretDay] = field(default_factory=list)
    week_number: int = 1
    weeks_remaining: int = 0
    sport_budgets: dict[str, float] = field(default_factory=dict)  # NEW
```

- [ ] **Step 2: Integrate `analyze_goals` in HeadCoach**

In `backend/app/agents/head_coach.py`, add the import and call at the top of `build_week()`:

```python
# Add at top of file with other imports:
import dataclasses
from ..core.goal_analysis import analyze_goals

# Replace the start of build_week() — before step 1:
def build_week(
    self,
    context: AgentContext,
    load_history: list[float],
) -> WeeklyPlan:
    # 0. Compute goal-driven sport budgets and inject into context
    budgets = analyze_goals(context.athlete)
    context = dataclasses.replace(
        context,
        sport_budgets={s.value: h for s, h in budgets.items()},
    )

    # 1. Invoke all specialist agents  (rest unchanged)
    recommendations: list[AgentRecommendation] = [
        a.analyze(context) for a in self.agents
    ]
    # ... rest of method unchanged
```

- [ ] **Step 3: Update RunningCoach to read sport_budgets**

In `backend/app/agents/running_coach.py`, replace the budget calculation (step 6):

```python
# Remove these lines:
#   run_ratio = 0.4 if context.athlete.primary_sport == Sport.LIFTING else 0.6
#   hours_budget = context.athlete.hours_per_week * run_ratio

# Replace with:
hours_budget = context.sport_budgets.get("running", context.athlete.hours_per_week * 0.6)
```

Also remove the `Sport` import if no longer used elsewhere in running_coach.py.
Check: `from ..schemas.athlete import Sport` — only remove if Sport is no longer referenced.

- [ ] **Step 4: Update LiftingCoach to read sport_budgets**

In `backend/app/agents/lifting_coach.py`, replace the budget calculation (steps 6-7):

```python
# Remove these lines:
#   lift_ratio = 0.6 if context.athlete.primary_sport == Sport.LIFTING else 0.4
#   hours_budget = context.athlete.hours_per_week * lift_ratio
#   running_load_ratio = 0.6

# Replace with:
hours_budget = context.sport_budgets.get("lifting", context.athlete.hours_per_week * 0.4)
running_load_ratio = context.sport_budgets.get("running", 0) / context.athlete.hours_per_week if context.athlete.hours_per_week > 0 else 0.6
```

- [ ] **Step 5: Run existing tests to confirm no regression**

```bash
"/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe" tests/backend/agents/ tests/backend/core/test_goal_analysis.py -v --tb=short
```

Expected: all previously passing tests still pass. `sport_budgets` has `default_factory=dict` so existing `AgentContext` construction without it still works.

- [ ] **Step 6: Commit**

```bash
git add backend/app/agents/base.py backend/app/agents/head_coach.py backend/app/agents/running_coach.py backend/app/agents/lifting_coach.py
git commit -m "feat: inject sport_budgets into AgentContext via goal_analysis"
```

---

## Task 3: biking_logic.py + BikingCoach

**Files:**
- Create: `backend/app/core/biking_logic.py`
- Create: `backend/app/agents/biking_coach.py`
- Create: `tests/backend/core/test_biking_logic.py`
- Create: `tests/backend/agents/test_biking_coach.py`

- [ ] **Step 1: Write failing tests for biking_logic**

Create `tests/backend/core/test_biking_logic.py`:

```python
from datetime import date
import pytest
from app.core.biking_logic import (
    estimate_ftp, compute_biking_fatigue, generate_biking_sessions,
)
from app.schemas.athlete import AthleteProfile, Sport
from app.schemas.connector import StravaActivity
from app.schemas.plan import WorkoutSlot


def _athlete(ftp=None):
    return AthleteProfile(
        name="Bob", age=30, sex="M", weight_kg=75, height_cm=178,
        sports=[Sport.BIKING], primary_sport=Sport.BIKING,
        goals=["improve FTP"], available_days=[1, 3, 5],
        hours_per_week=6.0, ftp_watts=ftp,
    )


def _ride(duration_s=3600, distance_m=40000):
    return StravaActivity(
        id="s1", name="Ride", sport_type="Ride",
        date=date(2026, 4, 1),
        duration_seconds=duration_s,
        distance_meters=distance_m,
    )


def test_estimate_ftp_uses_athlete_value():
    assert estimate_ftp(_athlete(ftp=250)) == 250


def test_estimate_ftp_cold_start():
    assert estimate_ftp(_athlete(ftp=None)) == 200


def test_compute_biking_fatigue_empty():
    f = compute_biking_fatigue([])
    assert f.local_muscular == 0.0
    assert f.cns_load == 0.0


def test_compute_biking_fatigue_with_ride():
    f = compute_biking_fatigue([_ride()])
    assert f.local_muscular > 0
    assert f.recovery_hours > 0


def test_generate_sessions_returns_workout_slots():
    sessions = generate_biking_sessions(
        ftp=200,
        week_number=1,
        phase="general_prep",
        available_days=[1, 3, 5],
        hours_budget=4.0,
        volume_modifier=1.0,
        week_start=date(2026, 4, 7),
    )
    assert len(sessions) >= 1
    for s in sessions:
        assert isinstance(s, WorkoutSlot)
        assert s.sport.value == "biking"


def test_generate_sessions_respects_available_days():
    sessions = generate_biking_sessions(
        ftp=200, week_number=1, phase="general_prep",
        available_days=[0, 2], hours_budget=3.0,
        volume_modifier=1.0, week_start=date(2026, 4, 7),
    )
    # All sessions must fall on Mon (0) or Wed (2)
    for s in sessions:
        assert s.date.weekday() in [0, 2]


def test_generate_sessions_zero_budget_returns_empty():
    sessions = generate_biking_sessions(
        ftp=200, week_number=1, phase="general_prep",
        available_days=[0, 2, 4], hours_budget=0.0,
        volume_modifier=1.0, week_start=date(2026, 4, 7),
    )
    assert sessions == []
```

- [ ] **Step 2: Run to verify failure**

```bash
"/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe" tests/backend/core/test_biking_logic.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement `biking_logic.py`**

Create `backend/app/core/biking_logic.py`:

```python
from __future__ import annotations

from datetime import date, timedelta

from ..schemas.athlete import AthleteProfile
from ..schemas.connector import StravaActivity
from ..schemas.fatigue import FatigueScore
from ..schemas.plan import WorkoutSlot
from ..schemas.athlete import Sport

_COLD_START_FTP = 200  # watts


def estimate_ftp(athlete: AthleteProfile) -> int:
    """Return stored FTP or cold-start default."""
    return athlete.ftp_watts if athlete.ftp_watts else _COLD_START_FTP


def compute_biking_fatigue(rides: list[StravaActivity]) -> FatigueScore:
    """Compute FatigueScore from a pre-filtered list of Ride activities."""
    if not rides:
        return FatigueScore(
            local_muscular=0.0, cns_load=0.0, metabolic_cost=0.0,
            recovery_hours=0.0, affected_muscles=[],
        )

    total_duration_h = sum(r.duration_seconds for r in rides) / 3600
    total_distance_km = sum((r.distance_meters or 0) for r in rides) / 1000

    # Cycling: low CNS load, moderate local (quads/glutes), moderate metabolic
    local = min(100.0, total_duration_h * 8.0)
    cns = min(30.0, total_duration_h * 3.0)          # much lower than running
    metabolic = min(100.0, total_distance_km * 0.8)
    recovery_h = 12.0 + total_duration_h * 2.0

    return FatigueScore(
        local_muscular=round(local, 1),
        cns_load=round(cns, 1),
        metabolic_cost=round(metabolic, 1),
        recovery_hours=round(recovery_h, 1),
        affected_muscles=["quads", "glutes", "calves"],
    )


# Workout type → intensity weight (for weekly_load calculation)
_INTENSITY: dict[str, float] = {
    "Z2_endurance_ride": 1.0,
    "Z3_tempo_ride": 1.4,
    "Z4_threshold_intervals": 1.8,
}

# Phase → session type preference
_PHASE_SESSION_MAP: dict[str, list[str]] = {
    "general_prep":    ["Z2_endurance_ride", "Z2_endurance_ride", "Z3_tempo_ride"],
    "specific_prep":   ["Z2_endurance_ride", "Z3_tempo_ride", "Z4_threshold_intervals"],
    "pre_competition": ["Z3_tempo_ride", "Z4_threshold_intervals", "Z4_threshold_intervals"],
    "competition":     ["Z2_endurance_ride", "Z3_tempo_ride"],
    "transition":      ["Z2_endurance_ride"],
}

# Session type → (base_duration_min, min_hours_budget_to_add)
_SESSION_DURATIONS: dict[str, tuple[int, float]] = {
    "Z2_endurance_ride":     (75, 1.0),
    "Z3_tempo_ride":         (60, 0.8),
    "Z4_threshold_intervals":(50, 0.7),
}


def generate_biking_sessions(
    ftp: int,
    week_number: int,
    phase: str,
    available_days: list[int],
    hours_budget: float,
    volume_modifier: float,
    week_start: date,
) -> list[WorkoutSlot]:
    """Generate biking WorkoutSlots for the week.

    ftp: athlete FTP in watts (used in notes)
    phase: MacroPhase value string
    available_days: 0=Mon … 6=Sun
    hours_budget: total hours available for biking this week
    volume_modifier: from periodization phase (0.5–1.0)
    week_start: Monday of the planning week
    """
    if hours_budget <= 0 or not available_days:
        return []

    session_types = _PHASE_SESSION_MAP.get(phase, _PHASE_SESSION_MAP["general_prep"])
    # Wave loading: week 3 of every 4 is deload (volume_modifier already handles this)
    effective_budget = hours_budget * volume_modifier

    sessions: list[WorkoutSlot] = []
    used_days: set[int] = set()
    budget_remaining = effective_budget

    fatigue_stub = FatigueScore(
        local_muscular=15.0, cns_load=5.0, metabolic_cost=20.0,
        recovery_hours=12.0, affected_muscles=["quads", "glutes"],
    )

    for session_type in session_types:
        base_min, min_budget = _SESSION_DURATIONS[session_type]
        if budget_remaining < min_budget:
            break

        # Find next available day not yet used
        day_offset = None
        for d in available_days:
            if d not in used_days:
                day_offset = d
                break
        if day_offset is None:
            break

        # Scale duration to budget (cap at base_duration)
        duration_min = min(base_min, int(budget_remaining * 60))
        duration_min = max(20, duration_min)  # floor 20min

        session_date = week_start + timedelta(days=day_offset)
        sessions.append(WorkoutSlot(
            date=session_date,
            sport=Sport.BIKING,
            workout_type=session_type,
            duration_min=int(duration_min * volume_modifier),
            fatigue_score=fatigue_stub,
            notes=f"FTP: {ftp}W | {session_type.replace('_', ' ')}",
        ))
        used_days.add(day_offset)
        budget_remaining -= duration_min / 60

    return sessions
```

- [ ] **Step 4: Run biking_logic tests**

```bash
"/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe" tests/backend/core/test_biking_logic.py -v
```

Expected: 7 passed.

- [ ] **Step 5: Write failing tests for BikingCoach**

Create `tests/backend/agents/test_biking_coach.py`:

```python
from datetime import date
import pytest
from app.agents.base import AgentContext, AgentRecommendation
from app.agents.biking_coach import BikingCoach
from app.schemas.athlete import AthleteProfile, Sport


def _athlete(ftp=200):
    return AthleteProfile(
        name="Caro", age=32, sex="F", weight_kg=62, height_cm=168,
        sports=[Sport.BIKING, Sport.RUNNING], primary_sport=Sport.BIKING,
        goals=["improve FTP"], available_days=[1, 3, 5],
        hours_per_week=8.0, ftp_watts=ftp,
    )


def _context(athlete=None):
    a = athlete or _athlete()
    return AgentContext(
        athlete=a,
        date_range=(date(2026, 4, 7), date(2026, 4, 13)),
        phase="general_prep",
        week_number=1,
        weeks_remaining=20,
        sport_budgets={"biking": 4.8, "running": 3.2},
    )


def test_name_is_biking():
    assert BikingCoach().name == "biking"


def test_analyze_returns_recommendation():
    result = BikingCoach().analyze(_context())
    assert isinstance(result, AgentRecommendation)


def test_analyze_sessions_are_biking_sport():
    result = BikingCoach().analyze(_context())
    for s in result.suggested_sessions:
        assert s.sport.value == "biking"


def test_analyze_zero_budget_returns_no_sessions():
    ctx = _context()
    ctx = AgentContext(**{**ctx.__dict__, "sport_budgets": {"biking": 0.0}})
    result = BikingCoach().analyze(ctx)
    assert result.suggested_sessions == []
    assert result.weekly_load == 0.0


def test_analyze_weekly_load_positive_with_sessions():
    result = BikingCoach().analyze(_context())
    if result.suggested_sessions:
        assert result.weekly_load > 0
```

- [ ] **Step 6: Run to verify failure, then implement BikingCoach**

```bash
"/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe" tests/backend/agents/test_biking_coach.py -v
```

Expected: `ImportError`.

Create `backend/app/agents/biking_coach.py`:

```python
from __future__ import annotations

from datetime import timedelta

from ..agents.base import AgentContext, AgentRecommendation, BaseAgent
from ..core.biking_logic import (
    compute_biking_fatigue, estimate_ftp, generate_biking_sessions,
)
from ..core.periodization import get_current_phase
from ..core.readiness import compute_readiness


class BikingCoach(BaseAgent):
    """Specialist agent for cycling: FTP-aware, Coggan zones, wave loading."""

    @property
    def name(self) -> str:
        return "biking"

    def analyze(self, context: AgentContext) -> AgentRecommendation:
        # 1. Filter Strava rides to 7 days before this week
        prior_rides = [
            a for a in context.strava_activities
            if a.sport_type in ("Ride", "VirtualRide")
            and context.date_range[0] - timedelta(days=7) <= a.date < context.date_range[0]
        ]

        # 2. FTP: use athlete's stored value or cold start
        ftp = estimate_ftp(context.athlete)

        # 3. Readiness modifier from Terra data
        readiness_modifier = compute_readiness(context.terra_health)

        # 4. Fatigue from last week's rides
        fatigue_score = compute_biking_fatigue(prior_rides)

        # 5. Periodization phase
        phase = get_current_phase(context.athlete.target_race_date, context.date_range[0])

        # 6. Budget from goal analysis (injected by HeadCoach)
        hours_budget = context.sport_budgets.get("biking", 0.0)

        # 7. Generate sessions
        sessions = generate_biking_sessions(
            ftp=ftp,
            week_number=context.week_number,
            phase=phase.phase.value,
            available_days=context.athlete.available_days,
            hours_budget=hours_budget,
            volume_modifier=phase.volume_modifier,
            week_start=context.date_range[0],
        )

        # 8. Weekly load
        _INTENSITY = {
            "Z2_endurance_ride": 1.0,
            "Z3_tempo_ride": 1.4,
            "Z4_threshold_intervals": 1.8,
        }
        weekly_load = sum(
            s.duration_min * _INTENSITY.get(s.workout_type, 1.0)
            for s in sessions
        )

        return AgentRecommendation(
            agent_name=self.name,
            fatigue_score=fatigue_score,
            weekly_load=weekly_load,
            suggested_sessions=sessions,
            readiness_modifier=readiness_modifier,
            notes=f"FTP {ftp}W | Phase: {phase.phase.value} | Week: {context.week_number}",
        )
```

- [ ] **Step 7: Run all biking tests**

```bash
"/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe" tests/backend/core/test_biking_logic.py tests/backend/agents/test_biking_coach.py -v
```

Expected: all passed.

- [ ] **Step 8: Commit**

```bash
git add backend/app/core/biking_logic.py backend/app/agents/biking_coach.py tests/backend/core/test_biking_logic.py tests/backend/agents/test_biking_coach.py
git commit -m "feat: add BikingCoach with FTP-aware session generation"
```

---

## Task 4: swimming_logic.py + SwimmingCoach

**Files:**
- Create: `backend/app/core/swimming_logic.py`
- Create: `backend/app/agents/swimming_coach.py`
- Create: `tests/backend/core/test_swimming_logic.py`
- Create: `tests/backend/agents/test_swimming_coach.py`

- [ ] **Step 1: Write failing tests for swimming_logic**

Create `tests/backend/core/test_swimming_logic.py`:

```python
from datetime import date
import pytest
from app.core.swimming_logic import (
    estimate_css, compute_swimming_fatigue, generate_swimming_sessions,
)
from app.schemas.athlete import AthleteProfile, Sport
from app.schemas.connector import StravaActivity
from app.schemas.plan import WorkoutSlot


def _athlete(css=None):
    return AthleteProfile(
        name="Marie", age=26, sex="F", weight_kg=60, height_cm=165,
        sports=[Sport.SWIMMING], primary_sport=Sport.SWIMMING,
        goals=["triathlon"], available_days=[1, 3, 6],
        hours_per_week=5.0, css_per_100m=css,
    )


def _swim(duration_s=1800, distance_m=1500):
    return StravaActivity(
        id="sw1", name="Swim", sport_type="Swim",
        date=date(2026, 4, 1),
        duration_seconds=duration_s,
        distance_meters=distance_m,
    )


def test_estimate_css_uses_athlete_value():
    assert estimate_css(_athlete(css=90.0)) == 90.0


def test_estimate_css_cold_start():
    # Cold start = 1:45/100m = 105 seconds/100m
    assert estimate_css(_athlete(css=None)) == 105.0


def test_compute_swimming_fatigue_empty():
    f = compute_swimming_fatigue([])
    assert f.local_muscular == 0.0


def test_compute_swimming_fatigue_with_swim():
    f = compute_swimming_fatigue([_swim()])
    assert f.local_muscular > 0
    assert "shoulders" in f.affected_muscles


def test_generate_sessions_returns_workout_slots():
    sessions = generate_swimming_sessions(
        css_per_100m=105.0,
        week_number=1,
        phase="general_prep",
        available_days=[1, 3, 6],
        hours_budget=3.0,
        volume_modifier=1.0,
        week_start=date(2026, 4, 7),
    )
    assert len(sessions) >= 1
    for s in sessions:
        assert isinstance(s, WorkoutSlot)
        assert s.sport.value == "swimming"


def test_generate_sessions_zero_budget():
    sessions = generate_swimming_sessions(
        css_per_100m=105.0, week_number=1, phase="general_prep",
        available_days=[1, 3], hours_budget=0.0,
        volume_modifier=1.0, week_start=date(2026, 4, 7),
    )
    assert sessions == []
```

- [ ] **Step 2: Run to verify failure**

```bash
"/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe" tests/backend/core/test_swimming_logic.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement `swimming_logic.py`**

Create `backend/app/core/swimming_logic.py`:

```python
from __future__ import annotations

from datetime import date, timedelta

from ..schemas.athlete import AthleteProfile, Sport
from ..schemas.connector import StravaActivity
from ..schemas.fatigue import FatigueScore
from ..schemas.plan import WorkoutSlot

_COLD_START_CSS = 105.0  # seconds per 100m = 1:45/100m


def estimate_css(athlete: AthleteProfile) -> float:
    """Return stored CSS (s/100m) or cold-start default."""
    return athlete.css_per_100m if athlete.css_per_100m else _COLD_START_CSS


def compute_swimming_fatigue(swims: list[StravaActivity]) -> FatigueScore:
    """Compute FatigueScore from a pre-filtered list of Swim activities."""
    if not swims:
        return FatigueScore(
            local_muscular=0.0, cns_load=0.0, metabolic_cost=0.0,
            recovery_hours=0.0, affected_muscles=[],
        )

    total_duration_h = sum(s.duration_seconds for s in swims) / 3600
    total_distance_m = sum((s.distance_meters or 0) for s in swims)

    # Swimming: moderate local (shoulders/lats), low CNS, moderate metabolic
    local = min(100.0, total_distance_m / 100 * 1.5)   # per 100m
    cns = min(20.0, total_duration_h * 2.0)
    metabolic = min(100.0, total_duration_h * 12.0)
    recovery_h = 10.0 + total_duration_h * 1.5

    return FatigueScore(
        local_muscular=round(local, 1),
        cns_load=round(cns, 1),
        metabolic_cost=round(metabolic, 1),
        recovery_hours=round(recovery_h, 1),
        affected_muscles=["shoulders", "lats", "triceps"],
    )


_PHASE_SESSION_MAP: dict[str, list[str]] = {
    "general_prep":    ["Z1_technique", "Z2_endurance_swim"],
    "specific_prep":   ["Z2_endurance_swim", "Z3_threshold_set"],
    "pre_competition": ["Z3_threshold_set", "Z2_endurance_swim"],
    "competition":     ["Z2_endurance_swim"],
    "transition":      ["Z1_technique"],
}

_SESSION_DURATIONS: dict[str, tuple[int, float]] = {
    "Z1_technique":       (45, 0.6),
    "Z2_endurance_swim":  (60, 0.8),
    "Z3_threshold_set":   (50, 0.7),
}

_INTENSITY: dict[str, float] = {
    "Z1_technique": 0.8,
    "Z2_endurance_swim": 1.0,
    "Z3_threshold_set": 1.5,
}


def generate_swimming_sessions(
    css_per_100m: float,
    week_number: int,
    phase: str,
    available_days: list[int],
    hours_budget: float,
    volume_modifier: float,
    week_start: date,
) -> list[WorkoutSlot]:
    """Generate swimming WorkoutSlots for the week."""
    if hours_budget <= 0 or not available_days:
        return []

    session_types = _PHASE_SESSION_MAP.get(phase, _PHASE_SESSION_MAP["general_prep"])
    effective_budget = hours_budget * volume_modifier

    sessions: list[WorkoutSlot] = []
    used_days: set[int] = set()
    budget_remaining = effective_budget

    fatigue_stub = FatigueScore(
        local_muscular=12.0, cns_load=4.0, metabolic_cost=18.0,
        recovery_hours=10.0, affected_muscles=["shoulders", "lats"],
    )

    css_pace_str = f"{int(css_per_100m // 60)}:{int(css_per_100m % 60):02d}/100m"

    for session_type in session_types:
        base_min, min_budget = _SESSION_DURATIONS[session_type]
        if budget_remaining < min_budget:
            break

        day_offset = None
        for d in available_days:
            if d not in used_days:
                day_offset = d
                break
        if day_offset is None:
            break

        duration_min = min(base_min, int(budget_remaining * 60))
        duration_min = max(20, duration_min)

        sessions.append(WorkoutSlot(
            date=week_start + timedelta(days=day_offset),
            sport=Sport.SWIMMING,
            workout_type=session_type,
            duration_min=int(duration_min * volume_modifier),
            fatigue_score=fatigue_stub,
            notes=f"CSS: {css_pace_str} | {session_type.replace('_', ' ')}",
        ))
        used_days.add(day_offset)
        budget_remaining -= duration_min / 60

    return sessions
```

- [ ] **Step 4: Run swimming_logic tests**

```bash
"/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe" tests/backend/core/test_swimming_logic.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Write and run SwimmingCoach tests**

Create `tests/backend/agents/test_swimming_coach.py`:

```python
from datetime import date
from app.agents.base import AgentContext, AgentRecommendation
from app.agents.swimming_coach import SwimmingCoach
from app.schemas.athlete import AthleteProfile, Sport


def _athlete():
    return AthleteProfile(
        name="Marie", age=26, sex="F", weight_kg=60, height_cm=165,
        sports=[Sport.SWIMMING, Sport.RUNNING], primary_sport=Sport.SWIMMING,
        goals=["triathlon"], available_days=[1, 3, 6],
        hours_per_week=8.0, css_per_100m=100.0,
    )


def _context():
    return AgentContext(
        athlete=_athlete(),
        date_range=(date(2026, 4, 7), date(2026, 4, 13)),
        phase="general_prep", week_number=1, weeks_remaining=20,
        sport_budgets={"swimming": 4.0, "running": 4.0},
    )


def test_name_is_swimming():
    assert SwimmingCoach().name == "swimming"


def test_analyze_returns_recommendation():
    result = SwimmingCoach().analyze(_context())
    assert isinstance(result, AgentRecommendation)


def test_sessions_are_swimming_sport():
    result = SwimmingCoach().analyze(_context())
    for s in result.suggested_sessions:
        assert s.sport.value == "swimming"
```

```bash
"/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe" tests/backend/agents/test_swimming_coach.py -v
```

Expected: `ImportError`.

Create `backend/app/agents/swimming_coach.py`:

```python
from __future__ import annotations

from datetime import timedelta

from ..agents.base import AgentContext, AgentRecommendation, BaseAgent
from ..core.swimming_logic import (
    compute_swimming_fatigue, estimate_css, generate_swimming_sessions,
)
from ..core.periodization import get_current_phase
from ..core.readiness import compute_readiness


class SwimmingCoach(BaseAgent):
    """Specialist agent for swimming: CSS-based zones, technique focus."""

    @property
    def name(self) -> str:
        return "swimming"

    def analyze(self, context: AgentContext) -> AgentRecommendation:
        prior_swims = [
            a for a in context.strava_activities
            if a.sport_type == "Swim"
            and context.date_range[0] - timedelta(days=7) <= a.date < context.date_range[0]
        ]

        css = estimate_css(context.athlete)
        readiness_modifier = compute_readiness(context.terra_health)
        fatigue_score = compute_swimming_fatigue(prior_swims)
        phase = get_current_phase(context.athlete.target_race_date, context.date_range[0])
        hours_budget = context.sport_budgets.get("swimming", 0.0)

        sessions = generate_swimming_sessions(
            css_per_100m=css,
            week_number=context.week_number,
            phase=phase.phase.value,
            available_days=context.athlete.available_days,
            hours_budget=hours_budget,
            volume_modifier=phase.volume_modifier,
            week_start=context.date_range[0],
        )

        _INTENSITY = {
            "Z1_technique": 0.8, "Z2_endurance_swim": 1.0, "Z3_threshold_set": 1.5,
        }
        weekly_load = sum(
            s.duration_min * _INTENSITY.get(s.workout_type, 1.0) for s in sessions
        )

        return AgentRecommendation(
            agent_name=self.name,
            fatigue_score=fatigue_score,
            weekly_load=weekly_load,
            suggested_sessions=sessions,
            readiness_modifier=readiness_modifier,
            notes=f"CSS {css:.0f}s/100m | Phase: {phase.phase.value}",
        )
```

```bash
"/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe" tests/backend/core/test_swimming_logic.py tests/backend/agents/test_swimming_coach.py -v
```

Expected: all passed.

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/swimming_logic.py backend/app/agents/swimming_coach.py tests/backend/core/test_swimming_logic.py tests/backend/agents/test_swimming_coach.py
git commit -m "feat: add SwimmingCoach with CSS-based session generation"
```

---

## Task 5: nutrition_logic.py + NutritionCoach + route

**Files:**
- Create: `backend/app/core/nutrition_logic.py`
- Create: `backend/app/agents/nutrition_coach.py`
- Create: `backend/app/routes/nutrition.py`
- Create: `tests/backend/core/test_nutrition_logic.py`
- Create: `tests/backend/agents/test_nutrition_coach.py`

- [ ] **Step 1: Write failing tests for nutrition_logic**

Create `tests/backend/core/test_nutrition_logic.py`:

```python
import pytest
from app.core.nutrition_logic import compute_nutrition_directives
from app.schemas.athlete import AthleteProfile, Sport, DayType
from app.schemas.nutrition import DayNutrition, NutritionPlan


def _athlete(weight=75.0):
    return AthleteProfile(
        name="Alex", age=30, sex="M", weight_kg=weight, height_cm=178,
        sports=[Sport.RUNNING, Sport.LIFTING], primary_sport=Sport.RUNNING,
        goals=["marathon"], available_days=[0, 2, 4, 6], hours_per_week=10.0,
    )


def test_returns_nutrition_plan():
    result = compute_nutrition_directives(_athlete())
    assert isinstance(result, NutritionPlan)


def test_all_day_types_covered():
    result = compute_nutrition_directives(_athlete())
    for day_type in [DayType.REST, DayType.STRENGTH, DayType.ENDURANCE_SHORT, DayType.ENDURANCE_LONG]:
        assert day_type in result.targets_by_day_type


def test_endurance_long_has_more_carbs_than_rest():
    result = compute_nutrition_directives(_athlete(weight=75.0))
    rest_carbs = result.targets_by_day_type[DayType.REST].macro_target.carbs_g_per_kg
    endo_carbs = result.targets_by_day_type[DayType.ENDURANCE_LONG].macro_target.carbs_g_per_kg
    assert endo_carbs > rest_carbs


def test_intra_effort_none_for_short_sessions():
    result = compute_nutrition_directives(_athlete())
    assert result.targets_by_day_type[DayType.ENDURANCE_SHORT].intra_effort_carbs_g_per_h is None


def test_intra_effort_present_for_long_sessions():
    result = compute_nutrition_directives(_athlete())
    assert result.targets_by_day_type[DayType.ENDURANCE_LONG].intra_effort_carbs_g_per_h is not None
    assert result.targets_by_day_type[DayType.ENDURANCE_LONG].intra_effort_carbs_g_per_h > 0


def test_protein_is_1_8_per_kg():
    result = compute_nutrition_directives(_athlete(weight=75.0))
    for day_type, dn in result.targets_by_day_type.items():
        assert abs(dn.macro_target.protein_g_per_kg - 1.8) < 0.01
```

- [ ] **Step 2: Run to verify failure**

```bash
"/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe" tests/backend/core/test_nutrition_logic.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement `nutrition_logic.py`**

Create `backend/app/core/nutrition_logic.py`:

```python
from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from ..schemas.athlete import AthleteProfile, DayType
from ..schemas.nutrition import DayNutrition, MacroTarget, NutritionPlan

_REPO_ROOT = Path(__file__).resolve().parents[3]
_NUTRITION_DATA: dict = json.loads(
    (_REPO_ROOT / ".bmad-core" / "data" / "nutrition-targets.json").read_text()
)

# carbs_g_per_kg ranges from nutrition-targets.json (midpoint used)
_CARBS_BY_DAY_TYPE: dict[DayType, float] = {
    DayType.STRENGTH:         4.5,   # [4, 5] midpoint
    DayType.ENDURANCE_SHORT:  5.5,   # [5, 6] midpoint
    DayType.ENDURANCE_LONG:   6.5,   # [6, 7] midpoint
    DayType.REST:             3.5,   # [3, 4] midpoint
    DayType.RACE:             7.0,   # race day: max carb
}

_PROTEIN_G_PER_KG = 1.8   # constant across all day types
_FAT_G_PER_KG = 1.2       # moderate fat

# Intra-effort carbs: only for sessions > 60 min (ENDURANCE_LONG, RACE)
_INTRA_EFFORT_G_PER_H: dict[DayType, float | None] = {
    DayType.STRENGTH:         None,
    DayType.ENDURANCE_SHORT:  None,     # < 60min sessions
    DayType.ENDURANCE_LONG:   45.0,    # midpoint [30, 60] g/h
    DayType.REST:             None,
    DayType.RACE:             75.0,    # midpoint [60, 90] g/h
}


def compute_nutrition_directives(athlete: AthleteProfile) -> NutritionPlan:
    """Compute per-day-type nutrition targets for the athlete.

    Returns a NutritionPlan with targets for all DayType values.
    Calories computed from macros: carbs*4 + protein*4 + fat*9 (per kg × weight).
    """
    targets: dict[DayType, DayNutrition] = {}

    for day_type in [DayType.REST, DayType.STRENGTH, DayType.ENDURANCE_SHORT,
                     DayType.ENDURANCE_LONG, DayType.RACE]:
        carbs = _CARBS_BY_DAY_TYPE[day_type]
        protein = _PROTEIN_G_PER_KG
        fat = _FAT_G_PER_KG
        calories = int(
            (carbs * athlete.weight_kg * 4)
            + (protein * athlete.weight_kg * 4)
            + (fat * athlete.weight_kg * 9)
        )

        targets[day_type] = DayNutrition(
            day_type=day_type,
            macro_target=MacroTarget(
                carbs_g_per_kg=carbs,
                protein_g_per_kg=protein,
                fat_g_per_kg=fat,
                calories_total=calories,
            ),
            intra_effort_carbs_g_per_h=_INTRA_EFFORT_G_PER_H[day_type],
        )

    return NutritionPlan(
        athlete_id=athlete.id,
        weight_kg=athlete.weight_kg,
        targets_by_day_type=targets,
    )
```

- [ ] **Step 4: Run nutrition_logic tests**

```bash
"/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe" tests/backend/core/test_nutrition_logic.py -v
```

Expected: 7 passed.

- [ ] **Step 5: Implement NutritionCoach + tests**

Create `tests/backend/agents/test_nutrition_coach.py`:

```python
from datetime import date
from app.agents.base import AgentContext, AgentRecommendation
from app.agents.nutrition_coach import NutritionCoach
from app.schemas.athlete import AthleteProfile, Sport


def _athlete():
    return AthleteProfile(
        name="Alex", age=30, sex="M", weight_kg=75, height_cm=178,
        sports=[Sport.RUNNING], primary_sport=Sport.RUNNING,
        goals=["marathon"], available_days=[0, 2, 4, 6], hours_per_week=10.0,
    )


def _context():
    return AgentContext(
        athlete=_athlete(),
        date_range=(date(2026, 4, 7), date(2026, 4, 13)),
        phase="general_prep", week_number=1, weeks_remaining=20,
        sport_budgets={"running": 10.0},
    )


def test_name_is_nutrition():
    assert NutritionCoach().name == "nutrition"


def test_analyze_returns_recommendation():
    result = NutritionCoach().analyze(_context())
    assert isinstance(result, AgentRecommendation)


def test_no_physical_sessions():
    result = NutritionCoach().analyze(_context())
    assert result.suggested_sessions == []


def test_weekly_load_is_zero():
    result = NutritionCoach().analyze(_context())
    assert result.weekly_load == 0.0


def test_readiness_modifier_is_one():
    result = NutritionCoach().analyze(_context())
    assert result.readiness_modifier == 1.0


def test_notes_contains_directives():
    result = NutritionCoach().analyze(_context())
    assert "carbs" in result.notes.lower() or "rest" in result.notes.lower()
```

Create `backend/app/agents/nutrition_coach.py`:

```python
from __future__ import annotations

from ..agents.base import AgentContext, AgentRecommendation, BaseAgent
from ..core.nutrition_logic import compute_nutrition_directives
from ..schemas.fatigue import FatigueScore


class NutritionCoach(BaseAgent):
    """Specialist agent for nutrition: carb periodization by day type.

    Does not generate physical sessions. Produces nutrition directives
    as structured notes. weekly_load = 0, readiness_modifier = 1.0.
    """

    @property
    def name(self) -> str:
        return "nutrition"

    def analyze(self, context: AgentContext) -> AgentRecommendation:
        plan = compute_nutrition_directives(context.athlete)

        # Format directives as human-readable notes
        lines = []
        for day_type, dn in plan.targets_by_day_type.items():
            mt = dn.macro_target
            line = (
                f"{day_type.value}: carbs={mt.carbs_g_per_kg}g/kg "
                f"protein={mt.protein_g_per_kg}g/kg "
                f"kcal≈{mt.calories_total}"
            )
            if dn.intra_effort_carbs_g_per_h:
                line += f" | intra: {dn.intra_effort_carbs_g_per_h}g/h"
            lines.append(line)

        return AgentRecommendation(
            agent_name=self.name,
            fatigue_score=FatigueScore(
                local_muscular=0.0, cns_load=0.0, metabolic_cost=0.0,
                recovery_hours=0.0, affected_muscles=[],
            ),
            weekly_load=0.0,
            suggested_sessions=[],
            readiness_modifier=1.0,
            notes="\n".join(lines),
        )
```

```bash
"/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe" tests/backend/agents/test_nutrition_coach.py -v
```

Expected: 6 passed.

- [ ] **Step 6: Create nutrition route**

Create `backend/app/routes/nutrition.py`:

```python
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..core.nutrition_logic import compute_nutrition_directives
from ..db.models import AthleteModel
from ..dependencies import get_db, get_current_athlete_id
from ..routes.athletes import athlete_model_to_response
from ..schemas.nutrition import NutritionPlan

router = APIRouter(prefix="/athletes", tags=["nutrition"])

DB = Annotated[Session, Depends(get_db)]


def _require_own(
    athlete_id: str,
    current_id: Annotated[str, Depends(get_current_athlete_id)],
) -> str:
    if current_id != athlete_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return athlete_id


@router.get("/{athlete_id}/nutrition-directives", response_model=NutritionPlan)
def get_nutrition_directives(
    athlete_id: str,
    db: DB,
    _: Annotated[str, Depends(_require_own)],
) -> NutritionPlan:
    """Return per-day-type macro targets for the athlete."""
    athlete_model = db.get(AthleteModel, athlete_id)
    if athlete_model is None:
        raise HTTPException(status_code=404, detail="Athlete not found")
    athlete = athlete_model_to_response(athlete_model)
    return compute_nutrition_directives(athlete)
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/core/nutrition_logic.py backend/app/agents/nutrition_coach.py backend/app/routes/nutrition.py tests/backend/core/test_nutrition_logic.py tests/backend/agents/test_nutrition_coach.py
git commit -m "feat: add NutritionCoach with carb periodization by day type"
```

---

## Task 6: recovery_logic.py + RecoveryCoach + route

**Files:**
- Create: `backend/app/core/recovery_logic.py`
- Create: `backend/app/agents/recovery_coach.py`
- Create: `backend/app/routes/recovery.py`
- Create: `tests/backend/core/test_recovery_logic.py`
- Create: `tests/backend/agents/test_recovery_coach.py`

- [ ] **Step 1: Write failing tests for recovery_logic**

Create `tests/backend/core/test_recovery_logic.py`:

```python
from datetime import date, timedelta
import pytest
from app.core.recovery_logic import compute_recovery_status, RecoveryStatus
from app.schemas.connector import TerraHealthData


def _terra(days=7, hrv=55.0, sleep=7.5, score=75.0):
    today = date.today()
    return [
        TerraHealthData(
            date=today - timedelta(days=i),
            hrv_rmssd=hrv,
            sleep_duration_hours=sleep,
            sleep_score=score,
        )
        for i in range(days)
    ]


def test_returns_recovery_status():
    result = compute_recovery_status([], None, date.today())
    assert isinstance(result, RecoveryStatus)


def test_cold_start_readiness_is_one():
    result = compute_recovery_status([], None, date.today())
    assert result.readiness_modifier == 1.0


def test_good_hrv_sleep_readiness_above_one():
    result = compute_recovery_status(_terra(hrv=65.0, sleep=8.0, score=85.0), None, date.today())
    assert result.readiness_modifier >= 1.0


def test_poor_sleep_reduces_readiness():
    result = compute_recovery_status(_terra(hrv=50.0, sleep=5.0, score=40.0), None, date.today())
    assert result.readiness_modifier < 1.0


def test_hrv_trend_values():
    result = compute_recovery_status(_terra(), None, date.today())
    assert result.hrv_trend in ("improving", "stable", "declining")


def test_sleep_banking_active_near_race():
    near_race = date.today() + timedelta(weeks=1)
    result = compute_recovery_status(_terra(), near_race, date.today())
    assert result.sleep_banking_active is True


def test_sleep_banking_inactive_far_race():
    far_race = date.today() + timedelta(weeks=20)
    result = compute_recovery_status(_terra(), far_race, date.today())
    assert result.sleep_banking_active is False
```

- [ ] **Step 2: Run to verify failure**

```bash
"/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe" tests/backend/core/test_recovery_logic.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement `recovery_logic.py`**

Create `backend/app/core/recovery_logic.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from ..core.readiness import compute_readiness
from ..schemas.connector import TerraHealthData

_SLEEP_BANKING_WEEKS = 2  # activate sleep banking if race within this many weeks


@dataclass
class RecoveryStatus:
    readiness_modifier: float       # [0.5, 1.5]
    hrv_trend: str                  # "improving" | "stable" | "declining"
    sleep_avg_hours: float | None   # average sleep over last 7 days
    sleep_banking_active: bool      # True if race within _SLEEP_BANKING_WEEKS
    recommendation: str             # human-readable coaching note


def compute_recovery_status(
    terra_data: list[TerraHealthData],
    target_race_date: date | None,
    week_start: date,
) -> RecoveryStatus:
    """Compute recovery status from Terra health data.

    Delegates readiness_modifier to existing compute_readiness().
    Adds HRV trend (3-point slope) and sleep banking flag.
    """
    readiness_modifier = compute_readiness(terra_data)

    # HRV trend: compare first 3 vs last 3 entries (oldest-first after sort)
    hrv_values = [
        e.hrv_rmssd
        for e in sorted(terra_data, key=lambda e: e.date)
        if e.hrv_rmssd is not None
    ]
    hrv_trend = _compute_hrv_trend(hrv_values)

    # Sleep average
    sleep_values = [e.sleep_duration_hours for e in terra_data if e.sleep_duration_hours]
    sleep_avg = round(sum(sleep_values) / len(sleep_values), 1) if sleep_values else None

    # Sleep banking
    sleep_banking_active = False
    if target_race_date:
        weeks_to_race = (target_race_date - week_start).days // 7
        sleep_banking_active = 0 < weeks_to_race <= _SLEEP_BANKING_WEEKS

    # Recommendation
    recommendation = _build_recommendation(
        readiness_modifier, hrv_trend, sleep_avg, sleep_banking_active
    )

    return RecoveryStatus(
        readiness_modifier=readiness_modifier,
        hrv_trend=hrv_trend,
        sleep_avg_hours=sleep_avg,
        sleep_banking_active=sleep_banking_active,
        recommendation=recommendation,
    )


def _compute_hrv_trend(hrv_values: list[float]) -> str:
    """Return 'improving', 'stable', or 'declining' based on 3-point comparison."""
    if len(hrv_values) < 4:
        return "stable"
    early_mean = sum(hrv_values[:3]) / 3
    late_mean = sum(hrv_values[-3:]) / 3
    delta_pct = (late_mean - early_mean) / early_mean if early_mean > 0 else 0
    if delta_pct > 0.05:
        return "improving"
    if delta_pct < -0.05:
        return "declining"
    return "stable"


def _build_recommendation(
    modifier: float,
    trend: str,
    sleep_avg: float | None,
    banking: bool,
) -> str:
    parts = []
    if modifier < 0.7:
        parts.append("Readiness low — reduce intensity, prioritize sleep and recovery.")
    elif modifier < 0.9:
        parts.append("Readiness moderate — avoid maximal efforts.")
    else:
        parts.append("Readiness good — proceed as planned.")

    if trend == "declining":
        parts.append("HRV declining — monitor for overtraining.")
    elif trend == "improving":
        parts.append("HRV improving — recovery on track.")

    if banking:
        parts.append("Sleep banking active — target 8.5-10h/night this week.")
    elif sleep_avg is not None and sleep_avg < 7.0:
        parts.append(f"Sleep averaging {sleep_avg}h — aim for 7.5-8h minimum.")

    return " ".join(parts)
```

- [ ] **Step 4: Run recovery_logic tests**

```bash
"/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe" tests/backend/core/test_recovery_logic.py -v
```

Expected: 7 passed.

- [ ] **Step 5: Implement RecoveryCoach + tests**

Create `tests/backend/agents/test_recovery_coach.py`:

```python
from datetime import date
from app.agents.base import AgentContext, AgentRecommendation
from app.agents.recovery_coach import RecoveryCoach
from app.schemas.athlete import AthleteProfile, Sport


def _athlete():
    return AthleteProfile(
        name="Pat", age=35, sex="M", weight_kg=80, height_cm=182,
        sports=[Sport.RUNNING], primary_sport=Sport.RUNNING,
        goals=["marathon"], available_days=[0, 2, 4, 6], hours_per_week=10.0,
    )


def _context():
    return AgentContext(
        athlete=_athlete(),
        date_range=(date(2026, 4, 7), date(2026, 4, 13)),
        phase="general_prep", week_number=1, weeks_remaining=20,
        sport_budgets={"running": 10.0},
    )


def test_name_is_recovery():
    assert RecoveryCoach().name == "recovery"


def test_analyze_returns_recommendation():
    result = RecoveryCoach().analyze(_context())
    assert isinstance(result, AgentRecommendation)


def test_weekly_load_is_zero():
    result = RecoveryCoach().analyze(_context())
    assert result.weekly_load == 0.0


def test_readiness_modifier_in_range():
    result = RecoveryCoach().analyze(_context())
    assert 0.5 <= result.readiness_modifier <= 1.5


def test_no_sessions_when_readiness_normal():
    result = RecoveryCoach().analyze(_context())
    # No terra data = readiness 1.0 = no forced recovery sessions
    assert result.suggested_sessions == []
```

Create `backend/app/agents/recovery_coach.py`:

```python
from __future__ import annotations

from datetime import timedelta

from ..agents.base import AgentContext, AgentRecommendation, BaseAgent
from ..core.recovery_logic import compute_recovery_status
from ..schemas.athlete import Sport
from ..schemas.fatigue import FatigueScore
from ..schemas.plan import WorkoutSlot

_LOW_READINESS_THRESHOLD = 0.7


class RecoveryCoach(BaseAgent):
    """Specialist agent for recovery: HRV-guided readiness, sleep banking.

    Does not consume training budget. Adds a recovery session if readiness is low.
    weekly_load = 0 (recovery sessions do not count as training load).
    """

    @property
    def name(self) -> str:
        return "recovery"

    def analyze(self, context: AgentContext) -> AgentRecommendation:
        status = compute_recovery_status(
            context.terra_health,
            context.athlete.target_race_date,
            context.date_range[0],
        )

        sessions: list[WorkoutSlot] = []

        # Add an active_recovery session if readiness is low
        if status.readiness_modifier < _LOW_READINESS_THRESHOLD:
            # Pick the first available day for a recovery session
            if context.athlete.available_days:
                recovery_day = context.date_range[0] + timedelta(
                    days=context.athlete.available_days[0]
                )
                sessions.append(WorkoutSlot(
                    date=recovery_day,
                    sport=Sport.RUNNING,    # generic; frontend shows as "recovery"
                    workout_type="active_recovery",
                    duration_min=30,
                    fatigue_score=FatigueScore(
                        local_muscular=5.0, cns_load=2.0, metabolic_cost=5.0,
                        recovery_hours=4.0, affected_muscles=[],
                    ),
                    notes="Active recovery: light walk or yoga. No intensity.",
                ))

        return AgentRecommendation(
            agent_name=self.name,
            fatigue_score=FatigueScore(
                local_muscular=0.0, cns_load=0.0, metabolic_cost=0.0,
                recovery_hours=0.0, affected_muscles=[],
            ),
            weekly_load=0.0,
            suggested_sessions=sessions,
            readiness_modifier=status.readiness_modifier,
            notes=status.recommendation,
        )
```

```bash
"/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe" tests/backend/agents/test_recovery_coach.py -v
```

Expected: 5 passed.

- [ ] **Step 6: Create recovery route**

Create `backend/app/routes/recovery.py`:

```python
from __future__ import annotations

from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.recovery_logic import compute_recovery_status
from ..db.models import AthleteModel
from ..dependencies import get_db, get_current_athlete_id
from ..routes.athletes import athlete_model_to_response

router = APIRouter(prefix="/athletes", tags=["recovery"])

DB = Annotated[Session, Depends(get_db)]


def _require_own(
    athlete_id: str,
    current_id: Annotated[str, Depends(get_current_athlete_id)],
) -> str:
    if current_id != athlete_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return athlete_id


class RecoveryStatusResponse(BaseModel):
    readiness_modifier: float
    hrv_trend: str
    sleep_avg_hours: float | None
    sleep_banking_active: bool
    recommendation: str


@router.get("/{athlete_id}/recovery-status", response_model=RecoveryStatusResponse)
def get_recovery_status(
    athlete_id: str,
    db: DB,
    _: Annotated[str, Depends(_require_own)],
) -> RecoveryStatusResponse:
    """Return current recovery status based on Terra/HRV data."""
    from datetime import date
    from ..services.connector_service import fetch_connector_data

    athlete_model = db.get(AthleteModel, athlete_id)
    if athlete_model is None:
        raise HTTPException(status_code=404, detail="Athlete not found")
    athlete = athlete_model_to_response(athlete_model)
    connector_data = fetch_connector_data(athlete_id, db)

    status = compute_recovery_status(
        terra_data=connector_data.get("terra_health", []),
        target_race_date=athlete.target_race_date,
        week_start=date.today(),
    )

    return RecoveryStatusResponse(
        readiness_modifier=status.readiness_modifier,
        hrv_trend=status.hrv_trend,
        sleep_avg_hours=status.sleep_avg_hours,
        sleep_banking_active=status.sleep_banking_active,
        recommendation=status.recommendation,
    )
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/core/recovery_logic.py backend/app/agents/recovery_coach.py backend/app/routes/recovery.py tests/backend/core/test_recovery_logic.py tests/backend/agents/test_recovery_coach.py
git commit -m "feat: add RecoveryCoach with HRV-guided readiness and sleep banking"
```

---

## Task 7: Agent factory + wire everything

**Files:**
- Create: `backend/app/routes/_agent_factory.py`
- Modify: `backend/app/routes/onboarding.py`
- Modify: `backend/app/routes/plans.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create `_agent_factory.py`**

Create `backend/app/routes/_agent_factory.py`:

```python
from __future__ import annotations

from ..agents.base import BaseAgent
from ..agents.biking_coach import BikingCoach
from ..agents.lifting_coach import LiftingCoach
from ..agents.nutrition_coach import NutritionCoach
from ..agents.recovery_coach import RecoveryCoach
from ..agents.running_coach import RunningCoach
from ..agents.swimming_coach import SwimmingCoach
from ..schemas.athlete import AthleteProfile, Sport


def build_agents(athlete: AthleteProfile) -> list[BaseAgent]:
    """Instantiate specialist agents based on athlete's active sports.

    Sport-specific agents (Running, Lifting, Biking, Swimming) are only
    created if the athlete has that sport in their sports list.
    NutritionCoach and RecoveryCoach are always included.
    """
    agents: list[BaseAgent] = []

    if Sport.RUNNING in athlete.sports:
        agents.append(RunningCoach())
    if Sport.LIFTING in athlete.sports:
        agents.append(LiftingCoach())
    if Sport.BIKING in athlete.sports:
        agents.append(BikingCoach())
    if Sport.SWIMMING in athlete.sports:
        agents.append(SwimmingCoach())

    agents.append(NutritionCoach())
    agents.append(RecoveryCoach())

    return agents
```

- [ ] **Step 2: Update `onboarding.py` to use build_agents**

In `backend/app/routes/onboarding.py`, the call to `_create_plan_for_athlete` passes through to `plans.py`. No direct change needed here — just verify `_create_plan_for_athlete` in `plans.py` uses the factory (done in next step).

- [ ] **Step 3: Update `plans.py` to use build_agents**

In `backend/app/routes/plans.py`:

Replace the import block at the top:
```python
# REMOVE these lines:
# from ..agents.lifting_coach import LiftingCoach
# from ..agents.running_coach import RunningCoach

# ADD this import:
from ..routes._agent_factory import build_agents
```

Replace the coach instantiation in `_create_plan_for_athlete`:
```python
# REMOVE:
# coach = HeadCoach(agents=[RunningCoach(), LiftingCoach()])

# REPLACE WITH:
coach = HeadCoach(agents=build_agents(athlete))
```

- [ ] **Step 4: Update `main.py` to include new routers**

In `backend/app/main.py`, add the two new router imports and `include_router` calls:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes.auth import router as auth_router
from .routes.onboarding import router as onboarding_router
from .routes.athletes import router as athletes_router
from .routes.connectors import router as connectors_router
from .routes.plans import router as plans_router
from .routes.reviews import router as reviews_router
from .routes.nutrition import router as nutrition_router   # NEW
from .routes.recovery import router as recovery_router     # NEW

app = FastAPI(title="Resilio Plus API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(onboarding_router)
app.include_router(athletes_router)
app.include_router(connectors_router)
app.include_router(plans_router)
app.include_router(reviews_router)
app.include_router(nutrition_router)   # NEW
app.include_router(recovery_router)    # NEW
```

- [ ] **Step 5: Run full test suite**

```bash
"/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe" tests/ -q --tb=short 2>&1 | tail -10
```

Expected: all new tests passing + no regression in existing tests.
Pre-existing failures (ignore): `test_resolve_path_absolute`, `test_vdot_continuity` (3 tests), `test_fetch_hevy_workouts_maps_to_schema`, `test_skill_weather_contract` (3), `test_migrate_profile_onboarding_v0` (3).

- [ ] **Step 6: Run E2E tests specifically to verify onboarding still works**

```bash
"/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe" tests/e2e/ -v
```

Expected: 6 passed (onboarding flow still works with new agents).

- [ ] **Step 7: Commit**

```bash
git add backend/app/routes/_agent_factory.py backend/app/routes/plans.py backend/app/main.py
git commit -m "feat: wire all 6 agents via build_agents factory in plans + onboarding"
```

---

## Task 8: Final verification + push

- [ ] **Step 1: Run complete test suite**

```bash
"/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe" tests/ -q --tb=short 2>&1 | tail -8
```

Expected: ≥ 1167 + ~50 new tests passing. Count new tests passing (should be ~50 between goal_analysis, biking_logic, swimming_logic, nutrition_logic, recovery_logic and all agent tests).

- [ ] **Step 2: Push to GitHub**

```bash
git push origin main
```

---

## Final Verification Checklist

- [ ] `pytest tests/backend/core/test_goal_analysis.py` → 7 passed
- [ ] `pytest tests/backend/core/test_biking_logic.py` → 7 passed
- [ ] `pytest tests/backend/core/test_swimming_logic.py` → 6 passed
- [ ] `pytest tests/backend/core/test_nutrition_logic.py` → 7 passed
- [ ] `pytest tests/backend/core/test_recovery_logic.py` → 7 passed
- [ ] `pytest tests/backend/agents/test_biking_coach.py` → 5 passed
- [ ] `pytest tests/backend/agents/test_swimming_coach.py` → 3 passed
- [ ] `pytest tests/backend/agents/test_nutrition_coach.py` → 6 passed
- [ ] `pytest tests/backend/agents/test_recovery_coach.py` → 5 passed
- [ ] `pytest tests/e2e/` → 6 passed (onboarding flow unbroken)
- [ ] `git push origin main` → pushed
