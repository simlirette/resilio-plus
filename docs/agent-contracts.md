# `agent-contracts.md` — Spec des contrats de sortie structurés des agents LLM

> **Version 1 (livrable B3).** Spécification exhaustive et implémentable des 8 contrats de sortie structurés des agents LLM du système Resilio+, plus le bloc de construction central `PrescribedSession`. Référence pour Phase C (prompts système par agent) et Phase D (implémentation backend). Dérivé de `user-flow-complete.md` v4, `agent-flow-langgraph.md` v1, `agent-roster.md` v1, `schema-core.md` v1, `agent-views.md` v1. Cible la version finale du produit, pas une livraison V1 intermédiaire.

## 1. Objet et périmètre

Ce document formalise :

1. Les **principes transversaux** applicables à tous les contrats : structure commune `ContractMetadata`, versioning, idempotence, traçabilité, flags inter-agents typés, synthèse multi-flags.
2. Le **bloc de construction central** `PrescribedSession` (et son draft LLM), réutilisé par `Recommendation.sessions[]`.
3. Les **8 contrats B3** complets : `Recommendation`, `NutritionVerdict`, `RecoveryAssessment`, `EnergyAssessment`, `FollowupQuestionSet`, `LogisticAdjustment`, `OverrideFlagReset`, plus les règles de synthèse multi-flags du Head Coach.
4. Les **règles de propagation inter-agents** : `flag_for_head_coach`, `flag_for_recovery_coach`, `pass_to_energy_coach`, escalades Nutrition → Energy, Energy → Recovery.
5. Le **traitement des contrats fall-through** (annulation par overlay, supersedure, deferral).
6. Les **invariants transversaux cross-contrats** (43 invariants formalisés).

Ne décrit pas : les prompts système par agent (Phase C), les valeurs numériques de seuils cliniques et calibrations (Phase C), le code d'implémentation (Phase D).

---

## 2. Principes architecturaux transversaux

### 2.1 Cohérence avec les décisions antérieures

Les décisions B1 et B2 ne sont pas rouvertes. Les contrats B3 respectent strictement :

- **Agents LLM produisent du structuré, nodes et services persistent** (B1, B2 §2.1). Chaque contrat B3 est consommé par un node dédié ; les mutations sur `AthleteState` passent par ces nodes ou par les 4 services déterministes.
- **Services déterministes pour les index dérivés** (B1 §3). Aucun contrat B3 n'écrit `strain_state`, les triplets `objective_*`, `allostatic_load_state`.
- **Architecture à trois champs pour Readiness et EA** (B1 §3.2-3.3). `effective_*` calculé à la volée, non persisté.
- **Recovery Coach propriétaire de l'overlay `recovery_takeover_active`** (roster A3). `RecoveryAssessment` est le contrat de consultation ; en takeover, pas de contrat mais messages directs.
- **Hiérarchie d'arbitrage clinique** : Recovery > Energy > Nutrition > coachs disciplines (roster A3). Matérialisée dans les règles de dispatch et la priorisation des flags.
- **9 vues spec en B2** avec isolation par discipline pour les 4 coachs disciplines. Chaque contrat référence la vue qui l'a produit via `metadata.invocation_trigger` et `view_built_at`.
- **Outputs des spokes ne sont JAMAIS dans les vues des autres agents** (B2 §2.1). Les contrats B3 transitent via input distinct du prompt LLM (notamment pour le Head Coach en synthèse multi-flags).

### 2.2 `ContractMetadata` — composition, pas héritage

Chaque contrat inclut à plat un sous-modèle `ContractMetadata` commun. Pas d'héritage Pydantic (incompatible avec les discriminated unions). Composition stricte.

```python
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, model_validator

from resilio.schema.views import AgentId, InvocationTrigger


class ContractMetadata(BaseModel):
    """Métadonnées communes à tous les contrats B3."""
    contract_id: str = Field(..., description="UUID v4, stable pour idempotence")
    schema_version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    emitted_by: AgentId
    emitted_at: datetime
    invocation_trigger: InvocationTrigger
    view_built_at: datetime
    correlation_id: str | None = None
    thread_id: str | None = None
```

**Invariants universels sur `ContractMetadata`** :

| ID | Prédicat |
|---|---|
| CM1 | `emitted_at >= view_built_at`. Un contrat ne peut pas référencer un snapshot futur |
| CM2 | `(emitted_by, invocation_trigger)` ∈ table `ADMISSIBLE_EMISSIONS` (reprend la table §8.1 de `agent-views.md`) |

### 2.3 Versioning

`schema_version` indépendant pour chaque classe de contrat. Sémantique stricte :

- **Major** (`1.x.x → 2.0.0`) : breaking change (suppression, renommage, resserrement de type). Node consommateur refuse major incompatible → exception `ContractSchemaMismatchError`, contrat routé vers dead-letter.
- **Minor** (`1.0.x → 1.1.0`) : ajout de champ optionnel. Compatible ascendant.
- **Patch** (`1.0.0 → 1.0.1`) : clarifications de docstring, ajustement de `description`.

Les nodes consommateurs déclarent `SUPPORTED_VERSIONS: set[str]` explicite. Phase D implémente, Phase C aligne entre prompts et code.

### 2.4 Idempotence

Un contrat ré-émis (retry réseau, relance LangGraph après checkpoint) ne produit zéro mutation supplémentaire. Trois couches.

**Couche 1. `contract_id` stable**. Table `processed_contracts (contract_id PK, consumer_node, processed_at, outcome, outcome_detail)`. Retry avec même `contract_id` → short-circuit, renvoie `outcome` mémorisé.

**Couche 2. Mutations naturellement idempotentes côté node**. `persist_prescribed_sessions` fait un upsert sur `(plan_id, block_id, day_slot, discipline, session_type)`. `persist_nutrition_targets` fait un upsert sur `(athlete_id, target_date)`. `activate_clinical_frame` vérifie `recovery_takeover_active == False` avant set.

**Couche 3. Pas d'effets de bord externes dans les nodes de persistance**. Notifications push, logs d'audit consommateur, escalades inter-agents sont déclenchés par le Coordinator **après** confirmation de mutations réelles, pas en short-circuit idempotent.

### 2.5 Traçabilité forensique

Table DB `contract_emissions` dédiée :

| Colonne | Rôle |
|---|---|
| `contract_id` | PK, FK vers `processed_contracts` |
| `contract_type` | Nom de classe (`Recommendation`, `NutritionVerdict`, …) |
| `metadata` | `ContractMetadata` sérialisé JSON |
| `payload_json` | Contrat complet sérialisé |
| `view_snapshot_hash` | Hash SHA-256 du snapshot de la vue consommée |
| `prompt_ref` | Référence vers version de prompt (Phase C) |
| `created_at` | |

Coût : deux écritures DB par invocation LLM structurée. Bénéfice : reproductibilité complète, audit clinique.

### 2.6 Flags inter-agents typés

Les champs `flag_for_head_coach`, `flag_for_recovery_coach`, `pass_to_energy_coach` sont des objets structurés, pas des strings.

```python
class FlagCode(str, Enum):
    # Charge et récupération
    HIGH_STRAIN_ACCUMULATED = "high_strain_accumulated"
    DELOAD_SUGGESTED = "deload_suggested"
    HRV_DEGRADED = "hrv_degraded"
    SLEEP_DEBT = "sleep_debt"
    OVERRIDE_PATTERN_DETECTED = "override_pattern_detected"
    # Compliance
    COMPLIANCE_DROP = "compliance_drop"
    RPE_SYSTEMATIC_OVERSHOOT = "rpe_systematic_overshoot"
    # Énergie
    EA_LOW_NORMAL_TRENDING_DOWN = "ea_low_normal_trending_down"
    EA_SUBCLINICAL = "ea_subclinical"
    RED_S_SUSPECTED = "red_s_suspected"
    # Cliniques
    INJURY_SUSPECTED = "injury_suspected"
    CLINICAL_ESCALATION_REQUIRED = "clinical_escalation_required"
    # Logistique et intent
    SCHEDULE_CONFLICT_DETECTED = "schedule_conflict_detected"
    OBJECTIVE_CONTRADICTION = "objective_contradiction"


class FlagSeverity(str, Enum):
    INFO = "info"
    WATCH = "watch"
    CONCERN = "concern"
    CRITICAL = "critical"


class HeadCoachFlag(BaseModel):
    code: FlagCode
    severity: FlagSeverity
    message: str = Field(..., max_length=300)
    structured_payload: dict | None = None


class RecoveryCoachFlag(BaseModel):
    code: FlagCode
    severity: FlagSeverity
    clinical_signals: dict
    urgency: Literal["next_report", "proactive_24h", "immediate_takeover"]

    @model_validator(mode="after")
    def _code_restricted(self):
        admissible = {
            FlagCode.HRV_DEGRADED, FlagCode.SLEEP_DEBT,
            FlagCode.INJURY_SUSPECTED, FlagCode.OVERRIDE_PATTERN_DETECTED,
            FlagCode.CLINICAL_ESCALATION_REQUIRED,
        }
        if self.code not in admissible:
            raise ValueError(f"RecoveryCoachFlag.code must be in {admissible}")
        return self
```

Chaque contrat restreint le sous-ensemble de `FlagCode` admissible selon le périmètre de son émetteur (voir sections par contrat).

### 2.7 Synthèse multi-flags : Head Coach exécute, Coordinator agrège

Cohérent A3 roster §Rapport hebdomadaire. Le Coordinator agrège et route les flags vers le Head Coach via `AggregatedFlagsPayload` en input distinct du prompt (§6). Le Head Coach exécute la règle `< 3 flags` vs `≥ 3 flags` dans son prompt système (Phase C). Aucun contrat B3 pour la synthèse elle-même — la sortie est un message conversationnel direct.

### 2.8 Fall-through : persistance, pas drop silencieux

Un contrat émis puis rendu obsolète par overlay ou state change entre émission et consommation est **persisté avec statut explicite**, pas abandonné.

```python
class ContractProcessingOutcome(str, Enum):
    APPLIED = "applied"
    IDEMPOTENT_NOOP = "idempotent_noop"
    SUPERSEDED_BY_OVERLAY = "superseded_by_overlay"
    SUPERSEDED_BY_NEWER = "superseded_by_newer"
    SUPERSEDED_BY_STATE_CHANGE = "superseded_by_state_change"
    REJECTED_VALIDATION = "rejected_validation"
    REJECTED_SCHEMA_VERSION = "rejected_schema_version"
    DEFERRED_WAITING_PRECONDITION = "deferred_waiting_precondition"
```

Traitement unifié : §7.

### 2.9 Hiérarchie d'arbitrage clinique : enforcement au niveau node

Hiérarchie **Recovery > Energy > Nutrition > disciplines** portée par l'**ordre d'exécution des nodes** dans `build_proposed_plan`, pas par les contrats. Les contrats ne connaissent pas leur priorité. Séquence dans `build_proposed_plan` :

1. Lecture `RecoveryAssessment` → si `action ∈ {suspend, escalate_to_takeover}`, drop tous les autres contrats discipline en `SUPERSEDED_BY_OVERLAY`.
2. Lecture `EnergyAssessment` → si `clinical_escalation.required == True` ou `ea_status == CLINICAL_RED_S`, annoter les `Recommendation` discipline avec contraintes de modulation (pas de drop).
3. Lecture `NutritionVerdict` → idem si `status == escalate_to_energy_coach` (escalade déjà traitée en amont).
4. Merge des `Recommendation` discipline → `detect_conflicts` → `resolve_conflicts` selon `ObjectiveProfile.primary`.

### 2.10 Cohérence vue ↔ contrat

Invariants universels :

| ID | Prédicat |
|---|---|
| CG1 | Pour tout contrat émis avec trigger `T` et émetteur `A`, la vue consommée est celle spécifiée en `agent-views.md` §8.1 pour `(A, T)` |
| CG2 | Les champs disciplinaires du contrat sont cohérents avec `target_discipline` de la vue (ex : `Recommendation.discipline == view.target_discipline`) |
| CG3 | `metadata.view_built_at` précède `metadata.emitted_at` |

---

## 3. `PrescribedSession` — bloc de construction central

### 3.1 Arbitrage : discriminated union par discipline

Décision : **discriminated union par discipline** avec base commune `PrescribedSessionCommon`. Motivations : typage strict, LLM structured output optimal, validators par discipline, cohérence avec B1 §4.4 (`BlockDisciplineSpec` déjà paramétré par discipline).

Inconvénient accepté : 4 sous-classes + 1 base. La verbosité est compensée par la sûreté de typage.

### 3.2 Base commune `PrescribedSessionCommon`

```python
from resilio.schema.core import Discipline, VolumeTarget, MuscleGroup


class PrescribedSessionStatus(str, Enum):
    UPCOMING = "upcoming"
    COMPLETED = "completed"
    MISSED = "missed"
    MODIFIED = "modified"
    SKIPPED = "skipped"


class PlanLinkType(str, Enum):
    ACTIVE = "active"
    BASELINE = "baseline"


class SessionModification(BaseModel):
    modified_at: datetime
    modified_by: Literal[
        "head_coach_logistic_adjustment",
        "discipline_coach_block_regen",
        "user_direct_edit",
        "recovery_coach_suspension",
    ]
    change_summary: str = Field(..., max_length=200)
    previous_values_hash: str


class StrainAnnotationOverride(BaseModel):
    """Override des tables knowledge/strain-contributions/ pour cette séance."""
    rationale: str = Field(..., max_length=200)
    group_multiplier_overrides: dict[MuscleGroup, float] = Field(default_factory=dict)
    base_strain_multiplier: float | None = Field(None, ge=0.0, le=2.5)


class PrescribedSessionCommon(BaseModel):
    """Champs partagés, non concrète. Sous-classes disciplinaires héritent et étendent."""

    session_id: str = Field(..., description="UUID v4, stable sur durée de vie")

    # Liens plan (FK externes)
    plan_link_type: PlanLinkType
    plan_id: str
    block_id: str | None = None

    # Planification
    scheduled_date: date | None = None
    day_slot: int | None = Field(None, ge=1, le=14)
    sequence_in_week: int | None = Field(None, ge=1, le=14)

    # Volume et charge
    planned_duration_minutes: int = Field(..., ge=5, le=360)
    target_rpe: float | None = Field(None, ge=1.0, le=10.0)

    strain_annotation_override: StrainAnnotationOverride | None = None

    # Contexte
    rationale: str = Field(..., max_length=500)
    block_theme_context: str | None = Field(None, max_length=150)
    contraindications_respected: list[str] = Field(default_factory=list, max_length=10)

    # Cycle de vie
    status: PrescribedSessionStatus = PrescribedSessionStatus.UPCOMING
    logged_session_id: str | None = None
    modification_history: list[SessionModification] = Field(default_factory=list)

    # Overrides logistiques (posés par LogisticAdjustment §9)
    preferred_time_of_day_override: Literal[
        "early_morning", "morning", "midday",
        "afternoon", "evening", "night",
    ] | None = None
    location_context_override: Literal[
        "commercial_gym", "home", "outdoor",
        "track", "pool_indoor", "pool_outdoor", "open_water", "mixed",
    ] | None = None

    # Métadonnées
    created_at: datetime
    last_modified_at: datetime
    created_by_coach: Discipline
```

### 3.3 Sous-classes disciplinaires

Les structures disciplinaires capturent la spécificité de prescription par modalité. Taxonomies exhaustives (`session_type`, exercise names, zones) sont stabilisées Phase C.

```python
# ─── LIFTING ──────────────────────────────────────────────────────────────

class LiftingIntensitySpec(BaseModel):
    percent_1rm: float | None = Field(None, ge=20.0, le=105.0)
    target_rpe: float | None = Field(None, ge=1.0, le=10.0)
    target_rir: int | None = Field(None, ge=0, le=10)

    @model_validator(mode="after")
    def _at_least_one(self):
        if not any([self.percent_1rm, self.target_rpe is not None, self.target_rir is not None]):
            raise ValueError("Au moins une métrique d'intensité")
        return self


class PrescribedExercise(BaseModel):
    exercise_name: str
    primary_muscle_groups: list[MuscleGroup] = Field(..., min_length=1)
    sets: int = Field(..., ge=1, le=20)
    reps_prescribed: int | str
    intensity: LiftingIntensitySpec
    tempo: str | None = Field(None, pattern=r"^\d[\dX]\d[\dX]$")
    rest_seconds: int = Field(..., ge=0, le=600)
    notes: str | None = Field(None, max_length=150)


class PrescribedLiftingSession(PrescribedSessionCommon):
    discipline: Literal[Discipline.LIFTING] = Discipline.LIFTING
    session_type: str
    exercises: list[PrescribedExercise] = Field(..., min_length=1, max_length=15)
    estimated_total_tonnage_kg: float | None = None
    estimated_total_working_sets: int | None = None


# ─── RUNNING ──────────────────────────────────────────────────────────────

class RunningZone(str, Enum):
    Z1_EASY = "z1_easy"
    Z2_AEROBIC = "z2_aerobic"
    Z3_TEMPO = "z3_tempo"
    Z4_THRESHOLD = "z4_threshold"
    Z5_VO2MAX = "z5_vo2max"
    Z5B_ANAEROBIC = "z5b_anaerobic"


class PaceTarget(BaseModel):
    pace_seconds_per_km_min: int
    pace_seconds_per_km_max: int
    derivation: Literal["vdot", "lactate_threshold", "hr_only", "rpe_only"]

    @model_validator(mode="after")
    def _ordered(self):
        if self.pace_seconds_per_km_min > self.pace_seconds_per_km_max:
            raise ValueError("pace min ≤ pace max")
        return self


class PrescribedInterval(BaseModel):
    repetitions: int = Field(..., ge=1, le=50)
    distance_m: int | None = Field(None, gt=0)
    duration_seconds: int | None = Field(None, gt=0)
    zone: RunningZone
    pace_target: PaceTarget | None = None
    hr_zone_bpm_range: tuple[int, int] | None = None
    recovery_type: Literal["jog", "walk", "standing", "active"]
    recovery_duration_seconds: int = Field(..., ge=0, le=900)

    @model_validator(mode="after")
    def _distance_xor_duration(self):
        if (self.distance_m is None) == (self.duration_seconds is None):
            raise ValueError("Exactement un parmi distance_m et duration_seconds")
        return self


class PrescribedRunningSession(PrescribedSessionCommon):
    discipline: Literal[Discipline.RUNNING] = Discipline.RUNNING
    session_type: str
    warmup: list[PrescribedInterval] = Field(default_factory=list)
    main_set: list[PrescribedInterval] = Field(..., min_length=1)
    cooldown: list[PrescribedInterval] = Field(default_factory=list)
    total_distance_km_estimate: float | None = None
    terrain: Literal["flat", "rolling", "hilly", "track", "treadmill", "mixed"] | None = None


# ─── SWIMMING ─────────────────────────────────────────────────────────────

class SwimStroke(str, Enum):
    FREESTYLE = "freestyle"
    BACKSTROKE = "backstroke"
    BREASTSTROKE = "breaststroke"
    BUTTERFLY = "butterfly"
    CHOICE = "choice"
    DRILL = "drill"


class SwimPaceTarget(BaseModel):
    seconds_per_100m_min: int
    seconds_per_100m_max: int
    derivation: Literal["css", "rpe_only"]


class PrescribedSwimSet(BaseModel):
    repetitions: int = Field(..., ge=1, le=50)
    distance_m: int = Field(..., gt=0)
    stroke: SwimStroke
    pace_target: SwimPaceTarget | None = None
    rest_seconds: int = Field(..., ge=0, le=300)
    equipment: list[Literal["fins", "paddles", "pull_buoy", "snorkel", "kickboard"]] = Field(
        default_factory=list
    )
    focus: str | None = Field(None, max_length=150)


class PrescribedSwimmingSession(PrescribedSessionCommon):
    discipline: Literal[Discipline.SWIMMING] = Discipline.SWIMMING
    session_type: str
    warmup: list[PrescribedSwimSet] = Field(default_factory=list)
    main_set: list[PrescribedSwimSet] = Field(..., min_length=1)
    cooldown: list[PrescribedSwimSet] = Field(default_factory=list)
    total_distance_m_estimate: int | None = None
    pool_length_m: Literal[25, 33, 50] | None = None
    environment: Literal["pool_indoor", "pool_outdoor", "open_water"] | None = None


# ─── BIKING ───────────────────────────────────────────────────────────────

class PowerZone(str, Enum):
    Z1_ACTIVE_RECOVERY = "z1"
    Z2_ENDURANCE = "z2"
    Z3_TEMPO = "z3"
    Z4_LT = "z4"
    Z5_VO2MAX = "z5"
    Z6_ANAEROBIC = "z6"
    Z7_NEUROMUSCULAR = "z7"


class PowerTarget(BaseModel):
    percent_ftp_min: float = Field(..., ge=30.0, le=200.0)
    percent_ftp_max: float = Field(..., ge=30.0, le=200.0)
    zone: PowerZone

    @model_validator(mode="after")
    def _ordered(self):
        if self.percent_ftp_min > self.percent_ftp_max:
            raise ValueError("percent_ftp_min ≤ percent_ftp_max")
        return self


class PrescribedPowerInterval(BaseModel):
    repetitions: int = Field(..., ge=1, le=50)
    duration_seconds: int = Field(..., gt=0)
    power_target: PowerTarget
    cadence_target_rpm: tuple[int, int] | None = None
    recovery_duration_seconds: int = Field(..., ge=0, le=900)
    recovery_power_percent_ftp: float | None = Field(None, ge=0.0, le=100.0)


class PrescribedBikingSession(PrescribedSessionCommon):
    discipline: Literal[Discipline.BIKING] = Discipline.BIKING
    session_type: str
    warmup: list[PrescribedPowerInterval] = Field(default_factory=list)
    main_set: list[PrescribedPowerInterval] = Field(..., min_length=1)
    cooldown: list[PrescribedPowerInterval] = Field(default_factory=list)
    total_tss_estimate: float | None = None
    environment: Literal["indoor_trainer", "outdoor_road", "outdoor_gravel", "outdoor_mtb"] | None = None


# ─── Discriminated Union ──────────────────────────────────────────────────

PrescribedSession = Annotated[
    PrescribedLiftingSession
    | PrescribedRunningSession
    | PrescribedSwimmingSession
    | PrescribedBikingSession,
    Field(discriminator="discipline"),
]
```

