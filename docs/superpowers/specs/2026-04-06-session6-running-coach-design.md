# Session 6 — Running Coach : Design Spec

**Date :** 2026-04-06
**Statut :** Approuvé (auto mode)
**Session suivante :** S7 — Lifting Coach (Exercise DB + DUP + output format Hevy)

---

## Contexte

S5 a livré le `RunningCoachAgent` comme stub déterministe (retourne une séance hardcodée). S6 remplace ce stub par une vraie implémentation :

1. Lookup VDOT avec interpolation linéaire (`core/vdot.py`)
2. Sélection de séances par phase/TID/ACWR (`agents/running_coach/prescriber.py`)
3. Construction de sessions au format Runna/Garmin-compatible
4. Appel Anthropic LLM pour les `coaching_notes` (partie qualitative)
5. Route API `POST /plan/running` exposant le tout

### Ce que S6 NE fait PAS

- Pas d'auth JWT (S11)
- Pas de stockage DB du plan généré (S11)
- Pas de push Strava/Garmin (S9)
- Pas d'agents Swimming/Biking/Nutrition (S7-S15)

---

## Architecture

```
core/
└── vdot.py                        ← NEW — get_vdot_paces() + format_pace()

agents/running_coach/
├── __init__.py                    ← existant (vide)
├── prescriber.py                  ← NEW — RunningPrescriber (déterministe)
└── agent.py                       ← REPLACE stub — LLM coaching_notes + orchestration

api/v1/
└── plan.py                        ← NEW — POST /plan/running

api/
└── main.py                        ← MODIFY — monter plan_router
```

### Flux de données

```
POST /api/v1/plan/running  {athlete_state: {...}}
  → AthleteState.model_validate(body)
  → RunningCoachAgent().run(state)
    → get_agent_view(state, AgentType.running_coach) → view dict
    → prescribe(view)
      → get_vdot_paces(vdot) → paces dict
      → RunningPrescriber.build_week_plan(view) → plan dict (sans coaching_notes)
          [interne: select_session_types(phase, acwr, week) + build_sessions(session_types, paces, view)]
      → AnthropicClient.messages.create(system_prompt, context) → coaching_notes list
      → merge coaching_notes → return plan dict complet
  → JSON response (Runna-compatible)
```

---

## Livrables détaillés

### 1. `core/vdot.py`

```python
from __future__ import annotations

import json
from pathlib import Path

_TABLE: dict[str, dict] = {}
_PACE_KEYS = [
    "easy_fast_sec_km", "easy_slow_sec_km", "marathon_sec_km",
    "threshold_sec_km", "interval_sec_km", "repetition_sec_400m",
]


def _load_table() -> dict[str, dict]:
    global _TABLE
    if not _TABLE:
        path = Path(__file__).parent.parent / "data" / "vdot_paces.json"
        _TABLE = json.loads(path.read_text())["table"]
    return _TABLE


def get_vdot_paces(vdot: float) -> dict:
    """
    Retourne les allures pour un VDOT donné (interpolation linéaire).
    
    Args:
        vdot: VDOT de l'athlète (ex: 38.2)
    
    Returns:
        dict avec clés: easy_fast_sec_km, easy_slow_sec_km, marathon_sec_km,
        threshold_sec_km, interval_sec_km, repetition_sec_400m
        Toutes les valeurs en secondes.
    """
    table = _load_table()
    vdot = max(20.0, min(85.0, vdot))  # Clamp dans la plage
    low = int(vdot)
    frac = vdot - low
    
    low_paces = table[str(low)]
    high_paces = table.get(str(low + 1), low_paces)
    
    return {
        k: low_paces[k] + frac * (high_paces[k] - low_paces[k])
        for k in _PACE_KEYS
    }


def format_pace(sec_per_km: float) -> str:
    """Convertit secondes/km en 'M:SS/km'."""
    total = int(round(sec_per_km))
    m, s = divmod(total, 60)
    return f"{m}:{s:02d}/km"


def format_pace_400m(sec_per_400m: float) -> str:
    """Convertit secondes/400m en 'M:SS/400m'."""
    total = int(round(sec_per_400m))
    m, s = divmod(total, 60)
    return f"{m}:{s:02d}/400m"
```

---

### 2. `agents/running_coach/prescriber.py`

Logique déterministe pure — aucun appel LLM ici.

#### TID par phase

