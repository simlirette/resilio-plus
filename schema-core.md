# `schema-core.md` — Schémas Pydantic fondamentaux de `AthleteState`

> **Version 1 (livrable B1).** Spécification exhaustive et implémentable des schémas Pydantic fondamentaux du système Resilio+. Référence pour Phase B2 (`_AGENT_VIEWS`), Phase B3 (contrats de sortie structurés des agents) et Phase D (implémentation backend). Dérivé de `user-flow-complete.md` v4, `agent-flow-langgraph.md` v1, `agent-roster.md` v1. Cible la version finale du produit, pas une livraison V1 intermédiaire.

## Objet et périmètre

Ce document formalise :

1. La structure complète de `AthleteState` par catégorie.
2. Les sous-modèles Pydantic détaillés : `ExperienceProfile`, `ObjectiveProfile`, `InjuryHistory`, `PracticalConstraints`.
3. Les schémas des index dérivés : `StrainState`, triplets Readiness et EA, `AllostaticLoadState`.
4. La structure des plans : `ActivePlan`, `BaselinePlan`, `PlanBlock`, `PlanComponent`, `TradeOff`.
5. Les validators cross-champ exhaustifs.
6. La structure des tables `knowledge/strain-contributions/` avec exemples minimaux.

Ne décrit pas : les prompts système par agent (Phase C), les `_AGENT_VIEWS` par agent (Phase B2), les contrats de sortie structurés des agents (Phase B3), le code d'implémentation (Phase D).

---

## Principes architecturaux transversaux

Trois principes actés en Phase A conditionnent toute la spec.

### Agents LLM produisent du structuré, nodes et services persistent

Aucun agent LLM n'écrit directement sur un sous-modèle structuré de `AthleteState`. Les agents produisent des payloads structurés en sortie ; les mutations sont appliquées par des nodes LangGraph dédiés (`persist_block`, `persist_injury`, `apply_logistic_adjustment`, etc.) ou par les services déterministes. Unique exception : les messages conversationnels.

### Services déterministes pour les index dérivés

Quatre services Python externes aux graphes LangGraph écrivent les champs `DERIVED_*` : `StrainComputationService`, `ReadinessComputationService`, `EnergyAvailabilityService`, `AllostaticLoadService`. Aucun de ces index n'est écrit par un agent LLM.

### Architecture à trois champs pour Readiness et EA

Triplet `objective_* / user_*_signal / effective_*` : le service écrit l'objectif, un node handler écrit le signal user, l'effectif est une **fonction pure** calculée à la volée. L'effectif n'est pas persisté.

### Règle de nesting vs référence DB

`AthleteState` est un modèle Pydantic qui porte en attributs directs : identité, profils, plans, index dérivés, état de parcours, métadonnées techniques. Les **logs** (`LOGS_TRAINING`, `LOGS_PHYSIO`, `LOGS_NUTRITION`) et les **messages** (`CONVO.messages`) sont dans des tables DB séparées, injectés dans les `_AGENT_VIEWS` à la lecture avec des fenêtres pertinentes par agent (spec Phase B2).

---

## Table des matières

