# Session 2 — Schémas : Design Spec

**Date :** 2026-04-04
**Statut :** Approuvé
**Session suivante :** S3 — Connecteurs (Strava OAuth + Hevy CSV/API)

---

## Contexte

S1 a livré le toolchain complet (Poetry, Dockerfile, Alembic, config). Les SQLAlchemy models (`models/database.py`) sont complets depuis le départ — 8 tables avec JSONB pour les structures complexes et colonnes relationnelles pour les métriques time-series.

S2 pose la couche de validation Pydantic au-dessus des SQLAlchemy models, génère la première migration Alembic, et implémente `get_agent_view()` — la fonction centrale du token economy définie au §2.3 du master doc.

### État du repo en entrée de S2

| Élément | Statut |
|---|---|
| `models/database.py` | Existant — 8 tables SQLAlchemy complètes |
| `alembic/env.py` + `alembic.ini` | Existants — configurés, zéro migration |
| `tests/conftest.py` | Existant — Simon dicts + fixtures DB async |
| `models/schemas.py` | Manquant → livré en S2 |
| `models/views.py` | Manquant → livré en S2 |
| `alembic/versions/` | Vide → première migration en S2 |

---

## Livrables S2

### 1. `models/schemas.py` — AthleteState Pydantic complet

~15 sub-models qui reflètent exactement le JSON §2.1 du master doc. Structure :

```
AthleteStateSchema
├── profile: AthleteProfile
│   ├── training_history: TrainingHistory
│   ├── injuries_history: list[Injury]
│   ├── lifestyle: Lifestyle
│   ├── goals: Goals
│   ├── equipment: Equipment
│   └── available_days: dict[str, DayAvailability]
├── current_phase: CurrentPhase
├── running_profile: RunningProfile
│   └── training_paces: TrainingPaces
├── lifting_profile: LiftingProfile
│   └── volume_landmarks: dict[str, VolumeLandmarks]
├── swimming_profile: SwimmingProfile
├── biking_profile: BikingProfile
├── nutrition_profile: NutritionProfile
│   └── macros_target: MacrosTarget
├── fatigue: FatigueState
│   └── acwr_by_sport: ACWRBySport
├── compliance: Compliance
└── weekly_volumes: WeeklyVolumes
```

**Règles de design :**

- `model_config = ConfigDict(strict=False)` — Pydantic coerce les données JSONB sans planter
- Les champs inconnus au moment du onboarding sont `Optional` avec `None` par défaut — les données arrivent progressivement via les connecteurs
- `athlete_id: UUID` + `updated_at: datetime` au niveau root — identité et fraîcheur
- Pas de schemas FastAPI request/response (S11), pas de modèles workout output (S6/S7)

**Sub-models et leurs champs clés :**