| Phase | Modèle | Easy% | Z2% | Z3% | Sessions types |
|---|---|---|---|---|---|
| `base_building` | Pyramidal | 75 | 15 | 10 | 2-3 easy + 0-1 tempo + 1 long |
| `build` | Polarisé | 80 | 5 | 15 | 2 easy + 1 interval + 1 long |
| `peak` | Polarisé | 80 | 5 | 15 | 2 easy + 1 interval + 1 long (-15% volume) |

#### Ajustement ACWR

| ACWR | Règle |
|---|---|
| > 1.5 (danger) | Toutes sessions → easy_run uniquement, pas de qualité |
| > 1.3 (caution) | Interval → Tempo, Tempo → Easy |
| ≤ 1.3 (safe) | Plan normal TID |

#### Séance semaine 4 (deload)

Volume hebdomadaire × 0.75. Types de séances : easy uniquement + long run réduit.

#### Templates de séances

**Easy Run (`easy_run`)**
```python
blocks = [
    {"type": "warmup", "distance_km": 0.5, "pace_target": format_pace(recovery_pace), "notes": "Jog très lent"},
    {"type": "run", "distance_km": volume_km - 1.0, "pace_target": format_pace(easy_fast), "pace_zone": "E-pace"},
    {"type": "cooldown", "distance_km": 0.5, "pace_target": format_pace(recovery_pace), "notes": "Ralentir progressivement"},
]
estimated_tss = volume_km * 1.0
```

**Tempo Run (`tempo_run`)**
```python
blocks = [
    {"type": "warmup", "distance_km": 2.0, "pace_target": format_pace(easy_slow)},
    {"type": "tempo", "distance_km": threshold_km, "pace_target": format_pace(threshold), "pace_zone": "T-pace", "notes": "Confortablement difficile — quelques mots possibles"},
    {"type": "cooldown", "distance_km": 1.5, "pace_target": format_pace(easy_slow)},
]
estimated_tss = threshold_km * 1.6 + 3.5 * 1.0  # warmup + cooldown
```

**Interval Run (`interval_run`)**
```python
blocks = [
    {"type": "warmup", "distance_km": 2.0, "pace_target": format_pace(easy_slow)},
    {"type": "strides", "repetitions": 4, "distance_m": 100, "pace_target": format_pace(interval), "recovery_duration_sec": 60, "recovery_type": "walk"},
    {"type": "interval", "repetitions": 5, "distance_m": 800, "pace_target": format_pace(interval), "pace_zone": "I-pace", "recovery_duration_sec": 180, "recovery_type": "jog", "recovery_pace": format_pace(easy_slow), "notes": "Arrêt si rep 4 > 5s plus lent que rep 1"},
    {"type": "cooldown", "distance_km": 1.5, "pace_target": format_pace(easy_slow)},
]
estimated_tss = 5 * 0.8 * 2.0 + 3.5 * 1.0  # 5 reps × 0.8km
```

**Long Run (`long_run`)**
```python
blocks = [
    {"type": "long_run", "distance_km": long_km, "pace_target": format_pace(easy_slow), "pace_zone": "E-pace (slow end)", "notes": "Rythme conversationnel strict"},
]
estimated_tss = long_km * 0.8
```

**Recovery Run (`recovery_run`)**
```python
recovery_pace_sec = easy_slow + 20  # Plus lent que Easy
blocks = [
    {"type": "run", "distance_km": 3.0, "pace_target": format_pace(recovery_pace_sec), "notes": "Plus lent que l'allure Easy — jamais plus vite"},
]
estimated_tss = 3.0 * 0.7
```

#### Sélection des jours de course

La vue filtrée contient `available_days` avec `{day: {available: bool, max_hours: float}}`.

La prescription respecte les jours disponibles. Les sessions sont assignées dans cet ordre :
1. Long Run → samedi ou dimanche (max_hours ≥ 1.5)
2. Qualité (tempo/interval) → mercredi ou jeudi (max_hours ≥ 1.0)
3. Easy Run → mardi et/ou jeudi restant

#### Interface publique du prescripteur

```python
class RunningPrescriber:
    def build_week_plan(self, view: dict) -> dict:
        """Point d'entrée unique. Retourne le plan complet sans coaching_notes."""
        # Extrait les champs nécessaires de view
        # Appelle _select_session_types() et _build_sessions()
        # Retourne dict avec: agent, week, phase, tid_model,
        #   total_km_prescribed, acwr_running, sessions[]

    def _select_session_types(self, phase: str, acwr: float, week: int) -> list[str]:
        """Retourne la liste ordonnée de types de séances."""

    def _build_sessions(self, session_types: list[str], paces: dict, view: dict) -> list[dict]:
        """Construit les sessions au format Runna-compatible."""
```

