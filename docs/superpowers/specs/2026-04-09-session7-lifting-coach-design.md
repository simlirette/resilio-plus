# Session 7 — Lifting Coach : Design Spec

**Date :** 2026-04-09
**Statut :** Approuvé (auto mode)
**Session suivante :** S8 — Recovery Coach (readiness score + gate keeper + HRV pipeline)

---

## Contexte

S5 a livré `LiftingCoachAgent` comme stub déterministe. S7 remplace ce stub par une vraie implémentation :

1. Base d'exercices étendue à ~80 exercices dans `exercise_database.json`
2. `LiftingPrescriber` déterministe (DUP, MEV/MRV hybride, CNS Tier restriction)
3. `LiftingCoachAgent` avec LLM pour `coaching_notes`
4. Route API `POST /plan/lifting`

### Ce que S7 NE fait PAS

- Pas de suivi du poids utilisé semaine après semaine (nécessite DB — S11)
- Pas de calcul de 1RM en live (pas d'historique)
- Pas de gestion Swimming/Biking/Nutrition
- Pas d'auth JWT (S11)

---

## Architecture

```
data/
└── exercise_database.json         ← EXPAND 23 → ~80 exercices

agents/lifting_coach/
├── __init__.py                    ← existant (vide)
├── agent.py                       ← REPLACE stub — LLM coaching_notes
├── prescriber.py                  ← NEW — LiftingPrescriber (déterministe)
└── system_prompt.md.txt           ← existant

api/v1/
└── plan.py                        ← MODIFY — ajouter POST /plan/lifting

api/
└── main.py                        ← PAS de changement (plan_router déjà monté)
```

### Flux de données

```
POST /api/v1/plan/lifting  {athlete_state: {...}}
  → AthleteState.model_validate(body)
  → LiftingCoachAgent().run(state)
    → get_agent_view(state, AgentType.lifting_coach) → view dict
    → prescribe(view)
      → LiftingPrescriber.build_week_plan(view) → plan dict (sans coaching_notes)
          [sélection DUP, enforcement MRV, templates de séances, format Hevy]
      → AnthropicClient.messages.create(...) → coaching_notes list
      → merge → return plan dict complet
  → JSON response (Hevy-compatible)
```

---

## Livrables détaillés

### 1. Expansion exercise_database.json

**Format actuel (conserver)** :
```json
{
  "exercise_id": "D04AC939",
  "name": "Barbell Bench Press",
  "tier": 3,
  "muscle_primary": "chest",
  "muscle_secondary": ["shoulders", "triceps"],
  "equipment": ["barbell", "bench"],
  "movement_pattern": "horizontal_push",
  "sfr_score": 6,
  "form_cues_fr": ["..."],
  "hevy_exercise_id": "D04AC939"
}
```

**Champs obligatoires** : `exercise_id`, `name`, `tier` (1-3), `muscle_primary`, `muscle_secondary` (list), `equipment` (list), `movement_pattern`, `sfr_score` (1-10), `form_cues_fr` (list, 2-4 items), `hevy_exercise_id`.

**Règle SFR/Tier** :
- Tier 1 → SFR ≥ 7 : isolation/machine/cable, peu de fatigue systémique
- Tier 2 → SFR 5-8 : variation compound, charge modérée
- Tier 3 → SFR ≤ 6 : compound lourd, fatigue CNS élevée

**Exercices à ajouter (~57 nouveaux)** — couvrir tous les tiers des `volume_landmarks.json` :

*Chest (manquants)* : Machine Chest Press (T1, SFR 9), Pec Deck (T1, SFR 9), Dumbbell Bench Press (T2, SFR 7), Barbell Incline Press (T3, SFR 6), DB Fly Flat (T1, SFR 9)

*Back (manquants)* : Machine Row (T1, SFR 9), Dumbbell Row (T2, SFR 7), Chest-Supported Row (T2, SFR 8), T-Bar Row (T3, SFR 6)

*Shoulders (manquants)* : DB Lateral Raise (T2, SFR 8), DB Overhead Press (T2, SFR 7), Barbell Overhead Press (T3, SFR 6), Machine Shoulder Press (T1, SFR 9), Reverse Fly Machine (T1, SFR 9)

*Biceps (manquants)* : Machine Preacher Curl (T1, SFR 9), Cable Curl (T1, SFR 9), Barbell Curl (T2, SFR 7), DB Hammer Curl (T2, SFR 7), Bayesian Cable Curl (T1, SFR 9)

*Triceps (manquants)* : DB Skull Crusher (T2, SFR 7), Close-Grip Bench Press (T3, SFR 6), Machine Tricep Dip (T1, SFR 9)

*Quadriceps (manquants)* : Leg Extension (T1, SFR 9), Walking Lunges (T2, SFR 7), Barbell Front Squat (T3, SFR 5), Goblet Squat (T2, SFR 8)

*Hamstrings (manquants)* : Lying Leg Curl (T1, SFR 9), Nordic Curl (T2, SFR 7), Romanian Deadlift (Barbell) (T3, SFR 6), Sumo Deadlift (T3, SFR 6)

*Glutes (manquants)* : Hip Thrust (Machine) (T1, SFR 9), Hip Thrust (Barbell) (T2, SFR 7), Cable Kickback (T1, SFR 9), Abductor Machine (T1, SFR 9), Step-Up (T2, SFR 7)

*Calves (manquants)* : Seated Calf Raise (T1, SFR 9), Calf Press on Leg Press (T1, SFR 9), Standing Calf Raise (Dumbbell) (T2, SFR 7), Standing Calf Raise (Barbell) (T3, SFR 5)

*Core (manquants)* : Cable Crunch (T2, SFR 8), Hanging Leg Raise (T2, SFR 7), Dead Bug (T1, SFR 9), Pallof Press (T1, SFR 9), Plank (T1, SFR 8)

*Hip external rotators (manquants)* : Banded Hip External Rotation (T1, SFR 9), Clamshell (T1, SFR 9), Side-lying Hip Abduction (T1, SFR 9)

**Total cible : ~80 exercices** (23 existants + ~57 nouveaux).

---

### 2. `agents/lifting_coach/prescriber.py`

Logique déterministe pure — aucun appel LLM.

#### DUP (Daily Undulating Periodization) par phase

| Phase | Upper A | Upper B | Lower |
|-------|---------|---------|-------|
| `base_building` | Hypertrophie : 3×10-12 RPE 8 RIR 2 | Force : 4×6-8 RPE 8 RIR 2 | Mixte : 3×10-12 RPE 7-8 |
| `build` | Force : 4×5-7 RPE 8-9 RIR 1-2 | Puissance : 5×3-5 RPE 8 RIR 2 | Hypertrophie : 3×10-12 RPE 8 |
| `peak` | Maintenance : 2×8-10 RPE 7 RIR 3 | Maintenance : 2×8-10 RPE 7 RIR 3 | Maintenance : 2×8-10 RPE 7 |

Repos entre séries :
- Hypertrophie : 90-120s
- Force/Puissance : 180-240s
- Maintenance : 60-90s

#### Ajustement ACWR Lifting

| `fatigue.acwr_by_sport_lifting` | Règle |
|--------------------------------|-------|
| > 1.5 (danger) | Toutes séances → 2 séries (pas 3-5), Tier 1 uniquement, RPE max 7 |
| > 1.3 (caution) | Pas de Tier 3, réduire volume de 1 série par exercice |
| ≤ 1.3 (safe) | Plan normal DUP |

#### Restriction CNS / Phase

```python
allow_tier3 = (
    cns_load_7day_avg <= 65
    and phase not in ("peak", "taper")
    and acwr <= 1.3
)
```

Si `allow_tier3 = False` → exercices Tier 3 remplacés par leur équivalent Tier 1/2 du même groupe musculaire.

#### Semaine de deload (week % 4 == 0)

Volume × 60%, Tier 1 seulement, RPE max 7, repos réduit.
Sessions types → seulement Upper A (maintenance) + Lower (maintenance), pas de Upper B.

#### Enforcement MEV/MRV hybride

```python
def _get_mrv_hybrid(muscle: str, phase: str, landmarks: dict) -> int:
    base_mrv = landmarks["muscles"][muscle]["mrv_hybrid"]
    is_lower = muscle in ("quadriceps", "hamstrings", "glutes", "calves")
    if is_lower:
        multiplier = landmarks["phase_adjustments"][phase]["lower_body_mrv_multiplier"]
        return int(base_mrv * multiplier)
    return base_mrv
```

Algorithme de sélection des exercices :
1. Pour chaque muscle group dans la session :
   - Calculer `sets_remaining = mrv_hybrid - current_volume`
   - Si `sets_remaining <= 0` → skip ce muscle
   - Sélectionner exercice (Tier 3 si allowed, sinon Tier 1/2 par SFR desc)
   - N_sets = min(target_sets_per_exercise, sets_remaining)
   - Ajouter à la semaine : `weekly_volume[muscle] += N_sets`

#### Interface publique du prescripteur

```python
class LiftingPrescriber:
    def __init__(self, exercise_db_path: Path | None = None):
        """Charge exercise_database.json au démarrage (lazy cache)."""

    def build_week_plan(self, view: dict) -> dict:
        """Point d'entrée unique. Retourne plan complet sans coaching_notes."""
        # Returns: {agent, week, phase, dup_model, sessions[], cns_tier3_allowed: bool}

    def _select_dup_config(self, phase: str, week: int) -> dict:
        """Retourne config DUP pour la phase (n_sets, rep_range, rpe, rir, rest)."""

    def _get_session_types(self, sessions_per_week: int, week: int) -> list[str]:
        """Retourne subset selon sessions/semaine :
        3 → ["upper_a", "lower", "upper_b"]
        2 → ["upper_a", "lower"]
        1 → ["upper_a"]
        Deload (week % 4 == 0) → max 2 sessions."""

    def _get_mrv_hybrid(self, muscle: str, phase: str) -> int:
        """MRV hybride ajusté pour la phase."""

    def _build_session(
        self, session_type: str, dup_config: dict, view: dict,
        weekly_volume: dict, week: int, phase: str, day: str
    ) -> dict:
        """Construit une session Hevy-compatible."""

    def _select_exercise(
        self, muscle: str, equipment: list[str], allow_tier3: bool, exclude: set
    ) -> dict | None:
        """Sélectionne le meilleur exercice disponible (SFR desc, Tier constraint)."""

    def _assign_days(
        self, session_types: list[str], available_days: dict
    ) -> dict[str, str]:
        """Assigne upper_a/upper_b/lower aux jours disponibles."""
```

#### Assignation des jours

```python
_DAY_ORDER_UPPER = ["monday", "tuesday", "thursday", "saturday"]
_DAY_ORDER_LOWER = ["wednesday", "thursday", "saturday", "sunday"]
```

1. Lower → premier jour de `_DAY_ORDER_LOWER` disponible avec `max_hours ≥ 1.0`
2. Upper A → premier jour `_DAY_ORDER_UPPER` disponible (différent de lower)
3. Upper B → autre jour `_DAY_ORDER_UPPER` (si sessions_per_week ≥ 3)

#### Contenu des sessions

**Upper A (hypertrophie)** — groupe musculaires : chest, back_lats, shoulders_lateral, biceps, triceps

Ordre de prescription :
1. Chest : 1 exercice Tier 3 (si allowed) + 1 Tier 1/2 → target 3 séries chacun
2. Back : 1 exercice Tier 3 (si allowed) + 1 Tier 1 → target 3 séries chacun
3. Shoulders : 2 exercices Tier 1 → target 3 séries chacun
4. Biceps : 1 exercice Tier 1 → target 3 séries
5. Triceps : 1 exercice Tier 1 → target 3 séries

**Upper B (force)** — même groupes, moins d'exercices, plus de séries :
1. Chest : 1 Tier 3 + 1 Tier 2 → 4 séries
2. Back : 1 Tier 3 + 1 Tier 2 → 4 séries
3. Shoulders : 1 Tier 2 → 3 séries
4. Biceps + Triceps : 1 exercice chacun → 3 séries

**Lower** — groupe musculaires : quadriceps, hamstrings, glutes, calves, hip_external_rotators

1. Quads : 1 Tier 3/2 (squat/hack) + 1 Tier 1 (leg press/extension) → 3 séries
2. Hamstrings : 1 Tier 1 (leg curl) + 1 Tier 2 (RDL DB) → 3 séries
3. Glutes : 1 Tier 1 (hip thrust machine ou cable kickback) → 2-3 séries
4. Calves : 1 Tier 1 (seated calf raise) → 3 séries
5. Hip external rotators : 1 Tier 1 (clamshell ou banded) → 2 séries (TOUJOURS — prévention blessures)

---

### 3. Format de sortie — Plan hebdomadaire Hevy-compatible

```json
{
  "agent": "lifting_coach",
  "week": 3,
  "phase": "base_building",
  "dup_model": "DUP 3-way (Hypertrophie / Force / Maintenance)",
  "cns_tier3_allowed": true,
  "coaching_notes": [
    "VDOT 38.2 → quadriceps et ischio-jambiers déjà stimulés par la course. MRV hybride réduit en conséquence.",
    "Séance Upper B (Force) : privilégier la qualité d'exécution sur la charge — objectif RIR 2.",
    "Si les séances de course de la semaine dépassent 25km, réduire Upper B à 3 séries (pas 4)."
  ],
  "sessions": [
    {
      "hevy_workout": {
        "id": "lift_w3_monday_upper_a",
        "title": "Upper A — Hypertrophie",
        "type": "upper_a",
        "day": "monday",
        "week": 3,
        "phase": "base_building",
        "estimated_duration_min": 65,
        "dup_focus": "hypertrophy",
        "exercises": [
          {
            "exercise_id": "D04AC939",
            "name": "Barbell Bench Press",
            "muscle_primary": "chest",
            "tier": 3,
            "sets": [
              {"set_number": 1, "type": "warmup", "weight_kg": null, "reps": 10, "rpe": null, "rir": null},
              {"set_number": 2, "type": "normal", "weight_kg": null, "reps": 10, "rpe": 8, "rir": 2},
              {"set_number": 3, "type": "normal", "weight_kg": null, "reps": 10, "rpe": 8, "rir": 2},
              {"set_number": 4, "type": "normal", "weight_kg": null, "reps": 10, "rpe": 8, "rir": 2}
            ],
            "rest_seconds": 120,
            "progression_note": "Double progression : garder même poids jusqu'à 3×12 RIR 2, puis +2.5kg"
          }
        ]
      }
    }
  ]
}
```

**Règles du format Hevy** :
- `weight_kg: null` — l'athlète règle son propre poids par RPE/RIR (auto-régulation)
- `type: "warmup"` — 1 set d'échauffement avant chaque exercice Tier 2/3 (pas Tier 1)
- `type: "normal"` — set de travail
- `progression_note` — texte clair pour la double progression
- `rest_seconds` — selon focus DUP (90-120 hypertrophie, 180-240 force)

---

### 4. `agents/lifting_coach/agent.py`

Remplace le stub S5. Même pattern exact que `RunningCoachAgent` (S6) :

```python
import json
from pathlib import Path

import anthropic

from agents.base_agent import BaseAgent
from agents.lifting_coach.prescriber import LiftingPrescriber
from core.config import settings
from models.views import AgentType

_SYSTEM_PROMPT = (Path(__file__).parent / "system_prompt.md.txt").read_text()

class LiftingCoachAgent(BaseAgent):
    agent_type = AgentType.lifting_coach

    def __init__(self) -> None:
        self._prescriber = LiftingPrescriber()
        self._client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    def prescribe(self, view: dict) -> dict:
        plan = self._prescriber.build_week_plan(view)
        plan["coaching_notes"] = self._get_coaching_notes(view, plan)
        return plan

    def _get_coaching_notes(self, view: dict, plan: dict) -> list[str]:
        """Appel LLM pour notes qualitatives. Fallback = []."""
        user_content = (
            f"Génère 3-5 coaching_notes techniques CONCISES pour ce plan de musculation :\n"
            f"{json.dumps(plan, ensure_ascii=False, indent=2)}\n\n"
            f"Contexte athlète :\n{json.dumps(view, ensure_ascii=False, indent=2)}"
        )
        try:
            message = self._client.messages.create(
                model=settings.ANTHROPIC_MODEL,
                max_tokens=512,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_content}],
            )
            text = message.content[0].text
            lines = [l.strip().lstrip("-•*").strip() for l in text.split("\n") if l.strip()]
            return [l for l in lines if l][:5]
        except Exception:
            return []
```

**Note** : Le fichier system prompt s'appelle `system_prompt.md.txt` (extension `.txt` existante dans le repo).

---

### 5. `api/v1/plan.py` — Ajout route `/lifting`

Ajouter dans le fichier existant (ne pas remplacer la route `/running`) :

```python
class LiftingPlanRequest(BaseModel):
    athlete_state: dict

@router.post("/lifting")
def generate_lifting_plan(body: LiftingPlanRequest) -> dict:
    """Génère un plan de musculation hebdomadaire Hevy-compatible."""
    try:
        state = AthleteState.model_validate(body.athlete_state)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    agent = LiftingCoachAgent()
    return agent.run(state)
```

Ajouter l'import : `from agents.lifting_coach.agent import LiftingCoachAgent`

---

### 6. Tests

**`tests/test_exercise_database.py`** — tests supplémentaires (fichier existant) :
- `test_exercise_db_has_80_exercises` : `len(exercises) >= 75` (marge sur l'objectif 80)
- `test_all_exercises_have_hevy_id` : chaque exercice a `hevy_exercise_id` non-vide
- `test_tier1_sfr_above_7` : tous Tier 1 ont `sfr_score >= 7`
- `test_all_muscles_covered` : au moins 1 exercice par muscle group des landmarks

**`tests/test_lifting_prescriber.py`** (6 tests) :
- `test_select_session_types_3x_week` : 3 sessions/semaine → ["upper_a", "lower", "upper_b"]
- `test_dup_base_building_upper_a` : phase=base_building, type=upper_a → 3 sets, 10-12 reps, RPE 8
- `test_cns_blocks_tier3` : cns_load_7day_avg=70 → aucun exercice Tier 3 dans le plan
- `test_mrv_hybrid_enforced` : muscle au MRV → exercice skippé
- `test_deload_reduces_volume` : week=4 → total_sets ≤ 60% semaine normale
- `test_build_week_plan_hevy_format` : chaque session a `hevy_workout.id`, `.exercises[]`, `.exercises[].sets[]`

**`tests/test_lifting_agent.py`** (4 tests) :
- `test_prescribe_mocked_llm` : plan a "sessions" et "coaching_notes"
- `test_output_schema_valid` : chaque session a `hevy_workout.id`, `.exercises`, `.exercises[].sets`
- `test_coaching_notes_merged` : notes LLM parsées (pas de tirets)
- `test_llm_error_returns_empty_notes` : exception → coaching_notes=[]

**`tests/test_plan_route.py`** — tests supplémentaires (fichier existant) :
- `test_post_lifting_plan_returns_200` : POST avec simon_pydantic_state → 200
- `test_post_lifting_plan_invalid_body` : body invalide → 422
- `test_post_lifting_plan_agent_receives_state` : agent reçoit AthleteState valide

**Total S7 : ~17 nouveaux tests → ~107 total**

---

## Décisions techniques

| Décision | Choix | Raison |
|----------|-------|--------|
| Exercise DB taille | ~80 (vs 400+) | Couvre 100% des cas d'un athlète hybride, maintenable |
| Poids dans les sets | `null` (auto-régulation RPE) | Pas d'historique 1RM disponible avant S11 ; RPE + RIR suffisent |
| Nom du système prompt | `system_prompt.md.txt` | Fichier existant dans le repo, ne pas renommer |
| DUP model | 3-way Hypertrophie/Force/Maintenance | Optimal pour 3 sessions/semaine, supporte tous les splits courants |
| Volume tracking | `weekly_volume: dict[str, int]` en mémoire | Pas de DB en S7 — tracking intra-prescripteur uniquement |
| Erreur LLM | Fallback coaching_notes=[] | Plan toujours retourné même sans LLM |