### 3.4 `PrescribedSessionDraft` — sortie LLM

Les coachs disciplines émettent un `PrescribedSessionDraft` (session_id, timestamps, status absents), hydraté en `PrescribedSession` par `persist_prescribed_sessions`. Split explicite : agents produisent du structuré, nodes persistent.

```python
class PrescribedSessionDraft(BaseModel):
    """Payload LLM. Même structure que PrescribedSession mais :
    - session_id absent
    - status absent (défaut UPCOMING)
    - created_at / last_modified_at absents
    - logged_session_id / modification_history absents
    - discriminated union également par discipline (4 variantes draft)"""
    # Structure identique aux sous-classes PrescribedLifting/Running/Swimming/Biking
    # sans les champs techniques. Implémentation Phase D par factory depuis la classe hydratée.
```

### 3.5 Invariants `PrescribedSession`

| ID | Prédicat | Niveau |
|---|---|---|
| PS1 | `discipline == created_by_coach` | modèle |
| PS2 | `plan_link_type == BASELINE ⇒ block_id is None` | modèle |
| PS3 | `plan_link_type == ACTIVE ⇒ block_id is not None` | modèle |
| PS4 | Exactement un parmi `scheduled_date` et `day_slot` | modèle |
| PS5 | `status ∈ {COMPLETED, MODIFIED} ⇒ logged_session_id IS NOT NULL` | modèle |
| PS6 | `logged_session_id IS NOT NULL ⇒ status ∈ {COMPLETED, MODIFIED}` | modèle |
| PS7 | `modification_history` ordonné chronologiquement | modèle |
| PS8 | `contraindications_respected` ⊆ injury_ids actifs à la prescription | node |
| PS9 | `plan_id` référence un plan existant non completed/superseded | node |
| PS10 | `block_id` si présent référence un `PlanBlock.id` appartenant à `plan_id` | node |
| PS11 | Somme `exercises[].sets` (Lifting) ≤ plafond hebdo selon `BlockDisciplineSpec` | node, non-bloquant |
| PS12 | Running/Biking/Swimming : `main_set` non vide (garanti par `min_length=1`) | modèle |
| PS13 | `strain_annotation_override.group_multiplier_overrides` clés ⊆ 18 `MuscleGroup` | modèle, hérite SC4 B1 |
| PS14 | `scheduled_date`, si présent, ∈ `[plan.start_date, plan.end_date]` | node |

### 3.6 Persistance et table DB

Table `prescribed_sessions` externe à `AthleteState`.

- PK : `session_id`.
- Index : `(plan_id, block_id, scheduled_date)`, `(athlete_id, status)` via jointure plan.
- Colonne `payload_json` : sérialisation Pydantic complète. Colonnes dénormalisées : `discipline`, `status`, `plan_id`, `block_id`, `scheduled_date`, `source_contract_id`.
- Nodes de mutation : `persist_prescribed_sessions` (insertion initiale), `update_session_status` (post-log), `apply_logistic_adjustment` (modification logistique), `mark_session_superseded` (block_regen ou suspension).

### 3.7 Cycle de vie des sessions

```
UPCOMING ──(log entré)──▶ COMPLETED  ou  MODIFIED
UPCOMING ──(date passée sans log)──▶ MISSED
UPCOMING ──(user skip explicite)──▶ SKIPPED
UPCOMING ──(block_regen ou suspension)──▶ MODIFIED (modification_history)
```

Transitions inverses interdites sauf correction admin explicite (hors B3).

---

## 4. Contrats B3 — catalogue

Les sections suivantes spécifient les 7 contrats individuels et le bloc synthèse multi-flags. Chaque spec inclut : émetteur, triggers, classe Pydantic complète avec validators, invariants vue ↔ contrat (niveau node), mécanique de dispatch, règles de propagation, fall-through spécifique.

### 4.1 Table des contrats et consommateurs

| Contrat | Émetteur | Triggers | Nodes consommateurs |
|---|---|---|---|
| `Recommendation` | Coachs disciplines | `PLAN_GEN_DELEGATE_SPECIALISTS`, `CHAT_WEEKLY_REPORT` | `build_proposed_plan` (planning), agrégation flags (review) |
| `NutritionVerdict` | Nutrition Coach | `CHAT_DAILY_CHECKIN`, `CHAT_WEEKLY_REPORT`, `PLAN_GEN_DELEGATE_SPECIALISTS` | `persist_nutrition_targets` |
| `RecoveryAssessment` | Recovery Coach (consultation) | `CHAT_INJURY_REPORT`, `CHAT_WEEKLY_REPORT`, `MONITORING_HRV`, `MONITORING_SLEEP` | `dispatch_recovery_assessment` → `flag_override_pattern` / `apply_recovery_deload` / `suspend_active_plan` / `activate_clinical_frame` |
| `EnergyAssessment` | Energy Coach | `PLAN_GEN_DELEGATE_SPECIALISTS`, `CHAT_WEEKLY_REPORT`, `MONITORING_EA`, `ESCALATION_NUTRITION_TO_ENERGY` | `dispatch_energy_assessment` → `persist_energy_plan_component`, flags Head Coach / Recovery |
| `FollowupQuestionSet` | Onboarding Coach (consultation Phase 5) | `FOLLOWUP_CONSULT_ONBOARDING` | `consume_followup_set` → `head_coach_ask_question` → `update_profile_deltas` |
| `LogisticAdjustment` | Head Coach | `CHAT_ADJUSTMENT_REQUEST` (niveau logistique uniquement) | `apply_logistic_adjustment` |
| `OverrideFlagReset` | Head Coach | `CHAT_FREE_QUESTION`, `CHAT_WEEKLY_REPORT`, `CHAT_DAILY_CHECKIN` | `reset_override_flag` |

Pas de contrat structuré pour les messages conversationnels directs du Head Coach ni pour les messages takeover du Recovery Coach (unique exception aux principes §2.1).

---

## 5. `Recommendation` (coachs disciplines)

### 5.1 Émetteurs et modes

Émis par les 4 coachs disciplines (Lifting, Running, Swimming, Biking) sous deux modes discriminés.

| Trigger | Mode | Sessions prescrites | Contenu |
|---|---|---|---|
| `PLAN_GEN_DELEGATE_SPECIALISTS` | `planning` | Oui, hydratées par `persist_prescribed_sessions` | Prescription forward-looking pour baseline / first_personalized / block_regen |
| `CHAT_WEEKLY_REPORT` | `review` | Non | Synthèse analytique rétrospective de la semaine, flags, propositions pour la semaine suivante |

Un seul contrat avec discriminateur `recommendation_mode`. Partage 70 % des champs entre modes ; deux classes distinctes seraient redondantes.

### 5.2 Classe Pydantic

```python
from resilio.schema.core import Discipline, VolumeTarget

class RecommendationMode(str, Enum):
    PLANNING = "planning"
    REVIEW = "review"


class BlockThemePrimary(str, Enum):
    BASE_AEROBIC = "base_aerobic"
    ACCUMULATION = "accumulation"
    INTENSIFICATION = "intensification"
    PEAKING = "peaking"
    TAPER = "taper"
    DELOAD = "deload"
    TRANSITION = "transition"
    TECHNIQUE_FOCUS = "technique_focus"
    STRENGTH_EMPHASIS = "strength_emphasis"
    HYPERTROPHY_EMPHASIS = "hypertrophy_emphasis"
    MAINTENANCE = "maintenance"


class BlockThemeDescriptor(BaseModel):
    """Thème typé structurellement + modificateurs."""
    primary: BlockThemePrimary
    modifiers: list[Literal[
        "low_volume", "high_volume", "low_intensity", "high_intensity",
        "cycle_phase_adjusted", "cross_training_bias",
    ]] = Field(default_factory=list, max_length=3)
    narrative: str = Field(..., max_length=150)


class VolumeTargetSummary(BaseModel):
    weekly_volume: VolumeTarget
    intensity_split_pct: dict[str, float]
    estimated_weekly_strain_aggregate: float = Field(..., ge=0.0, le=100.0)


class BlockAnalysis(BaseModel):
    """Section rétrospective, mode REVIEW uniquement."""
    compliance_rate: float = Field(..., ge=0.0, le=1.0)
    sessions_completed: int = Field(..., ge=0)
    sessions_missed: int = Field(..., ge=0)
    sessions_modified: int = Field(..., ge=0)

    observed_vs_prescribed_delta_pct: dict[Literal[
        "volume", "intensity_avg", "rpe_avg",
    ], float]

    key_observations: list[str] = Field(..., min_length=1, max_length=5)
    next_week_proposal: VolumeTargetSummary | None = None


class RecommendationTradeOff(BaseModel):
    """Candidat pour active_plan.trade_offs_disclosed après acceptation par resolve_conflicts."""
    sacrificed_element: str = Field(..., max_length=100)
    protected_element: str = Field(..., max_length=100)
    rationale: str = Field(..., max_length=300)
    magnitude: Literal["minor", "moderate", "significant"]
    requires_user_acknowledgment: bool = False


DISCIPLINE_ADMISSIBLE_FLAGS: set[FlagCode] = {
    FlagCode.HIGH_STRAIN_ACCUMULATED,
    FlagCode.DELOAD_SUGGESTED,
    FlagCode.COMPLIANCE_DROP,
    FlagCode.RPE_SYSTEMATIC_OVERSHOOT,
    FlagCode.SCHEDULE_CONFLICT_DETECTED,
    FlagCode.OBJECTIVE_CONTRADICTION,
    FlagCode.INJURY_SUSPECTED,
}


class Recommendation(BaseModel):
    """Contrat B3 émis par un coach discipline en planning ou review."""

    metadata: ContractMetadata

    recommendation_mode: RecommendationMode
    discipline: Discipline

    # Planning fields
    generation_mode: Literal["baseline", "first_personalized", "block_regen"] | None = None
    block_theme: BlockThemeDescriptor | None = None
    sessions: list[PrescribedSessionDraft] = Field(default_factory=list, max_length=14)
    weekly_volume_target: VolumeTarget | None = None
    weekly_intensity_distribution: dict[str, float] | None = None
    projected_strain_contribution: dict[str, float] | None = None

    # Review field
    block_analysis: BlockAnalysis | None = None

    # Planning only
    proposed_trade_offs: list[RecommendationTradeOff] = Field(default_factory=list, max_length=5)

    # Communication
    notes_for_head_coach: str | None = Field(None, max_length=500)
    flag_for_head_coach: HeadCoachFlag | None = None

    # ─── Validators ───────────────────────────────────────────────────────

    @model_validator(mode="after")
    def _validate_mode_fields(self):
        """REC1 — champs conditionnels par recommendation_mode."""
        if self.recommendation_mode == RecommendationMode.PLANNING:
            missing = []
            if not self.sessions:
                missing.append("sessions")
            if self.block_theme is None:
                missing.append("block_theme")
            if self.generation_mode is None:
                missing.append("generation_mode")
            if self.weekly_volume_target is None:
                missing.append("weekly_volume_target")
            if self.weekly_intensity_distribution is None:
                missing.append("weekly_intensity_distribution")
            if self.projected_strain_contribution is None:
                missing.append("projected_strain_contribution")
            if missing:
                raise ValueError(f"PLANNING mode requires: {missing}")
            if self.block_analysis is not None:
                raise ValueError("block_analysis forbidden in PLANNING mode")
        else:
            if self.sessions:
                raise ValueError("sessions forbidden in REVIEW mode")
            if self.block_analysis is None:
                raise ValueError("block_analysis required in REVIEW mode")
            if self.generation_mode is not None:
                raise ValueError("generation_mode forbidden in REVIEW mode")
            if self.proposed_trade_offs:
                raise ValueError("proposed_trade_offs forbidden in REVIEW mode")
        return self

    @model_validator(mode="after")
    def _validate_trigger_mode_alignment(self):
        """REC2 — trigger ↔ mode."""
        t = self.metadata.invocation_trigger
        mapping = {
            InvocationTrigger.PLAN_GEN_DELEGATE_SPECIALISTS: RecommendationMode.PLANNING,
            InvocationTrigger.CHAT_WEEKLY_REPORT: RecommendationMode.REVIEW,
        }
        if t not in mapping:
            raise ValueError(f"Recommendation: trigger {t} non admissible")
        if mapping[t] != self.recommendation_mode:
            raise ValueError(f"Trigger {t} requires mode {mapping[t]}")
        return self

    @model_validator(mode="after")
    def _validate_discipline_coherence(self):
        """REC3 — toutes sessions ont discipline == self.discipline."""
        for s in self.sessions:
            if s.discipline != self.discipline:
                raise ValueError(f"Session discipline {s.discipline} ≠ {self.discipline}")
        return self

    @model_validator(mode="after")
    def _validate_intensity_distribution(self):
        """REC4 — intensity valeurs ∈ [0, 1], somme ∈ [0.98, 1.02]."""
        if self.weekly_intensity_distribution is None:
            return self
        for k, v in self.weekly_intensity_distribution.items():
            if not (0.0 <= v <= 1.0):
                raise ValueError(f"intensity zone {k}: {v} ∉ [0, 1]")
        total = sum(self.weekly_intensity_distribution.values())
        if not (0.98 <= total <= 1.02):
            raise ValueError(f"intensity_distribution sum {total} ∉ [0.98, 1.02]")
        return self

    @model_validator(mode="after")
    def _validate_emitter(self):
        """REC5 — emitted_by cohérent avec discipline."""
        valid = {
            Discipline.LIFTING: AgentId.LIFTING,
            Discipline.RUNNING: AgentId.RUNNING,
            Discipline.SWIMMING: AgentId.SWIMMING,
            Discipline.BIKING: AgentId.BIKING,
        }
        if self.metadata.emitted_by != valid[self.discipline]:
            raise ValueError(f"emitted_by {self.metadata.emitted_by} ≠ {valid[self.discipline]}")
        return self

    @model_validator(mode="after")
    def _validate_sessions_same_plan(self):
        """REC6 — toutes sessions pointent vers le même plan_id et plan_link_type."""
        if len(self.sessions) <= 1:
            return self
        first = self.sessions[0]
        for s in self.sessions[1:]:
            if s.plan_id != first.plan_id or s.plan_link_type != first.plan_link_type:
                raise ValueError("sessions cross plan_id/plan_link_type incohérents")
        return self

    @model_validator(mode="after")
    def _validate_flag_admissibility(self):
        """REC-F — flag_for_head_coach.code ∈ DISCIPLINE_ADMISSIBLE_FLAGS."""
        if self.flag_for_head_coach is not None \
                and self.flag_for_head_coach.code not in DISCIPLINE_ADMISSIBLE_FLAGS:
            raise ValueError(f"Flag code {self.flag_for_head_coach.code} hors périmètre discipline")
        return self
```

### 5.3 Invariants vue ↔ contrat (niveau node)

| ID | Prédicat | Action |
|---|---|---|
| REC7 | `discipline == view.target_discipline` | reject, retry LLM |
| REC8 | `generation_mode == context.plan_generation_mode` | reject, retry |
| REC9 | Chaque session : `contraindications_respected ⊆ injury_ids actifs pertinents` | reject, retry |
| REC10 | `weekly_volume_target.unit` cohérent avec `PlanComponent[D].total_volume_arc[*].unit` | reject |
| REC11 | Mode `block_regen` : sessions ciblent le bloc suivant, pas les blocs passés | reject |
| REC12 | Mode `baseline` : `sessions[].plan_link_type == BASELINE`, `block_id is None` | reject |
| REC13 | Modes `first_personalized` / `block_regen` : `sessions[].plan_link_type == ACTIVE`, `block_id is not None` | reject |

### 5.4 Mécanique `build_proposed_plan`

Le graphe `plan_generation` enchaîne `delegate_specialists → merge_recommendations → detect_conflicts → resolve_conflicts → build_proposed_plan`.

**`delegate_specialists`**. Parallélise invocations LLM sur disciplines actives (`coaching_scope[D] == FULL`) + Nutrition + Energy. Chaque invocation reçoit sa vue B2. Isolation stricte : aucun coach discipline ne reçoit les `Recommendation` des autres.

**`merge_recommendations`**. Applique l'ordre hiérarchique clinique §2.9 : lecture `RecoveryAssessment`, `EnergyAssessment`, `NutritionVerdict` avant merge des `Recommendation` disciplines. Si Recovery en `suspend` ou `escalate_to_takeover` : tous les `Recommendation` marqués `SUPERSEDED_BY_OVERLAY`.

**`detect_conflicts`**. Cinq familles :

```python
class ConflictFamily(str, Enum):
    TEMPORAL = "temporal"
    WEEKLY_TIME_BUDGET = "weekly_time_budget"
    STRAIN_CROSS_DISCIPLINE = "strain_cross_discipline"
    INTENSITY_CROSS_DISCIPLINE = "intensity_cross_discipline"
    CONTRAINDICATION_VIOLATION = "contraindication_violation"


class DetectedConflict(BaseModel):
    """Interne au graphe LangGraph, pas contrat B3."""
    family: ConflictFamily
    involved_disciplines: list[Discipline] = Field(..., min_length=1, max_length=4)
    involved_session_indices: dict[Discipline, list[int]]
    severity: Literal["minor", "moderate", "blocking"]
    description: str = Field(..., max_length=300)
    suggested_resolution: str | None = Field(None, max_length=200)
```

**`resolve_conflicts`**. Logique déterministe, précédence :

1. `CONTRAINDICATION_VIOLATION` severity=blocking : session fautive retirée, discipline re-invoquée avec prompt renforcé (retry ≤ 1).
2. Hiérarchie d'objectifs pour strain/intensity cross-discipline : discipline `PRIMARY` protégée, `SECONDARY`/`SUPPORT` décalée ou réduite.
3. Budget temps hebdo : réduction proportionnelle au poids `DisciplineRoleInPlan`.
4. Temporel : déplacement selon `TimeAvailability`.

Chaque résolution produit un `TradeOff` ajouté à `active_plan.trade_offs_disclosed`.

**Invariant RES1** : si conflit `blocking` non résolu après 1 retry, graphe signale `resolution_failure`, retour au Coordinator pour présentation honnête user.

**`build_proposed_plan`**. Trois effets :

1. Construit `ActivePlan` ou `BaselinePlan` selon `generation_mode` : `blocks[]` avec un seul `detail_level=FULL`, `discipline_components[D]` pour chaque discipline active, `trade_offs_disclosed` concaténés, `objective_snapshot` et `coaching_scope_snapshot` copies profondes (invariant PL15 B1).
2. Appelle `persist_prescribed_sessions` : pour chaque `PrescribedSessionDraft`, génère `session_id`, timestamps, valide PS1-PS14, upsert en table.
3. Met à jour `BlockDisciplineSpec.prescribed_session_ids` avec les IDs retournés.

Plan persisté en `status=DRAFT` (active) ou `PENDING_CONFIRMATION` (baseline), confirmation après `present_to_athlete → revise_plan → finalize_plan`.

### 5.5 Mode REVIEW (`CHAT_WEEKLY_REPORT`)

Flow distinct. Pas de consommation par `build_proposed_plan` :

1. `handle_weekly_report` invoque en consultation coachs disciplines actifs + Nutrition + Recovery + Energy.
2. Chaque discipline émet `Recommendation(mode=REVIEW)` avec `block_analysis`.
3. Le Coordinator agrège les `flag_for_head_coach` (cohérent §2.7).
4. Le Head Coach reçoit en input distinct : `list[Recommendation]` mode REVIEW, `NutritionVerdict` weekly, `RecoveryAssessment` si consulté, `EnergyAssessment` review, `AggregatedFlagsPayload`.
5. Le Head Coach produit un message direct, applique la règle `< 3` vs `≥ 3 flags` (§6).

