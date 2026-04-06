# Session 5 — Agent Base Class + Head Coach Graph + ACWR : Design Spec

**Date :** 2026-04-05
**Statut :** Approuvé (auto mode)
**Session suivante :** S6 — Agents spécialistes avec appels LLM réels (Running Coach + Lifting Coach)

---

## Contexte

S4 a livré les connecteurs de données (Apple Health, GPX, FIT, food search). S5 câble la couche agent :
le graph LangGraph du Head Coach existe (`agents/head_coach/graph.py`) mais ne peut pas être importé
car `models/athlete_state.py` est manquant. Cette session répare ce blocage et complète les nœuds
marqués `TODO Session 5` dans le graph.

### État du repo en entrée de S5

| Élément | Statut |
|---|---|
| `models/schemas.py` — `AthleteStateSchema` Pydantic | ✅ Existant |
| `models/views.py` — `get_agent_view()` + `AGENT_VIEW_MAP` | ✅ Existant |
| `agents/head_coach/graph.py` — structure complète | ✅ Existant (4 nœuds TODO S5) |
| `agents/head_coach/edge_cases/scenario_[a-c].py` | ✅ Existant |
| `models/athlete_state.py` | ❌ Manquant → **bloque l'import du graph** |
| `agents/head_coach/edge_cases/__init__.py` | ❌ Manquant → `get_alternatives_for_conflict` introuvable |
| `agents/__init__.py`, `agents/base_agent.py` | ❌ Manquant → S5 |
| `agents/running_coach/agent.py` | ❌ Manquant → S5 (stub sans LLM) |
| `agents/lifting_coach/agent.py` | ❌ Manquant → S5 (stub sans LLM) |
| `core/acwr.py` | ❌ Manquant → S5 |

---

## Ce que S5 NE fait PAS

- Pas d'appels LLM réels (Anthropic) → S6 (les agents S5 sont des stubs déterministes)
- Pas de `node_recovery_gate` complet → S8
- Pas de `node_resolve_conflicts` / `node_merge_plans` → S9
- Pas de `node_nutrition_prescription` → S15
- Pas d'API route `/plan` → S6

---

## Livrables S5

### 1. `models/athlete_state.py` — `AthleteState` (LangGraph state)

`AthleteState` étend `AthleteStateSchema` en ajoutant les champs d'orchestration LangGraph
(pending_decision, conflicts, partial_plans, etc.). La mutation est activée via `model_config`.

```python
from pydantic import BaseModel, ConfigDict, Field
from models.schemas import AthleteStateSchema


class ConstraintMatrix(BaseModel):
    """Matrice de contraintes hebdomadaire — schedule par jour."""
    model_config = ConfigDict(frozen=False)
    schedule: dict[str, dict] = {}  # "monday" -> {"assigned": ["squat"], "max_hours": 1.5}


class AthleteState(AthleteStateSchema):
    """
    État LangGraph du Head Coach — étend AthleteStateSchema avec les champs d'orchestration.
    Mutable (frozen=False) pour permettre les mutations dans les nœuds du graph.
    """
    model_config = ConfigDict(strict=False, frozen=False)

    # ── Orchestration LangGraph ──────────────────────────────
    pending_decision: dict | None = None          # Edge case en attente de décision humaine
    pending_conflicts: list[dict] = []            # Conflits détectés (couches 1-3)
    partial_plans: dict[str, dict] = {}           # Plans partiels par agent (agent_type -> plan)
    decision_log: list[dict] = []                 # Historique des décisions humaines
    constraint_matrix: ConstraintMatrix = Field(default_factory=ConstraintMatrix)

    # ── Input de décision humaine ────────────────────────────
    user_decision_input: str | None = None        # "CONFIRM" | "OTHER_OPTIONS" | "CUSTOM: ..."
    reported_unavailable_days: list[str] = []     # Jours imprévus indisponibles

    # ── Champs calculés (nœud load_state) ───────────────────
    acwr_computed: float | None = None            # ACWR EWMA calculé à partir des 28 derniers jours

    # ── Circuit breaker résolution de conflits ───────────────
    resolution_iterations: int = 0
    conflicts_resolved: bool = True
```

**Important :** `AthleteState` hérite de `AthleteStateSchema` donc possède déjà tous les champs
`profile`, `fatigue`, `running_profile`, `lifting_profile`, `current_phase`, etc.

---

### 2. `core/acwr.py` — Calcul ACWR via EWMA

Fonction utilitaire pure (pas de dépendances FastAPI/DB). Facilement testable.