```python
class TrainingHistory(BaseModel):
    total_years_training: float
    years_running: float
    years_lifting: float
    years_swimming: float
    current_weekly_volume_hours: float
    longest_run_ever_km: float | None = None
    current_5k_time_min: float | None = None
    current_10k_time_min: float | None = None
    current_half_marathon_min: float | None = None
    estimated_1rm: dict[str, float] = {}  # squat, bench_press, deadlift, overhead_press

class Injury(BaseModel):
    type: str
    year: int
    duration_weeks: int
    side: str | None = None
    recurrent: bool = False
    notes: str | None = None

class Lifestyle(BaseModel):
    work_type: str
    work_hours_per_day: float
    commute_active: bool
    sleep_avg_hours: float
    stress_level: str  # "low" | "moderate" | "high" | "very_high"
    alcohol_per_week: int = 0
    smoking: bool = False

class Goals(BaseModel):
    primary: str
    secondary: str | None = None
    tertiary: str | None = None
    timeline_weeks: int
    priority_hierarchy: list[str] = []

class Equipment(BaseModel):
    gym_access: bool
    gym_equipment: list[str] = []
    pool_access: bool = False
    pool_type: str | None = None
    outdoor_running: bool = True
    treadmill: bool = False
    heart_rate_monitor: bool = False
    gps_watch: str | None = None
    power_meter_bike: bool = False

class DayAvailability(BaseModel):
    available: bool
    max_hours: float
    preferred_time: str | None = None  # "morning" | "evening" | "noon"

class AthleteProfile(BaseModel):
    first_name: str
    age: int
    sex: Literal["M", "F"]
    weight_kg: float
    height_cm: float
    body_fat_percent: float | None = None
    resting_hr: int | None = None
    max_hr_measured: int | None = None
    max_hr_formula: int | None = None
    training_history: TrainingHistory
    injuries_history: list[Injury] = []
    lifestyle: Lifestyle
    goals: Goals
    equipment: Equipment
    active_sports: list[str] = []
    available_days: dict[str, DayAvailability] = {}

class CurrentPhase(BaseModel):
    macrocycle: str  # "base_building" | "build" | "peak" | "taper" | "race" | "transition"
    mesocycle_week: int
    mesocycle_length: int = 4
    next_deload: str | None = None
    target_event: str | None = None
    target_event_date: date | None = None

class TrainingPaces(BaseModel):
    easy_min_per_km: str
    easy_max_per_km: str
    marathon_pace_per_km: str | None = None
    threshold_pace_per_km: str
    interval_pace_per_km: str
    repetition_pace_per_km: str
    long_run_pace_per_km: str

class RunningProfile(BaseModel):
    vdot: float
    training_paces: TrainingPaces
    weekly_km_current: float
    weekly_km_target: float
    max_long_run_km: float
    cadence_avg: int | None = None
    preferred_terrain: str = "road"

class VolumeLandmarks(BaseModel):
    mev: int   # Minimum Effective Volume
    mav: int   # Maximum Adaptive Volume
    mrv_hybrid: int  # Maximum Recoverable Volume (hybrid athlete context)

class LiftingProfile(BaseModel):
    training_split: str  # "upper_lower" | "ppl" | "full_body" | etc.
    sessions_per_week: int
    current_volume_per_muscle: dict[str, int] = {}
    volume_landmarks: dict[str, VolumeLandmarks] = {}
    progression_model: str = "double_progression"
    rir_target_range: list[int] = [1, 3]

class SwimmingProfile(BaseModel):
    reference_times: dict[str, float] = {}  # {"100m": 95.0, "400m": 420.0}
    technique_level: str = "beginner"  # "beginner" | "intermediate" | "advanced"
    weekly_volume_km: float = 0.0

class BikingProfile(BaseModel):
    ftp_watts: float | None = None
    weekly_volume_km: float = 0.0

class MacrosTarget(BaseModel):
    protein_g: float
    carbs_g: float
    fat_g: float

class NutritionProfile(BaseModel):
    tdee_estimated: float
    macros_target: MacrosTarget
    supplements_current: list[str] = []
    dietary_restrictions: list[str] = []
    allergies: list[str] = []

class ACWRBySport(BaseModel):
    running: float | None = None
    lifting: float | None = None
    biking: float | None = None
    swimming: float | None = None

class FatigueState(BaseModel):
    acwr: float | None = None
    acwr_trend: str | None = None  # "stable" | "rising" | "falling"
    acwr_by_sport: ACWRBySport = ACWRBySport()
    weekly_fatigue_score: float | None = None
    fatigue_by_muscle: dict[str, float] = {}
    cns_load_7day_avg: float | None = None
    recovery_score_today: float | None = None
    hrv_rmssd_today: float | None = None
    hrv_rmssd_baseline: float | None = None
    sleep_hours_last_night: float | None = None
    sleep_quality_subjective: int | None = None  # 1-10
    fatigue_subjective: int | None = None  # 1-10

class Compliance(BaseModel):
    last_4_weeks_completion_rate: float | None = None
    missed_sessions_this_week: list[str] = []
    nutrition_adherence_7day: float | None = None

class WeeklyVolumes(BaseModel):
    running_km: float = 0.0
    lifting_sessions: int = 0
    swimming_km: float = 0.0
    biking_km: float = 0.0
    total_training_hours: float = 0.0

class AthleteStateSchema(BaseModel):
    model_config = ConfigDict(strict=False)

    athlete_id: UUID
    updated_at: datetime
    profile: AthleteProfile
    current_phase: CurrentPhase
    running_profile: RunningProfile
    lifting_profile: LiftingProfile
    swimming_profile: SwimmingProfile = SwimmingProfile()
    biking_profile: BikingProfile = BikingProfile()
    nutrition_profile: NutritionProfile
    fatigue: FatigueState = FatigueState()
    compliance: Compliance = Compliance()
    weekly_volumes: WeeklyVolumes = WeeklyVolumes()
```

---

### 2. `models/views.py` — `get_agent_view()`

**`AgentType` enum :**

```python
class AgentType(str, Enum):
    head_coach = "head_coach"
    running_coach = "running_coach"
    lifting_coach = "lifting_coach"
    swimming_coach = "swimming_coach"
    biking_coach = "biking_coach"
    nutrition_coach = "nutrition_coach"
    recovery_coach = "recovery_coach"
```

**Architecture :** `AGENT_VIEW_MAP` est un `dict[AgentType, Callable[[AthleteStateSchema], dict]]`. Chaque agent a sa propre fonction de projection — propre, testable unitairement, extensible en S5 sans toucher aux schemas.

La fonction principale retourne un `dict` (pas un sous-modèle Pydantic) — les agents LangGraph travaillent nativement avec des dicts. Le Head Coach reçoit l'AthleteState complet sérialisé.

**Exemple — vue Running Coach :**
```python
def _running_view(state: AthleteStateSchema) -> dict:
    return {
        "identity": state.profile.model_dump(
            include={"first_name", "age", "sex", "weight_kg"}
        ),
        "goals": state.profile.goals.model_dump(),
        "constraints": {
            "injuries_history": [i.model_dump() for i in state.profile.injuries_history]
        },
        "equipment": state.profile.equipment.model_dump(),
        "available_days": {
            k: v.model_dump() for k, v in state.profile.available_days.items()
        },
        "running_profile": state.running_profile.model_dump(),
        "fatigue": {
            "acwr_by_sport_running": state.fatigue.acwr_by_sport.running,
            "hrv_rmssd_today": state.fatigue.hrv_rmssd_today,
            "recovery_score_today": state.fatigue.recovery_score_today,
        },
        "current_phase": state.current_phase.model_dump(),
    }
```