Note : `acwr_running` dans le plan de sortie est extrait de `view["acwr_computed"]` (mis à `None` si absent).

#### Contrainte de volume

```python
max_week_km = current_km * 1.10  # Règle du 10%
if mesocycle_week % 4 == 0:      # Semaine de deload (semaine 4, 8...)
    target_km = current_km * 0.75
else:
    target_km = min(current_km * 1.05, max_week_km)  # Progression prudente
```

#### Contrainte shin splints

Si `injuries_history` contient `shin_splints` : max +7% (pas 10%).

---

### 3. `agents/running_coach/agent.py`

Remplace le stub S5. Deux responsabilités :
1. Orchestrer `RunningPrescriber` (déterministe)
2. Appeler Anthropic pour les `coaching_notes` (qualitatif)

```python
import anthropic
from pathlib import Path

from agents.base_agent import BaseAgent
from agents.running_coach.prescriber import RunningPrescriber
from core.config import settings
from models.views import AgentType

_SYSTEM_PROMPT = (Path(__file__).parent / "system_prompt.md").read_text()

class RunningCoachAgent(BaseAgent):
    agent_type = AgentType.running_coach

    def __init__(self):
        self._prescriber = RunningPrescriber()
        self._client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    def prescribe(self, view: dict) -> dict:
        plan = self._prescriber.build_week_plan(view)
        plan["coaching_notes"] = self._get_coaching_notes(view, plan)
        return plan

    def _get_coaching_notes(self, view: dict, plan: dict) -> list[str]:
        """Appel LLM pour les coaching notes qualitatives."""
        import json
        user_content = (
            f"Génère 3-5 coaching_notes techniques CONCISES pour ce plan de course :\n"
            f"{json.dumps(plan, ensure_ascii=False, indent=2)}\n\n"
            f"Contexte athlète :\n{json.dumps(view, ensure_ascii=False, indent=2)}"
        )
        message = self._client.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=512,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )
        # Parser la réponse LLM — extraire les bullet points
        text = message.content[0].text
        lines = [l.strip().lstrip("-•*").strip() for l in text.split("\n") if l.strip()]
        return [l for l in lines if l][:5]  # Max 5 notes
```

---

### 4. Format de sortie — Plan hebdomadaire complet

```json
{
  "agent": "running_coach",
  "week": 3,
  "phase": "base_building",
  "tid_model": "pyramidal",
  "total_km_prescribed": 24.0,
  "acwr_running": 1.08,
  "coaching_notes": [
    "VDOT 38.2 confirmé — allures issues du tableau Jack Daniels.",
    "La séance tempo du jeudi est facultative : si les jambes sont lourdes du lifting du mercredi, remplacer par un easy run.",
    "Cadence cible : 168-172 pas/min — utiliser le métronome de la Garmin Forerunner 265."
  ],
  "sessions": [
    {
      "run_workout": {
        "id": "run_w3_tuesday_easy",
        "name": "Easy Run",
        "type": "easy_run",
        "day": "tuesday",
        "week": 3,
        "phase": "base_building",
        "estimated_duration_min": 44,
        "estimated_distance_km": 7.0,
        "estimated_tss": 7.0,
        "blocks": [
          {"type": "warmup", "distance_km": 0.5, "pace_target": "7:30/km", "notes": "Jog très lent"},
          {"type": "run", "distance_km": 6.0, "pace_target": "6:18/km", "pace_zone": "E-pace"},
          {"type": "cooldown", "distance_km": 0.5, "pace_target": "7:30/km"}
        ],
        "sync_target": "garmin_structured_workout"
      }
    },
    {
      "run_workout": {
        "id": "run_w3_thursday_tempo",
        "name": "Tempo Run",
        "type": "tempo_run",
        "day": "thursday",
        "week": 3,
        "phase": "base_building",
        "estimated_duration_min": 48,
        "estimated_distance_km": 9.0,
        "estimated_tss": 14.4,
        "blocks": [
          {"type": "warmup", "distance_km": 2.0, "pace_target": "6:57/km"},
          {"type": "tempo", "distance_km": 5.5, "pace_target": "5:18/km", "pace_zone": "T-pace"},
          {"type": "cooldown", "distance_km": 1.5, "pace_target": "6:57/km"}
        ],
        "sync_target": "garmin_structured_workout"
      }
    },
    {
      "run_workout": {
        "id": "run_w3_saturday_long",
        "name": "Long Run",
        "type": "long_run",
        "day": "saturday",
        "week": 3,
        "phase": "base_building",
        "estimated_duration_min": 81,
        "estimated_distance_km": 12.0,
        "estimated_tss": 9.6,
        "blocks": [
          {"type": "long_run", "distance_km": 12.0, "pace_target": "6:57/km", "pace_zone": "E-pace (slow end)"}
        ],
        "sync_target": "garmin_structured_workout"
      }
    }
  ]
}
```