```python
def compute_ewma_acwr(
    daily_loads: list[float],
    acute_days: int = 7,
    chronic_days: int = 28,
) -> tuple[float, float, float]:
    """
    Calcule l'ACWR (Acute:Chronic Workload Ratio) via EWMA.

    Args:
        daily_loads: liste de charges quotidiennes (du plus ancien au plus récent),
                     longueur idéale >= 28 jours. Valeurs manquantes = 0.0.
        acute_days: fenêtre aiguë (défaut 7j)
        chronic_days: fenêtre chronique (défaut 28j)

    Returns:
        (acute_load, chronic_load, acwr)
        acwr = 0.0 si chronic_load == 0

    Formule EWMA :
        λ_acute   = 2 / (acute_days + 1)   ≈ 0.25  (7j)
        λ_chronic = 2 / (chronic_days + 1) ≈ 0.069 (28j)
        ewma_t = ewma_{t-1} + λ * (load_t - ewma_{t-1})

    Zones ACWR :
        < 0.8  : sous-charge (désentraînement potentiel)
        0.8–1.3: zone sûre
        1.3–1.5: attention (flag à l'athlète)
        > 1.5  : danger (risque blessure élevé)
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
    """Retourne la zone ACWR : 'underload' | 'safe' | 'caution' | 'danger'."""
    if acwr < 0.8:
        return "underload"
    if acwr <= 1.3:
        return "safe"
    if acwr <= 1.5:
        return "caution"
    return "danger"
```

---

### 3. `agents/__init__.py` et `agents/head_coach/__init__.py`

Fichiers `__init__.py` vides (marqueurs de package Python).

---

### 4. `agents/head_coach/edge_cases/__init__.py`

Expose `get_alternatives_for_conflict` — référencée dans `graph.py` ligne 124.

```python
from agents.head_coach.edge_cases.scenario_a_1rm_veto import get_alternatives as _alts_a
from agents.head_coach.edge_cases.scenario_b_schedule_conflict import get_alternatives as _alts_b
from agents.head_coach.edge_cases.scenario_c_acwr_event import get_alternatives as _alts_c

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

---

### 5. `agents/base_agent.py` — Classe de base abstraite

```python
from abc import ABC, abstractmethod
from models.views import AgentType, get_agent_view
from models.schemas import AthleteStateSchema


class BaseAgent(ABC):
    """
    Classe de base pour tous les agents spécialistes Resilio+.

    Interface :
    - Chaque agent a un `agent_type` identifiant son domaine
    - `prescribe(view: dict) -> dict` est la méthode à implémenter
    - `run(state)` est appelé par le Head Coach — extrait la vue filtrée et appelle prescribe()

    En S5 : prescribe() retourne un plan stub déterministe (sans appel LLM).
    En S6+ : prescribe() appelle l'Anthropic API avec le system_prompt de l'agent.
    """

    agent_type: AgentType

    @abstractmethod
    def prescribe(self, view: dict) -> dict:
        """
        Prescrit un plan partiel à partir de la vue filtrée de l'agent.
        Retourne un dict avec au minimum {"sessions": [], "notes": ""}.
        """

    def run(self, state: AthleteStateSchema) -> dict:
        """
        Appelé par le Head Coach. Extrait la vue filtrée et appelle prescribe().
        Retourne le plan partiel.
        """
        view = get_agent_view(state, self.agent_type)
        return self.prescribe(view)
