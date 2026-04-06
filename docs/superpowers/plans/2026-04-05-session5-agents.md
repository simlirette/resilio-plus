# Session 5 — Agent Base Class + Head Coach Graph + ACWR Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the LangGraph Head Coach infrastructure — AthleteState (Pydantic), ACWR utilities, BaseAgent ABC, Running/Lifting stubs, and 3 TODO graph nodes — so `agents/head_coach/graph.py` imports and runs without errors.

**Architecture:** `models/athlete_state.py` provides the mutable Pydantic state for LangGraph; `core/acwr.py` is a pure utility; `agents/base_agent.py` defines the ABC all specialist agents implement; the graph nodes are pure functions that read/write the state. No LLM calls in S5 — all agents return deterministic stubs.

**Tech Stack:** Python 3.11, Pydantic v2, LangGraph 0.2, Poetry

---

## Critical Context

**Naming collision:** `models/database.py` already has `class AthleteState` (SQLAlchemy ORM). The new `models/athlete_state.py` creates a *different* `AthleteState` (Pydantic for LangGraph). Always import with the full module path to avoid confusion:
- `from models.athlete_state import AthleteState` → Pydantic (for LangGraph)
- `from models.database import AthleteState` → SQLAlchemy ORM (for DB)

**graph.py uses `state.get()` dict-style on Pydantic objects** — this is a pre-existing bug that Task 5 fixes by replacing with attribute access.

**Poetry path on Windows:** `/c/Users/simon/AppData/Local/Python/pythoncore-3.14-64/Scripts/poetry.exe`
Use `poetry run pytest ...` for all test commands.

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `core/acwr.py` | Create | EWMA ACWR computation + zone classifier |
| `models/athlete_state.py` | Create | AthleteState Pydantic model (LangGraph state) |
| `tests/conftest.py` | Modify | Add `simon_pydantic_state` fixture |
| `agents/__init__.py` | Create | Package marker |
| `agents/head_coach/__init__.py` | Create | Package marker |
| `agents/head_coach/edge_cases/__init__.py` | Create | Expose `get_alternatives_for_conflict` |
| `agents/base_agent.py` | Create | BaseAgent ABC |
| `agents/running_coach/__init__.py` | Create | Package marker |
| `agents/running_coach/agent.py` | Create | RunningCoachAgent stub |
| `agents/lifting_coach/__init__.py` | Create | Package marker |
| `agents/lifting_coach/agent.py` | Create | LiftingCoachAgent stub |
| `agents/head_coach/graph.py` | Modify | Fix 4 `.get()` calls + complete 3 TODO nodes |
| `tests/test_acwr.py` | Create | 5 ACWR unit tests |
| `tests/test_athlete_state.py` | Create | 3 AthleteState unit tests |
| `tests/test_base_agent.py` | Create | 3 BaseAgent / stub agent tests |
| `tests/test_head_coach_graph.py` | Create | 4 graph integration tests |

---

## Task 1: ACWR Utility (`core/acwr.py`)

**Files:**
- Create: `core/acwr.py`
- Create: `tests/test_acwr.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_acwr.py
"""Tests unitaires pour compute_ewma_acwr et acwr_zone."""

import pytest

from core.acwr import acwr_zone, compute_ewma_acwr


def test_ewma_acwr_empty_loads():
    """Liste vide → tout à zéro."""
    acute, chronic, acwr = compute_ewma_acwr([])
    assert acute == 0.0
    assert chronic == 0.0
    assert acwr == 0.0


def test_ewma_acwr_single_day():
    """Un seul jour → acute = chronic = la charge, ACWR = 1.0."""
    acute, chronic, acwr = compute_ewma_acwr([100.0])
    assert acute == pytest.approx(100.0)
    assert chronic == pytest.approx(100.0)
    assert acwr == pytest.approx(1.0)


def test_ewma_acwr_safe_zone():
    """28 jours de charge constante → ACWR ≈ 1.0, zone safe."""
    loads = [100.0] * 28
    acute, chronic, acwr = compute_ewma_acwr(loads)
    assert acwr == pytest.approx(1.0, rel=1e-3)
    assert acwr_zone(acwr) == "safe"


def test_ewma_acwr_danger_zone():
    """Pic de charge la dernière semaine → ACWR > 1.5, zone danger."""
    # 21 jours de faible charge, puis 7 jours de charge triple
    loads = [50.0] * 21 + [300.0] * 7
    _, _, acwr = compute_ewma_acwr(loads)
    assert acwr > 1.5
    assert acwr_zone(acwr) == "danger"


def test_ewma_acwr_underload():
    """Charge réduite à zéro la dernière semaine → ACWR < 0.8, zone underload."""
    # 21 jours de charge normale, puis 7 jours de repos complet
    loads = [100.0] * 21 + [0.0] * 7
    _, _, acwr = compute_ewma_acwr(loads)
    assert acwr < 0.8
    assert acwr_zone(acwr) == "underload"
```