---

### 5. `api/v1/plan.py`

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from models.athlete_state import AthleteState
from agents.running_coach.agent import RunningCoachAgent

router = APIRouter()

class RunningPlanRequest(BaseModel):
    athlete_state: dict

@router.post("/running")
def generate_running_plan(body: RunningPlanRequest) -> dict:
    """Génère un plan de course hebdomadaire Runna/Garmin-compatible."""
    try:
        state = AthleteState.model_validate(body.athlete_state)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))
    
    agent = RunningCoachAgent()
    return agent.run(state)
```

Monter dans `api/main.py` :
```python
from api.v1.plan import router as plan_router
app.include_router(plan_router, prefix="/api/v1/plan", tags=["plan"])
```

---

### 6. Tests

**`tests/test_vdot.py`** (5 tests) :
- `test_vdot_exact_lookup` : VDOT 38 → threshold_sec_km == 318 (depuis la table)
- `test_vdot_interpolation` : VDOT 38.5 → threshold entre 38 et 39
- `test_vdot_clamp_low` : VDOT 10 → valeurs VDOT 20 (clamp)
- `test_vdot_clamp_high` : VDOT 100 → valeurs VDOT 85 (clamp)
- `test_format_pace` : 318 sec/km → "5:18/km"

**`tests/test_running_prescriber.py`** (5 tests) :
- `test_select_sessions_base_building` : phase=base_building → ["easy_run", "tempo_run", "long_run"]
- `test_acwr_danger_drops_to_easy` : acwr=1.6 → uniquement easy_run
- `test_acwr_caution_downgrades_intensity` : acwr=1.4, interval prévu → retourne tempo
- `test_volume_cap_10_percent` : current=22km, +12% demandé → max 24.2km
- `test_deload_week` : mesocycle_week=4 → volume × 0.75

**`tests/test_running_agent.py`** (3 tests) :
- `test_prescribe_mocked_llm` : mock Anthropic → retourne dict avec "sessions" et "coaching_notes"
- `test_output_schema_valid` : chaque session a run_workout.id, .blocks, .sync_target
- `test_coaching_notes_merged` : les coaching_notes LLM sont dans le plan retourné

**`tests/test_plan_route.py`** (3 tests) :
- `test_post_running_plan_returns_200` : POST avec simon_pydantic_state.model_dump() → 200 + plan JSON
- `test_post_running_plan_invalid_body` → 422
- `test_post_running_plan_mocks_agent` : mock RunningCoachAgent.run → vérifie le body transmis

**Total S6 : 16 nouveaux tests → 87 total (71 S1-S5 + 16 S6)**

---

## Décisions techniques

| Décision | Choix | Raison |
|---|---|---|
| Prescription déterministe vs LLM | Déterministe pour la structure + LLM pour coaching_notes uniquement | Testabilité, fiabilité, pas de non-déterminisme sur les allures |
| Anthropic client dans agent | `__init__` instantiation | Simple, conforme au pattern S5 |
| Parsing coaching_notes LLM | Split par lignes, max 5 | Robuste — même si le LLM retourne du markdown |
| VDOT hors plage | Clamp [20, 85] | Les valeurs hors plage dans la table JSON sont extrapolées avec précaution |
| API route body | `{athlete_state: dict}` → AthleteState.model_validate | Stateless — pas de lookup DB en S6 |
| Route prefix | `/api/v1/plan` | Conforme au design doc `api/endpoints_design.md` |
| Erreur LLM | Fallback coaching_notes vides [] | Le plan est toujours retourné même sans LLM |