Pas de mutation métier. Seule écriture : messages.

Exception : `block_analysis.compliance_rate < 0.5` sur une discipline peut déclencher `handle_block_end_trigger` proactivement → bascule `block_regen`. Transition inter-graphe, pas mutation directe depuis le contrat.

### 5.6 Fall-through `Recommendation`

Voir §7 pour le traitement unifié. Scénarios typiques :

- **Takeover activé pendant `delegate_specialists`** : 4 `Recommendation` en vol, Recovery activé. `merge_recommendations` détecte, persiste les 4 en `SUPERSEDED_BY_OVERLAY`, abandonne construction plan. Coordinator invoque `recovery_takeover`.
- **Objectif changé entre émission planning et consommation** : `Recommendation` basée sur ancien objectif. `SUPERSEDED_BY_OVERLAY` (via overlay `onboarding_reentry_active`).
- **Retry LangGraph** : même `contract_id`, `persist_prescribed_sessions` détecte via `processed_contracts`, retourne les `session_id` déjà persistés. `IDEMPOTENT_NOOP`.


---

## 6. `NutritionVerdict` (Nutrition Coach)

### 6.1 Émetteur, triggers, modes

Trois modes discriminés.

| Trigger | Mode | `daily_targets` | `plan_rules` | `daily_assessment` | `weekly_assessment` |
|---|---|---|---|---|---|
| `CHAT_DAILY_CHECKIN` | `daily` | obligatoire | — | obligatoire | — |
| `CHAT_WEEKLY_REPORT` | `weekly` | — | — | — | obligatoire |
| `PLAN_GEN_DELEGATE_SPECIALISTS` | `planning` | — | obligatoire | — | — |

### 6.2 Sous-modèles

```python
class NutritionStatus(str, Enum):
    OK = "ok"
    MILD_ADJUSTMENT = "mild_adjustment"
    CONCERN = "concern"
    ESCALATE_TO_ENERGY_COACH = "escalate_to_energy_coach"


class SupplementSuggestion(BaseModel):
    """Supplément ponctuel. Pas de posologie thérapeutique."""
    name: Literal[
        "creatine", "caffeine_anhydrous", "whey_protein", "casein",
        "electrolytes", "beta_alanine", "sodium_bicarbonate",
        "vitamin_d", "iron", "magnesium", "omega_3",
    ]
    dose_mg: int = Field(..., ge=0, le=20000)
    timing: Literal["morning", "pre_workout", "intra_workout", "post_workout", "evening", "with_meal"]
    rationale: str = Field(..., max_length=150)


class MealDistributionHint(BaseModel):
    meals_per_day: int = Field(..., ge=1, le=8)
    pre_workout_carbs_g: int | None = Field(None, ge=0, le=200)
    intra_workout_carbs_g_per_hour: int | None = Field(None, ge=0, le=120)
    post_workout_protein_g: int | None = Field(None, ge=0, le=80)
    post_workout_carbs_g: int | None = Field(None, ge=0, le=200)


class DailyNutritionTargets(BaseModel):
    """Cibles quotidiennes. Source unique pour affichage user au jour J."""
    target_date: date
    calories_kcal: int = Field(..., ge=800, le=6500)
    protein_g: int = Field(..., ge=20, le=400)
    carbs_g: int = Field(..., ge=20, le=1200)
    fat_g: int = Field(..., ge=15, le=300)

    # Dérivés utiles
    protein_g_per_kg_bw: float | None = Field(None, ge=0.5, le=5.0)
    fiber_g: int | None = Field(None, ge=0, le=80)
    hydration_ml: int | None = Field(None, ge=1000, le=8000)

    meal_distribution_hint: MealDistributionHint | None = None

    # Champs supplémentaires optionnels
    sodium_mg: int | None = Field(None, ge=500, le=10000)
    caffeine_mg: int | None = Field(None, ge=0, le=800)
    supplements: list[SupplementSuggestion] = Field(default_factory=list, max_length=5)
    caffeine_timing_hint: Literal["morning_only", "pre_workout_only", "avoid_late"] | None = None

    training_load_anticipated: Literal[
        "rest", "light", "moderate", "heavy", "very_heavy",
    ] = "moderate"

    rationale: str = Field(..., max_length=300)

    @model_validator(mode="after")
    def _macros_vs_calories_coherence(self):
        """NV-T1 — kcal calculé depuis macros ∈ ±5 % de calories_kcal."""
        computed = 4 * self.protein_g + 4 * self.carbs_g + 9 * self.fat_g
        if abs(computed - self.calories_kcal) / self.calories_kcal > 0.05:
            raise ValueError(f"Macros ({computed}) incohérents avec kcal ({self.calories_kcal})")
        return self

    @model_validator(mode="after")
    def _caffeine_timing_coherence(self):
        """NV-T2 — caffeine_mg > 0 sans caffeine_timing_hint → warn (non-bloquant Phase D)."""
        # Phase D : logging.warning, non raise
        return self


class DailyAssessment(BaseModel):
    intake_observed_kcal: int | None = Field(None, ge=0)
    intake_observed_protein_g: int | None = Field(None, ge=0)
    intake_observed_carbs_g: int | None = Field(None, ge=0)
    intake_observed_fat_g: int | None = Field(None, ge=0)
    intake_coverage_ratio: float | None = Field(None, ge=0.0, le=2.0)

    user_energy_signal_score: Literal["very_low", "low", "neutral", "high", "very_high"] | None = None
    sleep_quality_recent: Literal["poor", "fair", "good", "excellent"] | None = None

    status: NutritionStatus
    observation: str = Field(..., max_length=300)


class AdjustmentDirection(str, Enum):
    INCREASE = "increase"
    DECREASE = "decrease"
    HOLD = "hold"
    REDISTRIBUTE = "redistribute"


class NutritionAdjustment(BaseModel):
    target: Literal[
        "calories_total", "protein", "carbs", "fat",
        "pre_workout_carbs", "post_workout_protein", "hydration",
    ]
    direction: AdjustmentDirection
    magnitude_pct: float | None = Field(None, ge=0.0, le=50.0)
    rationale: str = Field(..., max_length=200)

    @model_validator(mode="after")
    def _hold_has_no_magnitude(self):
        if self.direction == AdjustmentDirection.HOLD and self.magnitude_pct is not None:
            raise ValueError("magnitude_pct doit être None si HOLD")
        if self.direction != AdjustmentDirection.HOLD and self.magnitude_pct is None:
            raise ValueError("magnitude_pct requis si direction != HOLD")
        return self


class WeeklyAssessment(BaseModel):
    compliance_rate: float = Field(..., ge=0.0, le=1.0)
    mean_daily_intake_kcal: int | None = Field(None, ge=0)
    mean_daily_protein_g_per_kg_bw: float | None = Field(None, ge=0.0, le=5.0)
    mean_daily_deficit_surplus_kcal: int | None = None
    intake_variability_cv: float | None = Field(None, ge=0.0, le=1.0)
    key_observations: list[str] = Field(..., min_length=1, max_length=5)
    proposed_adjustments: list[NutritionAdjustment] = Field(default_factory=list, max_length=5)


class NutritionPlanRuleCondition(BaseModel):
    session_type: Literal[
        "rest_day", "lifting_any", "lifting_lower_heavy", "lifting_upper_heavy",
        "endurance_short", "endurance_long", "endurance_intervals",
        "swimming_any", "biking_any", "any_training",
    ]
    discipline_filter: Discipline | None = None


class NutritionPlanRule(BaseModel):
    rule_id: str
    condition: NutritionPlanRuleCondition

    kcal_delta: int = Field(..., ge=-1500, le=1500)
    protein_g_delta: int = Field(..., ge=-100, le=150)
    carbs_g_delta: int = Field(..., ge=-200, le=400)
    fat_g_delta: int = Field(..., ge=-80, le=80)

    pre_workout_carbs_g: int | None = Field(None, ge=0, le=200)
    intra_workout_carbs_g_per_hour: int | None = Field(None, ge=0, le=120)
    post_workout_protein_g: int | None = Field(None, ge=0, le=80)

    rationale: str = Field(..., max_length=200)


class NutritionBaselineTargets(BaseModel):
    maintenance_calories_kcal: int = Field(..., ge=1200, le=5500)
    baseline_protein_g_per_kg_bw: float = Field(..., ge=1.0, le=3.5)
    baseline_carbs_g_per_kg_bw: float = Field(..., ge=1.0, le=10.0)
    baseline_fat_g_per_kg_bw: float = Field(..., ge=0.5, le=2.5)

    phase_intent: Literal[
        "recomposition", "fat_loss_mild", "fat_loss_aggressive",
        "weight_gain_slow", "weight_gain_aggressive",
        "performance_maintenance", "perf_surplus_light",
    ]
    target_rate_kg_per_week: float | None = Field(None, ge=-1.2, le=1.2)


class NutritionPlanRules(BaseModel):
    plan_id: str
    block_id: str

    baseline: NutritionBaselineTargets
    rules: list[NutritionPlanRule] = Field(..., min_length=1, max_length=15)

    dietary_restrictions_accounted_for: list[str] = Field(default_factory=list)
    cycle_phase_modulation: dict[str, dict] | None = None
    rationale: str = Field(..., max_length=500)


class EnergyCoachEscalation(BaseModel):
    """Porte le contexte d'escalade Nutrition → Energy, pas un bool nu."""
    escalation_reason: Literal[
        "ea_subclinical_suspected",
        "red_s_pattern_suspected",
        "chronic_deficit_persistent",
        "hrv_nutrition_convergence",
        "cycle_related_dysregulation",
    ]
    urgency: Literal["next_weekly_report", "proactive_24h", "immediate"]
    supporting_signals: dict[str, float | str] = Field(default_factory=dict)
    nutrition_context_summary: str = Field(..., max_length=400)
```

### 6.3 Classe `NutritionVerdict`

```python
class VerdictMode(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    PLANNING = "planning"


NUTRITION_ADMISSIBLE_FLAGS: set[FlagCode] = {
    FlagCode.EA_LOW_NORMAL_TRENDING_DOWN,
    FlagCode.EA_SUBCLINICAL,
    FlagCode.RED_S_SUSPECTED,
    FlagCode.COMPLIANCE_DROP,
    FlagCode.SLEEP_DEBT,
}


class NutritionVerdict(BaseModel):
    metadata: ContractMetadata

    verdict_mode: VerdictMode
    status: NutritionStatus

    # Conditionnels par mode
    daily_targets: DailyNutritionTargets | None = None
    daily_assessment: DailyAssessment | None = None
    weekly_assessment: WeeklyAssessment | None = None
    plan_rules: NutritionPlanRules | None = None

    daily_adjustments: list[NutritionAdjustment] = Field(default_factory=list, max_length=3)

    flag_for_head_coach: HeadCoachFlag | None = None
    pass_to_energy_coach: EnergyCoachEscalation | None = None
    notes_for_head_coach: str | None = Field(None, max_length=500)

    # ─── Validators ───────────────────────────────────────────────────────

    @model_validator(mode="after")
    def _validate_emitter(self):
        """NV1 — emitted_by == NUTRITION."""
        if self.metadata.emitted_by != AgentId.NUTRITION:
            raise ValueError(f"emitted_by doit être NUTRITION")
        return self

    @model_validator(mode="after")
    def _validate_trigger_mode_alignment(self):
        """NV2 — trigger ↔ verdict_mode."""
        t = self.metadata.invocation_trigger
        mapping = {
            InvocationTrigger.CHAT_DAILY_CHECKIN: VerdictMode.DAILY,
            InvocationTrigger.CHAT_WEEKLY_REPORT: VerdictMode.WEEKLY,
            InvocationTrigger.PLAN_GEN_DELEGATE_SPECIALISTS: VerdictMode.PLANNING,
        }
        if t not in mapping or mapping[t] != self.verdict_mode:
            raise ValueError(f"trigger {t} ↔ mode {self.verdict_mode} incohérent")
        return self

    @model_validator(mode="after")
    def _validate_mode_fields(self):
        """NV3 — champs conditionnels par mode."""
        if self.verdict_mode == VerdictMode.DAILY:
            if self.daily_targets is None or self.daily_assessment is None:
                raise ValueError("DAILY requires daily_targets and daily_assessment")
            if self.weekly_assessment or self.plan_rules:
                raise ValueError("DAILY forbids weekly_assessment / plan_rules")
        elif self.verdict_mode == VerdictMode.WEEKLY:
            if self.weekly_assessment is None:
                raise ValueError("WEEKLY requires weekly_assessment")
            if self.daily_targets or self.daily_assessment or self.plan_rules or self.daily_adjustments:
                raise ValueError("WEEKLY forbids daily_* / plan_rules / daily_adjustments")
        else:
            if self.plan_rules is None:
                raise ValueError("PLANNING requires plan_rules")
            if self.daily_targets or self.daily_assessment or self.weekly_assessment \
                    or self.daily_adjustments:
                raise ValueError("PLANNING forbids daily_* / weekly_assessment / daily_adjustments")
        return self

    @model_validator(mode="after")
    def _validate_escalation_consistency(self):
        """NV4 — status ESCALATE ⇔ pass_to_energy_coach."""
        if self.status == NutritionStatus.ESCALATE_TO_ENERGY_COACH \
                and self.pass_to_energy_coach is None:
            raise ValueError("status=ESCALATE requires pass_to_energy_coach")
        if self.pass_to_energy_coach is not None \
                and self.status not in {NutritionStatus.CONCERN, NutritionStatus.ESCALATE_TO_ENERGY_COACH}:
            raise ValueError("pass_to_energy_coach requires status ∈ {CONCERN, ESCALATE}")
        return self

    @model_validator(mode="after")
    def _validate_flag_admissibility(self):
        """NV5 — flag_for_head_coach.code ∈ NUTRITION_ADMISSIBLE_FLAGS."""
        if self.flag_for_head_coach is not None \
                and self.flag_for_head_coach.code not in NUTRITION_ADMISSIBLE_FLAGS:
            raise ValueError(f"Flag {self.flag_for_head_coach.code} hors périmètre Nutrition")
        return self

    @model_validator(mode="after")
    def _validate_red_s_implies_escalation(self):
        """NV6 — flag RED_S_SUSPECTED ou EA_SUBCLINICAL ⇒ escalation obligatoire."""
        if self.flag_for_head_coach is not None and self.flag_for_head_coach.code in {
            FlagCode.RED_S_SUSPECTED, FlagCode.EA_SUBCLINICAL,
        }:
            if self.pass_to_energy_coach is None:
                raise ValueError(f"Flag {self.flag_for_head_coach.code} requires pass_to_energy_coach")
        return self

    @model_validator(mode="after")
    def _validate_target_date_daily(self):
        """NV7 — DAILY : target_date ∈ emitted_at ± 1 jour."""
        if self.verdict_mode != VerdictMode.DAILY:
            return self
        delta = abs((self.daily_targets.target_date - self.metadata.emitted_at.date()).days)
        if delta > 1:
            raise ValueError("daily_targets.target_date trop éloigné de emitted_at")
        return self
```

### 6.4 Invariants vue ↔ contrat (niveau node)

| ID | Prédicat | Action |
|---|---|---|
| NV8 | Mode PLANNING : `plan_rules.plan_id == active_plan.plan_id` en construction | reject, retry |
| NV9 | `plan_rules.dietary_restrictions_accounted_for == view.practical_constraints.meals.dietary_restrictions` | reject, retry |
| NV10 | `daily_targets.training_load_anticipated` cohérent avec sessions prescrites du jour | warn + correction auto |
| NV11 | Si `cycle_active == True` et PLANNING : `plan_rules.cycle_phase_modulation IS NOT NULL` | warn |
| NV12 | `baseline.maintenance_calories_kcal` ∈ ±25 % TDEE estimé | warn, pas reject |
| NV13 | DAILY : `intake_coverage_ratio < 0.7` et status OK → incohérent | reject |

### 6.5 Mécanique `persist_nutrition_targets`

**Mode DAILY** :

1. Pré-check overlay (`recovery_takeover_active == False`). KO → `SUPERSEDED_BY_OVERLAY`.
2. Upsert `nutrition_daily_targets (athlete_id, target_date) PK` avec `source_contract_id`, `created_at`, `updated_at`.
3. Applique `daily_adjustments` : recalcule et upsert si target jour courant, insert pour dates futures avec flag `source=adjustment_anticipated`.
4. Écrit `processed_contracts` avec `outcome=APPLIED`.
5. Si `pass_to_energy_coach` présent : émet event `NutritionToEnergyEscalationEvent` vers Coordinator. Coordinator décide selon `urgency`.

**Mode WEEKLY**. Aucune mutation targets. Le contrat alimente :
- Agrégation flags pour synthèse Head Coach.
- Routage éventuel vers Energy.
- Audit forensique.

`weekly_assessment.proposed_adjustments` affichés au user, pas appliqués. Confirmation user déclenche invocation ultérieure.

**Mode PLANNING** :

1. Pré-check : `active_plan.status == DRAFT`, sinon `SUPERSEDED_BY_OVERLAY`.
2. Vérifier NV9. Divergence → reject, retry.
3. Upsert en tables `nutrition_plan_rules` et `nutrition_plan_baselines`.
4. **Matérialisation des daily_targets pour le bloc courant FULL** : pour chaque jour, évaluation des règles contre les sessions prescribed, upsert `nutrition_daily_targets` avec `source=plan_materialization`.
5. Blocs futurs (SUMMARY) : matérialisation paresseuse au passage de bloc.

**Invariant node NVN1** : une seule ligne `nutrition_daily_targets` active par date. Dernière écriture gagne, trace via `nutrition_daily_targets_history`.

### 6.6 Composante nutrition du plan