- [ ] **Step 2: Run to confirm FAIL**

```
poetry run pytest tests/test_acwr.py -v
```
Expected: `ModuleNotFoundError: No module named 'core.acwr'`

- [ ] **Step 3: Create `core/acwr.py`**

```python
# core/acwr.py
"""
Calcul ACWR (Acute:Chronic Workload Ratio) via EWMA.
Fonction utilitaire pure — pas de dépendances DB/FastAPI.
"""


def compute_ewma_acwr(
    daily_loads: list[float],
    acute_days: int = 7,
    chronic_days: int = 28,
) -> tuple[float, float, float]:
    """
    Calcule l'ACWR via EWMA (Exponentially Weighted Moving Average).

    Args:
        daily_loads: charges quotidiennes du plus ancien au plus récent.
                     Idéalement >= 28 valeurs. Valeurs manquantes = 0.0.
        acute_days:  fenêtre aiguë (défaut 7j)
        chronic_days: fenêtre chronique (défaut 28j)

    Returns:
        (ewma_acute, ewma_chronic, acwr)
        acwr = 0.0 si chronic == 0

    Formule:
        λ = 2 / (N + 1)
        ewma_t = ewma_{t-1} + λ * (load_t - ewma_{t-1})
    """
    if not daily_loads:
        return 0.0, 0.0, 0.0

    lambda_acute = 2 / (acute_days + 1)
    lambda_chronic = 2 / (chronic_days + 1)

    ewma_acute = daily_loads[0]
    ewma_chronic = daily_loads[0]

    for load in daily_loads[1:]:
        ewma_acute = ewma_acute + lambda_acute * (load - ewma_acute)
        ewma_chronic = ewma_chronic + lambda_chronic * (load - ewma_chronic)

    acwr = ewma_acute / ewma_chronic if ewma_chronic > 0 else 0.0
    return ewma_acute, ewma_chronic, acwr


def acwr_zone(acwr: float) -> str:
    """
    Classifie l'ACWR en zone de charge.

    Returns:
        'underload' : < 0.8
        'safe'      : 0.8 – 1.3
        'caution'   : 1.3 – 1.5
        'danger'    : > 1.5
    """
    if acwr < 0.8:
        return "underload"
    if acwr <= 1.3:
        return "safe"
    if acwr <= 1.5:
        return "caution"
    return "danger"
```

- [ ] **Step 4: Run tests — expect PASS**

```
poetry run pytest tests/test_acwr.py -v
```
Expected: `5 passed`

- [ ] **Step 5: Lint**

```
poetry run ruff check core/acwr.py tests/test_acwr.py
```
Expected: no output (clean)

- [ ] **Step 6: Commit**

```bash
git add core/acwr.py tests/test_acwr.py
git commit -m "feat: add ACWR EWMA utility + 5 unit tests"
```

---

## Task 2: AthleteState Pydantic Model (`models/athlete_state.py`)

**Files:**
- Create: `models/athlete_state.py`
- Modify: `tests/conftest.py` (append `simon_pydantic_state` fixture at end of file)
- Create: `tests/test_athlete_state.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_athlete_state.py
"""
Tests pour AthleteState (Pydantic LangGraph state).
IMPORTANT : ce n'est PAS models.database.AthleteState (SQLAlchemy).
"""
import uuid
from datetime import datetime, timezone

import pytest

from models.schemas import AthleteStateSchema


def test_athlete_state_extends_schema(simon_pydantic_state):
    """AthleteState hérite de AthleteStateSchema — a tous ses champs."""
    from models.athlete_state import AthleteState

    assert isinstance(simon_pydantic_state, AthleteState)
    assert isinstance(simon_pydantic_state, AthleteStateSchema)
    # Champs hérités de AthleteStateSchema
    assert simon_pydantic_state.profile is not None
    assert simon_pydantic_state.fatigue is not None
    assert simon_pydantic_state.running_profile is not None


def test_athlete_state_mutable(simon_pydantic_state):
    """AthleteState est mutable (frozen=False) — la mutation directe fonctionne."""
    simon_pydantic_state.pending_decision = {
        "conflict_id": "TEST",
        "status": "awaiting_user_input",
    }
    assert simon_pydantic_state.pending_decision["conflict_id"] == "TEST"

    simon_pydantic_state.acwr_computed = 1.25
    assert simon_pydantic_state.acwr_computed == 1.25


def test_athlete_state_defaults(simon_pydantic_state):
    """AthleteState a des valeurs par défaut correctes pour les champs d'orchestration."""
    # pending_decision commence à None
    # (simon_pydantic_state fresh depuis fixture — avant toute mutation)
    assert simon_pydantic_state.pending_conflicts == []
    assert simon_pydantic_state.partial_plans == {}
    assert simon_pydantic_state.acwr_computed is None
    assert simon_pydantic_state.resolution_iterations == 0
    assert simon_pydantic_state.conflicts_resolved is True
```