```

---

### 6. `agents/running_coach/agent.py` — Stub Running Coach

```python
class RunningCoachAgent(BaseAgent):
    agent_type = AgentType.running_coach

    def prescribe(self, view: dict) -> dict:
        """
        S5 : stub déterministe sans LLM.
        S6 : sera remplacé par un appel Anthropic avec system_prompt.
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
            "notes": "S5 stub — LLM prescription en S6.",
        }
```

Fichier `agents/running_coach/__init__.py` vide.

---

### 7. `agents/lifting_coach/agent.py` — Stub Lifting Coach

```python
class LiftingCoachAgent(BaseAgent):
    agent_type = AgentType.lifting_coach

    def prescribe(self, view: dict) -> dict:
        """S5 stub déterministe sans LLM."""
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
            "notes": "S5 stub — LLM prescription en S6.",
        }
```

Fichier `agents/lifting_coach/__init__.py` vide.

---

### 8. Corriger les appels `state.get()` dans `agents/head_coach/graph.py`

Le graph existant utilise la syntaxe dict `state.get("field", default)` qui échoue sur un Pydantic BaseModel.
Ces 4 lignes doivent être remplacées par un accès attribut avant d'ajouter les nœuds :

| Ligne | Avant | Après |
|---|---|---|
| `node_check_edge_cases` | `state.get("reported_unavailable_days", [])` | `state.reported_unavailable_days or []` |
| `node_process_human_decision` | `state.get("user_decision_input", "")` | `state.user_decision_input or ""` |
| `route_after_conflict_resolution` | `state.get("resolution_iterations", 0)` | `state.resolution_iterations` |
| `route_after_conflict_resolution` | `state.get("conflicts_resolved", True)` | `state.conflicts_resolved` |

---

### 9. Compléter les nœuds TODO S5 dans `agents/head_coach/graph.py`

#### `node_load_athlete_state` (TODO S5)

Calcule l'ACWR EWMA à partir des données de fatigue déjà présentes dans le state.
Les données sont passées dans `AthleteState` par l'appelant (API route) — pas d'accès DB depuis ce nœud.

```python
from core.acwr import compute_ewma_acwr

def node_load_athlete_state(state: AthleteState) -> AthleteState:
    """
    Nœud 1 : Calculer les champs dérivés depuis l'AthleteState.
    L'AthleteState est pré-chargé depuis la DB par l'appelant.
    Ce nœud calcule l'ACWR EWMA et met à jour fatigue.acwr.
    """
    # Utiliser les daily_loads si disponibles dans constraint_matrix,
    # sinon utiliser l'acwr déjà dans fatigue comme valeur de secours
    daily_loads = state.constraint_matrix.schedule.get("_daily_loads_28d", [])
    if daily_loads and isinstance(daily_loads, list):
        _, _, acwr = compute_ewma_acwr(daily_loads)
        state.acwr_computed = acwr
        if state.fatigue.acwr is None:
            state.fatigue.acwr = acwr
    else:
        # Fallback : utiliser l'acwr déjà calculé dans fatigue
        state.acwr_computed = state.fatigue.acwr
    return state
```

#### `node_detect_conflicts` (TODO S5)

Détection sur 3 couches. Peuple `state.pending_conflicts`.

```python
import json
from pathlib import Path

_MUSCLE_OVERLAP = None

def _load_muscle_overlap() -> dict:
    global _MUSCLE_OVERLAP
    if _MUSCLE_OVERLAP is None:
        path = Path(__file__).parents[2] / "data" / "muscle_overlap.json"
        if path.exists():
            _MUSCLE_OVERLAP = json.loads(path.read_text())
        else:
            _MUSCLE_OVERLAP = {}
    return _MUSCLE_OVERLAP

def node_detect_conflicts(state: AthleteState) -> AthleteState:
    """Détection de conflits sur 3 couches."""
    conflicts = []

    # Couche 1 : Scheduling — sessions vs jours disponibles
    available_days = [
        day for day, avail in state.profile.available_days.items()
        if avail.available
    ]
    sessions_planned = sum(
        1 for sessions in state.constraint_matrix.schedule.values()
        if sessions.get("assigned")
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

    # Couche 2 : Overlap musculaire — vérifier les jours consécutifs
    overlap_data = _load_muscle_overlap()
    schedule = state.constraint_matrix.schedule
    day_order = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for i, day in enumerate(day_order[:-1]):
        next_day = day_order[i + 1]
        today_session = schedule.get(day, {})
        next_session = schedule.get(next_day, {})
        today_muscles = set(today_session.get("primary_muscles", []))
        next_muscles = set(next_session.get("primary_muscles", []))
        overlap = today_muscles & next_muscles
        if overlap:
            conflicts.append({
                "layer": "muscle_overlap",
                "severity": "warning",
                "days": [day, next_day],
                "muscles": list(overlap),
                "message": (
                    f"Overlap musculaire {day}/{next_day} : "
                    f"{', '.join(overlap)} sollicités < 24h d'intervalle."
                ),
            })

    # Couche 3 : Fatigue cumulée — ACWR
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

#### `node_delegate_to_agents` (TODO S5 — partiel)

Délègue aux agents actifs (Running + Lifting en S5). Les autres agents (Swimming, Biking, Nutrition) restent des no-ops jusqu'à S6-S7.

```python
from agents.running_coach.agent import RunningCoachAgent
from agents.lifting_coach.agent import LiftingCoachAgent

_AGENT_REGISTRY = {
    "running": RunningCoachAgent(),
    "lifting": LiftingCoachAgent(),
}

def node_delegate_to_agents(state: AthleteState) -> AthleteState:
    """
    Délègue aux agents spécialistes actifs.
    En S5 : Running + Lifting uniquement (stubs sans LLM).
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