Tables externes (pas de `Discipline.NUTRITION` dans l'enum, nutrition n'est pas une discipline d'entraînement) :

- `nutrition_plan_rules` (PK `rule_id`, index `plan_id`)
- `nutrition_plan_baselines` (PK `plan_id`)
- `nutrition_daily_targets` (PK `(athlete_id, target_date)`)
- `nutrition_daily_targets_history` (PK auto-increment, index `(athlete_id, target_date)`)

Delta B3 sur `ActivePlan` (B1 §4.6) : champ `nutrition_rules_persisted: bool = False` comme marqueur.

### 6.7 Fall-through spécifique

Voir §7. Scénarios typiques :
- Mode DAILY pendant takeover actif : `SUPERSEDED_BY_OVERLAY`, user voit targets précédents.
- Mode PLANNING simultané à `handle_goal_change` : règles basées sur objectif obsolète, `SUPERSEDED_BY_OVERLAY`, re-invocation après re-entry.
- Mode DAILY avec `pass_to_energy_coach.urgency=immediate` pendant Energy suspendu par takeover : `NutritionVerdict` appliqué normalement, escalade queued.

---

## 7. `RecoveryAssessment` (Recovery Coach en consultation)

### 7.1 Émetteur, triggers, scope

Émis par Recovery Coach en consultation exclusivement. En takeover : messages directs, pas de contrat.

Triggers : `CHAT_INJURY_REPORT`, `CHAT_WEEKLY_REPORT`, `MONITORING_HRV`, `MONITORING_SLEEP`.

### 7.2 Sévérité et action orthogonales

`severity` et `recommendation.action_type` sont deux axes distincts, bornés par validators.

```python
class RecoverySeverity(str, Enum):
    NONE = "none"
    WATCH = "watch"
    CONCERN = "concern"
    CRITICAL = "critical"
```

### 7.3 Signal summary structuré

```python
class HRVSummary(BaseModel):
    baseline_ms: float | None = Field(None, ge=10.0, le=200.0)
    current_ms: float | None = Field(None, ge=10.0, le=200.0)
    deviation_sd: float | None = Field(None, ge=-5.0, le=5.0)
    trend_7d: Literal["stable", "declining", "recovering", "volatile", "insufficient_data"]
    consecutive_days_below_baseline: int = Field(..., ge=0, le=60)


class SleepSummary(BaseModel):
    target_hours_per_night: float | None = Field(None, ge=4.0, le=12.0)
    mean_hours_7d: float | None = Field(None, ge=0.0, le=14.0)
    debt_hours_14d: float | None = Field(None, ge=-20.0, le=40.0)
    quality_trend: Literal["stable", "deteriorating", "improving", "insufficient_data"]
    nights_critically_short_7d: int = Field(..., ge=0, le=7)


class StrainSummary(BaseModel):
    aggregate_current: float = Field(..., ge=0.0, le=100.0)
    peak_24h: float = Field(..., ge=0.0, le=100.0)
    aggregate_trend_7d: Literal["accumulating", "stable", "recovering"]
    high_strain_muscle_groups: list[MuscleGroup] = Field(default_factory=list, max_length=18)


class RPESummary(BaseModel):
    mean_7d: float | None = Field(None, ge=1.0, le=10.0)
    mean_vs_prescribed_delta_7d: float | None = Field(None, ge=-5.0, le=5.0)
    sessions_rpe_overshoot_7d: int = Field(..., ge=0, le=20)


class AllostaticSummary(BaseModel):
    current_value: float = Field(..., ge=0.0, le=100.0)
    zone: AllostaticLoadZone
    trend_7d_slope: float = Field(..., ge=-10.0, le=10.0)
    trend_14d_slope: float = Field(..., ge=-10.0, le=10.0)
    dominant_contributor: Literal[
        "strain_aggregate", "sleep_debt", "hrv_deviation",
        "reported_stress", "rpe_trend", "nutrition_deficit",
    ] | None = None


class RecoverySignalSummary(BaseModel):
    hrv: HRVSummary
    sleep: SleepSummary
    strain: StrainSummary
    rpe: RPESummary
    allostatic: AllostaticSummary

    user_reported_soreness: Literal["none", "mild", "moderate", "severe"] | None = None
    user_reported_stress: Literal["low", "moderate", "high", "very_high"] | None = None
    user_reported_motivation: Literal["high", "neutral", "low", "very_low"] | None = None
```

### 7.4 Détection pattern override

```python
class OverridePatternDetection(BaseModel):
    detected: bool

    consecutive_days: int | None = Field(None, ge=0, le=60)
    mean_divergence: float | None = Field(None, ge=0.0, le=100.0)
    objective_trend_direction: Literal["declining", "stable", "ambiguous"] | None = None
    evidence_summary: str | None = Field(None, max_length=300)

    @model_validator(mode="after")
    def _fields_required_when_detected(self):
        if self.detected:
            if any(v is None for v in (
                self.consecutive_days, self.mean_divergence,
                self.objective_trend_direction, self.evidence_summary,
            )):
                raise ValueError("detected=True requires all detection fields")
            if self.objective_trend_direction == "ambiguous":
                raise ValueError("detected=True incompatible avec objective_trend ambiguous")
        return self
```

### 7.5 Recommendation discriminée par action

```python
class RecoveryActionContinue(BaseModel):
    action_type: Literal["continue"] = "continue"
    rationale: str = Field(..., max_length=400)
    monitor_signals: list[Literal[
        "hrv_trend", "sleep_quality", "strain_accumulation",
        "rpe_overshoot", "allo_trend", "user_soreness",
    ]] = Field(..., min_length=1, max_length=6)


class RecoveryActionDeload(BaseModel):
    action_type: Literal["deload"] = "deload"
    duration_days: int = Field(..., ge=3, le=21)
    volume_reduction_pct: float = Field(..., ge=10.0, le=70.0)
    intensity_reduction_pct: float = Field(..., ge=0.0, le=50.0)
    preserved_session_ids: list[str] = Field(default_factory=list, max_length=5)
    removed_session_categories: list[Literal[
        "vo2_intervals", "threshold", "max_effort_strength", "long_run",
        "high_volume_lifting", "race_pace_work",
    ]] = Field(default_factory=list, max_length=6)
    rationale: str = Field(..., max_length=400)
    reassessment_date: date


class RecoveryActionSuspend(BaseModel):
    """Suspension active_plan sans takeover UX. Pause préventive non-urgente."""
    action_type: Literal["suspend"] = "suspend"
    expected_duration_days: int | None = Field(None, ge=1, le=180)
    suspension_reason_category: Literal[
        "preventive_high_allostatic_load",
        "sustained_hrv_decline",
        "sleep_collapse_non_acute",
        "chronic_rpe_overshoot",
        "user_requested_pause_medical_motivated",
    ]
    reassessment_date: date
    permitted_activities: list[Literal[
        "easy_walking", "mobility_work", "easy_swimming",
        "light_cycling_z1", "yoga_restorative", "full_rest",
    ]] = Field(default_factory=list, max_length=6)
    rationale: str = Field(..., max_length=400)


class RecoveryActionEscalateToTakeover(BaseModel):
    """Escalade vers recovery_takeover graph."""
    action_type: Literal["escalate_to_takeover"] = "escalate_to_takeover"
    trigger_category: Literal[
        "injury_reported_requires_diagnostic",
        "hrv_critical_drop",
        "sleep_acute_collapse",
        "allostatic_alarm_zone",
        "multi_signal_convergence",
    ]
    injury_payload_draft: dict | None = None
    initial_protocol_seed: str = Field(..., max_length=500)
    rationale: str = Field(..., max_length=400)


RecoveryRecommendationDiscriminated = Annotated[
    RecoveryActionContinue
    | RecoveryActionDeload
    | RecoveryActionSuspend
    | RecoveryActionEscalateToTakeover,
    Field(discriminator="action_type"),
]
```

### 7.6 Classe `RecoveryAssessment`

```python
RECOVERY_ADMISSIBLE_FLAGS: set[FlagCode] = {
    FlagCode.HIGH_STRAIN_ACCUMULATED,
    FlagCode.HRV_DEGRADED,
    FlagCode.SLEEP_DEBT,
    FlagCode.OVERRIDE_PATTERN_DETECTED,
    FlagCode.RPE_SYSTEMATIC_OVERSHOOT,
    FlagCode.INJURY_SUSPECTED,
    FlagCode.CLINICAL_ESCALATION_REQUIRED,
    FlagCode.DELOAD_SUGGESTED,
}


class RecoveryAssessment(BaseModel):
    metadata: ContractMetadata

    severity: RecoverySeverity
    signal_summary: RecoverySignalSummary
    override_pattern: OverridePatternDetection
    recommendation: RecoveryRecommendationDiscriminated

    flag_for_head_coach: HeadCoachFlag | None = None
    notes_for_head_coach: str | None = Field(None, max_length=500)

    @model_validator(mode="after")
    def _validate_emitter(self):
        """RA1 — emitted_by == RECOVERY."""
        if self.metadata.emitted_by != AgentId.RECOVERY:
            raise ValueError("emitted_by doit être RECOVERY")
        return self

    @model_validator(mode="after")
    def _validate_trigger_admissible(self):
        """RA2 — trigger ∈ admissibles consultation."""
        admissible = {
            InvocationTrigger.CHAT_INJURY_REPORT,
            InvocationTrigger.CHAT_WEEKLY_REPORT,
            InvocationTrigger.MONITORING_HRV,
            InvocationTrigger.MONITORING_SLEEP,
        }
        if self.metadata.invocation_trigger not in admissible:
            raise ValueError(f"trigger {self.metadata.invocation_trigger} non admissible")
        return self

    @model_validator(mode="after")
    def _validate_severity_action_coherence(self):
        """RA3 — severity ↔ action bornes."""
        sev = self.severity
        action = self.recommendation.action_type
        if sev == RecoverySeverity.NONE and action != "continue":
            raise ValueError(f"severity=none incohérent avec action={action}")
        if sev == RecoverySeverity.CRITICAL and action == "continue":
            raise ValueError("severity=critical incohérent avec action=continue")
        if action in ("escalate_to_takeover", "suspend") \
                and sev not in {RecoverySeverity.CONCERN, RecoverySeverity.CRITICAL}:
            raise ValueError(f"action={action} requires severity ∈ {{concern, critical}}")
        return self

    @model_validator(mode="after")
    def _validate_injury_trigger_action(self):
        """RA4 — CHAT_INJURY_REPORT ⇒ action=escalate_to_takeover obligatoire."""
        if self.metadata.invocation_trigger == InvocationTrigger.CHAT_INJURY_REPORT:
            if self.recommendation.action_type != "escalate_to_takeover":
                raise ValueError("CHAT_INJURY_REPORT requires action=escalate_to_takeover")
            if self.recommendation.trigger_category != "injury_reported_requires_diagnostic":
                raise ValueError("trigger_category must be injury_reported_requires_diagnostic")
        return self

    @model_validator(mode="after")
    def _validate_override_pattern_evidence(self):
        """RA5 — override_pattern.detected=True requiert signal physiologique convergent."""
        if not self.override_pattern.detected:
            return self
        evidence_found = (
            self.signal_summary.hrv.trend_7d == "declining"
            or (self.signal_summary.sleep.debt_hours_14d is not None
                and self.signal_summary.sleep.debt_hours_14d > 0)
            or self.signal_summary.allostatic.trend_7d_slope > 0
        )
        if not evidence_found:
            raise ValueError("override_pattern.detected=True sans signal convergent")
        return self

    @model_validator(mode="after")
    def _validate_flag_admissibility(self):
        """RA6 — flag_for_head_coach.code ∈ RECOVERY_ADMISSIBLE_FLAGS."""
        if self.flag_for_head_coach is not None \
                and self.flag_for_head_coach.code not in RECOVERY_ADMISSIBLE_FLAGS:
            raise ValueError(f"Flag {self.flag_for_head_coach.code} hors périmètre Recovery")
        return self

    @model_validator(mode="after")
    def _validate_injury_payload_shape(self):
        """RA7 — trigger_category=injury_reported_requires_diagnostic ⇒ injury_payload_draft valide."""
        if self.recommendation.action_type != "escalate_to_takeover":
            return self
        rec = self.recommendation
        if rec.trigger_category == "injury_reported_requires_diagnostic":
            if rec.injury_payload_draft is None:
                raise ValueError("injury_reported requires injury_payload_draft")
            required = {"region", "severity", "status"}
            missing = required - set(rec.injury_payload_draft.keys())
            if missing:
                raise ValueError(f"injury_payload_draft missing: {missing}")
        else:
            if rec.injury_payload_draft is not None:
                raise ValueError(f"injury_payload_draft forbidden for trigger_category={rec.trigger_category}")
        return self
```

### 7.7 Invariants vue ↔ state (niveau node)

| ID | Prédicat | Action |
|---|---|---|
| RA9 | `CHAT_INJURY_REPORT` ⇒ `view.last_user_message_classified_intent == INJURY_REPORT` | reject |
| RA10 | `MONITORING_HRV` ⇒ `view.monitoring_event_payload.event_type == hrv_deviation` | reject |
| RA11 | `MONITORING_SLEEP` ⇒ `view.monitoring_event_payload.event_type == sleep_degradation` | reject |
| RA12 | `signal_summary.strain.high_strain_muscle_groups ⊆ view.strain_state.by_group` | reject |
| RA13 | action=deload ⇒ `active_plan != None AND status == ACTIVE` | reject, retry |
| RA14 | action=suspend ⇒ `active_plan.status ∈ {ACTIVE, DRAFT}` | reject |
| RA15 | action=escalate_to_takeover ⇒ `recovery_takeover_active == False` | `IDEMPOTENT_NOOP` |
| RA16 | `preserved_session_ids ⊆ prescribed_sessions du bloc courant` (deload) | reject |

### 7.8 Mécanique de dispatch

Deux dispatchs orthogonaux :

```
                 RecoveryAssessment
                        │
       ┌────────────────┼─────────────────────┐
       ▼                ▼                     ▼
override_pattern   recommendation         contract_emissions
   detected?        action_type              (audit)
       │                │
       ▼                ▼
flag_override_     ┌────┴──────┬──────┬─────────────────┐
pattern (si True)  ▼           ▼      ▼                 ▼
                continue     deload suspend    escalate_to_takeover
                (no-op)        │      │                 │
                               ▼      ▼                 ▼
                      apply_recovery  suspend_      activate_clinical_
                      _deload         active_plan   frame + invoke
                                                    recovery_takeover
```

**`flag_override_pattern`** : set `persistent_override_pattern.active=True`, `first_detected_at` si pas déjà set, `last_confirmed_at=now`, autres champs depuis contrat. Idempotence : si déjà active, seuls `last_confirmed_at`, `consecutive_days_detected`, `divergence_magnitude` updatés. `first_detected_at` conservé.

**`apply_recovery_deload`** (nouveau node B3) : identifie bloc courant, applique reductions sur sessions du bloc `[today, today + duration_days]` sauf `preserved_session_ids`, marque `removed_session_categories` en `SKIPPED`, annote `modification_history`. Pas de suspension, pas d'overlay. Head Coach notifie user.

**`suspend_active_plan`** : set `active_plan.status=SUSPENDED`, `suspended_at=now`, `suspended_reason`, `suspension_triggered_by="recovery_coach"`. Ne set **pas** `recovery_takeover_active`. Différence fondamentale : suspend = mutation métier silencieuse, takeover = bascule UX + conversationnelle.

**`activate_clinical_frame`** : set `recovery_takeover_active=True`, `active_plan.status=SUSPENDED`, crée `active_recovery_thread_id`, signal frontend bascule UX, retour au Coordinator pour invoquer `recovery_takeover` graph.

### 7.9 Interactions et frontières

- **Interaction Energy** : Energy Coach peut flag `flag_for_recovery_coach` avec `urgency=immediate_takeover` → Coordinator invoque Recovery en consultation → `RecoveryAssessment` peut escalader → `activate_clinical_frame`. Droit de veto Recovery préservé.
- **Takeover actif interdit l'émission** : Les triggers `MONITORING_*`, `CHAT_WEEKLY_REPORT`, `CHAT_INJURY_REPORT` sont court-circuités côté Coordinator quand `recovery_takeover_active == True`. Exception : nouvelle blessure distincte pendant takeover peut ajouter `persist_injury` dans le graph takeover.

### 7.10 Fall-through spécifique

Voir §7. Scénarios :
- Escalation émis pendant takeover déjà actif : `IDEMPOTENT_NOOP`.
- Deload émis, entre temps block_regen démarré : `SUPERSEDED_BY_NEWER`, Recovery re-consulté dans le block_regen.
- Suspend avec `active_plan.status != ACTIVE` : reject RA14, retry ou escalade.


---

## 8. `EnergyAssessment` (Energy Coach)

### 8.1 Émetteur, triggers, modes

Quatre triggers admissibles, tous en consultation exclusive.

| Trigger | Mode | Escalation possible |
|---|---|---|
| `PLAN_GEN_DELEGATE_SPECIALISTS` | `planning` | Vers Recovery si pattern alarmant |
| `CHAT_WEEKLY_REPORT` | `review` | Vers Recovery ou Head Coach |
| `MONITORING_EA` | `monitoring` | Escalade probable Recovery |
| `ESCALATION_NUTRITION_TO_ENERGY` | `nutrition_escalation` | Escalade Recovery si convergence |

### 8.2 Zones EA, trajectoire, contexte cycle

```python
from resilio.schema.core import EAZone, CyclePhase


class EAHistoryPoint(BaseModel):
    week_start: date
    mean_ea_kcal_per_kg_ffm: float = Field(..., ge=0.0, le=100.0)
    dominant_zone: EAZone
    days_with_valid_data: int = Field(..., ge=0, le=7)
    mean_intake_kcal: float | None = None
    mean_eee_kcal: float | None = None


class EATrajectory(BaseModel):
    """Fenêtres par trigger : MONITORING=28j, PLANNING=60j, REVIEW=28j, ESCALATION=28j."""
    window_days: int = Field(..., ge=7, le=180)
    points: list[EAHistoryPoint] = Field(..., min_length=1, max_length=26)

    trend_slope_kcal_per_week: float = Field(..., ge=-50.0, le=50.0)
    consecutive_weeks_below_30: int = Field(..., ge=0, le=52)
    consecutive_weeks_below_20: int = Field(..., ge=0, le=52)

    @model_validator(mode="after")
    def _ordered_chronological(self):
        for i in range(len(self.points) - 1):
            if self.points[i].week_start >= self.points[i + 1].week_start:
                raise ValueError("points doit être ordonné chronologiquement")
        return self


class CycleContext(BaseModel):
    cycle_phase: CyclePhase
    cycle_day: int | None = Field(None, ge=1, le=60)
    cycle_length_days: int | None = Field(None, ge=21, le=60)

    phase_clinical_significance: Literal[
        "normal_eumenorrheic", "amenorrhea_concerning",
        "post_menopausal_reference", "hormonal_contraception_stable",
        "irregular_pattern_concerning", "unknown_insufficient_data",
    ]

    modulation_applied: bool = False
    modulation_rationale: str | None = Field(None, max_length=300)

    @model_validator(mode="after")
    def _modulation_requires_rationale(self):
        if self.modulation_applied and self.modulation_rationale is None:
            raise ValueError("modulation_applied=True requires modulation_rationale")
        return self
```

### 8.3 Recommandation composite

```python
class CaloricAdjustment(BaseModel):
    """Ajustement structurel au niveau du plan/bloc. Distinct des NutritionAdjustment quotidiens."""
    direction: Literal["increase", "decrease", "maintain"]
    magnitude_pct: float | None = Field(None, ge=0.0, le=40.0)
    duration_scope: Literal["next_block", "current_cycle_phase", "sustained_until_reassessment"]
    reassessment_date: date | None = None
    rationale: str = Field(..., max_length=300)

    @model_validator(mode="after")
    def _magnitude_coherence(self):
        if self.direction == "maintain" and self.magnitude_pct is not None:
            raise ValueError("magnitude_pct None si maintain")
        if self.direction != "maintain" and self.magnitude_pct is None:
            raise ValueError("magnitude_pct required if increase/decrease")
        return self


class TrainingLoadModulation(BaseModel):
    direction: Literal["reduce", "redistribute", "maintain"]
    volume_reduction_pct: float | None = Field(None, ge=0.0, le=50.0)
    intensity_reduction_pct: float | None = Field(None, ge=0.0, le=30.0)
    duration_days: int = Field(..., ge=3, le=60)
    affected_disciplines: list[Discipline] = Field(default_factory=list, max_length=4)
    rationale: str = Field(..., max_length=300)

    @model_validator(mode="after")
    def _direction_coherence(self):
        if self.direction == "maintain":
            if self.volume_reduction_pct is not None or self.intensity_reduction_pct is not None:
                raise ValueError("reductions None si maintain")
        elif self.direction == "reduce":
            if self.volume_reduction_pct is None and self.intensity_reduction_pct is None:
                raise ValueError("au moins une réduction requise")
        return self


class ClinicalEscalation(BaseModel):
    """Toujours présente. required=bool distingue diagnostic vs aucune escalade."""
    required: bool
    escalation_type: Literal[
        "red_s_suspected_requires_workup",
        "sustained_clinical_zone_requires_review",
        "converging_signals_require_recovery_consultation",
        "hormonal_dysregulation_suspected",
    ] | None = None
    external_referral_suggested: bool = False
    urgency: Literal["next_weekly_review", "proactive_48h", "immediate"] | None = None
    rationale: str | None = Field(None, max_length=400)

    @model_validator(mode="after")
    def _fields_required_when_required(self):
        if not self.required:
            forbidden = [self.escalation_type, self.urgency, self.rationale]
            if any(v is not None for v in forbidden) or self.external_referral_suggested:
                raise ValueError("required=False forbids escalation_type/urgency/rationale/referral")
            return self
        if self.escalation_type is None or self.urgency is None or self.rationale is None:
            raise ValueError("required=True requires escalation_type, urgency, rationale")
        return self


class EnergyRecommendation(BaseModel):
    """3 leviers indépendants. Un assessment sans aucun levier actif ET sans escalation
    est suspect (validator EA11)."""
    caloric_adjustment: CaloricAdjustment | None = None
    training_load_modulation: TrainingLoadModulation | None = None
    clinical_escalation: ClinicalEscalation
```

### 8.4 Classe `EnergyAssessment`

```python
ENERGY_ADMISSIBLE_FLAGS: set[FlagCode] = {
    FlagCode.EA_LOW_NORMAL_TRENDING_DOWN,
    FlagCode.EA_SUBCLINICAL,
    FlagCode.RED_S_SUSPECTED,
    FlagCode.SLEEP_DEBT,
    FlagCode.HRV_DEGRADED,
}


class EnergyAssessmentMode(str, Enum):
    PLANNING = "planning"
    REVIEW = "review"
    MONITORING = "monitoring"
    NUTRITION_ESCALATION = "nutrition_escalation"


class EnergyAssessment(BaseModel):
    metadata: ContractMetadata
    assessment_mode: EnergyAssessmentMode

    ea_current_estimated: float | None = Field(None, ge=0.0, le=100.0)
    ea_status_interpretation: EAZone
    ffm_source: Literal[
        "connector_measured", "onboarding_estimated", "defaulted_fallback", "unavailable",
    ]

    trajectory: EATrajectory
    cycle_context: CycleContext | None = None
    recommendation: EnergyRecommendation

    flag_for_head_coach: HeadCoachFlag | None = None
    flag_for_recovery_coach: RecoveryCoachFlag | None = None
    notes_for_head_coach: str | None = Field(None, max_length=500)

    @model_validator(mode="after")
    def _validate_emitter(self):
        """EA1 — emitted_by == ENERGY."""
        if self.metadata.emitted_by != AgentId.ENERGY:
            raise ValueError("emitted_by doit être ENERGY")
        return self

    @model_validator(mode="after")
    def _validate_trigger_mode_alignment(self):
        """EA2 — trigger ↔ assessment_mode."""
        mapping = {
            InvocationTrigger.PLAN_GEN_DELEGATE_SPECIALISTS: EnergyAssessmentMode.PLANNING,
            InvocationTrigger.CHAT_WEEKLY_REPORT: EnergyAssessmentMode.REVIEW,
            InvocationTrigger.MONITORING_EA: EnergyAssessmentMode.MONITORING,
            InvocationTrigger.ESCALATION_NUTRITION_TO_ENERGY: EnergyAssessmentMode.NUTRITION_ESCALATION,
        }
        t = self.metadata.invocation_trigger
        if t not in mapping or mapping[t] != self.assessment_mode:
            raise ValueError(f"trigger {t} ↔ mode {self.assessment_mode} incohérent")
        return self

    @model_validator(mode="after")
    def _validate_ffm_unavailable_mode(self):
        """EA4 — ffm_source=unavailable ⇒ ea_current_estimated=None + flag obligatoire."""
        if self.ffm_source == "unavailable":
            if self.ea_current_estimated is not None:
                raise ValueError("ffm_source=unavailable incompatible avec ea_current_estimated")
            if self.flag_for_head_coach is None:
                raise ValueError("ffm_source=unavailable requires flag_for_head_coach")
        return self

    @model_validator(mode="after")
    def _validate_ea_zone_coherence(self):
        """EA5 — interpretation cohérent avec ea calculé, tolérance ±1 cran."""
        if self.ea_current_estimated is None:
            return self
        def expected_zone(ea: float) -> EAZone:
            if ea >= 45: return EAZone.OPTIMAL
            if ea >= 30: return EAZone.LOW_NORMAL
            if ea >= 20: return EAZone.SUBCLINICAL
            return EAZone.CLINICAL_RED_S
        zone_order = [EAZone.CLINICAL_RED_S, EAZone.SUBCLINICAL, EAZone.LOW_NORMAL, EAZone.OPTIMAL]
        expected = expected_zone(self.ea_current_estimated)
        if abs(zone_order.index(expected) - zone_order.index(self.ea_status_interpretation)) > 1:
            raise ValueError(f"interpretation {self.ea_status_interpretation} divergeant de {expected}")
        return self

    @model_validator(mode="after")
    def _validate_clinical_zone_requires_escalation(self):
        """EA6 — CLINICAL_RED_S ⇒ clinical_escalation.required=True."""
        if self.ea_status_interpretation == EAZone.CLINICAL_RED_S:
            if not self.recommendation.clinical_escalation.required:
                raise ValueError("CLINICAL_RED_S requires clinical_escalation.required=True")
        return self

    @model_validator(mode="after")
    def _validate_subclinical_trajectory_escalation(self):
        """EA7 — 2 semaines consécutives <20 ⇒ escalation obligatoire."""
        if self.trajectory.consecutive_weeks_below_20 >= 2:
            if not self.recommendation.clinical_escalation.required:
                raise ValueError("consecutive_weeks_below_20>=2 requires escalation")
        return self

    @model_validator(mode="after")
    def _validate_flag_admissibility(self):
        """EA8 — flag_for_head_coach ∈ ENERGY_ADMISSIBLE_FLAGS."""
        if self.flag_for_head_coach is not None \
                and self.flag_for_head_coach.code not in ENERGY_ADMISSIBLE_FLAGS:
            raise ValueError(f"Flag {self.flag_for_head_coach.code} hors périmètre Energy")
        return self

    @model_validator(mode="after")
    def _validate_recovery_flag_coherence(self):
        """EA9 — flag_for_recovery ⇒ ea != OPTIMAL."""
        if self.flag_for_recovery_coach is not None \
                and self.ea_status_interpretation == EAZone.OPTIMAL:
            raise ValueError("flag_for_recovery_coach incohérent avec OPTIMAL")
        return self

    @model_validator(mode="after")
    def _validate_recovery_flag_urgency_coherence(self):
        """EA10 — urgency=immediate_takeover requires clinical_escalation.required + urgency=immediate."""
        if self.flag_for_recovery_coach is None:
            return self
        if self.flag_for_recovery_coach.urgency == "immediate_takeover":
            if not self.recommendation.clinical_escalation.required:
                raise ValueError("immediate_takeover requires clinical_escalation.required")
            if self.recommendation.clinical_escalation.urgency != "immediate":
                raise ValueError("immediate_takeover requires clinical_escalation.urgency=immediate")
        return self

    @model_validator(mode="after")
    def _validate_assessment_has_signal(self):
        """EA11 — zone concerning sans aucun levier actif = bug."""
        has_caloric = (self.recommendation.caloric_adjustment is not None
                       and self.recommendation.caloric_adjustment.direction != "maintain")
        has_load = (self.recommendation.training_load_modulation is not None
                    and self.recommendation.training_load_modulation.direction != "maintain")
        has_escalation = self.recommendation.clinical_escalation.required
        has_flag = self.flag_for_head_coach is not None or self.flag_for_recovery_coach is not None
        in_concerning = self.ea_status_interpretation in {EAZone.SUBCLINICAL, EAZone.CLINICAL_RED_S}
        if in_concerning and not any([has_caloric, has_load, has_escalation, has_flag]):
            raise ValueError(f"EA {self.ea_status_interpretation} sans aucun levier actif")
        return self

    @model_validator(mode="after")
    def _validate_planning_requires_adjustments(self):
        """EA12 — PLANNING requires caloric et training_load renseignés (au minimum maintain)."""
        if self.assessment_mode != EnergyAssessmentMode.PLANNING:
            return self
        if self.recommendation.caloric_adjustment is None:
            raise ValueError("PLANNING requires caloric_adjustment")
        if self.recommendation.training_load_modulation is None:
            raise ValueError("PLANNING requires training_load_modulation")
        return self
```

### 8.5 Invariants vue ↔ state (niveau node)

| ID | Prédicat | Action |
|---|---|---|
| EA13 | `trajectory.window_days` cohérent avec trigger ±10 % | warn |
| EA14 | `cycle_context` présent ⇔ `cycle_active==True` OU `cycle_phase ∈ {amenorrhea, post_menopause, irregular_pattern}` | reject, retry |
| EA15 | NUTRITION_ESCALATION ⇒ `view.escalation_context IS NOT NULL` | reject |
| EA16 | `ffm_source=connector_measured` ⇒ `ffm != None AND freshness < 30j` | reject, retry |
| EA17 | `ffm_source=unavailable` ⇒ `ffm == None` | reject |
| EA18 | `affected_disciplines ⊆ state.coaching_scope FULL` | reject |
| EA19 | PLANNING ⇒ `active_plan.status == DRAFT` | `SUPERSEDED_BY_NEWER` si bascule |

### 8.6 Mécanique `dispatch_energy_assessment`

Dispatchs **cumulatifs**, contrairement à Recovery (actions discriminées) :

```
             EnergyAssessment
                   │
    ┌──────────────┼─────────────────────┐
    ▼              ▼                     ▼
caloric_       training_load_      clinical_escalation
adjustment     modulation          [required=True]
    │              │                     │
    ▼              ▼            ┌────────┴────────┐
persist_energy_plan_component   ▼                 ▼
(mode PLANNING uniquement)  flag_for_         flag_for_
                            head_coach         recovery_coach
                                                   │
                                                   ▼
                                      Coordinator routage
                                      selon urgency
```

**`persist_energy_plan_component`** (nouveau node B3). Tables externes :

- `energy_plan_caloric_directives` (PK `directive_id`, index `plan_id`)
- `energy_plan_load_modulations` (PK `modulation_id`, index `plan_id`)
- `energy_plan_cycle_modulations` (PK `modulation_id`, index `plan_id`)

Mode PLANNING :
1. Vérifier `active_plan.status == DRAFT`. KO → `SUPERSEDED_BY_OVERLAY`.
2. Insert directives caloric, load, cycle (si modulation_applied).
3. Annote `active_plan.energy_component_persisted=True`.

Modes REVIEW/MONITORING/NUTRITION_ESCALATION : pas d'écriture plan. Contrat alimente synthèse Head Coach ou dispatch escalades.

**Dispatch `flag_for_recovery_coach`** selon `urgency` :

- `next_report` : noté en state technique, Recovery consulté au prochain weekly report.
- `proactive_24h` : event Recovery consultation sur scheduler 24h, respect plafond proactif.
- `immediate_takeover` : bypass plafond, invocation immédiate Recovery Coach avec trigger `MONITORING_EA` et `monitoring_event_payload.escalation_source="energy_coach"`.

**Séquence `immediate_takeover`** :

```
EnergyAssessment
  ├─ clinical_escalation.required=True + urgency=immediate
  └─ flag_for_recovery.urgency=immediate_takeover
       │
       ▼
Recovery consultation immédiate (trigger MONITORING_EA)
       │
       ▼
RecoveryAssessment probable severity=critical + action=escalate_to_takeover
       │
       ▼
activate_clinical_frame → recovery_takeover graph démarre
```

Le chemin est **EA → Recovery consultation → Recovery takeover**, pas **EA → takeover direct**. Droit de veto Recovery préservé.

### 8.7 Mode dégradé FFM unavailable

Quand `ffm_source=unavailable`, Energy Coach ne peut pas calculer EA normalisé :

1. `ea_current_estimated = None`, interprétation limitée à OPTIMAL/LOW_NORMAL avec flag fort.
2. `flag_for_head_coach` obligatoire (EA4), typiquement `EA_LOW_NORMAL_TRENDING_DOWN` avec mention limitation.
3. Si proxys convergent vers suspicion : `clinical_escalation.required=True` avec `external_referral_suggested=True` pour inviter mesure FFM fiable.

### 8.8 Composante énergie du plan

Delta B3 sur `ActivePlan` (B1 §4.6) : champ `energy_component_persisted: bool = False`.

Tables indexées par `plan_id`. FK soft vers `active_plan.plan_id`.

### 8.9 Interaction Nutrition et escalade

Escalade Nutrition → Energy via `NutritionVerdict.pass_to_energy_coach` (§6). Coordinator invoque Energy avec trigger `ESCALATION_NUTRITION_TO_ENERGY` et `view.escalation_context` populé.

Energy ne ré-escalade **pas** vers Nutrition. Frontière clinique à sens unique. Energy peut `notes_for_head_coach` mentionner un ajustement nutritionnel ; pas d'escalade typée.

### 8.10 Fall-through spécifique

Voir §7. Scénarios :
- MONITORING avec takeover activé entre émission et consommation : plan mutations `SUPERSEDED_BY_OVERLAY`, `flag_for_recovery_coach` avec `urgency=immediate_takeover` court-circuité (`IDEMPOTENT_NOOP`).
- PLANNING avec `onboarding_reentry_active` activé : `SUPERSEDED_BY_OVERLAY`, re-invocation après re-entry.
- NUTRITION_ESCALATION consommé alors que Nutrition a rétracté l'escalade : Assessment reste valide, appliqué normalement.

---

## 9. `FollowupQuestionSet` (Onboarding Coach en consultation)

### 9.1 Émetteur, trigger, contexte

Émis par Onboarding Coach en consultation exclusive. Trigger unique `FOLLOWUP_CONSULT_ONBOARDING`, Phase 5 du parcours.

Contexte : après baseline, `compare_declarative_vs_observed` produit `BaselineObservations` injecté dans la vue via `ViewContext.baseline_observations` (B2 VC2). L'Onboarding Coach produit un set de questions ciblées ; le Head Coach reformule et pose en façade.

### 9.2 Structure

```python
class QuestionTarget(str, Enum):
    # Axes sous-profils
    CAPACITY = "capacity"
    TECHNIQUE = "technique"
    HISTORY = "history"
    OBJECTIVE = "objective"
    CONSTRAINTS = "constraints"
    # Cas particuliers
    CONTRADICTION_RESOLUTION = "contradiction_resolution"
    BASELINE_INSUFFICIENT = "baseline_insufficient"


class QuestionPriority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SubProfilePath(str, Enum):
    OBJECTIVE_PROFILE_PRIMARY = "objective_profile.primary"
    OBJECTIVE_PROFILE_SECONDARY = "objective_profile.secondary"
    OBJECTIVE_PROFILE_TRADE_OFFS = "objective_profile.trade_offs_acknowledged"
    EXPERIENCE_PROFILE_BY_DISCIPLINE = "experience_profile.by_discipline"
    PRACTICAL_CONSTRAINTS_AVAILABILITY = "practical_constraints.available_days"
    PRACTICAL_CONSTRAINTS_EQUIPMENT = "practical_constraints.equipment"
    PRACTICAL_CONSTRAINTS_SLEEP = "practical_constraints.sleep"
    PRACTICAL_CONSTRAINTS_WORK = "practical_constraints.work"
    PRACTICAL_CONSTRAINTS_MEALS = "practical_constraints.meals"
    INJURY_HISTORY = "injury_history.injuries"


class FollowupQuestion(BaseModel):
    question_id: str = Field(..., description="UUID v4 stable sur thread")

    question: str = Field(..., min_length=10, max_length=400)
    targets: list[QuestionTarget] = Field(..., min_length=1, max_length=3)
    rationale: str = Field(..., min_length=10, max_length=300)
    priority: QuestionPriority

    discipline_scope: Discipline | None = None

    target_sub_profile_paths: list[SubProfilePath] = Field(..., min_length=1, max_length=3)

    expected_response_format: Literal[
        "free_text", "numeric_value", "yes_no", "enum_choice",
        "date_or_duration", "multi_select",
    ]
    expected_enum_options: list[str] | None = Field(None, max_length=10)

    reformulation_hints: str | None = Field(None, max_length=200)

    @model_validator(mode="after")
    def _validate_enum_options(self):
        """FQ1 — enum_options requis ssi format ∈ {enum_choice, multi_select}."""
        needs = self.expected_response_format in {"enum_choice", "multi_select"}
        if needs and not self.expected_enum_options:
            raise ValueError(f"format={self.expected_response_format} requires enum_options")
        if not needs and self.expected_enum_options is not None:
            raise ValueError(f"enum_options forbidden for format={self.expected_response_format}")
        return self

    @model_validator(mode="after")
    def _validate_discipline_scope(self):
        """FQ2 — discipline_scope requis ssi EXPERIENCE_PROFILE_BY_DISCIPLINE."""
        needs = SubProfilePath.EXPERIENCE_PROFILE_BY_DISCIPLINE in self.target_sub_profile_paths
        if needs and self.discipline_scope is None:
            raise ValueError("EXPERIENCE_PROFILE_BY_DISCIPLINE requires discipline_scope")
        if not needs and self.discipline_scope is not None:
            raise ValueError("discipline_scope requires EXPERIENCE_PROFILE_BY_DISCIPLINE in paths")
        return self

    @model_validator(mode="after")
    def _validate_target_path_coherence(self):
        """FQ3 — targets ↔ target_sub_profile_paths cohérents."""
        coherence = {
            QuestionTarget.OBJECTIVE: {
                SubProfilePath.OBJECTIVE_PROFILE_PRIMARY,
                SubProfilePath.OBJECTIVE_PROFILE_SECONDARY,
                SubProfilePath.OBJECTIVE_PROFILE_TRADE_OFFS,
            },
            QuestionTarget.CAPACITY: {SubProfilePath.EXPERIENCE_PROFILE_BY_DISCIPLINE},
            QuestionTarget.TECHNIQUE: {SubProfilePath.EXPERIENCE_PROFILE_BY_DISCIPLINE},
            QuestionTarget.HISTORY: {SubProfilePath.EXPERIENCE_PROFILE_BY_DISCIPLINE},
            QuestionTarget.CONSTRAINTS: {
                SubProfilePath.PRACTICAL_CONSTRAINTS_AVAILABILITY,
                SubProfilePath.PRACTICAL_CONSTRAINTS_EQUIPMENT,
                SubProfilePath.PRACTICAL_CONSTRAINTS_SLEEP,
                SubProfilePath.PRACTICAL_CONSTRAINTS_WORK,
                SubProfilePath.PRACTICAL_CONSTRAINTS_MEALS,
            },
        }
        for target in self.targets:
            if target in {
                QuestionTarget.CONTRADICTION_RESOLUTION,
                QuestionTarget.BASELINE_INSUFFICIENT,
            }:
                continue
            admissible = coherence[target]
            if not set(self.target_sub_profile_paths) & admissible:
                raise ValueError(f"target={target} incohérent avec paths. Admissible: {admissible}")
        return self


class FollowupTransitionOutcome(str, Enum):
    READY_FOR_FIRST_PERSONALIZED = "ready_for_first_personalized"
    EXTEND_BASELINE_RECOMMENDED = "extend_baseline_recommended"
    REENTRY_ONBOARDING_RECOMMENDED = "reentry_onboarding_recommended"


class FollowupQuestionSet(BaseModel):
    metadata: ContractMetadata

    questions: list[FollowupQuestion] = Field(..., min_length=0, max_length=5)
    outcome: FollowupTransitionOutcome
    diagnostic_summary: str = Field(..., min_length=20, max_length=500)
    contradictions_detected: list[str] = Field(default_factory=list, max_length=5)

    baseline_extension_proposed_days: int | None = Field(None, ge=7, le=14)
    reentry_blocks_proposed: list[Literal[
        "objectives", "experience", "injuries", "constraints",
    ]] = Field(default_factory=list, max_length=4)

    notes_for_head_coach: str | None = Field(None, max_length=500)

    @model_validator(mode="after")
    def _validate_emitter(self):
        """FQS1 — emitted_by == ONBOARDING."""
        if self.metadata.emitted_by != AgentId.ONBOARDING:
            raise ValueError("emitted_by doit être ONBOARDING")
        return self

    @model_validator(mode="after")
    def _validate_trigger(self):
        """FQS2 — trigger == FOLLOWUP_CONSULT_ONBOARDING exclusif."""
        if self.metadata.invocation_trigger != InvocationTrigger.FOLLOWUP_CONSULT_ONBOARDING:
            raise ValueError("FollowupQuestionSet: seul FOLLOWUP_CONSULT_ONBOARDING autorisé")
        return self

    @model_validator(mode="after")
    def _validate_outcome_questions_coherence(self):
        """FQS3 — READY requires at least 1 HIGH priority question."""
        if self.outcome == FollowupTransitionOutcome.READY_FOR_FIRST_PERSONALIZED:
            high_count = sum(1 for q in self.questions if q.priority == QuestionPriority.HIGH)
            if high_count == 0:
                raise ValueError("READY requires at least 1 HIGH question")
        return self

    @model_validator(mode="after")
    def _validate_outcome_conditional_fields(self):
        """FQS4 — champs conditionnels par outcome."""
        if self.outcome == FollowupTransitionOutcome.EXTEND_BASELINE_RECOMMENDED:
            if self.baseline_extension_proposed_days is None:
                raise ValueError("EXTEND_BASELINE requires baseline_extension_proposed_days")
            if self.reentry_blocks_proposed:
                raise ValueError("reentry_blocks forbidden for EXTEND_BASELINE")
        elif self.outcome == FollowupTransitionOutcome.REENTRY_ONBOARDING_RECOMMENDED:
            if not self.reentry_blocks_proposed:
                raise ValueError("REENTRY requires non-empty reentry_blocks_proposed")
            if self.baseline_extension_proposed_days is not None:
                raise ValueError("baseline_extension forbidden for REENTRY")
        else:
            if self.baseline_extension_proposed_days or self.reentry_blocks_proposed:
                raise ValueError("extension/reentry forbidden for READY")
        return self

    @model_validator(mode="after")
    def _validate_contradictions_outcome_coherence(self):
        """FQS5 — contradictions non-vides + outcome READY nécessite question CONTRADICTION_RESOLUTION."""
        if self.contradictions_detected \
                and self.outcome == FollowupTransitionOutcome.READY_FOR_FIRST_PERSONALIZED:
            has_contradiction_q = any(
                QuestionTarget.CONTRADICTION_RESOLUTION in q.targets
                for q in self.questions
            )
            if not has_contradiction_q:
                raise ValueError("contradictions_detected + READY requires CONTRADICTION_RESOLUTION question")
        return self

    @model_validator(mode="after")
    def _validate_questions_ordering(self):
        """FQS6 — HIGH > MEDIUM > LOW."""
        order = {QuestionPriority.HIGH: 0, QuestionPriority.MEDIUM: 1, QuestionPriority.LOW: 2}
        for i in range(len(self.questions) - 1):
            if order[self.questions[i].priority] > order[self.questions[i + 1].priority]:
                raise ValueError("questions must be ordered HIGH > MEDIUM > LOW")
        return self

    @model_validator(mode="after")
    def _validate_question_ids_unique(self):
        """FQS7 — question_id uniques."""
        ids = [q.question_id for q in self.questions]
        if len(ids) != len(set(ids)):
            raise ValueError("question_id doivent être uniques")
        return self
```

### 9.3 Invariants vue ↔ contrat (niveau node)

| ID | Prédicat | Action |
|---|---|---|
| FQS8 | `view.baseline_observations IS NOT NULL` | reject construction en amont |
| FQS9 | Questions avec `target=CONTRADICTION_RESOLUTION` référencent contradictions existantes | warn |
| FQS10 | `discipline_scope ∈ view.scope.peer_disciplines_active` | reject, retry |
| FQS11 | `reentry_blocks_proposed` couvre les contradictions détectées | warn |
| FQS12 | `baseline_extension_proposed_days` cohérent avec `insufficient_data_reason` | warn |

### 9.4 Mécanique du flow

```
FollowupQuestionSet
        │
        ▼
consume_followup_set
        │
        ├── EXTEND_BASELINE → extend_baseline node (pas de question posée)
        ├── REENTRY → trigger_reentry_onboarding (overlay + invoke onboarding partiel)
        │
        └── READY → head_coach_ask_question (boucle)
                        │
                        ▼
                  collect_response [HITL]
                        │
                        ▼
                  update_profile_deltas
                        │
                        ▼
               [boucle sur questions restantes]
                        │
                        ▼
               dispatch_to_plan_generation
```

**`consume_followup_set`** : valide FQS1-FQS12, persiste en `contract_emissions`, branch sur `outcome`.

**`head_coach_ask_question`** (boucle) : reformule chaque question selon posture façade, HITL interrupt, réponse passée à `update_profile_deltas` avec `question_id`.

**Invariant de boucle FQ-L1** : si user refuse une question HIGH, bascule `EXTEND_BASELINE`.
**Invariant FQ-L2** : ordre HIGH d'abord, MEDIUM/LOW si temps disponible.

### 9.5 `update_profile_deltas`

Node qui consomme `(FollowupQuestion, user_response)`, produit `list[UpdateDelta]` :

```python
class UpdateDelta(BaseModel):
    question_id: str
    sub_profile_path: SubProfilePath
    discipline_scope: Discipline | None = None
    update_operation: Literal[
        "replace_field", "append_to_list", "remove_from_list",
        "update_nested_field", "acknowledge_trade_off",
    ]
    field_path: str
    new_value: dict | str | float | int | bool | list | None
    confidence: float = Field(..., ge=0.0, le=1.0)
    raw_response_excerpt: str = Field(..., max_length=500)


class UpdateProfileDeltasOutcome(BaseModel):
    question_id: str
    deltas_applied: list[UpdateDelta]
    deltas_deferred_for_confirmation: list[UpdateDelta]
    # confidence < 0.7 → Head Coach paraphrase + confirm
    deltas_rejected: list[dict]
    interpretation_notes: str | None = None
```

Routage par `SubProfilePath` (handlers dédiés, valident contre B1 §2) :
- `OBJECTIVE_PROFILE_*` : replace ou update nested, bump `revision_count`.
- `EXPERIENCE_PROFILE_BY_DISCIPLINE` : update granulaire `DisciplineExperience`, reset `bloc_marked_insufficient` si comblé.
- `PRACTICAL_CONSTRAINTS_*` : update granulaire, `last_updated_by="chat_turn_constraint_change"`.
- `INJURY_HISTORY` : append avec `declared_by="user_direct_correction"`. Si blessure **active**, escalade `CHAT_INJURY_REPORT` → takeover, pas Phase 5.

Idempotence : table `processed_followup_deltas (question_id PK, applied_at, outcome)`.

### 9.6 Transition finale `dispatch_to_plan_generation`

1. Vérifie tous UpdateDelta HIGH appliqués (pas en deferred). Si deferred bloque → confirmation Head Coach ; échec → `EXTEND_BASELINE`.
2. Mute `journey_phase = steady_state`.
3. Signal Coordinator pour invoquer `plan_generation` mode `first_personalized`.
4. Ferme thread `followup_transition`.

### 9.7 Fall-through spécifique

Voir §7. Scénarios :
- Takeover activé mid-Phase 5 : thread suspendu, `SUPERSEDED_BY_OVERLAY`. Reprise conditionnelle post-takeover.
- `handle_goal_change` mid-flow : FQS obsolète (contexte `BaselineObservations` changé), `SUPERSEDED_BY_NEWER`, nouveau `consult_onboarding_coach` post-reentry.
- Retry du contrat : table `processed_followup_deltas` conserve réponses déjà collectées par `question_id`, flow reprend à la question non posée.


---

## 10. `LogisticAdjustment` (Head Coach)

### 10.1 Émetteur, trigger, périmètre

Émis par Head Coach exclusivement, trigger unique `CHAT_ADJUSTMENT_REQUEST` niveau **logistique uniquement**. Trois niveaux possibles dans `handle_adjustment_request` :

| Niveau | Traitement | Contrat B3 |
|---|---|---|
| Logistique (jours, ordre, créneaux, lieu) | `apply_logistic_adjustment` | `LogisticAdjustment` |
| Volume / intensité | Refus, message direct avec explication | Aucun |
| Objectif / direction | Signal `redirect_to_onboarding_reentry`, overlay activé | Aucun |

Seul le niveau logistique produit un contrat structuré.

### 10.2 Types d'ajustements

Discriminated union à 6 types.

```python
class ReorderWithinWeek(BaseModel):
    adjustment_type: Literal["reorder_within_week"] = "reorder_within_week"
    week_start_date: date
    session_id_a: str
    session_id_b: str
    user_rationale_quote: str = Field(..., max_length=200)


class ShiftSessionDate(BaseModel):
    adjustment_type: Literal["shift_session_date"] = "shift_session_date"
    session_id: str
    original_date: date
    new_date: date
    days_shift: int = Field(..., ge=-7, le=7)
    user_rationale_quote: str = Field(..., max_length=200)

    @model_validator(mode="after")
    def _shift_coherence(self):
        expected = (self.new_date - self.original_date).days
        if expected != self.days_shift:
            raise ValueError(f"days_shift {self.days_shift} ≠ new-original {expected}")
        if self.days_shift == 0:
            raise ValueError("days_shift=0 pas de shift réel")
        return self


class ShiftMultipleSessions(BaseModel):
    adjustment_type: Literal["shift_multiple_sessions"] = "shift_multiple_sessions"
    session_ids: list[str] = Field(..., min_length=2, max_length=7)
    days_shift: int = Field(..., ge=-7, le=7)
    user_rationale_quote: str = Field(..., max_length=200)

    @model_validator(mode="after")
    def _shift_nonzero(self):
        if self.days_shift == 0:
            raise ValueError("days_shift=0")
        return self

    @model_validator(mode="after")
    def _session_ids_unique(self):
        if len(self.session_ids) != len(set(self.session_ids)):
            raise ValueError("session_ids uniques")
        return self


class RedistributeWeekly(BaseModel):
    """Restructuration semaine sans changer nombre de séances."""
    adjustment_type: Literal["redistribute_weekly"] = "redistribute_weekly"
    week_start_date: date
    new_schedule: dict[str, date] = Field(..., min_length=1, max_length=14)
    sessions_preserved_same_day: list[str] = Field(default_factory=list)
    user_rationale_quote: str = Field(..., max_length=200)

    @model_validator(mode="after")
    def _new_schedule_within_week(self):
        from datetime import timedelta
        week_end = self.week_start_date + timedelta(days=6)
        for sid, d in self.new_schedule.items():
            if not (self.week_start_date <= d <= week_end):
                raise ValueError(f"session {sid} hors semaine")
        return self

    @model_validator(mode="after")
    def _preserved_subset_of_schedule(self):
        if not set(self.sessions_preserved_same_day).issubset(set(self.new_schedule.keys())):
            raise ValueError("sessions_preserved_same_day ⊄ new_schedule.keys()")
        return self


class ModifyTimeSlot(BaseModel):
    adjustment_type: Literal["modify_time_slot"] = "modify_time_slot"
    session_id: str
    session_date: date
    new_preferred_time_of_day: Literal[
        "early_morning", "morning", "midday", "afternoon", "evening", "night",
    ]
    user_rationale_quote: str = Field(..., max_length=200)


class ModifyLocation(BaseModel):
    adjustment_type: Literal["modify_location"] = "modify_location"
    session_id: str
    session_date: date
    new_location_context: Literal[
        "commercial_gym", "home", "outdoor",
        "track", "pool_indoor", "pool_outdoor", "open_water", "mixed",
    ]
    equipment_compatible: bool = True
    user_rationale_quote: str = Field(..., max_length=200)

    @model_validator(mode="after")
    def _equipment_coherence(self):
        if not self.equipment_compatible:
            raise ValueError(
                "equipment_compatible=False : ModifyLocation ne peut être appliqué. "
                "Head Coach doit escalader vers block_regen."
            )
        return self


LogisticAdjustmentDiscriminated = Annotated[
    ReorderWithinWeek
    | ShiftSessionDate
    | ShiftMultipleSessions
    | RedistributeWeekly
    | ModifyTimeSlot
    | ModifyLocation,
    Field(discriminator="adjustment_type"),
]
```

### 10.3 Classe `LogisticAdjustment`

```python
HEAD_COACH_LOGISTIC_ADMISSIBLE_FLAGS: set[FlagCode] = {
    FlagCode.SCHEDULE_CONFLICT_DETECTED,
}


class LogisticAdjustment(BaseModel):
    metadata: ContractMetadata

    plan_id: str
    adjustment: LogisticAdjustmentDiscriminated

    user_request_summary: str = Field(..., min_length=10, max_length=400)
    impact_assessment: str = Field(..., max_length=500)
    user_confirmation_required: bool = True

    flag_for_head_coach: HeadCoachFlag | None = None
    notes_for_future_synthesis: str | None = Field(None, max_length=300)

    @model_validator(mode="after")
    def _validate_emitter(self):
        """LA1 — emitted_by == HEAD."""
        if self.metadata.emitted_by != AgentId.HEAD:
            raise ValueError("emitted_by doit être HEAD")
        return self

    @model_validator(mode="after")
    def _validate_trigger(self):
        """LA2 — trigger == CHAT_ADJUSTMENT_REQUEST exclusif."""
        if self.metadata.invocation_trigger != InvocationTrigger.CHAT_ADJUSTMENT_REQUEST:
            raise ValueError("seul CHAT_ADJUSTMENT_REQUEST autorisé")
        return self

    @model_validator(mode="after")
    def _validate_flag_admissibility(self):
        """LA3 — flag_for_head_coach ∈ HEAD_COACH_LOGISTIC_ADMISSIBLE_FLAGS."""
        if self.flag_for_head_coach is not None \
                and self.flag_for_head_coach.code not in HEAD_COACH_LOGISTIC_ADMISSIBLE_FLAGS:
            raise ValueError(f"Flag {self.flag_for_head_coach.code} hors périmètre logistique")
        return self

    @model_validator(mode="after")
    def _validate_notes_linked_to_flag(self):
        """LA4 — notes_for_future_synthesis ⇒ flag_for_head_coach présent."""
        if self.notes_for_future_synthesis is not None and self.flag_for_head_coach is None:
            raise ValueError("notes_for_future_synthesis requires flag_for_head_coach")
        return self
```

### 10.4 Invariants vue ↔ state (niveau node)

| ID | Prédicat | Action |
|---|---|---|
| LA5 | `plan_id == active_plan.plan_id` | reject, retry |
| LA6 | `active_plan.status == ACTIVE` | reject, retry |
| LA7 | `recovery_takeover_active == False` | `SUPERSEDED_BY_OVERLAY` |
| LA8 | `onboarding_reentry_active == False` | `SUPERSEDED_BY_OVERLAY` |
| LA9 | Reorder : sessions dans même semaine, UPCOMING | reject |
| LA10 | ShiftSession : UPCOMING, `new_date` dans bloc courant | reject |
| LA11 | ShiftMultiple : toutes dans même bloc, UPCOMING, même semaine après shift | reject |
| LA12 | Redistribute : toutes UPCOMING, bloc courant, nombre préservé | reject |
| LA13 | ModifyTimeSlot : `new_preferred_time_of_day` cohérent avec `practical_constraints.available_days` | warn/reject |
| LA14 | ModifyLocation : `new_location_context ∈ primary_location ∪ secondary_locations` | reject |
| LA15 | Pas de conflit temporel après shift | reject avec suggestion |
| LA16 | Respect contre-indications blessures actives | reject |
| LA17 | `active_plan.modification_count < 20` | reject avec message « propose block_regen » |

### 10.5 Mécanique `apply_logistic_adjustment`

Dispatch par `adjustment_type`. Mutations atomiques :

```
LogisticAdjustment
        │
        ▼
Pre-checks LA5–LA17
        │
        ▼
Snapshot pré-modification (hash PrescribedSession)
        │
        ▼
Dispatch par type :
  reorder → swap scheduled_date
  shift_session → update scheduled_date
  shift_multiple → update N sessions
  redistribute → update new_schedule
  modify_time → preferred_time_of_day_override
  modify_location → location_context_override
        │
        ▼
Pour chaque session mutée :
  - append SessionModification à modification_history
  - update last_modified_at
  - recalcul projected_strain si shift cross-semaine
        │
        ▼
Update active_plan :
  - append modification_history (logistic_adjustment)
  - bump modification_count
        │
        ▼
Notify user (confirm ou acknowledge)
```

**Flow confirmation required (défaut)** :
1. User demande, Head Coach émet `LogisticAdjustment` avec `user_confirmation_required=True`.
2. `apply_logistic_adjustment` applique en staging (table `pending_logistic_adjustments`).
3. Head Coach paraphrase : « Je propose X, tu confirmes ? »
4. HITL interrupt. User confirm ou annule.
5. `confirm_logistic_adjustment` (nouveau node) applique si confirm, supprime staging si annule.

**Flow no confirmation (shift marginal)** :
1. Head Coach émet avec `user_confirmation_required=False`.
2. Application directe, acknowledge au user.

**Pattern de détection long terme** : le node compte `LogisticAdjustment` sur 14 jours. Si `count >= 5` ou pattern récurrent (même jour shifté 3+ fois), annote `AthleteState.validation_warnings` pour surfaçage au prochain `handle_weekly_report`.

### 10.6 Delta `PrescribedSessionCommon`

Nouveaux champs §3.2 :
- `preferred_time_of_day_override: Literal | None` (set par `ModifyTimeSlot`)
- `location_context_override: Literal | None` (set par `ModifyLocation`)

Overrides explicitement distincts des contraintes cœur. Ne modifient ni `session_type`, ni volume, ni intensité, ni exercises/intervals/sets.

### 10.7 Fall-through spécifique

Voir §7. Scénarios :
- Takeover entre émission et consommation : plan suspendu, `SUPERSEDED_BY_OVERLAY`. User doit re-demander post-takeover.
- Session déjà modifiée par contrat plus récent : `SUPERSEDED_BY_NEWER`.
- Session déjà COMPLETED : `REJECTED_VALIDATION` (LA9/LA10).

### 10.8 Frontière `logistic vs block_regen`

Phase C du Head Coach précisera. Cas de vigilance :

| Demande apparente | Vraie nature |
|---|---|
| « Permuter 2 séances » | Logistique si pas de conflit strain |
| « Voyage 10 jours » | block_regen |
| « 2 séances au lieu de 4 » | Dépend : ponctuel → shift+skip ; structurel → block_regen |
| « Running en vélo » | Refus logistique + explication |
| « Home workout remplace salle » | Si equipment compatible → ModifyLocation ; sinon block_regen ou skip |

Principe : en doute, escalader (`block_regen` ou refus) plutôt que `LogisticAdjustment` approximatif.

---

## 11. `OverrideFlagReset` (Head Coach)

### 11.1 Émetteur, triggers, scope

Émis par Head Coach. Symétrique de `flag_override_pattern` (émis par Recovery Coach via `RecoveryAssessment.override_pattern.detected=True`).

Triggers admissibles : `CHAT_FREE_QUESTION`, `CHAT_WEEKLY_REPORT`, `CHAT_DAILY_CHECKIN`.

### 11.2 Motifs et classe

```python
class ResetBasisEnum(str, Enum):
    USER_REPORTED_RESOLUTION = "user_reported_resolution"
    OBSERVED_CONVERGENCE_SIGNALS = "observed_convergence_signals"
    CONTEXT_CHANGE_RESOLVED = "context_change_resolved"
    WEEKLY_SYNTHESIS_REASSESSMENT = "weekly_synthesis_reassessment"
    SYSTEM_ESCALATION_OUTDATED = "system_escalation_outdated"


class OverrideFlagReset(BaseModel):
    metadata: ContractMetadata

    reset_basis: ResetBasisEnum
    reset_rationale: str = Field(..., min_length=30, max_length=500)

    observed_signals_snapshot: dict[Literal[
        "user_signal_converged_days",
        "hrv_trend_normalized",
        "sleep_quality_recovered",
        "strain_aggregate_normalized",
        "allostatic_load_zone_normal",
        "days_since_flag_set",
    ], int | bool] = Field(default_factory=dict)

    original_set_at: datetime | None = None
    days_flag_was_active: int | None = Field(None, ge=0, le=365)

    user_acknowledgment_included: bool = False

    @model_validator(mode="after")
    def _validate_emitter(self):
        """OFR1 — emitted_by == HEAD."""
        if self.metadata.emitted_by != AgentId.HEAD:
            raise ValueError("emitted_by doit être HEAD")
        return self

    @model_validator(mode="after")
    def _validate_trigger_admissible(self):
        """OFR2 — trigger ∈ admissibles."""
        admissible = {
            InvocationTrigger.CHAT_FREE_QUESTION,
            InvocationTrigger.CHAT_WEEKLY_REPORT,
            InvocationTrigger.CHAT_DAILY_CHECKIN,
        }
        if self.metadata.invocation_trigger not in admissible:
            raise ValueError(f"trigger {self.metadata.invocation_trigger} non admissible")
        return self

    @model_validator(mode="after")
    def _validate_signals_per_basis(self):
        """OFR3 — snapshot requiert champs minimaux selon basis."""
        basis = self.reset_basis
        signals = self.observed_signals_snapshot

        if basis == ResetBasisEnum.OBSERVED_CONVERGENCE_SIGNALS:
            bool_signals = [
                signals.get("hrv_trend_normalized", False),
                signals.get("sleep_quality_recovered", False),
                signals.get("strain_aggregate_normalized", False),
                signals.get("allostatic_load_zone_normal", False),
            ]
            if sum(1 for s in bool_signals if s) < 2:
                raise ValueError("OBSERVED_CONVERGENCE requires at least 2 normalized signals")
            if signals.get("user_signal_converged_days", 0) < 3:
                raise ValueError("OBSERVED_CONVERGENCE requires converged_days >= 3")

        elif basis == ResetBasisEnum.USER_REPORTED_RESOLUTION:
            converged = signals.get("user_signal_converged_days", 0)
            bool_signals = [
                signals.get("hrv_trend_normalized", False),
                signals.get("sleep_quality_recovered", False),
                signals.get("strain_aggregate_normalized", False),
            ]
            if converged < 1 and not any(bool_signals):
                raise ValueError("USER_REPORTED requires converged >= 1 OR at least 1 normalized signal")

        elif basis == ResetBasisEnum.SYSTEM_ESCALATION_OUTDATED:
            if signals.get("days_since_flag_set", 0) < 30:
                raise ValueError("SYSTEM_ESCALATION requires days_since_flag_set >= 30")

        elif basis == ResetBasisEnum.WEEKLY_SYNTHESIS_REASSESSMENT:
            if self.metadata.invocation_trigger != InvocationTrigger.CHAT_WEEKLY_REPORT:
                raise ValueError("WEEKLY_SYNTHESIS requires trigger=CHAT_WEEKLY_REPORT")
        return self

    @model_validator(mode="after")
    def _validate_days_consistency(self):
        """OFR4 — days_flag_was_active cohérent avec original_set_at."""
        if self.original_set_at is None and self.days_flag_was_active is None:
            return self
        if self.original_set_at is None or self.days_flag_was_active is None:
            raise ValueError("original_set_at et days_flag_was_active ensemble")
        expected = (self.metadata.emitted_at - self.original_set_at).days
        if abs(expected - self.days_flag_was_active) > 1:
            raise ValueError(f"days_flag_was_active={self.days_flag_was_active} ≠ {expected}")
        return self
```

### 11.3 Invariants vue ↔ state (niveau node)

| ID | Prédicat | Action |
|---|---|---|
| OFR5 | `persistent_override_pattern.active == True` au moment de consommation | `IDEMPOTENT_NOOP` si déjà reset |
| OFR6 | `recovery_takeover_active == False` | `SUPERSEDED_BY_OVERLAY` |
| OFR7 | `contract.original_set_at == state.persistent_override_pattern.first_detected_at` | reject |
| OFR8 | `days_flag_was_active >= 2` (anti-oscillation) | reject, warn |
| OFR9 | `days_since_flag_set` cohérent avec state | reject |
| OFR10 | Pas de `RecoveryAssessment` récent (48h) avec `override_pattern.detected=True` | reject avec message |

### 11.4 Mécanique `reset_override_flag`

```
OverrideFlagReset
        │
        ▼
Pre-checks OFR1–OFR10
        │
        ├── OFR5 fail → IDEMPOTENT_NOOP
        ├── OFR6 fail → SUPERSEDED_BY_OVERLAY
        ├── OFR10 fail → reject
        │
        ▼
Snapshot pré-mutation
        │
        ▼
Mutations persistent_override_pattern :
  - active = False
  - reset_by = "head_coach"
  - reset_at = now
  - first_detected_at conservé (pas clear)
        │
        ▼
Insert override_flag_history :
  - set_at, set_by, reset_at, reset_by, reset_basis,
    reset_rationale, duration_days, source_contract_id
        │
        ▼
Persist processed_contracts outcome=APPLIED
```

Table `override_flag_history` dédiée pour audit long-terme des oscillations set/reset, distincte de `contract_emissions` (agrège les paires set/reset avec contexte joint).

### 11.5 Re-flag légitime post-reset

Un Recovery Coach peut re-détecter un pattern similaire après reset, émettre un nouveau `RecoveryAssessment` avec `override_pattern.detected=True`. Cycle set → reset → re-set admis. Trace dans `override_flag_history`.

M�canisme anti-thrashing reporté Phase C/D : si set/reset dans fenêtre courte (< 7 jours), Head Coach investigue davantage avant reset. Pas bloquant au niveau B3.

### 11.6 `user_acknowledgment_included` et UX

Distinction :
- **Reset silencieux** (`False`) : cas SYSTEM_ESCALATION_OUTDATED ou OBSERVED_CONVERGENCE. Minimise charge cognitive user.
- **Reset avec acknowledgment** (`True`) : cas USER_REPORTED_RESOLUTION ou WEEKLY_SYNTHESIS. Courtoisie de fermeture, pas dramatisation.

Le contrat trace le choix. Décision au Head Coach (prompt Phase C). Le node n'impose pas.

### 11.7 Fall-through spécifique

- Takeover activé entre émission et consommation : OFR6 → `SUPERSEDED_BY_OVERLAY`. Flag reste posé (posture clinique), Head Coach peut ré-émettre post-takeover si pertinent.
- Race condition set/reset simultanés : ordre par `metadata.emitted_at`. Reset puis re-set : nouveau `first_detected_at`, trace séparée dans history.
- Retry avec même `contract_id` : `IDEMPOTENT_NOOP`.

---

## 12. Synthèse multi-flags Head Coach

### 12.1 Situations de déclenchement

La synthèse multi-flags est invoquée dans 5 situations, toutes via l'algorithme de pré-traitement §12.4.

| Situation | Trigger | Contrats sources |
|---|---|---|
| Rapport hebdomadaire | `CHAT_WEEKLY_REPORT` | Recommendation(review)×4 + NutritionVerdict(weekly) + RecoveryAssessment + EnergyAssessment |
| Plan generation (delegate) | Post-`build_proposed_plan` | Recommendation(planning)×N + NutritionVerdict(planning) + EnergyAssessment(planning) |
| Check-in quotidien | `CHAT_DAILY_CHECKIN` | NutritionVerdict(daily) |
| Monitoring proactif | Events monitoring | RecoveryAssessment(monitoring) + EnergyAssessment(monitoring) |
| Adjustment request | `CHAT_ADJUSTMENT_REQUEST` | LogisticAdjustment + contrats récents |

Typiquement 0-2 flags sauf `CHAT_WEEKLY_REPORT` qui peut produire ≥ 3.

### 12.2 Structure `AggregatedFlagsPayload`

```python
class FlagSource(BaseModel):
    emitter_agent: AgentId
    contract_type: Literal[
        "Recommendation", "NutritionVerdict", "RecoveryAssessment",
        "EnergyAssessment", "LogisticAdjustment",
    ]
    contract_id: str
    emitted_at: datetime


class NormalizedFlag(BaseModel):
    """Flag unifié pour traitement homogène (absorbe HeadCoachFlag et RecoveryCoachFlag)."""
    source: FlagSource
    code: FlagCode
    severity: FlagSeverity
    message: str = Field(..., max_length=300)
    structured_payload: dict = Field(default_factory=dict)
    was_routed_from_recovery_coach_flag: bool = False


class ClinicalHierarchyRank(int, Enum):
    RECOVERY = 0
    ENERGY = 1
    NUTRITION = 2
    DISCIPLINE = 3


class AggregatedNote(BaseModel):
    source: FlagSource
    note: str = Field(..., max_length=500)


class FlagCorrelation(BaseModel):
    correlation_id: str
    pattern_name: Literal[
        "relative_underfueling",
        "overreaching_accumulation",
        "recovery_compromise_convergent",
        "compliance_disengagement",
        "schedule_stress_pattern",
        "red_s_multi_axis",
    ]
    constituent_flag_codes: list[FlagCode] = Field(..., min_length=2)
    confidence: float = Field(..., ge=0.0, le=1.0)
    narrative_hint: str = Field(..., max_length=400)
    constituent_flag_indices: list[int] = Field(..., min_length=2)


class AggregatedFlagsPayload(BaseModel):
    flags: list[NormalizedFlag]
    detected_correlations: list[FlagCorrelation] = Field(default_factory=list)
    aggregated_notes: list[AggregatedNote] = Field(default_factory=list)
    synthesis_strategy: Literal[
        "direct_listing",
        "narrative_synthesis",
        "single_flag_reformulation",
        "no_flags_only_notes",
        "nothing_to_report",
    ]
    invocation_context: Literal[
        "weekly_report", "plan_generation_present", "daily_checkin",
        "monitoring_proactive", "adjustment_request",
    ]
    total_flags_raw_count: int = Field(..., ge=0)
```

### 12.3 Matrice de détection de corrélations

```python
CORRELATION_PATTERNS = {
    "relative_underfueling": {
        "required_codes_any_of": {
            FlagCode.EA_LOW_NORMAL_TRENDING_DOWN,
            FlagCode.EA_SUBCLINICAL,
            FlagCode.RED_S_SUSPECTED,
        },
        "required_codes_additional": {
            FlagCode.SLEEP_DEBT,
            FlagCode.COMPLIANCE_DROP,
            FlagCode.RPE_SYSTEMATIC_OVERSHOOT,
            FlagCode.HRV_DEGRADED,
        },
        "min_additional": 1,
        "min_severity": FlagSeverity.WATCH,
        "confidence_base": 0.75,
    },
    "overreaching_accumulation": {
        "required_codes_any_of": {
            FlagCode.HIGH_STRAIN_ACCUMULATED,
            FlagCode.DELOAD_SUGGESTED,
        },
        "required_codes_additional": {
            FlagCode.HRV_DEGRADED,
            FlagCode.RPE_SYSTEMATIC_OVERSHOOT,
            FlagCode.SLEEP_DEBT,
        },
        "min_additional": 1,
        "min_severity": FlagSeverity.WATCH,
        "confidence_base": 0.70,
    },
    "recovery_compromise_convergent": {
        "required_codes_exact": {FlagCode.HRV_DEGRADED, FlagCode.SLEEP_DEBT},
        "all_required": True,
        "min_severity": FlagSeverity.CONCERN,
        "confidence_base": 0.85,
    },
    "compliance_disengagement": {
        "required_codes_exact": {FlagCode.COMPLIANCE_DROP, FlagCode.OVERRIDE_PATTERN_DETECTED},
        "all_required": True,
        "min_severity": FlagSeverity.WATCH,
        "confidence_base": 0.80,
    },
    "schedule_stress_pattern": {
        "required_codes_any_of": {
            FlagCode.SCHEDULE_CONFLICT_DETECTED,
            FlagCode.OBJECTIVE_CONTRADICTION,
        },
        "min_count": 2,
        "min_severity": FlagSeverity.WATCH,
        "confidence_base": 0.60,
    },
    "red_s_multi_axis": {
        "required_codes_exact": {
            FlagCode.EA_SUBCLINICAL,
            FlagCode.HRV_DEGRADED,
            FlagCode.SLEEP_DEBT,
        },
        "all_required": True,
        "min_severity": FlagSeverity.CONCERN,
        "confidence_base": 0.90,
    },
}
```

Valeurs numériques indicatives B3, calibrées Phase C avec revue littérature.

### 12.4 Algorithme de pré-traitement

Déterministe, testable unitairement, exécuté par le Coordinator avant invocation LLM Head Coach.

**Étape 1 — Collecte et normalisation** : récupère contrats du même `correlation_id`, extrait `flag_for_head_coach` et `flag_for_recovery_coach` en `NormalizedFlag`, concatène `notes_for_head_coach`.

**Étape 2 — Déduplication** : deux flags équivalents si `(code, emitter_agent, severity)`. Deux flags `HIGH_STRAIN_ACCUMULATED` de coachs différents → gardés séparés.

**Étape 3 — Priorisation** : tri descendant par (ClinicalHierarchyRank, FlagSeverity, timestamp).

**Étape 4 — Détection corrélations** : évaluation de chaque `CORRELATION_PATTERNS` contre les flags dédupliqués.

**Étape 5 — Stratégie** :

```python
def choose_synthesis_strategy(flags, notes, correlations):
    n_flags = len(flags)
    n_notes = len(notes)

    if n_flags == 0 and n_notes == 0:
        return "nothing_to_report"
    if n_flags == 0 and n_notes > 0:
        return "no_flags_only_notes"
    if n_flags == 1:
        return "single_flag_reformulation"
    if n_flags == 2:
        if correlations and any(c.confidence >= 0.80 for c in correlations):
            return "narrative_synthesis"
        return "direct_listing"
    return "narrative_synthesis"  # n_flags >= 3
```

Seuil `< 3` vs `≥ 3` respecté (roster), affinement : 2 flags très corrélés basculent en narrative.

### 12.5 Consommation par le Head Coach

Le Head Coach reçoit en paramètres d'invocation LLM :
1. `HeadCoachView` (standard B2).
2. `AggregatedFlagsPayload` (input distinct).
3. Contrats structurés des agents consultés (également en input distinct).

Comportement par `synthesis_strategy` :

| Strategy | Comportement attendu |
|---|---|
| `nothing_to_report` | Pas de flags mentionnés, traiter la demande user |
| `no_flags_only_notes` | Reformulation douce des notes, sans dramatisation |
| `single_flag_reformulation` | Mention en 1-2 phrases, respect de la sévérité |
| `direct_listing` | Liste priorisée, pas de fusion narrative |
| `narrative_synthesis` | Narrativation autour de `correlations[0]`, flags non-corrélés listés en fin |

### 12.6 Format narrative_synthesis

Pattern recommandé Phase C à 4 blocs :

1. **Ouverture factuelle** (1 phrase) — pattern central observé, issu de `correlations[0].narrative_hint`.
2. **Éléments convergents** (2-4 phrases) — signaux soutenant le narratif.
3. **Implication clinique / directionnelle** (1-2 phrases) — ligne d'action.
4. **Flags mineurs non-corrélés** — rapide mention, sans juxtaposition lourde.

Longueur cible : 100-250 mots.

Exemple roster « tendinite + EA basse + baisse allure » :
> « Cette semaine, plusieurs signaux convergent vers un même phénomène : ton allure sur long run a baissé, l'apport énergétique moyen est en dessous de tes besoins sur 10 jours, et la zone tendineuse que tu avais mentionnée reste sensible. La lecture la plus cohérente est un stress tendineux lié à la sous-alimentation plutôt qu'à la charge d'entraînement. Je propose qu'on réduise la course de 30 % cette semaine et qu'on remonte l'apport à 2650 kcal jusqu'à stabilisation. Le Lifting reste sur sa trajectoire, à suivre. »

### 12.7 Invariants sur l'algorithme

| ID | Prédicat |
|---|---|
| MF1 | `total_flags_raw_count >= len(flags)` (dédup monotone) |
| MF2 | `flags` ordonné selon hiérarchie clinique descendante |
| MF3 | Chaque `correlation.constituent_flag_indices` référence indices valides |
| MF4 | `synthesis_strategy == nothing_to_report` ⇒ 0 flags ET 0 notes |
| MF5 | `synthesis_strategy == narrative_synthesis` ⇒ ≥ 2 flags (tolérance 2 si corrélation forte) |
| MF6 | Flag avec `was_routed_from_recovery_coach_flag=True` a `source.emitter_agent == RECOVERY` |
| MF7 | `detected_correlations` trié par `confidence` descendante |

### 12.8 Traçabilité de synthèse

Tables dédiées :
- `synthesis_payloads_log` : `AggregatedFlagsPayload` persisté pour audit.
- `synthesis_invocations` : lien `correlation_id ↔ payload_id ↔ message_id + contract_ids`.

Permet debug : retracer flags agrégés pour un message, vérifier stratégie correcte, identifier cas où synthèse LLM a ignoré des signaux injectés.

### 12.9 Cas particuliers

- **Pas de Recovery Coach actif mais pattern convergent détecté** : pattern `recovery_compromise_convergent` détecté sur flags Nutrition + Energy. Narrative signale, Head Coach peut proposer consultation Recovery proactive.
- **Overlay actif** : `recovery_takeover_active == True` court-circuite `CHAT_WEEKLY_REPORT`. Flags pre-takeover persistés mais pas synthétisés.
- **Aucun flag ni note** : `nothing_to_report`. Rapport factuel sans dimension problématique.
- **Flag mineur isolé en check-in** : `single_flag_reformulation`, 1 phrase sans développement.


---

## 13. Traitement des contrats fall-through

### 13.1 Principes

Un contrat est fall-through quand l'état du système a changé entre son émission (invocation LLM) et sa consommation (node dispatch), rendant sa mutation non pertinente ou dangereuse. Trois causes principales :

- **Overlay activé** : `recovery_takeover_active` ou `onboarding_reentry_active` passé à `True`.
- **Supersedure** : un contrat plus récent cible les mêmes entités.
- **Préconditions changées** : l'objet cible du contrat n'est plus dans l'état attendu.

Principe central : **persistance, pas drop silencieux**. Tout contrat émis est consigné en `contract_emissions` ; son `ContractProcessingOutcome` est systématiquement enregistré en `processed_contracts`. Audit forensique complet.

### 13.2 `ContractProcessingOutcome`

```python
class ContractProcessingOutcome(str, Enum):
    APPLIED = "applied"
    IDEMPOTENT_NOOP = "idempotent_noop"
    SUPERSEDED_BY_OVERLAY = "superseded_by_overlay"
    SUPERSEDED_BY_NEWER = "superseded_by_newer"
    SUPERSEDED_BY_STATE_CHANGE = "superseded_by_state_change"
    REJECTED_VALIDATION = "rejected_validation"
    REJECTED_SCHEMA_VERSION = "rejected_schema_version"
    DEFERRED_WAITING_PRECONDITION = "deferred_waiting_precondition"


class PartialApplicationOutcome(BaseModel):
    """Détail pour outcome=APPLIED quand certaines mutations sont droppées."""
    applied_mutations: list[str]
    dropped_mutations: list[dict]  # {"mutation": str, "reason": str}
    coverage_ratio: float = Field(..., ge=0.0, le=1.0)
```

Outcome `APPLIED` peut être partiel (ex : `LogisticAdjustment` sur 7 sessions dont 2 déjà modifiées ailleurs). `outcome_detail = PartialApplicationOutcome` distingue « tout appliqué » vs « partiellement appliqué ».

### 13.3 Matrice overlay × contract

| Overlay actif | Contract | Outcome appliqué |
|---|---|---|
| `recovery_takeover_active` | Recommendation (planning) | SUPERSEDED_BY_OVERLAY |
| `recovery_takeover_active` | Recommendation (review) | APPLIED (audit uniquement, pas de mutation) |
| `recovery_takeover_active` | NutritionVerdict (daily/planning) | SUPERSEDED_BY_OVERLAY |
| `recovery_takeover_active` | NutritionVerdict (weekly) | APPLIED (audit) |
| `recovery_takeover_active` | LogisticAdjustment | SUPERSEDED_BY_OVERLAY |
| `recovery_takeover_active` | OverrideFlagReset | SUPERSEDED_BY_OVERLAY |
| `recovery_takeover_active` | EnergyAssessment (planning) | SUPERSEDED_BY_OVERLAY |
| `recovery_takeover_active` | EnergyAssessment (monitoring) | APPLIED (flags consommés, pas mutation plan) |
| `onboarding_reentry_active` | Recommendation (planning) | SUPERSEDED_BY_OVERLAY |
| `onboarding_reentry_active` | NutritionVerdict (planning) | SUPERSEDED_BY_OVERLAY |
| `onboarding_reentry_active` | EnergyAssessment (planning) | SUPERSEDED_BY_OVERLAY |
| `onboarding_reentry_active` | LogisticAdjustment | SUPERSEDED_BY_OVERLAY |
| `onboarding_reentry_active` | RecoveryAssessment (consultation) | APPLIED (Recovery garde autorité) |
| `onboarding_reentry_active` | FollowupQuestionSet | APPLIED normalement |

Principe : mutations métier plan et nutrition bloquées par overlays. Consultation et audit Recovery toujours admissibles.

### 13.4 Supersedure entre contrats

`SUPERSEDED_BY_NEWER` : un contrat plus récent touche les mêmes entités avant consommation de celui-ci.

```python
SUPERSEDURE_CONFIGS: dict[type, dict] = {
    Recommendation: {
        "target_key_fields": ["discipline", "plan_id"],
        "window_seconds": 300,
    },
    NutritionVerdict: {
        "target_key_fields": ["verdict_mode", "daily_targets.target_date"],
        "window_seconds": 3600,
    },
    LogisticAdjustment: {
        "target_key_fields": ["plan_id", "adjustment.session_id"],
        "window_seconds": 600,
    },
    RecoveryAssessment: {
        # Pas de supersedure automatique : Recovery est canonique
        "no_auto_supersedure": True,
    },
    EnergyAssessment: {
        "target_key_fields": ["assessment_mode"],
        "window_seconds": 600,
    },
    OverrideFlagReset: {
        "target_key_fields": ["athlete_id"],
        "window_seconds": 60,
    },
}
```

Supersedure déterministe : si deux contrats concurrents pointent vers mêmes `target_key_fields` dans fenêtre `window_seconds`, l'ancien reçoit `SUPERSEDED_BY_NEWER`.

### 13.5 Supersedure par changement d'état (`SUPERSEDED_BY_STATE_CHANGE`)

Distincte des overlays. Couvre :
- Session en `COMPLETED` avant consommation d'un `LogisticAdjustment` qui la ciblait.
- Plan passé en `COMPLETED` avant consommation de `Recommendation` pour ce plan.
- `persistent_override_pattern.active=False` avant consommation d'un `OverrideFlagReset` (déjà reset).

Détection au pré-check node. Distinction vs `REJECTED_VALIDATION` : validation échoue sur schéma ou prédicat invariant ; `SUPERSEDED_BY_STATE_CHANGE` signale transition légitime de l'état cible.

### 13.6 Deferral (`DEFERRED_WAITING_PRECONDITION`)

Rare. Contrat valide mais précondition temporairement non satisfaite, ré-évaluation prochaine attendue utile.

```python
DEFERRAL_POLICIES: dict[type, dict] = {
    Recommendation: {
        "deferrable_conditions": [],  # planning deferral non admis (rejeter directement)
    },
    NutritionVerdict: {
        "deferrable_conditions": ["active_plan.status==DRAFT_PENDING_CONFIRMATION"],
        "max_defer_seconds": 600,
    },
    EnergyAssessment: {
        "deferrable_conditions": ["active_plan.status==DRAFT_PENDING_CONFIRMATION"],
        "max_defer_seconds": 600,
    },
}
```

Table `deferred_contracts (contract_id PK, deferred_until, retry_count, max_retries)`. Worker Phase D réessaie.

### 13.7 Pré-check séquentiel node

Chaque node consommateur exécute le pré-check dans l'ordre strict :

```
1. Overlay check → si match → SUPERSEDED_BY_OVERLAY
2. Supersedure check → si newer contract exists → SUPERSEDED_BY_NEWER
3. State change check → si target moved state → SUPERSEDED_BY_STATE_CHANGE
4. Precondition check → si deferrable → DEFERRED, sinon → REJECTED_VALIDATION
5. Schema version check → si unsupported → REJECTED_SCHEMA_VERSION
6. Idempotence check → si processed → IDEMPOTENT_NOOP
7. Dispatch → APPLIED (éventuellement partiel)
```

L'ordre est critique : overlays court-circuitent avant tout. La détection supersedure précède l'exécution coûteuse de validation complète.

### 13.8 Pas de re-émission automatique par défaut

Principe : un contrat `SUPERSEDED_*` n'est pas re-émis automatiquement par le Coordinator. La logique applicative décide :

- `recovery_takeover` invoque `plan_generation` explicitement au `handoff_to_baseline`, re-invocation des coachs disciplines (nouveau `correlation_id`, pas ré-émission du contrat supersedé).
- `onboarding_reentry` termine → trigger `dispatch_to_plan_generation` explicite.
- `LogisticAdjustment` supersedé : user re-demande manuellement (Head Coach reformule impact dans message).

Exception pour deferral (§13.6).

### 13.9 Logging et monitoring

```python
class FallThroughLogEntry(BaseModel):
    contract_id: str
    contract_type: str
    emitted_by: AgentId
    emitted_at: datetime
    processed_at: datetime
    outcome: ContractProcessingOutcome
    outcome_detail: str | dict
    superseding_contract_id: str | None = None
    overlay_active: dict[str, bool] | None = None
    precondition_failures: list[str] | None = None
```

Niveaux de log :
- `APPLIED`, `IDEMPOTENT_NOOP`, `SUPERSEDED_BY_*` attendus : INFO.
- `REJECTED_VALIDATION` inattendu : WARN.
- `DEFERRED` > `max_retries` sans résolution : ERROR.
- `REJECTED_SCHEMA_VERSION` : ERROR.

M�triques Phase D :
- Ratio `SUPERSEDED_BY_OVERLAY / total` par contract_type : détecte drift design (overlays trop fréquents).
- Temps moyen émission → consommation : détecte latences LangGraph.
- Retries par DEFERRED : détecte préconditions bloquantes.

### 13.10 Récapitulatif

| Outcome | Sémantique | Mutation state | Re-émission |
|---|---|---|---|
| APPLIED | Succès (total ou partiel) | Oui | Non |
| IDEMPOTENT_NOOP | Déjà traité | Non | Non |
| SUPERSEDED_BY_OVERLAY | Overlay bloque | Non | Selon graph |
| SUPERSEDED_BY_NEWER | Contrat plus récent prioritaire | Non | Non |
| SUPERSEDED_BY_STATE_CHANGE | Cible transitée légitimement | Non | Non |
| REJECTED_VALIDATION | Schéma / invariant | Non | Retry LLM possible |
| REJECTED_SCHEMA_VERSION | Major mismatch | Non | Dead-letter |
| DEFERRED_WAITING_PRECONDITION | Précondition bientôt vraie | Non | Oui, timer |

---

## 14. Invariants transversaux cross-contrats

### 14.1 Organisation

43 invariants formalisés sur 8 catégories. Trois niveaux d'application selon mécanisme d'enforcement (§14.10).

| Catégorie | IDs | Enforcement |
|---|---|---|
| Cross-contract Pydantic | CC1-CC8 | Coordinator agrégation |
| Cross-contract state | CCS1-CCS12 | Nodes + persistence layer |
| Temporel et ordering | CCT1-CCT6 | Graph orchestration + locks |
| Monitoring proactif | MP1-MP4 | Coordinator proactive gate |
| Threads LangGraph | CT1-CT4 | Graph entry/exit |
| Audit et traçabilité | CA1-CA5 | Coordinator + middleware |
| Cohérence vue ↔ contrat | CV1-CV4 | Validators Pydantic |
| Reconciliation périodique | REC1-REC4 | Scheduler |

### 14.2 Cross-contract Pydantic

Vérifiés par le Coordinator sur l'ensemble des contrats d'une invocation (même `correlation_id`). Pas dans validators individuels (pas d'accès aux autres contrats).

| ID | Prédicat | Action |
|---|---|---|
| CC1 | Tous contrats d'un `correlation_id` ont `emitted_at` dans fenêtre ≤ 5 min | WARN, continue |
| CC2 | `PLAN_GEN_DELEGATE_SPECIALISTS` : au plus 1 `Recommendation` par discipline | Garde le dernier, WARN |
| CC3 | `PLAN_GEN_DELEGATE_SPECIALISTS` : au plus 1 `NutritionVerdict`, 1 `EnergyAssessment` | Idem CC2 |
| CC4 | `NutritionVerdict.pass_to_energy_coach != None` ⇒ `EnergyAssessment(nutrition_escalation)` émis dans même invocation ou schedulé selon urgency | WARN si absent immédiat |
| CC5 | `EnergyAssessment.flag_for_recovery_coach.urgency == immediate_takeover` ⇒ `RecoveryAssessment` émis dans fenêtre +2 min | ERROR si absent, fail-fast |
| CC6 | Contrats d'une invocation `plan_generation` référencent même `plan_id` | Reject contrats divergents |
| CC7 | `CHAT_WEEKLY_REPORT` : modes cohérents (`Recommendation(review)`, `NutritionVerdict(weekly)`, `EnergyAssessment(review)`) | Reject contrats en mode erroné |
| CC8 | `RecoveryAssessment.action == suspend/escalate_to_takeover` ⇒ aucun `Recommendation`/`LogisticAdjustment` consommé | `SUPERSEDED_BY_OVERLAY` |

### 14.3 Cross-contract state

Propriétés globales sur `AthleteState` + tables externes.

| ID | Prédicat | Enforcement |
|---|---|---|
| CCS1 | Exactement un `active_plan` ≠ COMPLETED/SUPERSEDED par athlète | Persistence layer |
| CCS2 | Exactement un `baseline_plan` ≠ COMPLETED/SUPERSEDED par athlète | Persistence layer |
| CCS3 | `recovery_takeover_active==True` ⇒ `active_plan.status ∈ {SUSPENDED, None}` | `activate_clinical_frame` + `handoff_to_baseline` |
| CCS4 | `onboarding_reentry_active==True` ⇒ `active_recovery_thread_id == None` | Handlers exclusifs |
| CCS5 | `persistent_override_pattern.active==True` ⇒ `first_detected_at IS NOT NULL` | `flag_override_pattern` |
| CCS6 | `persistent_override_pattern.reset_at IS NOT NULL` ⇒ `reset_at >= first_detected_at` | `reset_override_flag` |
| CCS7 | `prescribed_session.plan_link_type==ACTIVE` ⇒ `plan_id` et `block_id` existent dans `active_plan` | `persist_prescribed_sessions` + `apply_logistic_adjustment` |
| CCS8 | `contraindications_respected` référencent injuries actifs (pas supprimés) | `persist_prescribed_sessions` |
| CCS9 | `nutrition_daily_targets` : au plus 1 ligne active par `(athlete_id, target_date)` | Upsert |
| CCS10 | `active_plan.modification_count` monotone croissant | Tous nodes mutation plan |
| CCS11 | `SessionModification.modified_at >= prescribed_session.created_at` | Validators persistance |
| CCS12 | `effective_readiness.resolution == "pattern_neutralized" ⇔ persistent_override_pattern.active == True` | Fonction pure B1 |

### 14.4 Temporel et ordering

| ID | Prédicat | Enforcement |
|---|---|---|
| CCT1 | `build_proposed_plan` consomme après `delegate_specialists` complété (ou timeout) | Graph ordering |
| CCT2 | `persist_prescribed_sessions` après `build_proposed_plan`, avant `present_to_athlete` | Graph ordering |
| CCT3 | `flag_override_pattern` et `reset_override_flag` sérialisés sur `(athlete_id, "override_pattern_mutation")` | Lock applicatif |
| CCT4 | `activate_clinical_frame` précède toute mutation `recovery_takeover`. Lock `(athlete_id, "takeover_state")` | Graph entry condition |
| CCT5 | `apply_logistic_adjustment`, `suspend_active_plan`, `apply_recovery_deload` sérialisés sur `plan_id` | Lock applicatif |
| CCT6 | Séquence user-initiée (`handle_injury_report → activate_clinical_frame → recovery_takeover`) : persistance confirmée avant étape suivante | Graph ordering + transactions |

### 14.5 Monitoring proactif

| ID | Prédicat | Enforcement |
|---|---|---|
| MP1 | Contrats `MONITORING_*` vérifient plafond `PROACTIVE_CAP=2/semaine` avant consommation | `CoordinatorService.check_proactive_cap` |
| MP2 | Plafond atteint + non critical ⇒ `SUPERSEDED_BY_STATE_CHANGE` ou `DEFERRED` court | Coordinator |
| MP3 | `view.monitoring_event_payload.severity == critical` ⇒ bypass plafond, log spécial | Monitoring service |
| MP4 | `RecoveryAssessment(MONITORING_*)` avec `action == escalate_to_takeover` ⇒ bypass inconditionnel | Coordinator |

### 14.6 Threads LangGraph

| ID | Prédicat | Enforcement |
|---|---|---|
| CT1 | `active_onboarding_thread_id != None ⇔ journey_phase == onboarding OR onboarding_reentry_active == True` | Graph entry/exit |
| CT2 | `active_recovery_thread_id != None ⇔ recovery_takeover_active == True` | Graph entry/exit |
| CT3 | `active_followup_thread_id != None ⇔ journey_phase == followup_transition` | Graph entry/exit |
| CT4 | Thread LangGraph existe ⇔ entrée correspondante dans `AthleteState.technical` | Periodic reconciliation |

### 14.7 Audit et traçabilité

| ID | Prédicat | Enforcement |
|---|---|---|
| CA1 | `outcome != DEFERRED` ⇒ ligne `contract_emissions` existe | Coordinator pre-dispatch |
| CA2 | `outcome ∈ {APPLIED, IDEMPOTENT_NOOP, SUPERSEDED_*, REJECTED_*}` ⇒ ligne `processed_contracts` | Coordinator post-dispatch |
| CA3 | `view_snapshot_hash` reproductible (même snapshot → même hash SHA-256) | Test d'intégration |
| CA4 | Toute mutation `AthleteState` a ligne `audit_log` avec `source_contract_id` si dérivée | Logging middleware |
| CA5 | Tables externes (`prescribed_sessions`, `nutrition_daily_targets`, etc.) ont `source_contract_id` FK | Schéma DB |

### 14.8 Cohérence vue ↔ contrat

| ID | Prédicat | Enforcement |
|---|---|---|
| CV1 | `contract.metadata.invocation_trigger == view_used.invocation_trigger` | Validators Pydantic CM2 |
| CV2 | Contrat coach discipline : `contract.discipline == view_used.target_discipline` | Validators contrat |
| CV3 | `contract.metadata.view_built_at < contract.metadata.emitted_at` | Validators Pydantic CM1 |
| CV4 | `FollowupQuestionSet` : écarts en `rationale` correspondent à `view.baseline_observations` | Validator FQS9, WARN |

### 14.9 Reconciliation périodique

Invariants vérifiés en post-hoc par scheduler. Ne bloquent pas les opérations, alertent si violés.

| ID | Prédicat | Fréquence |
|---|---|---|
| REC1 | `active_recovery_thread_id` pointe vers thread existant dans checkpointer LangGraph | Quotidien |
| REC2 | Pour chaque `active_plan` : nombre `prescribed_sessions(status=UPCOMING)` ≤ total `discipline_components[*].total_volume_arc` | Hebdomadaire |
| REC3 | `override_flag_history` : aucun `reset_at` sans `set_at` préalable | Hebdomadaire |
| REC4 | Ratio `SUPERSEDED_BY_OVERLAY / APPLIED` stable dans le temps | Quotidien, métrique |

### 14.10 Stratégie d'enforcement par bande

| Bande | Mécanisme | Invariants |
|---|---|---|
| **A** | Pydantic immédiat | CC1-CC8, CV1-CV4, invariants intra-contrat §5-11 |
| **B** | Node consommateur | CCS1-CCS12 (partiellement), CT1-CT4 |
| **C** | Transactionnel + locks | CCT1-CCT6, MP1-MP4 |
| **D** | Construction architecturale | CCS12, CA3, CA5 (DB schema), REC1-REC4 |

### 14.11 Delta `AthleteState.technical`

Ajouts Phase D pour supporter les invariants cross-contract :

```python
class AthleteState(BaseModel):
    # ... champs existants B1 §1.12 ...
    last_contract_processed_at: datetime | None = None
    # Timestamp dernier contrat consommé. Invariants temporels + latency monitoring.
    locked_operations: dict[str, str] = Field(default_factory=dict)
    # Locks applicatifs en cours : {"operation_key": "lock_holder_id"}
    # Ex : {"override_pattern_mutation": "reset_override_flag_node_xyz"}
    # Cleaned en fin d'opération, TTL 30s max.
```

### 14.12 Tables ajoutées Phase D

Consolidation des tables mentionnées dans les sections précédentes :

- `contract_emissions` (§2.5)
- `processed_contracts` (§2.4)
- `deferred_contracts` (§13.6)
- `pending_logistic_adjustments` (§10.5)
- `override_flag_history` (§11.4)
- `synthesis_payloads_log` et `synthesis_invocations` (§12.8)
- `audit_log` (§14.7 CA4, nouveau)
- `nutrition_daily_targets`, `nutrition_daily_targets_history` (§6.6)
- `nutrition_plan_rules`, `nutrition_plan_baselines` (§6.6)
- `energy_plan_caloric_directives`, `energy_plan_load_modulations`, `energy_plan_cycle_modulations` (§8.8)
- `prescribed_sessions` (§3.6)

### 14.13 Tests d'invariants

Cible Phase D : environ 50 tests d'invariants pour B3, en plus des tests contrats individuels.

Stratégie :
- **Invariants Pydantic** : test unitaire direct sur `model_validate()`.
- **Invariants state** : test d'intégration avec fixture `AthleteState` + invocation node, assertion post-mutation.
- **Invariants ordering** : test de simulation de graphe avec race conditions injectées.
- **Invariants audit** : test d'intégration vérifiant lignes dans tables dédiées.
- **Invariants fonction pure** (CCS12) : test exhaustif sur les 7 branches de résolution (B1 §3.2).

Format : chaque invariant `XX{n}` a un test `test_{xx_n}_{description}`.

---

## 15. Résumé des décisions structurelles B3

### 15.1 Décisions majeures consolidées

1. **Composition vs héritage sur `ContractMetadata`** : composition stricte, permet discriminated unions propres sur contrats concrets.
2. **`PrescribedSession` en discriminated union par discipline** : typage strict > verbosité. Split `PrescribedSessionDraft` (sortie LLM) / `PrescribedSession` (DB-hydraté).
3. **Table `contract_emissions` dédiée** pour audit forensique, distincte de `processed_contracts` (idempotence).
4. **Flags inter-agents typés** (`HeadCoachFlag`, `RecoveryCoachFlag`) avec `FlagCode` enum + restrictions par périmètre émetteur.
5. **Synthèse multi-flags : agrégation Coordinator, exécution Head Coach** dans son prompt. Pas de contrat B3 pour la synthèse elle-même.
6. **Hiérarchie clinique au niveau node, pas au niveau contrat**. Contrats ignorants de leur priorité, `build_proposed_plan` orchestre.
7. **`Recommendation` unifié planning/review** avec discriminateur `recommendation_mode`. Partage ~70 % des champs.
8. **`NutritionVerdict` en 3 modes** (daily/weekly/planning). `pass_to_energy_coach` typé (`EnergyCoachEscalation`), pas bool.
9. **`RecoveryAssessment` en consultation uniquement**. En takeover : messages directs. Severity et action orthogonales.
10. **`EnergyAssessment` en 4 modes** (planning/review/monitoring/nutrition_escalation). Recommandation composite 3 leviers (caloric, load, clinical_escalation).
11. **`FollowupQuestionSet` max 5 questions ordonnées HIGH>MEDIUM>LOW**. Outcome tripartite (ready, extend, reentry).
12. **`LogisticAdjustment` logistique uniquement**. Discriminated union 6 types. Volume/intensité → refus. Objectif → re-entry.
13. **`OverrideFlagReset` symétrique à `flag_override_pattern`** avec anti-oscillation (`days_flag_was_active >= 2`).
14. **`PrescribedSessionCommon` delta** : `preferred_time_of_day_override` + `location_context_override` (LogisticAdjustment).
15. **`ActivePlan` delta** : `nutrition_rules_persisted`, `energy_component_persisted` (markers booléens).
16. **Fall-through outcomes 8 valeurs** avec `PartialApplicationOutcome`, `SUPERSEDURE_CONFIGS`, `DEFERRAL_POLICIES`. Pas de re-émission auto par défaut.
17. **43 invariants cross-contrats** répartis en 8 catégories et 4 bandes d'enforcement.
18. **~50 tests d'invariants cible Phase D** en plus des tests contrats individuels.

### 15.2 Nouveaux nodes introduits en B3

- `persist_prescribed_sessions` (hydrate drafts en PrescribedSession, table externe)
- `persist_nutrition_targets` (dispatch par mode)
- `apply_recovery_deload` (distinct de suspend et takeover)
- `persist_energy_plan_component` (directives caloric/load/cycle)
- `consume_followup_set`, `update_profile_deltas`, `dispatch_to_plan_generation`
- `apply_logistic_adjustment`, `confirm_logistic_adjustment`
- `reset_override_flag`

### 15.3 Articulation avec B1, B2, A1-A3

- **B1 `AthleteState`** : delta minimal (`last_contract_processed_at`, `locked_operations` sur technical; `nutrition_rules_persisted`, `energy_component_persisted` sur ActivePlan). Services déterministes intacts.
- **B2 `AgentView`** : invariants CV1-CV4 couplent trigger contrat ↔ vue. Aucune vue modifiée.
- **A3 `agent-roster`** : hiérarchie clinique matérialisée en ordre de consommation node. Droits de mutation par agent respectés (flags typés par périmètre).
- **A2 `agent-flow-langgraph`** : graphes `plan_generation`, `chat_turn`, `recovery_takeover`, `followup_transition`, `onboarding` inchangés. Nodes B3 s'insèrent aux points spécifiés.

### 15.4 Ambitions volontairement reportées

- Valeurs numériques de seuils cliniques (Phase C avec revue littérature).
- Taxonomies exhaustives (`session_type`, exercise names, pattern_names) : squelettes posés, valeurs finales Phase C.
- Implémentations SQL, codage locks Redis, workers deferral : Phase D.
- Calibrations `confidence_base` des CORRELATION_PATTERNS : Phase C.
- Mécanisme anti-thrashing set/reset < 7 jours : Phase C/D.

---

## 16. Points reportés

### 16.1 Phase C — Prompts système par agent

Pour chaque agent, le prompt système doit être aligné sur son contrat B3 :

- **Coach Lifting / Running / Swimming / Biking** : structure `Recommendation` par mode, respect DISCIPLINE_ADMISSIBLE_FLAGS, frontière logistic vs block_regen.
- **Nutrition Coach** : 3 modes `NutritionVerdict`, escalation Energy avec `EnergyCoachEscalation`, seuils d'escalade, références USDA/Open Food Facts/FCÉN.
- **Recovery Coach** : consultation vs takeover, severity ↔ action, détection `override_pattern` (seuils `consecutive_days`, `mean_divergence`).
- **Energy Coach** : 4 modes, zones EA (seuils 45/30/20 kcal/kg FFM), cycle context, mode dégradé FFM unavailable.
- **Onboarding Coach** : Phase 5 consultation, `FollowupQuestionSet` construit depuis `BaselineObservations`, frontières extend/reentry.
- **Head Coach** : synthèse multi-flags (< 3 / ≥ 3 flags, narrativation), `LogisticAdjustment`, `OverrideFlagReset`, façade paraphrasant questions Onboarding.

Calibrations numériques à poser : seuils HRV déviation, sleep debt thresholds, strain aggregate cutoffs, EA zones exactes (bornes 20/30/45), RED-S pattern criteria, `confidence_base` des 6 CORRELATION_PATTERNS, `PROACTIVE_CAP` affiné si besoin.

### 16.2 Phase D — Implémentation backend

- Services Pydantic v2 : `ContractMetadata`, 7 contrats, `PrescribedSession` union.
- Coordinator : pré-traitement agrégation multi-flags, dispatch par `invocation_trigger`, gestion outcomes.
- Nouveaux nodes LangGraph (§15.2) avec idempotence `processed_contracts`.
- Tables DB : 13 tables listées §14.12.
- Locks applicatifs Redis (CCT3-CCT5) : `override_pattern_mutation`, `takeover_state`, `plan_mutation_{plan_id}`.
- Worker deferral (DEFERRED contracts) avec retry policy.
- Scheduler reconciliation (REC1-REC4) quotidien/hebdomadaire.
- Tests : ~50 invariants + couverture contrats individuels.
- Métriques : ratios fall-through, latences, retries.

### 16.3 Phase E et au-delà

- Anti-thrashing set/reset oscillations détection.
- Personnalisation de `CORRELATION_PATTERNS` par profil athlète (sensibilités individuelles).
- Versions mineures contrats pour enrichissement progressif sans breaking change.
- Possibilité d'étendre matrice d'admissible emissions sur nouveaux triggers.

---

*Document validé B3. Prochaine session : Phase C — prompts système par agent.*