- [ ] **Step 2: Run to confirm FAIL**

```
poetry run pytest tests/test_athlete_state.py -v
```
Expected: `ModuleNotFoundError: No module named 'models.athlete_state'`

- [ ] **Step 3: Create `models/athlete_state.py`**

```python
# models/athlete_state.py
"""
AthleteState Pydantic — état LangGraph du Head Coach.

Ce module est DISTINCT de models.database.AthleteState (SQLAlchemy ORM).
- models.athlete_state.AthleteState  → Pydantic, pour LangGraph (ce fichier)
- models.database.AthleteState       → SQLAlchemy ORM, pour la DB
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from models.schemas import AthleteStateSchema


class ConstraintMatrix(BaseModel):
    """Matrice de contraintes hebdomadaire — schedule par jour."""

    model_config = ConfigDict(frozen=False)

    # Clés : noms de jours ("monday", …) ou "_daily_loads_28d" (liste de charges)
    # Exemple : {"monday": {"assigned": ["squat"], "max_hours": 1.5, "primary_muscles": ["quadriceps"]}}
    # Exemple : {"_daily_loads_28d": [100.0, 85.0, …]}  ← 28 derniers jours de charge TRIMP
    # Any car les valeurs peuvent être dict (sessions) ou list[float] (daily_loads)
    schedule: dict[str, Any] = Field(default_factory=dict)


class AthleteState(AthleteStateSchema):
    """
    État LangGraph du Head Coach — étend AthleteStateSchema avec les champs d'orchestration.

    Mutable (frozen=False) pour que les nœuds du graph puissent écrire directement.
    AthleteStateSchema contient déjà : profile, fatigue, running_profile, lifting_profile, etc.
    """

    model_config = ConfigDict(strict=False, frozen=False)

    # ── Orchestration LangGraph ──────────────────────────────────────────────
    pending_decision: dict | None = None
    pending_conflicts: list[dict] = Field(default_factory=list)
    partial_plans: dict[str, dict] = Field(default_factory=dict)
    decision_log: list[dict] = Field(default_factory=list)
    constraint_matrix: ConstraintMatrix = Field(default_factory=ConstraintMatrix)

    # ── Input de décision humaine ────────────────────────────────────────────
    user_decision_input: str | None = None
    reported_unavailable_days: list[str] = Field(default_factory=list)

    # ── Champs calculés (nœud load_state) ───────────────────────────────────
    acwr_computed: float | None = None

    # ── Circuit breaker résolution de conflits ───────────────────────────────
    resolution_iterations: int = 0
    conflicts_resolved: bool = True
```

- [ ] **Step 4: Add `simon_pydantic_state` fixture to `tests/conftest.py`**

Append at the end of `tests/conftest.py` (after the last fixture):

```python
@pytest.fixture
def simon_pydantic_state():
    """AthleteState Pydantic (LangGraph) pour Simon — sans DB."""
    from datetime import datetime, timezone

    from models.athlete_state import AthleteState as PydanticAthleteState

    return PydanticAthleteState(
        athlete_id=SIMON_ID,
        updated_at=datetime.now(timezone.utc),
        profile={
            "first_name": "Simon",
            "age": 32,
            "sex": "M",
            "weight_kg": 78.5,
            "height_cm": 178,
            "body_fat_percent": 16.5,
            "resting_hr": 58,
            "max_hr_measured": 188,
            "active_sports": ["running", "lifting"],
            "available_days": SIMON_AVAILABLE_DAYS,
            **SIMON_PROFILE_DATA,
        },
        current_phase={
            "macrocycle": "base_building",
            "mesocycle_week": 3,
            "mesocycle_length": 4,
        },
        running_profile=SIMON_RUNNING_PROFILE,
        lifting_profile=SIMON_LIFTING_PROFILE,
        nutrition_profile=SIMON_NUTRITION_PROFILE,
    )
```