1. [Énumération de `AthleteState` par catégorie](#1-énumération-de-athletestate-par-catégorie)
2. [Sous-modèles détaillés](#2-sous-modèles-détaillés)
3. [Index dérivés](#3-index-dérivés)
4. [Plans](#4-plans)
5. [Validators cross-champ](#5-validators-cross-champ)
6. [Tables `knowledge/strain-contributions/`](#6-tables-knowledgestrain-contributions)
7. [Constantes et seuils](#7-constantes-et-seuils)
8. [Résumé des décisions structurantes B1](#8-résumé-des-décisions-structurantes-b1)

---

## 1. Énumération de `AthleteState` par catégorie

Toutes les catégories ci-dessous sont des attributs Pydantic directs du modèle `AthleteState` sauf mention contraire. Types détaillés aux sections suivantes.

### 1.1 IDENT

| Champ | Type | Origine |
|---|---|---|
| `athlete_id` | `str` (UUID) | Créé signup |
| `date_of_birth` | `date` | Signup, âge dérivé |
| `biological_sex` | `Literal["male", "female"]` | Signup |
| `height` | `float` (cm) | Signup |
| `weight` | `float` (kg) | Signup, re-saisi |
| `ffm` | `float \| None` | Dérivée initialement, raffinée Onboarding Coach |
| `cycle_active` | `bool` | V3, défaut `False` |
| `cycle_phase` | `CyclePhase \| None` | V3 |
| `cycle_day` | `int \| None` | V3, optionnel |
| `cycle_length_days` | `int \| None` | V3, optionnel |
| `timezone` | `str` (IANA) | Signup |
| `locale` | `str` | Signup, défaut depuis navigateur |
| `unit_preference` | `Literal["metric", "imperial"]` | Signup, affichage uniquement |

### 1.2 SCOPE

| Champ | Type |
|---|---|
| `coaching_scope` | `dict[Domain, ScopeLevel]` — 6 domaines × 3 niveaux |
| `peer_disciplines_active` | `list[Discipline]` — dérivé, coerce |

### 1.3 JOURNEY

| Champ | Type |
|---|---|
| `journey_phase` | `JourneyPhase` — 7 valeurs mutuellement exclusives |
| `recovery_takeover_active` | `bool` — overlay |
| `onboarding_reentry_active` | `bool` — overlay |
| `assessment_mode` | `bool` |

### 1.4 SUB_PROFILES

| Champ | Type | Propriétaire |
|---|---|---|
| `experience_profile` | `ExperienceProfile \| None` | Onboarding Coach |
| `objective_profile` | `ObjectiveProfile \| None` | Onboarding Coach (création/abandon), Head Coach (révision) |
| `injury_history` | `InjuryHistory` | Onboarding Coach + Recovery Coach |
| `practical_constraints` | `PracticalConstraints \| None` | Onboarding Coach |

### 1.5 CLASSIFICATION

| Champ | Type |
|---|---|
| `classification` | `dict[Discipline, DimensionClassification]` |
| `confidence_levels` | `dict[tuple[Discipline, ClassificationDimension], float]` |
| `radar_data` | `RadarData` — dérivé, coerce |
| `last_classification_update` | `datetime \| None` |

### 1.6 PLANS

| Champ | Type |
|---|---|
| `baseline_plan` | `BaselinePlan \| None` |
| `active_plan` | `ActivePlan \| None` |

### 1.7 DERIVED_STRAIN

| Champ | Type |
|---|---|
| `strain_state` | `StrainState \| None` |

### 1.8 DERIVED_READINESS

| Champ | Type |
|---|---|
| `objective_readiness` | `ReadinessValue \| None` |
| `user_readiness_signal` | `UserReadinessSignal \| None` |
| `persistent_override_pattern` | `PersistentOverridePattern` |

`effective_readiness` n'est **pas persisté** : calculé à la volée via `computed_field` sur `AthleteState`.

### 1.9 DERIVED_EA

| Champ | Type |
|---|---|
| `objective_energy_availability` | `EnergyAvailabilityValue \| None` |
| `user_energy_signal` | `UserEnergySignal \| None` |

`effective_energy_availability` n'est **pas persisté** : calculé à la volée.

### 1.10 DERIVED_ALLO

| Champ | Type |
|---|---|
| `allostatic_load_state` | `AllostaticLoadState \| None` |

### 1.11 CONVO

Messages persistés dans table DB séparée. Sur `AthleteState` :

| Champ | Type |
|---|---|
| `last_classified_intent` | `ClassifiedIntent \| None` |
| `last_message_at` | `datetime \| None` |

### 1.12 TECHNICAL

| Champ | Type |
|---|---|
| `active_onboarding_thread_id` | `str \| None` |
| `active_plan_generation_thread_id` | `str \| None` |
| `active_followup_thread_id` | `str \| None` |
| `active_recovery_thread_id` | `str \| None` |
| `proactive_messages_last_7d` | `list[datetime]` — fenêtre glissante, coerce |
| `connector_status` | `dict[ConnectorName, ConnectorStatus]` |
| `validation_warnings` | `list[ValidationWarning]` — TTL < 24h, coerce |
| `created_at` | `datetime` |
| `updated_at` | `datetime` |

---

## 2. Sous-modèles détaillés

### 2.1 Énumérations partagées

```python
from enum import Enum
from typing import Literal

class Discipline(str, Enum):
    LIFTING = "lifting"
    RUNNING = "running"
    SWIMMING = "swimming"
    BIKING = "biking"

class Domain(str, Enum):
    LIFTING = "lifting"
    RUNNING = "running"
    SWIMMING = "swimming"
    BIKING = "biking"
    NUTRITION = "nutrition"
    RECOVERY = "recovery"

class ScopeLevel(str, Enum):
    FULL = "full"
    TRACKING = "tracking"
    DISABLED = "disabled"

class JourneyPhase(str, Enum):
    SIGNUP = "signup"
    SCOPE_SELECTION = "scope_selection"
    ONBOARDING = "onboarding"
    BASELINE_PENDING_CONFIRMATION = "baseline_pending_confirmation"
    BASELINE_ACTIVE = "baseline_active"
    FOLLOWUP_TRANSITION = "followup_transition"
    STEADY_STATE = "steady_state"

class CyclePhase(str, Enum):
    FOLLICULAR = "follicular"
    OVULATORY = "ovulatory"
    LUTEAL_EARLY = "luteal_early"
    LUTEAL_LATE = "luteal_late"
    AMENORRHEA = "amenorrhea"
    POST_MENOPAUSE = "post_menopause"
    HORMONAL_CONTRACEPTION_STABLE = "hormonal_contraception_stable"
    UNKNOWN = "unknown"

class MuscleGroup(str, Enum):
    # Bas du corps
    QUADS = "quads"
    HAMSTRINGS = "hamstrings"
    GLUTES = "glutes"
    CALVES = "calves"
    HIP_FLEXORS = "hip_flexors"
    ADDUCTORS = "adductors"
    ABDUCTORS = "abductors"
    # Tronc
    LOWER_BACK = "lower_back"
    CORE = "core"
    UPPER_BACK = "upper_back"
    LATS = "lats"
    # Haut du corps
    CHEST = "chest"
    FRONT_DELTS = "front_delts"
    SIDE_DELTS = "side_delts"
    REAR_DELTS = "rear_delts"
    BICEPS = "biceps"
    TRICEPS = "triceps"
    FOREARMS = "forearms"

class ClassificationDimension(str, Enum):
    CAPACITY = "capacity"
    TECHNIQUE = "technique"
    HISTORY = "history"

class ClassificationLevel(str, Enum):
    NOVICE = "novice"
    BEGINNER_ADVANCED = "beginner_advanced"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    UNKNOWN = "unknown"
```

### 2.2 `ExperienceProfile`

Structure imbriquée par discipline. Entrée présente uniquement pour les disciplines en `coaching_scope[D] != "disabled"` en steady-state.

```python
from datetime import date, datetime
from pydantic import BaseModel, Field

class InterruptionRecord(BaseModel):
    duration_weeks: float = Field(..., ge=4.0)
    reason_category: Literal[
        "injury", "illness", "life_event", "motivation",
        "travel", "other", "unspecified"
    ]
    ended_at: date | None = None

class PRRecord(BaseModel):
    movement_or_distance: str
    value: float
    unit: Literal["kg", "lb", "sec", "min", "km", "mi", "m", "yd", "reps"]
    achieved_at: date | None = None
    context: Literal["competition", "training", "unofficial", "unknown"] = "unknown"

class DistanceRecord(BaseModel):
    distance_km: float = Field(..., gt=0.0)
    completed_count: int = Field(..., ge=1)
    best_time_seconds: int | None = None

class VolumeRecord(BaseModel):
    value: float = Field(..., ge=0.0)
    unit: Literal["km", "hours", "sessions", "total_tonnage_kg"]

class SessionExtremeRecord(BaseModel):
    value: float
    unit: Literal["km", "minutes", "kg_load", "reps_at_rpe"]
    approximate_date: date | None = None

class DisciplineExperience(BaseModel):
    years_structured: float | None = Field(None, ge=0.0, le=80.0)
    typical_frequency_per_week_12m: float | None = Field(None, ge=0.0, le=14.0)
    last_interruption_over_4w: InterruptionRecord | None = None

    prs_referenced: list[PRRecord] = Field(default_factory=list)
    movements_mastered: list[str] = Field(default_factory=list)
    # Taxonomie stabilisée Phase C par discipline. En B1, list[str] acceptant tout.
    distances_covered: list[DistanceRecord] = Field(default_factory=list)

    weekly_volume_recent_8w: VolumeRecord | None = None
    longest_session_recent_8w: SessionExtremeRecord | None = None
    most_intense_session_recent_8w: SessionExtremeRecord | None = None

    relative_charges: dict[str, float] | None = None
    # Lifting seulement. Ex : {"back_squat": 1.5, "deadlift": 2.0}

    bloc_marked_insufficient: bool = False

class ExperienceProfile(BaseModel):
    by_discipline: dict[Discipline, DisciplineExperience]
    last_updated_at: datetime
    last_updated_by: Literal[
        "onboarding_coach", "followup_transition", "user_correction"
    ]
```

### 2.3 `ObjectiveProfile`

```python
class ObjectiveCategory(str, Enum):
    STRENGTH_MAX = "strength_max"
    HYPERTROPHY = "hypertrophy"
    ENDURANCE_RACE = "endurance_race"
    POWER_ENDURANCE = "power_endurance"
    SPEED = "speed"
    RECOMPOSITION = "recomposition"
    FAT_LOSS = "fat_loss"
    WEIGHT_GAIN = "weight_gain"
    GENERAL_FITNESS = "general_fitness"
    RETURN_FROM_INJURY = "return_from_injury"
    LIFESTYLE_MAINTENANCE = "lifestyle_maintenance"
    HYBRID_STRENGTH_ENDURANCE = "hybrid_strength_endurance"
    HYBRID_AESTHETIC_PERFORMANCE = "hybrid_aesthetic_performance"

class ObjectivePriority(str, Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"

class ObjectiveHorizon(str, Enum):
    SHORT = "short"       # < 3 mois
    MEDIUM = "medium"     # 3–6 mois
    LONG = "long"         # 6–12 mois
    OPEN_ENDED = "open_ended"

class TargetMetric(BaseModel):
    metric_name: str
    current_value: float | None = None
    target_value: float
    unit: str

class Objective(BaseModel):
    category: ObjectiveCategory
    priority: ObjectivePriority
    horizon: ObjectiveHorizon
    target_date: date | None = None
    target_metric: TargetMetric | None = None
    free_text_description: str | None = Field(None, max_length=500)
    declared_at: datetime

class TradeOffDeclaration(BaseModel):
    """Trade-off reconnu par l'user, distinct des TradeOff système du plan."""
    sacrificed_objective_category: ObjectiveCategory
    protected_objective_category: ObjectiveCategory
    user_acknowledged_at: datetime

class ObjectiveProfile(BaseModel):
    primary: Objective
    secondary: list[Objective] = Field(default_factory=list, max_length=3)
    trade_offs_acknowledged: list[TradeOffDeclaration] = Field(default_factory=list)
    last_revision_at: datetime
    revision_count: int = Field(0, ge=0)
```

### 2.4 `InjuryHistory`

```python
class InjuryStatus(str, Enum):
    ACTIVE = "active"
    CHRONIC_MANAGED = "chronic_managed"
    RESOLVED = "resolved"
    HISTORICAL = "historical"

class InjurySeverity(str, Enum):
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"

class BodyRegion(str, Enum):
    ANKLE = "ankle"
    FOOT = "foot"
    CALF = "calf"
    SHIN = "shin"
    KNEE = "knee"
    THIGH_ANTERIOR = "thigh_anterior"
    THIGH_POSTERIOR = "thigh_posterior"
    HIP = "hip"
    GROIN = "groin"
    LOWER_BACK = "lower_back"
    MID_BACK = "mid_back"
    UPPER_BACK = "upper_back"
    ABDOMEN = "abdomen"
    RIBS = "ribs"
    NECK = "neck"
    SHOULDER = "shoulder"
    ELBOW = "elbow"
    WRIST = "wrist"
    HAND = "hand"
    UPPER_ARM = "upper_arm"
    FOREARM = "forearm"
    HEAD = "head"
    SYSTEMIC = "systemic"

class InjurySide(str, Enum):
    LEFT = "left"
    RIGHT = "right"
    BILATERAL = "bilateral"
    NOT_APPLICABLE = "not_applicable"

class ContraindicationType(str, Enum):
    AVOID_MOVEMENT_PATTERN = "avoid_movement_pattern"
    REDUCE_VOLUME = "reduce_volume"
    REDUCE_INTENSITY = "reduce_intensity"
    AVOID_IMPACT = "avoid_impact"
    AVOID_DISCIPLINE = "avoid_discipline"
    REQUIRE_WARMUP_PROTOCOL = "require_warmup_protocol"
    MONITOR_CLOSELY = "monitor_closely"

class Contraindication(BaseModel):
    type: ContraindicationType
    target: str
    notes: str | None = Field(None, max_length=300)

class InjuryRecord(BaseModel):
    injury_id: str = Field(..., description="UUID v4 stable")
    region: BodyRegion
    side: InjurySide = InjurySide.NOT_APPLICABLE
    specific_structure: str | None = Field(None, max_length=100)

    status: InjuryStatus
    severity: InjurySeverity

    onset_date: date | None = None
    resolved_date: date | None = None

    mechanism: str | None = Field(None, max_length=300)
    diagnosis: str | None = Field(None, max_length=200)
    diagnosed_by_professional: bool = False

    contraindications: list[Contraindication] = Field(default_factory=list)

    triggered_recovery_takeover: bool = False
    linked_recovery_thread_id: str | None = None

    declared_by: Literal[
        "onboarding_coach", "recovery_coach", "user_direct_correction"
    ]
    declared_at: datetime
    last_updated_at: datetime

class InjuryHistory(BaseModel):
    injuries: list[InjuryRecord] = Field(default_factory=list)
    has_active_injury: bool = False           # coerce via validator
    has_chronic_managed: bool = False         # coerce via validator
    last_updated_at: datetime
```

### 2.5 `PracticalConstraints`

```python
class DayOfWeek(str, Enum):
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"

class EquipmentCategory(str, Enum):
    FULL_GYM = "full_gym"
    HOME_GYM_EXTENSIVE = "home_gym_extensive"
    HOME_GYM_MINIMAL = "home_gym_minimal"
    NONE = "none"

class LocationContext(str, Enum):
    COMMERCIAL_GYM = "commercial_gym"
    HOME = "home"
    OUTDOOR = "outdoor"
    TRACK = "track"
    POOL_INDOOR = "pool_indoor"
    POOL_OUTDOOR = "pool_outdoor"
    OPEN_WATER = "open_water"
    MIXED = "mixed"

class ClimateZone(str, Enum):
    TROPICAL = "tropical"
    ARID = "arid"
    TEMPERATE_MILD = "temperate_mild"
    TEMPERATE_CONTINENTAL = "temperate_continental"
    COLD_CONTINENTAL = "cold_continental"
    POLAR_SUBARCTIC = "polar_subarctic"
    MOUNTAIN = "mountain"
    UNKNOWN = "unknown"

class TerrainAccessible(str, Enum):
    FLAT = "flat"
    ROLLING = "rolling"
    HILLY = "hilly"
    MOUNTAINOUS = "mountainous"
    MIXED = "mixed"

class GeographicContext(BaseModel):
    climate_zone: ClimateZone = ClimateZone.UNKNOWN
    altitude_m: int | None = Field(None, ge=0, le=6000)
    terrain_types_accessible: list[TerrainAccessible] = Field(default_factory=list)
    seasonal_variation: Literal["minimal", "moderate", "marked", "severe"] | None = None
    winter_indoor_substitution_required: bool = False

class TimeAvailability(BaseModel):
    day: DayOfWeek
    available: bool
    preferred_time_of_day: Literal[
        "early_morning", "morning", "midday",
        "afternoon", "evening", "night"
    ] | None = None
    max_session_minutes: int | None = Field(None, ge=15, le=360)

class SleepPattern(BaseModel):
    typical_bedtime: str | None = None     # "HH:MM"
    typical_waketime: str | None = None    # "HH:MM"
    target_hours_per_night: float = Field(7.5, ge=4.0, le=12.0)
    quality_self_assessment: Literal["poor", "fair", "good", "excellent"] | None = None

class WorkContext(BaseModel):
    occupation_physical_demand: Literal[
        "sedentary", "light", "moderate", "heavy", "very_heavy"
    ] | None = None
    typical_stress_level: Literal["low", "moderate", "high", "very_high"] | None = None
    travel_frequency: Literal["none", "occasional", "frequent", "very_frequent"] | None = None

class MealContext(BaseModel):
    typical_meals_per_day: int | None = Field(None, ge=1, le=8)
    dietary_restrictions: list[Literal[
        "none", "vegetarian", "vegan", "pescatarian",
        "halal", "kosher", "gluten_free", "lactose_free",
        "low_fodmap", "allergy_specific", "other"
    ]] = Field(default_factory=list)
    dietary_restrictions_notes: str | None = Field(None, max_length=300)
    cooking_capability: Literal["extensive", "moderate", "limited", "none"] | None = None
    budget_constraint: Literal["none", "moderate", "strict"] | None = None

class PracticalConstraints(BaseModel):
    available_days: list[TimeAvailability] = Field(..., min_length=7, max_length=7)
    total_weekly_minutes_budget: int | None = Field(None, ge=30, le=3000)

    equipment: list[EquipmentCategory] = Field(default_factory=list)
    specific_equipment_available: list[str] = Field(default_factory=list)
    primary_location: LocationContext | None = None
    secondary_locations: list[LocationContext] = Field(default_factory=list)

    sleep: SleepPattern
    work: WorkContext
    meals: MealContext | None = None
    geographic_context: GeographicContext | None = None

    financial_budget_flag: Literal["tight", "moderate", "flexible"] | None = None

    last_updated_at: datetime
    last_updated_by: Literal[
        "onboarding_coach",
        "chat_turn_constraint_change",
        "user_direct_correction"
    ]
```

### 2.6 `ClassificationData`

```python
class DimensionClassification(BaseModel):
    capacity: ClassificationLevel
    technique: ClassificationLevel
    history: ClassificationLevel

class RadarPoint(BaseModel):
    discipline: Discipline
    dimension: ClassificationDimension
    normalized_value: float = Field(..., ge=0.0, le=1.0)

class RadarData(BaseModel):
    points: list[RadarPoint]
    generated_at: datetime
```

---

## 3. Index dérivés

### 3.1 `StrainState`

Propriétaire exclusif d'écriture : `StrainComputationService`.

```python
class MuscleGroupStrain(BaseModel):
    current_value: float = Field(..., ge=0.0, le=100.0)
    peak_24h: float = Field(..., ge=0.0, le=100.0)
    ewma_tau_days: float = Field(..., gt=0.0)
    last_contribution_at: datetime | None = None

class StrainHistoryPoint(BaseModel):
    date: date
    aggregate: float = Field(..., ge=0.0, le=100.0)
    by_group: dict[MuscleGroup, float]

class StrainState(BaseModel):
    by_group: dict[MuscleGroup, MuscleGroupStrain]
    # Les 18 groupes exhaustifs, même si valeur 0.0
    aggregate: float = Field(..., ge=0.0, le=100.0)
    history: list[StrainHistoryPoint] = Field(..., max_length=21)
    last_computed_at: datetime
    recompute_trigger: Literal["session_logged", "daily_decay", "manual"]
```

### 3.2 Triplet Readiness

```python
class ReadinessValue(BaseModel):
    score: float = Field(..., ge=0.0, le=100.0)
    contributing_factors: dict[
        Literal["hrv", "sleep", "strain", "rpe_trend"],
        float
    ]
    computed_at: datetime

class UserReadinessSignal(BaseModel):
    score: float = Field(..., ge=0.0, le=100.0)
    submitted_at: datetime
    source: Literal["morning_checkin", "explicit_override"]

class PersistentOverridePattern(BaseModel):
    active: bool = False
    first_detected_at: datetime | None = None
    last_confirmed_at: datetime | None = None
    consecutive_days_detected: int = Field(0, ge=0)
    divergence_magnitude: float | None = Field(None, ge=0.0)
    reason: str | None = None
    set_by: Literal["recovery_coach", "system_fallback"] | None = None
    reset_by: Literal["head_coach", "system"] | None = None
    reset_at: datetime | None = None

class EffectiveReadiness(BaseModel):
    """Résultat de la fonction pure — non persisté."""
    score: float | None = Field(None, ge=0.0, le=100.0)
    resolution: Literal[
        "takeover_neutralized",
        "pattern_neutralized",
        "no_user_signal",
        "critical_zone_upward_blocked",
        "user_override_upward",
        "user_override_downward",
        "indeterminate",
    ]
    user_override_applied: bool
    safeguard_active: Literal[
        "recovery_takeover", "persistent_override_pattern", "critical_zone"
    ] | None = None
```

**Fonction pure de résolution.** Ordre de priorité descendant des safeguards. Seuils chargés depuis `knowledge/thresholds.json`.

```python
def resolve_effective_readiness(
    objective: ReadinessValue | None,
    user_signal: UserReadinessSignal | None,
    overlay_takeover_active: bool,
    override_pattern: PersistentOverridePattern,
    critical_threshold: float,
    user_signal_freshness_hours: int = 18,
    now: datetime = None,
) -> EffectiveReadiness:
    """Fonction pure. Aucune mutation, aucun effet de bord.
    Tests unitaires obligatoires pour les 7 branches de résolution."""

    if objective is None:
        return EffectiveReadiness(
            score=None, resolution="indeterminate",
            user_override_applied=False, safeguard_active=None,
        )

    # Règle 1 — overlay Recovery prime
    if overlay_takeover_active:
        return EffectiveReadiness(
            score=objective.score, resolution="takeover_neutralized",
            user_override_applied=False, safeguard_active="recovery_takeover",
        )

    # Règle 2 — pattern persistent détecté
    if override_pattern.active:
        return EffectiveReadiness(
            score=objective.score, resolution="pattern_neutralized",
            user_override_applied=False,
            safeguard_active="persistent_override_pattern",
        )

    # Pas de signal user récent
    user_signal_valid = (
        user_signal is not None
        and (now - user_signal.submitted_at).total_seconds() / 3600
            <= user_signal_freshness_hours
    )
    if not user_signal_valid:
        return EffectiveReadiness(
            score=objective.score, resolution="no_user_signal",
            user_override_applied=False, safeguard_active=None,
        )

    # Règle 3 — zone critique : override à la hausse bloqué, baisse passe
    in_critical_zone = objective.score < critical_threshold
    if in_critical_zone and user_signal.score > objective.score:
        return EffectiveReadiness(
            score=objective.score,
            resolution="critical_zone_upward_blocked",
            user_override_applied=False, safeguard_active="critical_zone",
        )

    # Règle 4 — override à la hausse hors zone critique : autorisé
    if user_signal.score >= objective.score:
        return EffectiveReadiness(
            score=user_signal.score, resolution="user_override_upward",
            user_override_applied=True, safeguard_active=None,
        )

    # Règle 5 — override à la baisse : toujours autorisé
    return EffectiveReadiness(
        score=user_signal.score, resolution="user_override_downward",
        user_override_applied=True, safeguard_active=None,
    )
```

### 3.3 Triplet Energy Availability

Structure analogue, **safeguards plus restrictifs sur l'override à la hausse**. Blocage en zones `SUBCLINICAL` et `CLINICAL_RED_S`.

```python
class EAZone(str, Enum):
    OPTIMAL = "optimal"                # ≥ 45 kcal/kg FFM
    LOW_NORMAL = "low_normal"          # 30–45
    SUBCLINICAL = "subclinical"        # 20–30
    CLINICAL_RED_S = "clinical_red_s"  # < 20

class EnergyAvailabilityValue(BaseModel):
    score: float = Field(..., ge=0.0)   # kcal/kg FFM
    zone: EAZone
    intake_kcal: float
    eee_kcal: float                     # Exercise Energy Expenditure
    ffm_kg: float
    computed_at: datetime

class UserEnergySignal(BaseModel):
    score: Literal["very_low", "low", "neutral", "high", "very_high"]
    numeric_proxy: float
    submitted_at: datetime
    source: Literal["daily_checkin", "weekly_report", "explicit_flag"]

class EffectiveEA(BaseModel):
    score: float | None
    zone: EAZone | None
    resolution: Literal[
        "takeover_neutralized",
        "pattern_neutralized",
        "no_user_signal",
        "clinical_zone_upward_blocked",
        "user_override_upward",
        "user_override_downward",
        "indeterminate",
    ]
    user_override_applied: bool
    safeguard_active: Literal[
        "recovery_takeover", "persistent_override_pattern", "clinical_zone"
    ] | None = None
```

**Fonction pure de résolution EA.** Mêmes étapes que Readiness, avec trois différences :

1. `user_signal_freshness_hours = 48` (EA évolue moins vite que HRV/sommeil).
2. Zone bloquante élargie : `SUBCLINICAL` + `CLINICAL_RED_S` (pas seulement `< critical_threshold`).
3. `persistent_override_pattern` sur Readiness neutralise aussi EA (déni énergétique probable).

### 3.4 `AllostaticLoadState`

Pas de triplet. Charge systémique peu accessible à l'introspection.

```python
class AllostaticLoadZone(str, Enum):
    NORMAL = "normal"
    ELEVATED = "elevated"
    ALARM = "alarm"

class AllostaticLoadHistoryPoint(BaseModel):
    date: date
    value: float
    zone: AllostaticLoadZone

class AllostaticLoadState(BaseModel):
    current_value: float = Field(..., ge=0.0, le=100.0)
    zone: AllostaticLoadZone
    trend_7d_slope: float
    trend_14d_slope: float
    contributing_factors: dict[Literal[
        "strain_aggregate", "sleep_debt", "hrv_deviation",
        "reported_stress", "rpe_trend", "nutrition_deficit"
    ], float]
    history: list[AllostaticLoadHistoryPoint] = Field(..., max_length=30)
    last_computed_at: datetime
```

### 3.5 Dépendances de calcul

```
LOGS_TRAINING ──┐
                ├──▶ StrainState ──────────────────┐
LOGS_PHYSIO ────┤                                  │
                ├──▶ ObjectiveReadiness ──┐        │
                │   (HRV, sleep, strain,  │        │
                │    rpe_trend)           │        │
LOGS_NUTRITION ─┼──▶ ObjectiveEA ─────────┼────────┼──▶ AllostaticLoadState
                │                         │        │
USER_SIGNALS ───┼──▶ UserReadinessSignal ─┤        │
                └──▶ UserEnergySignal ────┤        │
                                          ▼        ▼
                                 EffectiveReadiness, EffectiveEA
                                 (fonctions pures, non persistées)
```

**Ordre de recompute à l'insertion d'un log de session :** `StrainState` → `ObjectiveReadiness` → `ObjectiveEA` → `AllostaticLoadState`.

---

## 4. Plans

### 4.1 Énumérations partagées

```python
class PlanHorizon(str, Enum):
    FOUR_WEEKS = "4w"
    TWELVE_WEEKS = "12w"
    UNTIL_DATE = "until_date"

class ActivePlanStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    COMPLETED = "completed"
    SUPERSEDED = "superseded"

class BaselinePlanStatus(str, Enum):
    PENDING_CONFIRMATION = "pending_confirmation"
    ACTIVE = "active"
    COMPLETED = "completed"
    EXTENDED = "extended"
    SUPERSEDED = "superseded"

class BlockStatus(str, Enum):
    UPCOMING = "upcoming"
    CURRENT = "current"
    COMPLETED = "completed"
    SKIPPED = "skipped"

class BlockDetailLevel(str, Enum):
    FULL = "full"
    SUMMARY = "summary"

class DisciplineRoleInPlan(str, Enum):
    PRIMARY = "primary"
    CO_PRIMARY = "co_primary"
    SECONDARY = "secondary"
    MAINTENANCE = "maintenance"
    SUPPORT = "support"

class VolumeUnit(str, Enum):
    KILOMETERS = "km"
    HOURS = "hours"
    SESSIONS = "sessions"
    TOTAL_TONNAGE_KG = "total_tonnage_kg"
    TOTAL_WORKING_SETS = "total_working_sets"
    METERS_SWUM = "meters_swum"
```

### 4.2 Types structurels

```python
class VolumeTarget(BaseModel):
    value: float = Field(..., ge=0.0)
    unit: VolumeUnit

class IntensityDistribution(BaseModel):
    zones: dict[str, float]
    # Validator : valeurs dans [0.0, 1.0], somme ∈ [0.98, 1.02]
    # Taxonomie des clés par discipline stabilisée Phase C

class WeeklyVolumePoint(BaseModel):
    week_number: int = Field(..., ge=1)
    volume: VolumeTarget
```

### 4.3 `PlanComponent`

```python
class PlanComponent(BaseModel):
    discipline: Discipline
    role_in_plan: DisciplineRoleInPlan

    total_volume_arc: list[WeeklyVolumePoint]
    # Longueur == nombre de semaines couvertes par le plan

    peak_block_id: str | None = None
    deload_block_ids: list[str] = Field(default_factory=list)

    projected_strain_cap: float | None = Field(None, ge=0.0, le=100.0)

    deprioritized_vs_ideal: bool = False
    deprioritization_rationale: str | None = None
```

### 4.4 `PlanBlock`

```python
class BlockDisciplineSpec(BaseModel):
    """Renseigné uniquement si parent.detail_level == FULL."""
    discipline: Discipline
    weekly_volume_target: VolumeTarget
    intensity_distribution: IntensityDistribution
    key_sessions_per_week: int = Field(..., ge=0, le=14)
    block_theme_for_discipline: str | None = None
    prescribed_session_ids: list[str] = Field(default_factory=list)

class PlanBlock(BaseModel):
    id: str
    title: str
    theme: str
    # Texte libre : "accumulation", "intensification", "peaking",
    # "deload", "base_aerobic", "technique", combinaisons possibles.
    start_date: date
    end_date: date
    status: BlockStatus
    detail_level: BlockDetailLevel

    block_discipline_specs: dict[Discipline, BlockDisciplineSpec] | None = None

    actual_compliance_rate: float | None = Field(None, ge=0.0, le=1.0)
    block_completion_notes: str | None = None
```

### 4.5 `TradeOff`

Distinct de `TradeOffDeclaration` (posé par user dans `ObjectiveProfile`).

```python
class TradeOffCategory(str, Enum):
    VOLUME_DEPRIORITIZED = "volume_deprioritized"
    INTENSITY_DEPRIORITIZED = "intensity_deprioritized"
    OBJECTIVE_DELAYED = "objective_delayed"
    COMPOSITION_COMPROMISED = "composition_compromised"
    SCHEDULE_COMPRESSED = "schedule_compressed"
    DISCIPLINE_DEMOTED = "discipline_demoted"

class TradeOff(BaseModel):
    category: TradeOffCategory
    sacrificed_element: str
    protected_element: str
    rationale: str
    magnitude: Literal["minor", "moderate", "significant"]
    disclosed_at: datetime
    disclosed_in_plan_id: str
    acknowledged_by_user: bool = False
    acknowledged_at: datetime | None = None
```

### 4.6 `ActivePlan`

```python
class ActivePlan(BaseModel):
    plan_id: str
    generated_at: datetime
    generation_mode: Literal["first_personalized", "block_regen"]

    objective_snapshot: ObjectiveProfile
    coaching_scope_snapshot: dict[Domain, ScopeLevel]
    # Figé à generated_at, sert invariant PL15

    horizon: PlanHorizon
    start_date: date
    end_date: date | None = None

    blocks: list[PlanBlock] = Field(..., min_length=1)
    discipline_components: dict[Discipline, PlanComponent]
    trade_offs_disclosed: list[TradeOff] = Field(default_factory=list)

    status: ActivePlanStatus
    is_between_blocks: bool = False           # coerce via validator

    suspended_at: datetime | None = None
    suspended_reason: str | None = None
    suspension_triggered_by: Literal[
        "recovery_coach", "user_request", "monitoring_system"
    ] | None = None

    last_modification_at: datetime
    last_modification_type: Literal[
        "creation", "logistic_adjustment", "block_regen",
        "suspension", "resumption", "supersession"
    ] | None = None
    modification_count: int = Field(0, ge=0)
```

### 4.7 `BaselinePlan`

```python
class BaselineDisciplineSpec(BaseModel):
    discipline: Discipline
    prescribed_session_ids: list[str]
    modality_priority: Literal["complete_signal", "minimal_signal"]
    expected_representative_sessions: int = Field(..., ge=1)

class BaselineExtension(BaseModel):
    extended_at: datetime
    extension_days: int = Field(..., ge=1, le=14)
    reason: Literal[
        "short_pause", "insufficient_compliance",
        "insufficient_data_quality", "connector_lag"
    ]
    reason_detail: str | None = None
    new_end_date: date

class BaselinePlan(BaseModel):
    plan_id: str
    generated_at: datetime

    objective_snapshot: ObjectiveProfile
    coaching_scope_snapshot: dict[Domain, ScopeLevel]

    start_date: date
    planned_end_date: date
    effective_end_date: date | None = None

    planned_duration_days: int = Field(..., ge=7, le=21)

    disciplines_covered: list[Discipline] = Field(..., min_length=1)
    baseline_discipline_specs: dict[Discipline, BaselineDisciplineSpec]

    status: BaselinePlanStatus
    confirmed_at: datetime | None = None
    completed_at: datetime | None = None

    extensions: list[BaselineExtension] = Field(default_factory=list)

    shortened_due_to_connector_history: bool = False
    shortcut_rationale: str | None = None

    last_modification_at: datetime
```

### 4.8 Note sur `PrescribedSession`

Les `prescribed_session_ids` référencent une entité externe à `AthleteState`, persistée en table DB :

```
Table prescribed_sessions
  ├─ session_id (PK)
  ├─ plan_id (FK vers active_plan.plan_id ou baseline_plan.plan_id)
  ├─ block_id (FK vers PlanBlock.id, null si baseline)
  ├─ discipline
  ├─ scheduled_date | day_slot
  ├─ session_type, volume_prescribed, intensity_prescribed, parameters
  ├─ strain_annotation_override
  ├─ rationale
  ├─ status : "upcoming" | "completed" | "missed" | "modified" | "skipped"
  └─ logged_session_id (FK vers logs_training)
```

Spec Pydantic complète de `PrescribedSession` : **Phase B3** (contrat `Recommendation.sessions[]` des coachs disciplines, matérialisé par node `persist_prescribed_sessions`).

---

## 5. Validators cross-champ

### 5.1 Mécaniques

Trois niveaux d'application :

| Niveau | Syntaxe Pydantic | Usage |
|---|---|---|
| Champ | `@field_validator` | Bornes, formats, enums |
| Modèle | `@model_validator(mode="after")` sur sous-modèle | Invariants internes |
| AthleteState | `@model_validator(mode="after")` sur `AthleteState` | Invariants cross-modèles |

Comportements sur violation :

- **rejet** : lève `ValueError`, transaction annulée.
- **coerce** : valeur recalculée automatiquement, pas de rejet.
- **soft warn** : émet `logging.warning()` + ajoute une entrée `ValidationWarning` à `AthleteState.validation_warnings` (TTL < 24h). Pas de rejet.

### 5.2 Invariants IDENT

| ID | Prédicat | Niveau | Comportement |
|---|---|---|---|
| I1 | `biological_sex != "female"` → `cycle_active == False` | AthleteState | rejet |
| I2 | `cycle_active == False` → `cycle_phase is None` | AthleteState | rejet |
| I3 | `cycle_active == True` → `cycle_phase is not None` | AthleteState | rejet |
| I4 | `cycle_day is not None` → `cycle_active == True` | AthleteState | rejet |
| I5 | `cycle_length_days is not None` → `cycle_active == True` | AthleteState | rejet |
| I6 | `cycle_day is not None ∧ cycle_length_days is not None` → `1 ≤ cycle_day ≤ cycle_length_days` | AthleteState | rejet |
| I7 | `cycle_length_days ∈ [21, 40]` | champ | rejet |
| I8 | `ffm is not None` → `0 < ffm < weight` | AthleteState | rejet |
| I9 | `height ∈ [100, 250]` cm | champ | rejet |
| I10 | `weight ∈ [30, 300]` kg | champ | rejet |
| I11 | âge dérivé de `date_of_birth` ∈ [13, 100] | champ | rejet |
| I12 | `timezone` est un identifiant IANA valide | champ | rejet |

### 5.3 Invariants SCOPE

| ID | Prédicat | Niveau | Comportement |
|---|---|---|---|
| S1 | `coaching_scope` contient exactement les 6 clés `Domain` | modèle | rejet |
| S2 | Chaque valeur ∈ `ScopeLevel` | champ | rejet |
| S3 | `peer_disciplines_active == {D : coaching_scope[D] == FULL}` | AthleteState | coerce |

### 5.4 Invariants JOURNEY et TECHNICAL

| ID | Prédicat | Niveau | Comportement |
|---|---|---|---|
| J1 | `assessment_mode == True` ↔ `journey_phase ∈ {baseline_pending_confirmation, baseline_active, followup_transition}` | AthleteState | rejet |
| J2 | `journey_phase ∉ {signup, scope_selection}` → `∃ D : coaching_scope[D] == FULL` | AthleteState | rejet |
| J3 | `recovery_takeover_active == True` → `journey_phase ∈ {baseline_active, followup_transition, steady_state}` | AthleteState | rejet |
| J4 | `onboarding_reentry_active == True` → `journey_phase ∈ {baseline_active, followup_transition, steady_state}` | AthleteState | rejet |
| J5 | `active_onboarding_thread_id is not None` ↔ `journey_phase == onboarding ∨ onboarding_reentry_active == True` | AthleteState | rejet |
| J6 | `active_recovery_thread_id is not None` ↔ `recovery_takeover_active == True` | AthleteState | rejet |
| J7 | `active_followup_thread_id is not None` ↔ `journey_phase == followup_transition` | AthleteState | rejet |
| J8 | Format thread_id : `^[a-f0-9-]+:(onboarding\|plan_generation\|followup_transition\|recovery_takeover\|chat_turn):[a-f0-9-]{36}$` | champ | rejet |

### 5.5 Invariants SUB_PROFILES

**ExperienceProfile**

| ID | Prédicat | Niveau | Comportement |
|---|---|---|---|
| E1 | Clés de `by_discipline` ⊆ `Discipline` | modèle | rejet |
| E2 | Post-onboarding : `by_discipline.keys() == {D : coaching_scope[D] == FULL}` | AthleteState | soft warn |
| E3 | `DisciplineExperience.years_structured ≤ (âge - 5)` | AthleteState | soft warn |
| E4 | `relative_charges is not None` → `LIFTING ∈ by_discipline.keys()` | modèle | rejet |
| E5 | `distances_covered` non vide → `discipline ∈ {RUNNING, SWIMMING, BIKING}` | modèle | rejet |
| E6 | `PRRecord.unit` cohérent avec `movement_or_distance` (matrice Phase C) | modèle | rejet (stub) |

**ObjectiveProfile**

| ID | Prédicat | Niveau | Comportement |
|---|---|---|---|
| O1 | `primary is not None` | modèle | rejet |
| O2 | `primary.priority == PRIMARY` | modèle | rejet |
| O3 | `∀ obj ∈ secondary : obj.priority == SECONDARY` | modèle | rejet |
| O4 | `len(secondary) ≤ 3` | champ | rejet |
| O5 | `primary.horizon != OPEN_ENDED` → `primary.target_date is not None` | modèle | rejet |
| O6 | `primary.target_date > declared_at.date()` | modèle | rejet |
| O7 | `primary.target_metric.current_value != target_value` | modèle | soft warn |
| O8 | Non-contradiction primary ↔ secondary (matrice Phase C) | modèle | rejet (stub) |
| O9 | `primary.category ∈ {HYBRID_*}` → au moins une discipline de chaque côté active en FULL | AthleteState | soft warn |

**InjuryHistory**

| ID | Prédicat | Niveau | Comportement |
|---|---|---|---|
| IN1 | `status == RESOLVED` → `resolved_date is not None` | modèle | rejet |
| IN2 | `status ∈ {ACTIVE, CHRONIC_MANAGED}` → `resolved_date is None` | modèle | rejet |
| IN3 | `resolved_date ≥ onset_date` | modèle | rejet |
| IN4 | `has_active_injury ↔ ∃ r : r.status == ACTIVE` | modèle | coerce |
| IN5 | `has_chronic_managed ↔ ∃ r : r.status == CHRONIC_MANAGED` | modèle | coerce |
| IN6 | `triggered_recovery_takeover ∧ status == ACTIVE` → `linked_recovery_thread_id is not None` | modèle | rejet |
| IN7 | `side == NOT_APPLICABLE ↔ region ∈ {LOWER_BACK, MID_BACK, UPPER_BACK, ABDOMEN, RIBS, NECK, HEAD, SYSTEMIC}` | modèle | soft warn |

**PracticalConstraints**

| ID | Prédicat | Niveau | Comportement |
|---|---|---|---|
| PC1 | `available_days` : 7 entrées, chaque `DayOfWeek` distinct | modèle | rejet |
| PC2 | `meals is not None ↔ coaching_scope[NUTRITION] != DISABLED` | AthleteState | rejet |
| PC3 | `bedtime ∧ waketime` cohérents | modèle | soft warn |
| PC4 | `total_weekly_minutes_budget ≤ Σ max_session_minutes (day.available)` | modèle | soft warn |
| PC5 | `altitude_m > 1500` → `climate_zone == MOUNTAIN` | modèle | soft warn |
| PC6 | `seasonal_variation ∈ {marked, severe}` → `winter_indoor_substitution_required is not None` | modèle | rejet |

### 5.6 Invariants CLASSIFICATION

| ID | Prédicat | Niveau | Comportement |
|---|---|---|---|
| CL1 | `classification.keys() == {D : coaching_scope[D] == FULL}` | AthleteState | soft warn |
| CL2 | Pour chaque discipline classée, 3 dimensions présentes | modèle | rejet |
| CL3 | `confidence_levels` a une entrée par `(discipline, dimension)` pour chaque classée | modèle | rejet |
| CL4 | `confidence_levels[(d, dim)] ∈ [0.0, 1.0]` | champ | rejet |
| CL5 | `classification[d][dim] == UNKNOWN` → `confidence_levels[(d, dim)] < CONFIDENCE_UNKNOWN_THRESHOLD` | AthleteState | soft warn |
| CL6 | `radar_data` cohérent avec `classification` | AthleteState | coerce |

### 5.7 Invariants PLANS

| ID | Prédicat | Niveau | Comportement |
|---|---|---|---|
| PL1 | `horizon == UNTIL_DATE ↔ end_date is not None` | modèle | rejet |
| PL2 | `horizon == FOUR_WEEKS` → `end_date == start_date + 28d` | modèle | rejet |
| PL3 | `horizon == TWELVE_WEEKS` → `end_date == start_date + 84d` | modèle | rejet |
| PL4 | Au plus 1 bloc avec `detail_level == FULL` | modèle | rejet |
| PL5 | Au plus 1 bloc avec `status == CURRENT` | modèle | rejet |
| PL6 | `is_between_blocks ↔ (aucun CURRENT ∧ ≥1 COMPLETED ∧ ≥1 UPCOMING)` | modèle | coerce |
| PL7 | `block_discipline_specs is not None ↔ detail_level == FULL` | modèle | rejet |
| PL8 | `discipline_components.keys() == {D : coaching_scope_snapshot[D] == FULL}` | modèle | rejet |
| PL9 | `status == SUSPENDED ↔ (suspended_at, suspended_reason, suspension_triggered_by)` tous renseignés | modèle | rejet |
| PL10 | `status == SUSPENDED ∧ triggered_by == recovery_coach` → `recovery_takeover_active == True` | AthleteState | rejet |
| PL11 | `recovery_takeover_active == True ∧ active_plan is not None` → `active_plan.status == SUSPENDED` | AthleteState | rejet |
| PL12 | `blocks` triés par `start_date` ascendant, non chevauchants | modèle | rejet |
| PL13 | `PlanComponent.total_volume_arc` longueur == semaines couvertes | modèle | rejet |
| PL14 | `BaselinePlan.planned_duration_days ∈ [7, 21]` | champ | rejet |
| PL15 | `BaselinePlan.disciplines_covered ⊆ {D : coaching_scope_snapshot[D] == FULL}` | modèle | rejet |
| PL16 | `IntensityDistribution.zones` valeurs ≥ 0, somme ∈ [0.98, 1.02] | modèle | rejet |
| PL17 | `discipline_components` : exactement 1 PRIMARY **OU** ≥ 2 CO_PRIMARY ; pas de mélange | modèle | rejet |
| PL18 | `ObjectiveProfile.primary.category ∈ {HYBRID_*}` → ≥ 2 CO_PRIMARY | AthleteState | soft warn |
| PL19 | `BaselineExtension` list append-only, triée par `extended_at` | service | service |
| PL20 | `PlanBlock.id` unique dans le plan | modèle | rejet |
| PL21 | `PlanBlock.end_date > start_date` | modèle | rejet |

### 5.8 Invariants DERIVED_STRAIN

| ID | Prédicat | Niveau | Comportement |
|---|---|---|---|
| DS1 | `by_group.keys() == set(MuscleGroup)` (18 groupes exhaustifs) | modèle | rejet |
| DS2 | `aggregate ∈ [0.0, 100.0]` | champ | rejet |
| DS3 | `history` longueur ≤ 21 | champ | rejet |
| DS4 | `history` triée par date ascendante, dates distinctes | modèle | rejet |
| DS5 | `current_value ≤ peak_24h` pour chaque groupe | modèle | rejet |
| DS6 | `ewma_tau_days > 0` | champ | rejet |
| DS7 | Écart entre `max(history.date)` et `last_computed_at.date()` ≤ 1 jour | modèle | soft warn |

### 5.9 Invariants DERIVED_READINESS

| ID | Prédicat | Niveau | Comportement |
|---|---|---|---|
| DR1 | `ReadinessValue.score ∈ [0.0, 100.0]` | champ | rejet |
| DR2 | `contributing_factors` : clés ⊆ {hrv, sleep, strain, rpe_trend}, somme ∈ [0.98, 1.02] | modèle | rejet |
| DR3 | `UserReadinessSignal.score ∈ [0.0, 100.0]` | champ | rejet |
| DR4 | `PersistentOverridePattern.active == True` → `first_detected_at`, `last_confirmed_at`, `set_by` renseignés | modèle | rejet |
| DR5 | `active == True` → `consecutive_days_detected ≥ N_THRESHOLD` (5 proposé Phase C) | modèle | rejet |
| DR6 | `active == False ∧ reset_at is not None` → `reset_by is not None` | modèle | rejet |
| DR7 | `divergence_magnitude is not None` → `≥ MIN_DIVERGENCE` (15 proposé Phase C) | modèle | soft warn |

### 5.10 Invariants DERIVED_EA

| ID | Prédicat | Niveau | Comportement |
|---|---|---|---|
| DE1 | `zone == OPTIMAL ↔ score ≥ 45` | modèle | rejet |
| DE2 | `zone == LOW_NORMAL ↔ 30 ≤ score < 45` | modèle | rejet |
| DE3 | `zone == SUBCLINICAL ↔ 20 ≤ score < 30` | modèle | rejet |
| DE4 | `zone == CLINICAL_RED_S ↔ score < 20` | modèle | rejet |
| DE5 | `ffm_kg` cohérent avec `athlete_state.ffm` (écart ≤ 1 kg) | AthleteState | soft warn |
| DE6 | `score == (intake_kcal - eee_kcal) / ffm_kg` (tolérance ±0.5) | modèle | coerce |
| DE7 | `numeric_proxy` cohérent avec `score` discret (mapping fixe Phase C) | modèle | rejet |

### 5.11 Invariants DERIVED_ALLO

| ID | Prédicat | Niveau | Comportement |
|---|---|---|---|
| DA1 | `current_value ∈ [0.0, 100.0]` | champ | rejet |
| DA2 | Zones ↔ seuils (Phase C) | modèle | rejet |
| DA3 | `contributing_factors` : set de clés exhaustif prédéfini | modèle | rejet |
| DA4 | `history` longueur ≤ 30, triée, dates distinctes | modèle | rejet |
| DA5 | `trend_7d_slope`, `trend_14d_slope` cohérents avec `history` | modèle | coerce |

### 5.12 Invariants CONVO et TECHNICAL

| ID | Prédicat | Niveau | Comportement |
|---|---|---|---|
| T1 | `proactive_messages_last_7d` : timestamps `> now - 7j` | AthleteState | coerce |
| T2 | `len(proactive_messages_last_7d) ≤ PROACTIVE_CAP` (2/semaine par défaut) | AthleteState | soft warn |
| T3 | `connector_status.last_sync_at ≤ now` | modèle | rejet |
| T4 | `last_classified_intent` cohérent avec `last_message_at` | AthleteState | soft warn |

### 5.13 Invariants cross-catégories majeurs

Invariants touchant ≥ 3 catégories. Tests unitaires obligatoires Phase D.

| ID | Invariant | Catégories |
|---|---|---|
| X1 | `recovery_takeover_active == True` → (`active_plan.status == SUSPENDED` ∧ `active_recovery_thread_id is not None` ∧ `∃ r ∈ injuries : r.status == ACTIVE ∧ r.triggered_recovery_takeover == True`) | JOURNEY + PLANS + TECHNICAL + SUB_PROFILES |
| X2 | `journey_phase == onboarding ∨ onboarding_reentry_active == True` → `active_onboarding_thread_id is not None` | JOURNEY + TECHNICAL |
| X3 | `assessment_mode ↔ journey_phase ∈ {baseline_pending_confirmation, baseline_active, followup_transition}` | JOURNEY |
| X4 | `baseline_plan is not None ∧ status ∈ {active, extended}` → `assessment_mode == True` | PLANS + JOURNEY |
| X5 | `active_plan is not None ∧ status == ACTIVE` → `assessment_mode == False` | PLANS + JOURNEY |
| X6 | `coaching_scope[D] == FULL ↔ D ∈ discipline_components.keys() ↔ D ∈ classification.keys() ↔ D ∈ ExperienceProfile.by_discipline.keys()` — enforcé en tout temps, node `ensure_plan_scope_consistency` en sortie de `onboarding` re-entry | SCOPE + PLANS + CLASSIFICATION + SUB_PROFILES |
| X7 | `PersistentOverridePattern.active == True` → `consecutive_days_detected ≥ N` ∧ posé par Recovery Coach ∧ reset autorisé Head Coach uniquement | DERIVED_READINESS + traçabilité |
| X8 | `cycle_active == True` → tous agents avec accès IDENT reçoivent `cycle_phase` cohérent | IDENT + vues agents |
| X9 | `onboarding_reentry_active == True` → au moins un bloc onboarding pré-identifié en cours | JOURNEY + SUB_PROFILES |
| X10 | `active_plan.blocks[*].block_discipline_specs.keys() ⊆ discipline_components.keys()` pour tout bloc FULL | PLANS |

### 5.14 Mécanisme `soft warn`

```python
class ValidationWarningCategory(str, Enum):
    DECLARATIVE_INCONSISTENCY = "declarative_inconsistency"
    DERIVED_STALE = "derived_stale"
    SCOPE_TRANSITION = "scope_transition"
    CLINICAL_SANITY = "clinical_sanity"
    OTHER = "other"

class ValidationWarning(BaseModel):
    invariant_id: str                           # "E3", "CL5", etc.
    category: ValidationWarningCategory
    message: str
    detected_at: datetime
    fields_concerned: list[str]
    # TTL 24h : purgé par coerce sur AthleteState si detected_at < now - 24h
```

Comportement complet :

1. Validator soft warn détecte la violation.
2. `logging.warning()` émis avec contexte.
3. `ValidationWarning` append à `athlete_state.validation_warnings`.
4. Purge automatique des entrées > 24h à chaque mutation de `AthleteState`.
5. Head Coach lit `validation_warnings` et peut surface les incohérences déclaratives au user si pertinent (ex : E3 sur `years_structured` incohérent avec âge).

---

## 6. Tables `knowledge/strain-contributions/`

### 6.1 Organisation du répertoire

```
knowledge/
├── strain-contributions/
│   ├── lifting.json
│   ├── running.json
│   ├── swimming.json
│   ├── biking.json
│   └── _schema.json
├── thresholds.json
├── volume-landmarks/
├── pace-tables/
├── power-zones/
└── ...
```

Un fichier JSON par discipline. `_schema.json` valide structurellement les quatre fichiers au chargement par `StrainComputationService` (fail-fast).

### 6.2 Contrat de chargement

```python
class IntensityBandContribution(BaseModel):
    base_strain_per_unit: float = Field(..., ge=0.0, le=10.0)
    unit: VolumeUnit
    group_multipliers: dict[MuscleGroup, float]
    # Valeurs ∈ [0.0, 1.5], groupes absents = 0.0 implicite
    notes: str | None = None

class SessionTypeContribution(BaseModel):
    description: str
    typical_duration_minutes_range: list[int] = Field(..., min_length=2, max_length=2)
    intensity_bands: dict[str, IntensityBandContribution]

class StrainContributionTable(BaseModel):
    discipline: Discipline
    schema_version: str
    last_reviewed_at: date
    last_reviewed_by: str
    bibliography: list[str]                     # liste vide autorisée B1
    session_types: dict[str, SessionTypeContribution]
    ewma_tau_overrides: dict[MuscleGroup, float] | None = None
    notes: str | None = None
```

### 6.3 Convention des multiplicateurs

```
strain_added[G] = base_strain_per_unit × volume_realized × group_multipliers[G]
```

- `volume_realized` : volume réel loggué (pas prescrit) dans `unit` défini.
- Séances multi-zones : somme des contributions par zone.
- Si `strain_annotation_override` présent dans le log, remplace intégralement le calcul de la table.

**Bornes de sanity :** `strain_added[G]` cumulé par séance plafonné à 40 (enforced côté service, pas dans la table).

### 6.4 Exemples minimaux par discipline

Valeurs indicatives. Valeurs scientifiquement calibrées en Phase C.

**`lifting.json`**

```json
{
  "discipline": "lifting",
  "schema_version": "1.0.0",
  "last_reviewed_at": "2026-04-20",
  "last_reviewed_by": "pending_phase_c_review",
  "bibliography": [],
  "session_types": {
    "hypertrophy_lower": {
      "description": "Séance hypertrophie bas du corps, 8-15 reps, RIR 1-3",
      "typical_duration_minutes_range": [60, 90],
      "intensity_bands": {
        "below_70pct": {
          "base_strain_per_unit": 0.8,
          "unit": "total_working_sets",
          "group_multipliers": {
            "quads": 1.0, "hamstrings": 0.6, "glutes": 0.8,
            "calves": 0.3, "lower_back": 0.4, "core": 0.2
          }
        },
        "70_80pct": {
          "base_strain_per_unit": 1.2,
          "unit": "total_working_sets",
          "group_multipliers": {
            "quads": 1.1, "hamstrings": 0.7, "glutes": 0.9,
            "calves": 0.3, "lower_back": 0.5, "core": 0.2
          }
        }
      }
    },
    "strength_upper": {
      "description": "Séance force haut du corps, 3-6 reps, RPE 7-9",
      "typical_duration_minutes_range": [60, 90],
      "intensity_bands": {
        "80_90pct": {
          "base_strain_per_unit": 1.5,
          "unit": "total_working_sets",
          "group_multipliers": {
            "chest": 1.1, "front_delts": 0.7, "triceps": 0.8,
            "upper_back": 0.9, "lats": 1.0, "biceps": 0.5, "core": 0.3
          }
        },
        "above_90pct": {
          "base_strain_per_unit": 2.0,
          "unit": "total_working_sets",
          "group_multipliers": {
            "chest": 1.2, "front_delts": 0.8, "triceps": 0.9,
            "upper_back": 1.0, "lats": 1.1, "biceps": 0.6, "core": 0.4
          }
        }
      }
    }
  }
}
```

**`running.json`**

```json
{
  "discipline": "running",
  "schema_version": "1.0.0",
  "last_reviewed_at": "2026-04-20",
  "last_reviewed_by": "pending_phase_c_review",
  "bibliography": [],
  "session_types": {
    "easy_long_run": {
      "description": "Course continue Z1-Z2, terrain plat ou modérément vallonné",
      "typical_duration_minutes_range": [40, 150],
      "intensity_bands": {
        "zone_1_2": {
          "base_strain_per_unit": 0.6,
          "unit": "km",
          "group_multipliers": {
            "quads": 0.6, "hamstrings": 0.5, "glutes": 0.5,
            "calves": 0.8, "hip_flexors": 0.4, "core": 0.3, "lower_back": 0.3
          }
        }
      }
    },
    "tempo_threshold": {
      "description": "Course allure seuil, zone 3-4",
      "typical_duration_minutes_range": [30, 60],
      "intensity_bands": {
        "zone_3": {
          "base_strain_per_unit": 1.0,
          "unit": "km",
          "group_multipliers": {
            "quads": 0.8, "hamstrings": 0.7, "glutes": 0.6,
            "calves": 1.0, "hip_flexors": 0.5, "core": 0.4
          }
        },
        "zone_4": {
          "base_strain_per_unit": 1.4,
          "unit": "km",
          "group_multipliers": {
            "quads": 0.9, "hamstrings": 0.8, "glutes": 0.7,
            "calves": 1.1, "hip_flexors": 0.6, "core": 0.5
          }
        }
      }
    },
    "intervals_vo2max": {
      "description": "Intervalles courts haute intensité zone 5",
      "typical_duration_minutes_range": [30, 75],
      "intensity_bands": {
        "zone_5": {
          "base_strain_per_unit": 1.8,
          "unit": "km",
          "group_multipliers": {
            "quads": 1.1, "hamstrings": 1.0, "glutes": 0.9,
            "calves": 1.2, "hip_flexors": 0.8, "core": 0.6
          }
        }
      }
    }
  }
}
```

**`swimming.json`**

```json
{
  "discipline": "swimming",
  "schema_version": "1.0.0",
  "last_reviewed_at": "2026-04-20",
  "last_reviewed_by": "pending_phase_c_review",
  "bibliography": [],
  "session_types": {
    "technique_aerobic": {
      "description": "Technique + endurance aérobie, majorité crawl",
      "typical_duration_minutes_range": [30, 60],
      "intensity_bands": {
        "aerobic": {
          "base_strain_per_unit": 0.002,
          "unit": "meters_swum",
          "group_multipliers": {
            "lats": 1.0, "upper_back": 0.8, "rear_delts": 0.9,
            "side_delts": 0.6, "chest": 0.5, "triceps": 0.7,
            "core": 0.4, "forearms": 0.4
          }
        }
      }
    },
    "css_threshold": {
      "description": "Séance allure critique soutenue",
      "typical_duration_minutes_range": [40, 80],
      "intensity_bands": {
        "threshold": {
          "base_strain_per_unit": 0.003,
          "unit": "meters_swum",
          "group_multipliers": {
            "lats": 1.2, "upper_back": 1.0, "rear_delts": 1.0,
            "side_delts": 0.7, "chest": 0.6, "triceps": 0.9,
            "core": 0.5, "forearms": 0.5
          }
        }
      }
    }
  }
}
```

**`biking.json`**

```json
{
  "discipline": "biking",
  "schema_version": "1.0.0",
  "last_reviewed_at": "2026-04-20",
  "last_reviewed_by": "pending_phase_c_review",
  "bibliography": [],
  "session_types": {
    "endurance_z2": {
      "description": "Sortie endurance zone 2 puissance, terrain varié",
      "typical_duration_minutes_range": [60, 240],
      "intensity_bands": {
        "zone_1_2": {
          "base_strain_per_unit": 0.3,
          "unit": "hours",
          "group_multipliers": {
            "quads": 0.8, "hamstrings": 0.5, "glutes": 0.6,
            "calves": 0.4, "hip_flexors": 0.3, "core": 0.3, "lower_back": 0.3
          }
        }
      }
    },
    "sweet_spot_threshold": {
      "description": "Intervalles sweet spot et seuil FTP",
      "typical_duration_minutes_range": [60, 120],
      "intensity_bands": {
        "zone_3": {
          "base_strain_per_unit": 0.6,
          "unit": "hours",
          "group_multipliers": {
            "quads": 1.0, "hamstrings": 0.7, "glutes": 0.8,
            "calves": 0.4, "core": 0.4, "lower_back": 0.4
          }
        },
        "zone_4_5": {
          "base_strain_per_unit": 1.0,
          "unit": "hours",
          "group_multipliers": {
            "quads": 1.2, "hamstrings": 0.8, "glutes": 0.9,
            "calves": 0.4, "core": 0.5, "lower_back": 0.5
          }
        }
      }
    },
    "vo2_anaerobic_intervals": {
      "description": "Intervalles VO2max et anaérobies courts",
      "typical_duration_minutes_range": [60, 90],
      "intensity_bands": {
        "vo2_anaerobic": {
          "base_strain_per_unit": 1.5,
          "unit": "hours",
          "group_multipliers": {
            "quads": 1.3, "hamstrings": 0.9, "glutes": 1.0,
            "calves": 0.5, "core": 0.6, "lower_back": 0.5
          }
        }
      }
    }
  }
}
```

### 6.5 Chargement et validation au boot

```python
class StrainContributionRegistry:
    """Chargé une fois au boot. Eager, fail-fast."""

    def __init__(self, knowledge_path: Path):
        self._tables: dict[Discipline, StrainContributionTable] = {}

        for discipline in Discipline:
            file_path = knowledge_path / "strain-contributions" / f"{discipline.value}.json"
            raw = json.loads(file_path.read_text())
            self._tables[discipline] = StrainContributionTable(**raw)

        self._validate_coverage()

    def _validate_coverage(self):
        # SC1 — Les 4 disciplines ont leur table
        expected = set(Discipline)
        actual = set(self._tables.keys())
        if expected != actual:
            raise ConfigError(f"Missing strain tables: {expected - actual}")

        # SC2 — schema_version cohérent
        versions = {t.schema_version for t in self._tables.values()}
        if len(versions) > 1:
            raise ConfigError(f"Inconsistent schema versions: {versions}")

    def get(self, discipline: Discipline) -> StrainContributionTable:
        return self._tables[discipline]
```

### 6.6 Invariants de registre

| ID | Prédicat | Niveau |
|---|---|---|
| SC1 | Les 4 disciplines ont leur table chargée | boot |
| SC2 | `schema_version` cohérent entre les 4 tables | boot |
| SC3 | Tout `session_type` référencé par un log ou prescription existe dans la table discipline | service fail-fast |
| SC4 | Tout `MuscleGroup` dans `group_multipliers` appartient aux 18 groupes | modèle |
| SC5 | `base_strain_per_unit.unit ∈ VolumeUnit`, cohérent avec unit prescription et log | modèle |
| SC6 | `group_multipliers` valeurs ∈ [0.0, 1.5] (> 1.0 requiert `notes`) | modèle |
| SC7 | `typical_duration_minutes_range` obligatoire, `[min, max]` ordonné | modèle |
| SC8 | `bibliography` liste vide autorisée B1, validator non-vide active Phase C | modèle |

### 6.7 Mode dégradé si table incomplète

Log avec `session_type` absent de la table :

- **Dev/test** : `StrainComputationService` lève `UnknownSessionTypeError`.
- **Production** : fallback sur `session_type` default par discipline (`"generic_session"`, spec Phase C) avec `group_multipliers` conservatifs moyens. Log WARN, routé vers monitoring ops.

### 6.8 Versioning

`schema_version` sémantique :

- **Major** (`1.x.x → 2.0.0`) : breaking change structure. Migration exigée.
- **Minor** (`1.0.x → 1.1.0`) : ajout `session_types` ou `intensity_bands`. Compatible ascendant.
- **Patch** (`1.0.0 → 1.0.1`) : ajustement valeurs, bibliographie, notes.

Tables versionnées en git sous `knowledge/`. Revue scientifique Phase C et recalibrations → commits dédiés signés.

---

## 7. Constantes et seuils

### 7.1 Seuils cliniques — `knowledge/thresholds.json`

Chargés au boot par les services déterministes. Modifiables Phase C sans release de code.

```json
{
  "readiness": {
    "critical_threshold": 40.0,
    "user_signal_freshness_hours": 18
  },
  "energy_availability": {
    "optimal_min": 45.0,
    "low_normal_min": 30.0,
    "subclinical_min": 20.0,
    "user_signal_freshness_hours": 48
  },
  "allostatic_load": {
    "elevated_threshold": 60.0,
    "alarm_threshold": 80.0,
    "half_life_days": 10.0
  },
  "persistent_override_pattern": {
    "consecutive_days_threshold": 5,
    "min_divergence": 15.0
  },
  "strain": {
    "per_session_cap_per_group": 40.0,
    "default_ewma_tau_days": {
      "quads": 3.0, "hamstrings": 3.0, "glutes": 3.0,
      "calves": 2.0, "hip_flexors": 2.0, "adductors": 2.0, "abductors": 2.0,
      "lower_back": 3.5, "core": 2.0,
      "upper_back": 3.0, "lats": 3.0,
      "chest": 3.0, "front_delts": 2.5, "side_delts": 2.5, "rear_delts": 2.5,
      "biceps": 2.0, "triceps": 2.0, "forearms": 1.5
    }
  }
}
```

Valeurs indicatives B1. Calibration scientifique Phase C.

### 7.2 Constantes module-level

Touchent le comportement logiciel, pas les seuils cliniques.

```python
# Cap pro-activité Head Coach
PROACTIVE_CAP = 2  # messages/semaine

# Seuil de confidence pour marquage unknown dans classification
CONFIDENCE_UNKNOWN_THRESHOLD = 0.4

# TTL des ValidationWarning
VALIDATION_WARNING_TTL_HOURS = 24

# Fenêtre sliding du compteur proactif
PROACTIVE_WINDOW_DAYS = 7
```

---

## 8. Résumé des décisions structurantes B1

### Décisions confirmées pendant la session

1. **Nesting vs DB** : profils, plans, index dérivés, journey, technical = attributs Pydantic directs de `AthleteState`. Logs + messages = tables DB séparées, injectés dans les `_AGENT_VIEWS` (spec B2).
2. **Muscle groups** : 18 groupes, traps rattachés à `upper_back`, pas de 19e groupe.
3. **Strain history** : 21 jours glissants.
4. **Freshness** : Readiness 18h, EA 48h.
5. **`user_readiness_signal.score`** : continu 0–100.
6. **`cycle_phase`** : enum 8 valeurs (4 phases + 4 cas atypiques/unknown), `cycle_day` et `cycle_length_days` annexes optionnels.
7. **`baseline_plan` et `active_plan`** : deux objets distincts persistés en parallèle. Pas de confusion possible.
8. **`baseline_observations` / `baseline_metrics`** : non persistés. Calculés à la volée par `followup_transition`, spec B3.
9. **`ObjectiveProfile.secondary`** : plafond 3.
10. **Matrice contradictions objectifs** : stub en B1, remplie Phase C.
11. **`movements_mastered`** : `list[str]` en B1, enums par discipline Phase C.
12. **Ajout `GeographicContext`** dans `PracticalConstraints`.
13. **`BodyRegion`** : 23 régions, suffisant.
14. **`DisciplineRoleInPlan`** : 5 valeurs, `CO_PRIMARY` ajouté pour objectifs hybrides équilibrés.
15. **Transition de bloc** : Option B — `at_most_one_current`, champ dérivé `is_between_blocks`.
16. **Contrainte scope-plan** : enforcée en tout temps (invariant X6 strict), node `ensure_plan_scope_consistency` en sortie de `onboarding` re-entry.
17. **`confidence_levels`** : par `(discipline, dimension)`.
18. **Seuils** : cliniques → `knowledge/thresholds.json`, structurels → constantes module-level.
19. **`soft warn`** : `logging.warning()` + champ `validation_warnings` avec TTL 24h.
20. **`base_strain_per_unit`** : scalaire simple, modulation contextuelle côté service.
21. **Taxonomie `session_types`** : schéma figé B1, valeurs remplies Phase C.
22. **`typical_duration_minutes_range`** : obligatoire.
23. **Chargement tables** : eager au boot, fail-fast.
24. **`bibliography`** : obligatoire, liste vide autorisée B1, non-vide requis à partir Phase C.

### Points reportés à phases ultérieures

- **Phase B2** : spec exhaustive des 9 `_AGENT_VIEWS` Pydantic.
- **Phase B3** : contrats de sortie structurés des agents (`Recommendation`, `NutritionVerdict`, `RecoveryAssessment`, `EnergyAssessment`, `FollowupQuestionSet`, `PrescribedSession`).
- **Phase C** : valeurs numériques des seuils cliniques, matrice non-contradiction objectifs, matrice cohérence PR unité/movement, taxonomies exhaustives `session_types` et `movements_mastered` par discipline, tables VDOT/FTP/CSS/%1RM, revue bibliographique des tables de contribution.
- **Phase D** : implémentation, delta vs backend existant, réconciliation Claude Code.

---

*Document validé B1. Prochaine session : B2 — spec des 9 `_AGENT_VIEWS` Pydantic par agent, en cohérence avec les matrices du roster A3 et les schémas spécifiés ici.*