---

### 10. Tests

**`tests/test_acwr.py`** — 5 tests :
- `test_ewma_acwr_safe_zone` : charges homogènes → ACWR ≈ 1.0, zone "safe"
- `test_ewma_acwr_danger_zone` : pic de charge la dernière semaine → ACWR > 1.5, zone "danger"
- `test_ewma_acwr_underload` : charges décroissantes → ACWR < 0.8, zone "underload"
- `test_ewma_acwr_empty_loads` : liste vide → (0.0, 0.0, 0.0)
- `test_ewma_acwr_single_day` : 1 jour → acute = chronic = load, ACWR = 1.0

**`tests/test_athlete_state.py`** — 3 tests :
- `test_athlete_state_extends_schema` : `AthleteState` a les champs `profile`, `fatigue`, `running_profile` etc.
- `test_athlete_state_mutable` : peut assigner `state.pending_decision = {...}` sans erreur
- `test_athlete_state_defaults` : `pending_conflicts = []`, `partial_plans = {}`, `acwr_computed = None`

**`tests/test_base_agent.py`** — 3 tests :
- `test_running_coach_run_returns_plan` : `RunningCoachAgent().run(state)` → dict avec `sessions`
- `test_lifting_coach_run_returns_plan` : `LiftingCoachAgent().run(state)` → dict avec `sessions`
- `test_agent_uses_get_agent_view` : la vue Running ne contient pas `lifting_profile`

**`tests/test_head_coach_graph.py`** — 4 tests :
- `test_graph_compiles` : `build_head_coach_graph()` s'exécute sans erreur d'import
- `test_node_load_computes_acwr` : state avec daily_loads → `acwr_computed` non-None après `node_load_athlete_state`
- `test_node_detect_no_conflicts` : ACWR = 1.0, schedule vide → `pending_conflicts = []`
- `test_node_detect_acwr_danger` : ACWR = 1.6 → `pending_conflicts` contient un conflit "danger"

**Total : ~15 nouveaux tests → ~71 total (56 S1-S4 + 15 S5)**

---

## Structure des fichiers créés/modifiés

```
models/
└── athlete_state.py          ← AthleteState (LangGraph state) — NEW

core/
└── acwr.py                   ← compute_ewma_acwr + acwr_zone — NEW

agents/
├── __init__.py               ← NEW (vide)
├── base_agent.py             ← BaseAgent ABC — NEW
├── head_coach/
│   ├── __init__.py           ← NEW (vide)
│   ├── graph.py              ← MODIFIED (compléter 3 nœuds TODO S5)
│   └── edge_cases/
│       └── __init__.py       ← NEW (get_alternatives_for_conflict)
├── running_coach/
│   ├── __init__.py           ← NEW (vide)
│   └── agent.py              ← RunningCoachAgent stub — NEW
└── lifting_coach/
    ├── __init__.py           ← NEW (vide)
    └── agent.py              ← LiftingCoachAgent stub — NEW

tests/
├── test_acwr.py              ← NEW (5 tests)
├── test_athlete_state.py     ← NEW (3 tests)
├── test_base_agent.py        ← NEW (3 tests)
└── test_head_coach_graph.py  ← NEW (4 tests)
```

---

## Commandes de vérification post-S5

```bash
# Tests S5 uniquement
poetry run pytest tests/test_acwr.py tests/test_athlete_state.py \
  tests/test_base_agent.py tests/test_head_coach_graph.py -v

# Suite complète
poetry run pytest tests/ -v
# Expected: ~71 passed

# Vérifier que le graph s'importe sans erreur
python -c "from agents.head_coach.graph import head_coach_graph; print('OK')"

# Linter
poetry run ruff check .
```

---

## Décisions prises

| Décision | Choix | Raison |
|---|---|---|
| `AthleteState` type | Pydantic BaseModel mutable (frozen=False) | Cohérence avec le code existant qui mutate l'état directement |
| LLM calls en S5 | Non — stubs déterministes | Trop complexe pour S5 (mocking LLM = infrastructure séparée) |
| ACWR dans les nœuds | Pas d'accès DB direct | LangGraph nodes sont des fonctions pures — le state est pré-chargé par l'appelant API |
| `node_recovery_gate` | Reste stub (TODO S8) | Formule readiness complète non prévue en S5 |
| Agents couverts | Running + Lifting uniquement | Swimming/Biking/Nutrition en S6-S7 |
| CONFLICT_ID edge cases | Définis dans chaque scenario_*.py | Centralisés via `__init__.py` de edge_cases |