- [ ] **Step 5: Run tests — expect PASS**

```
poetry run pytest tests/test_athlete_state.py -v
```
Expected: `3 passed`

- [ ] **Step 6: Run full suite to ensure no regressions**

```
poetry run pytest tests/ -v --ignore=tests/test_head_coach_graph.py --ignore=tests/test_base_agent.py
```
Expected: all existing tests pass

- [ ] **Step 7: Lint**

```
poetry run ruff check models/athlete_state.py tests/test_athlete_state.py
```
Expected: no output

- [ ] **Step 8: Commit**

```bash
git add models/athlete_state.py tests/test_athlete_state.py tests/conftest.py
git commit -m "feat: add AthleteState Pydantic model + simon_pydantic_state fixture"
```

---

## Task 3: Package Markers + `edge_cases/__init__.py`

**Files:**
- Create: `agents/__init__.py` (empty)
- Create: `agents/head_coach/__init__.py` (empty)
- Create: `agents/head_coach/edge_cases/__init__.py`

No TDD for package markers — just create them and verify the import chain works.

- [ ] **Step 1: Create the empty package markers**

`agents/__init__.py` — empty file.

`agents/head_coach/__init__.py` — empty file.

- [ ] **Step 2: Create `agents/head_coach/edge_cases/__init__.py`**

```python
# agents/head_coach/edge_cases/__init__.py
"""
Expose get_alternatives_for_conflict — appelée dans node_process_human_decision
quand l'utilisateur demande d'autres options pour un conflit donné.
"""

from agents.head_coach.edge_cases.scenario_a_1rm_veto import (
    get_alternatives as _alts_a,
)
from agents.head_coach.edge_cases.scenario_b_schedule_conflict import (
    get_alternatives as _alts_b,
)
from agents.head_coach.edge_cases.scenario_c_acwr_event import (
    get_alternatives as _alts_c,
)

_ALTERNATIVES_MAP = {
    "A_1RM_RED_VETO": _alts_a,
    "B_SCHEDULE_CONFLICT": _alts_b,
    "C_ACWR_EVENT": _alts_c,
}


def get_alternatives_for_conflict(conflict_id: str, state) -> list[str]:
    """Retourne les alternatives pour un conflict_id donné."""
    fn = _ALTERNATIVES_MAP.get(conflict_id)
    if fn is None:
        return []
    return fn(state)
```

- [ ] **Step 3: Verify edge_cases imports work**

```
poetry run python -c "from agents.head_coach.edge_cases import get_alternatives_for_conflict; print('OK')"
```
Expected: `OK`

- [ ] **Step 4: Lint**

```
poetry run ruff check agents/__init__.py agents/head_coach/__init__.py agents/head_coach/edge_cases/__init__.py
```
Expected: no output

- [ ] **Step 5: Commit**

```bash
git add agents/__init__.py agents/head_coach/__init__.py agents/head_coach/edge_cases/__init__.py
git commit -m "feat: add package markers and edge_cases get_alternatives_for_conflict"
```

---

## Task 4: BaseAgent ABC + Running/Lifting Stubs

**Files:**
- Create: `agents/base_agent.py`
- Create: `agents/running_coach/__init__.py` (empty)
- Create: `agents/running_coach/agent.py`
- Create: `agents/lifting_coach/__init__.py` (empty)
- Create: `agents/lifting_coach/agent.py`
- Create: `tests/test_base_agent.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_base_agent.py
"""
Tests pour BaseAgent ABC et les stubs Running/Lifting Coach (S5).
Utilise simon_pydantic_state (AthleteState Pydantic, sans DB).
"""


def test_running_coach_run_returns_plan(simon_pydantic_state):
    """RunningCoachAgent.run() retourne un dict avec 'sessions'."""
    from agents.running_coach.agent import RunningCoachAgent

    agent = RunningCoachAgent()
    plan = agent.run(simon_pydantic_state)

    assert isinstance(plan, dict)
    assert "sessions" in plan
    assert len(plan["sessions"]) > 0
    assert plan["agent"] == "running_coach"


def test_lifting_coach_run_returns_plan(simon_pydantic_state):
    """LiftingCoachAgent.run() retourne un dict avec 'sessions'."""
    from agents.lifting_coach.agent import LiftingCoachAgent

    agent = LiftingCoachAgent()
    plan = agent.run(simon_pydantic_state)

    assert isinstance(plan, dict)
    assert "sessions" in plan
    assert len(plan["sessions"]) > 0
    assert plan["agent"] == "lifting_coach"


def test_agent_uses_get_agent_view(simon_pydantic_state):
    """La vue Running ne contient pas lifting_profile (filtrage correct)."""
    from agents.running_coach.agent import RunningCoachAgent
    from models.views import AgentType, get_agent_view

    view = get_agent_view(simon_pydantic_state, AgentType.running_coach)
    assert "running_profile" in view
    assert "lifting_profile" not in view
```