**Vues par agent (master doc §2.3) :**

| Agent | Champs inclus | Champs exclus |
|---|---|---|
| Head Coach | AthleteState complet | — |
| Running Coach | identity, goals, constraints, equipment, available_days, running_profile, fatigue.acwr_running + hrv + recovery, current_phase | lifting_profile, nutrition_profile, fatigue.fatigue_by_muscle |
| Lifting Coach | identity, goals, constraints, equipment, available_days, lifting_profile, fatigue.acwr_lifting + fatigue_by_muscle + cns_load + recovery, current_phase | running_profile, nutrition_profile |
| Swimming Coach | identity, goals, constraints, equipment, swimming_profile, fatigue.hrv + recovery, current_phase | running_profile, lifting_profile |
| Biking Coach | identity, goals, constraints, equipment, biking_profile, fatigue.acwr_biking + hrv + recovery, current_phase | running_profile, lifting_profile |
| Nutrition Coach | identity, goals, constraints, nutrition_profile, weekly_volumes (tous sports), current_phase | running_profile, lifting_profile, fatigue détaillée |
| Recovery Coach | identity, constraints, fatigue (complet), weekly_volumes (tous sports), compliance, current_phase | running_profile, lifting_profile, nutrition_profile |

**Signature publique :**
```python
def get_agent_view(state: AthleteStateSchema, agent: AgentType) -> dict:
    """Filtre l'AthleteState selon les permissions de l'agent."""
    return AGENT_VIEW_MAP[agent](state)
```

---

### 3. Migration Alembic — `alembic/versions/<hash>_initial_schema.py`

Générée via autogenerate depuis `models/database.py`. Aucune modification du schéma DB — les 8 tables SQLAlchemy sont complètes depuis S1.

**Commandes :**
```bash
docker compose up db -d
poetry run alembic revision --autogenerate -m "initial schema"
poetry run alembic upgrade head
poetry run alembic current  # → affiche le hash (head)
```

La migration est committée dans le repo. `alembic/versions/.gitkeep` est supprimé.

---

### 4. Tests

**`tests/test_schemas.py`** — validation des Pydantic models :
- Simon roundtrip : `AthleteStateSchema` construit depuis les dicts de `conftest.py` → `model_dump()` → `model_validate()` → identique
- Champs optionnels : `SwimmingProfile()` vide et `BikingProfile(ftp_watts=None)` passent sans erreur
- Validation des types : `sex="X"` rejette via `Literal`, string dans un champ `float` coerce correctement
- JSONB roundtrip : `model_validate(json.loads(json.dumps(state.model_dump(mode="json"))))` → identique

**`tests/test_views.py`** — validation de `get_agent_view()` :
- Running Coach : reçoit `running_profile`, ne reçoit PAS `lifting_profile`
- Lifting Coach : reçoit `fatigue_by_muscle` et `cns_load_7day_avg`, ne reçoit PAS `acwr_by_sport.running`
- Nutrition Coach : reçoit `weekly_volumes`, ne reçoit PAS `running_profile`
- Recovery Coach : reçoit `fatigue` complet
- Head Coach : reçoit tous les champs
- Aucun agent (sauf Head Coach) ne reçoit `profile.training_history`

Tous les tests utilisent `simon_dict` de `conftest.py` — pas de DB, pas de fixtures async, tests rapides.

---

## Ce que S2 ne fait PAS

- Pas de schemas FastAPI request/response → S11
- Pas de modèles workout output (RunWorkout, LiftWorkout) → S6/S7
- Pas d'implémentation des agents → S5
- Pas de logique ACWR/EWMA → S8
- Pas de modification des SQLAlchemy models → déjà complets en S1

---

## Commandes de vérification post-S2

```bash
# Tests (sans DB)
poetry run pytest tests/test_schemas.py tests/test_views.py -v

# Migration (nécessite PostgreSQL)
docker compose up db -d
poetry run alembic upgrade head
poetry run alembic current

# Tous les tests S1 + S2
poetry run pytest tests/ -v
```

---

## Décisions prises

| Décision | Choix | Raison |
|---|---|---|
| Organisation fichiers | 2 fichiers (`schemas.py` + `views.py`) | Responsabilités distinctes, YAGNI (pas de split par domaine) |
| Return type `get_agent_view()` | `dict` (pas un sous-modèle Pydantic) | LangGraph travaille nativement avec des dicts |
| Champs optionnels | `Optional` avec `None` par défaut | Les données arrivent progressivement via connecteurs |
| `get_agent_view()` en S2 | Oui (avancé depuis S5) | Consumer naturel des schemas — allège S5 (LangGraph + agents) |
| `ConfigDict(strict=False)` | Oui | Coercion JSONB sans planter sur des types voisins |