- [ ] **Step 2: Run to confirm FAIL**

```
poetry run pytest tests/test_base_agent.py -v
```
Expected: `ModuleNotFoundError: No module named 'agents.base_agent'`

- [ ] **Step 3: Create `agents/base_agent.py`**

```python
# agents/base_agent.py
"""
BaseAgent — classe de base abstraite pour tous les agents spécialistes Resilio+.

Interface publique :
    agent_type : AgentType  (attribut de classe)
    prescribe(view: dict) -> dict   (à implémenter — reçoit la vue filtrée)
    run(state) -> dict              (appelé par le Head Coach)

Flux d'appel Head Coach :
    node_delegate_to_agents → agent.run(state) → get_agent_view() → prescribe()
"""

from abc import ABC, abstractmethod

from models.schemas import AthleteStateSchema
from models.views import AgentType, get_agent_view


class BaseAgent(ABC):
    """Classe de base pour tous les agents spécialistes."""

    agent_type: AgentType

    @abstractmethod
    def prescribe(self, view: dict) -> dict:
        """
        Prescrit un plan partiel à partir de la vue filtrée de l'agent.

        Args:
            view: dict filtré par get_agent_view() — contient uniquement
                  les données pertinentes à cet agent.

        Returns:
            dict avec au minimum {"sessions": [], "agent": "<type>", "notes": ""}
        """

    def run(self, state: AthleteStateSchema) -> dict:
        """
        Appelé par le Head Coach. Extrait la vue filtrée et appelle prescribe().

        Args:
            state: AthleteState complet — seule la vue filtrée est transmise à prescribe()

        Returns:
            Plan partiel retourné par prescribe()
        """
        view = get_agent_view(state, self.agent_type)
        return self.prescribe(view)
```

- [ ] **Step 4: Create `agents/running_coach/__init__.py`** (empty file)

- [ ] **Step 5: Create `agents/running_coach/agent.py`**

```python
# agents/running_coach/agent.py
"""
Running Coach Agent — S5 stub sans appel LLM.
S6 : prescribe() sera remplacé par un appel Anthropic avec system_prompt.
"""

from agents.base_agent import BaseAgent
from models.views import AgentType


class RunningCoachAgent(BaseAgent):
    """Agent Running Coach — stub déterministe S5."""

    agent_type = AgentType.running_coach

    def prescribe(self, view: dict) -> dict:
        """
        S5 : stub déterministe sans LLM.
        Retourne une séance easy run basée sur le VDOT de l'athlète.
        """
        vdot = view.get("running_profile", {}).get("vdot", 35.0)
        return {
            "agent": "running_coach",
            "sessions": [
                {
                    "day": "tuesday",
                    "type": "easy_run",
                    "description": f"Easy run 45min @ Z1 (VDOT {vdot:.1f})",
                    "duration_min": 45,
                    "zone": "Z1",
                }
            ],
            "weekly_km_prescribed": 8.0,
            "notes": "S5 stub — prescription LLM en S6.",
        }
```

- [ ] **Step 6: Create `agents/lifting_coach/__init__.py`** (empty file)

- [ ] **Step 7: Create `agents/lifting_coach/agent.py`**

```python
# agents/lifting_coach/agent.py
"""
Lifting Coach Agent — S5 stub sans appel LLM.
S6/S7 : prescribe() sera remplacé par un appel Anthropic avec system_prompt.
"""

from agents.base_agent import BaseAgent
from models.views import AgentType


class LiftingCoachAgent(BaseAgent):
    """Agent Lifting Coach — stub déterministe S5."""

    agent_type = AgentType.lifting_coach

    def prescribe(self, view: dict) -> dict:
        """
        S5 : stub déterministe sans LLM.
        Retourne une séance upper body basée sur le split de l'athlète.
        """
        split = view.get("lifting_profile", {}).get("training_split", "upper_lower")
        return {
            "agent": "lifting_coach",
            "sessions": [
                {
                    "day": "monday",
                    "type": "upper_body",
                    "description": f"Upper Body — {split} split, Tier 1",
                    "exercises": ["Bench Press", "Pull-up", "OHP"],
                }
            ],
            "sessions_prescribed": 3,
            "notes": "S5 stub — prescription LLM en S7.",
        }
```

- [ ] **Step 8: Run tests — expect PASS**

```
poetry run pytest tests/test_base_agent.py -v
```
Expected: `3 passed`

- [ ] **Step 9: Lint**

```
poetry run ruff check agents/base_agent.py agents/running_coach/ agents/lifting_coach/
```
Expected: no output

- [ ] **Step 10: Commit**

```bash
git add agents/base_agent.py \
        agents/running_coach/__init__.py agents/running_coach/agent.py \
        agents/lifting_coach/__init__.py agents/lifting_coach/agent.py \
        tests/test_base_agent.py
git commit -m "feat: add BaseAgent ABC + Running/Lifting stub agents + 3 tests"
```

---

## Task 5: Fix graph.py + Complete 3 TODO Nodes

**Files:**
- Modify: `agents/head_coach/graph.py`
- Create: `tests/test_head_coach_graph.py`

### Context: what changes in graph.py

**Fix 1 — `node_check_edge_cases` (~line 89):**
```python
# BEFORE (fails on Pydantic):
unavailable_days = state.get("reported_unavailable_days", [])
# AFTER:
unavailable_days = state.reported_unavailable_days or []
```

**Fix 2 — `node_process_human_decision` (~line 108):**
```python
# BEFORE:
user_input = state.get("user_decision_input", "")
# AFTER:
user_input = state.user_decision_input or ""
```

**Fix 3 — `route_after_conflict_resolution` (~line 265):**
```python
# BEFORE:
iterations = state.get("resolution_iterations", 0)
if iterations >= 2:
    ...
if state.get("conflicts_resolved", True):
# AFTER:
iterations = state.resolution_iterations
if iterations >= 2:
    ...
if state.conflicts_resolved:
```

**New import to add at top of graph.py:**
```python
import json
from pathlib import Path

from agents.lifting_coach.agent import LiftingCoachAgent
from agents.running_coach.agent import RunningCoachAgent
from core.acwr import compute_ewma_acwr
```

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_head_coach_graph.py
"""
Tests d'intégration du Head Coach graph LangGraph.
Vérifie que le graph compile et que les 3 nœuds TODO S5 fonctionnent.
"""


def test_graph_compiles():
    """build_head_coach_graph() s'exécute sans erreur d'import ou de compilation."""
    from agents.head_coach.graph import build_head_coach_graph

    g = build_head_coach_graph()
    assert g is not None


def test_node_load_computes_acwr(simon_pydantic_state):
    """node_load_athlete_state calcule acwr_computed si daily_loads présents."""
    from agents.head_coach.graph import node_load_athlete_state

    # Injecter 28 jours de charge constante → ACWR ≈ 1.0
    simon_pydantic_state.constraint_matrix.schedule["_daily_loads_28d"] = [100.0] * 28
    result = node_load_athlete_state(simon_pydantic_state)

    assert result.acwr_computed is not None
    assert result.acwr_computed > 0.0


def test_node_detect_no_conflicts(simon_pydantic_state):
    """node_detect_conflicts ne crée pas de conflits si ACWR safe et schedule vide."""
    from agents.head_coach.graph import node_detect_conflicts

    simon_pydantic_state.acwr_computed = 1.0
    # schedule vide → pas de conflit scheduling ni overlap musculaire
    simon_pydantic_state.constraint_matrix.schedule = {}

    result = node_detect_conflicts(simon_pydantic_state)

    assert result.pending_conflicts == []
    assert result.conflicts_resolved is True


def test_node_detect_acwr_danger(simon_pydantic_state):
    """node_detect_conflicts crée un conflit 'danger' si ACWR > 1.5."""
    from agents.head_coach.graph import node_detect_conflicts

    simon_pydantic_state.acwr_computed = 1.6
    simon_pydantic_state.constraint_matrix.schedule = {}

    result = node_detect_conflicts(simon_pydantic_state)

    danger = [c for c in result.pending_conflicts if c["severity"] == "danger"]
    assert len(danger) == 1
    assert danger[0]["layer"] == "fatigue"
    assert danger[0]["acwr"] == 1.6
```

- [ ] **Step 2: Run to confirm FAIL**

```
poetry run pytest tests/test_head_coach_graph.py -v
```
Expected: errors related to missing `models.athlete_state` import in graph.py (before fixes)

- [ ] **Step 3: Fix the 4 `state.get()` calls in graph.py**

In `node_check_edge_cases` (around line 89), replace:
```python
    unavailable_days = state.get("reported_unavailable_days", [])
```
with:
```python
    unavailable_days = state.reported_unavailable_days or []
```

In `node_process_human_decision` (around line 108), replace:
```python
    user_input = state.get("user_decision_input", "")
```
with:
```python
    user_input = state.user_decision_input or ""
```

In `route_after_conflict_resolution` (around line 265), replace:
```python
    iterations = state.get("resolution_iterations", 0)
    if iterations >= 2:
        # Circuit breaker : résolution d'autorité basée sur priority_hierarchy
        return "merge_plans"
    if state.get("conflicts_resolved", True):
```
with:
```python
    iterations = state.resolution_iterations
    if iterations >= 2:
        # Circuit breaker : résolution d'autorité basée sur priority_hierarchy
        return "merge_plans"
    if state.conflicts_resolved:
```

- [ ] **Step 4: Add new imports at the top of graph.py**

After the existing imports block, add:
```python
import json
from pathlib import Path

from agents.lifting_coach.agent import LiftingCoachAgent
from agents.running_coach.agent import RunningCoachAgent
from core.acwr import compute_ewma_acwr
```

- [ ] **Step 5: Replace `node_load_athlete_state` TODO body**

Replace the entire `node_load_athlete_state` function body (the `# TODO Session 5` + `return state`):

```python
def node_load_athlete_state(state: AthleteState) -> AthleteState:
    """
    Nœud 1 : Calculer les champs dérivés depuis l'AthleteState.
    L'AthleteState est pré-chargé depuis la DB par l'appelant (API route).
    Ce nœud calcule l'ACWR EWMA et met à jour acwr_computed.
    """
    daily_loads = state.constraint_matrix.schedule.get("_daily_loads_28d", [])
    if daily_loads and isinstance(daily_loads, list):
        _, _, acwr = compute_ewma_acwr(daily_loads)
        state.acwr_computed = acwr
        if state.fatigue.acwr is None:
            state.fatigue.acwr = acwr
    else:
        state.acwr_computed = state.fatigue.acwr
    return state
```

- [ ] **Step 6: Replace `node_detect_conflicts` TODO body**

Replace the entire `node_detect_conflicts` function body (the `# TODO Session 5` block + `state.pending_conflicts = []` + `return state`):

```python
def node_detect_conflicts(state: AthleteState) -> AthleteState:
    """
    Nœud 3 : Détecter les conflits sur 3 couches.
    Couche 1 : Scheduling (sessions > jours disponibles)
    Couche 2 : Overlap musculaire (jours consécutifs)
    Couche 3 : Fatigue cumulée (ACWR zones caution/danger)
    """
    conflicts = []

    # ── Couche 1 : Scheduling ────────────────────────────────────────────────
    available_days = [
        day for day, avail in state.profile.available_days.items()
        if avail.available
    ]
    sessions_planned = sum(
        1 for sessions in state.constraint_matrix.schedule.values()
        if isinstance(sessions, dict) and sessions.get("assigned")
    )
    if sessions_planned > len(available_days):
        conflicts.append({
            "layer": "scheduling",
            "severity": "warning",
            "message": (
                f"{sessions_planned} sessions planifiées pour "
                f"{len(available_days)} jours disponibles."
            ),
        })

    # ── Couche 2 : Overlap musculaire ────────────────────────────────────────
    _overlap_data = _load_muscle_overlap()
    schedule = state.constraint_matrix.schedule
    day_order = [
        "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
    ]
    for i, day in enumerate(day_order[:-1]):
        next_day = day_order[i + 1]
        today_session = schedule.get(day, {})
        next_session = schedule.get(next_day, {})
        if not isinstance(today_session, dict) or not isinstance(next_session, dict):
            continue
        today_muscles = set(today_session.get("primary_muscles", []))
        next_muscles = set(next_session.get("primary_muscles", []))
        overlap = today_muscles & next_muscles
        if overlap:
            conflicts.append({
                "layer": "muscle_overlap",
                "severity": "warning",
                "days": [day, next_day],
                "muscles": sorted(overlap),
                "message": (
                    f"Overlap musculaire {day}/{next_day} : "
                    f"{', '.join(sorted(overlap))} sollicités < 24h d'intervalle."
                ),
            })

    # ── Couche 3 : Fatigue (ACWR) ────────────────────────────────────────────
    acwr = state.acwr_computed or state.fatigue.acwr or 0.0
    if acwr > 1.5:
        conflicts.append({
            "layer": "fatigue",
            "severity": "danger",
            "acwr": acwr,
            "message": (
                f"ACWR = {acwr:.2f} > 1.5 — zone danger. "
                "Risque de blessure élevé. Réduction de charge obligatoire."
            ),
        })
    elif acwr > 1.3:
        conflicts.append({
            "layer": "fatigue",
            "severity": "caution",
            "acwr": acwr,
            "message": (
                f"ACWR = {acwr:.2f} entre 1.3 et 1.5 — zone attention. "
                "Surveiller la récupération cette semaine."
            ),
        })

    state.pending_conflicts = conflicts
    state.conflicts_resolved = len(conflicts) == 0
    return state
```

- [ ] **Step 7: Add `_load_muscle_overlap` helper and `_AGENT_REGISTRY` before the node functions**

Add these two helper elements. Place `_load_muscle_overlap` **before** `node_detect_conflicts`, and `_AGENT_REGISTRY` **before** `node_delegate_to_agents`. Specifically:

After the `from models.athlete_state import AthleteState` import line, add at module level (after the imports, before the first function):

```python
# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

_MUSCLE_OVERLAP_CACHE: dict | None = None


def _load_muscle_overlap() -> dict:
    """Charge muscle_overlap.json une fois (cache module-level)."""
    global _MUSCLE_OVERLAP_CACHE
    if _MUSCLE_OVERLAP_CACHE is None:
        path = Path(__file__).parents[2] / "data" / "muscle_overlap.json"
        _MUSCLE_OVERLAP_CACHE = json.loads(path.read_text()) if path.exists() else {}
    return _MUSCLE_OVERLAP_CACHE


_AGENT_REGISTRY: dict[str, object] = {
    "running": RunningCoachAgent(),
    "lifting": LiftingCoachAgent(),
}
```

- [ ] **Step 8: Replace `node_delegate_to_agents` TODO body**

Replace the entire `node_delegate_to_agents` function body (the `# TODO Session 5-7` block + `return state`):

```python
def node_delegate_to_agents(state: AthleteState) -> AthleteState:
    """
    Nœud 6 : Head Coach délègue la prescription aux agents spécialistes actifs.
    En S5 : Running + Lifting uniquement (stubs déterministes sans LLM).
    En S6+ : tous les agents avec prescriptions LLM.
    """
    active_sports = state.profile.active_sports or ["running", "lifting"]
    partial_plans = {}

    for sport in active_sports:
        agent = _AGENT_REGISTRY.get(sport)
        if agent is not None:
            partial_plans[sport] = agent.run(state)

    state.partial_plans = partial_plans
    return state
```

- [ ] **Step 9: Run tests — expect PASS**

```
poetry run pytest tests/test_head_coach_graph.py -v
```
Expected: `4 passed`

- [ ] **Step 10: Run full test suite**

```
poetry run pytest tests/ -v
```
Expected: all ~71 tests pass (56 S1-S4 + 5 ACWR + 3 AthleteState + 3 BaseAgent + 4 Graph = 71)

- [ ] **Step 11: Verify graph import works end-to-end**

```
poetry run python -c "from agents.head_coach.graph import head_coach_graph; print('Graph OK:', type(head_coach_graph))"
```
Expected: `Graph OK: <class 'langgraph.graph.state.CompiledStateGraph'>`

- [ ] **Step 12: Lint**

```
poetry run ruff check agents/head_coach/graph.py tests/test_head_coach_graph.py
```
Expected: no output

- [ ] **Step 13: Commit**

```bash
git add agents/head_coach/graph.py tests/test_head_coach_graph.py
git commit -m "feat: complete S5 graph nodes (load_state, detect_conflicts, delegate_to_agents)"
```

---

## Post-S5 Verification

```bash
# Suite complète
poetry run pytest tests/ -v
# Expected: ~71 passed

# Vérifier l'import du graph
poetry run python -c "from agents.head_coach.graph import head_coach_graph; print('OK')"

# Linter global
poetry run ruff check .
```

---

## Update CLAUDE.md

After all tests pass, update `CLAUDE.md`:
- Mark S5 as ✅ FAIT
- Add new files to the repo structure section
