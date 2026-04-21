# `agent-views.md` — Spec des `_AGENT_VIEWS` Pydantic par agent

> **Version 1 (livrable B2).** Spécification exhaustive et implémentable des 9 vues agents Pydantic du système Resilio+. Référence pour Phase B3 (contrats de sortie structurés des agents) et Phase D (implémentation backend). Dérivé de `user-flow-complete.md` v4, `agent-flow-langgraph.md` v1, `agent-roster.md` v1, `schema-core.md` v1. Cible la version finale du produit, pas une livraison V1 intermédiaire.

## 1. Objet et périmètre

Ce document formalise :

1. Les **blocs de construction partagés** par toutes les vues : `ViewContext`, table de politique de fenêtres, 5 Window models, 3 payloads dérivés non persistés, 2 fonctions de filtrage.
2. Les **9 classes `_AGENT_VIEWS` Pydantic** — une par agent LLM, avec vue paramétrée pour les 4 coachs disciplines et deux vues distinctes pour l'Onboarding Coach (délégation vs consultation).
3. Les **invariants transversaux** cross-vues et la null-safety consolidée.
4. Les **triggers d'invocation admissibles** par vue et les règles de construction.

Ne décrit pas : les prompts système par agent (Phase C), les contrats de sortie structurés (Phase B3), le code d'implémentation (Phase D). Les valeurs numériques des seuils (fenêtres de défaut, pondérations, matrices de sévérité) sont indicatives B2 et seront révisées scientifiquement en Phase C.

**Exemples concrets de construction.** Livrés dans `docs/agent-views-examples.md` (annexe séparée). Chaque exemple sert de test-case pour Phase D.

---

## 2. Principes architecturaux transversaux

### 2.1 Vue = snapshot de `AthleteState`, pas de state dynamique

Une vue agent est construite par une fonction `get_xxx_coach_view(state, context) -> XxxCoachView`. Elle est **un snapshot immutable** de `AthleteState` au moment `context.now`, filtré et enrichi selon les droits d'accès de l'agent (roster A3). Aucun champ n'est mutable depuis la vue — les mutations passent par des nodes LangGraph dédiés (via les contrats de sortie Phase B3) ou par les services déterministes.

Les outputs des autres spokes consultés dans la même invocation (ex : `RecoveryAssessment`, `Recommendation`, `NutritionVerdict`) ne sont **pas** dans la vue. Ils transitent via le state du graphe LangGraph et sont passés en input distinct du prompt LLM.

### 2.2 `ViewContext` unique + table de politique de fenêtres

Tous les paramètres dynamiques à l'invocation (trigger, discipline cible, mode de génération de plan, payloads dérivés, thread IDs actifs) sont capturés dans une seule classe `ViewContext` partagée par toutes les vues. Les combinaisons incohérentes sont rejetées par des `@model_validator`.

Les **fenêtres temporelles** (profondeur des logs injectés) ne sont pas sur `ViewContext`. Elles sont définies dans une **table de politique `DEFAULT_WINDOWS[(agent_id, trigger)]`**, lue par chaque fonction de construction. Un champ `ViewContext.window_overrides` permet des exceptions explicites.

Motivation : séparer la donnée (politique modifiable sans toucher au code) de l'orchestration (ViewContext capture l'état d'invocation), et éviter la prolifération de sous-classes `ViewContext` par trigger.

### 2.3 Matérialisation des champs dérivés à la construction

Trois catégories de champs dérivés sont matérialisés (calculés à la construction, figés dans la vue) plutôt que laissés en `computed_field` :

**Fonctions pures de résolution Readiness / EA** (B1 §3.2-3.3). La fonction `resolve_effective_readiness` est appelée par `get_xxx_coach_view` avec les paramètres suivants, uniformes à travers toutes les vues :

```python
from resilio.schema.core.readiness import resolve_effective_readiness
from resilio.schema.core.ea import resolve_effective_ea
from resilio.knowledge import thresholds

thresholds_data = thresholds.load()  # lecture unique, cache module-level

effective_rd = resolve_effective_readiness(
    objective=state.objective_readiness,
    user_signal=state.user_readiness_signal,
    overlay_takeover_active=state.recovery_takeover_active,
    override_pattern=state.persistent_override_pattern,
    critical_threshold=thresholds_data.readiness.critical_threshold,
    user_signal_freshness_hours=thresholds_data.readiness.user_signal_freshness_hours,
    now=context.now,
)

effective_ea = resolve_effective_ea(
    objective=state.objective_energy_availability,
    user_signal=state.user_energy_signal,
    overlay_takeover_active=state.recovery_takeover_active,
    override_pattern=state.persistent_override_pattern,
    ea_thresholds=thresholds_data.energy_availability,
    user_signal_freshness_hours=thresholds_data.energy_availability.user_signal_freshness_hours,
    now=context.now,
)
```

`EffectiveReadiness` et `EffectiveEA` sont **toujours présents** dans les vues qui les exposent. Si `objective_readiness` est `None`, le résultat a `score=None` et `resolution="indeterminate"` — l'agent détecte l'absence via `resolution`, pas via `Optional`.

**Dérivés calculés** : `age_years` (depuis `date_of_birth` et `context.now`), `ea_zone_trajectory` (EnergyCoachView), `weekly_strain_aggregates` (EnergyCoachView).

**Payloads injectés depuis `ViewContext`** : `baseline_observations`, `monitoring_event_payload`, `escalation_context`.

### 2.4 Isolation stricte par discipline pour les 4 coachs disciplines

Un coach de discipline `D` ne voit que :
- `ExperienceProfile.by_discipline[D]`
- `classification[D]` et ses `confidence_levels[D][*]`
- Logs training filtrés à `D` (jamais les séances des peers)
- `InjuryHistory` filtrée via matrice `region-discipline-impact`
- `active_plan.discipline_components[D]` (les autres components masqués)

Cross-discipline uniquement sur `strain_state` (état musculaire complet), mais **sans l'origine disciplinaire** (pas de `last_contribution_at` par groupe — Recovery Coach est le seul à voir le détail avec origine).

### 2.5 Deux vues distinctes pour Onboarding Coach

L'Onboarding Coach opère dans deux modes structurellement différents :
- **Délégation** (Phase 2 initiale, re-entry partielle) : détient le tour conversationnel, voit les messages du thread onboarding, écrit les sous-profils via nodes `persist_block`. Pas de logs, pas d'index dérivés.
- **Consultation** (Phase 5) : ne parle pas au user, reçoit `BaselineObservations` précalculé, produit `FollowupQuestionSet`. Pas de logs bruts (écarts déjà synthétisés), pas de messages.

Une factory `get_onboarding_coach_view` dispatche vers la bonne classe selon `context.invocation_trigger`.

---

## 3. Blocs de construction partagés

### 3.1 `ViewContext`

Paramètres dynamiques à l'invocation d'une fonction de construction de vue. Passé à toutes les vues. Chaque fonction ignore les champs qui ne la concernent pas ; les validators garantissent que les champs obligatoires par trigger sont présents.

```python
from datetime import datetime
from enum import Enum
from typing import Literal
from pydantic import BaseModel, Field, model_validator

from resilio.schema.core import Discipline


class InvocationTrigger(str, Enum):
    # Plan generation
    PLAN_GEN_DELEGATE_SPECIALISTS = "plan_gen_delegate_specialists"
    PLAN_GEN_CONSULT_ONBOARDING = "plan_gen_consult_onboarding"
    PLAN_GEN_PRESENT_TO_ATHLETE = "plan_gen_present_to_athlete"
    PLAN_GEN_REVISE_PLAN = "plan_gen_revise_plan"

    # Chat turn handlers (Phase 7 steady_state)
    CHAT_FREE_QUESTION = "chat_free_question"
    CHAT_DAILY_CHECKIN = "chat_daily_checkin"
    CHAT_SESSION_LOG = "chat_session_log"
    CHAT_WEEKLY_REPORT = "chat_weekly_report"
    CHAT_INJURY_REPORT = "chat_injury_report"
    CHAT_GOAL_CHANGE = "chat_goal_change"
    CHAT_CONSTRAINT_CHANGE = "chat_constraint_change"
    CHAT_ADJUSTMENT_REQUEST = "chat_adjustment_request"
    CHAT_BLOCK_END_TRIGGER = "chat_block_end_trigger"

    # Onboarding (Phase 2 + re-entry)
    ONBOARDING_CONDUCT_BLOCK = "onboarding_conduct_block"
    ONBOARDING_REENTRY_CONDUCT_BLOCK = "onboarding_reentry_conduct_block"

    # Followup transition (Phase 5)
    FOLLOWUP_CONSULT_ONBOARDING = "followup_consult_onboarding"
    FOLLOWUP_HEAD_COACH_ASK = "followup_head_coach_ask"

    # Recovery takeover
    RECOVERY_ACTIVATE_FRAME = "recovery_activate_frame"
    RECOVERY_ASSESS_SITUATION = "recovery_assess_situation"
    RECOVERY_PROPOSE_PROTOCOL = "recovery_propose_protocol"
    RECOVERY_EVALUATE_READINESS = "recovery_evaluate_readiness"

    # Monitoring proactif
    MONITORING_HRV = "monitoring_hrv"
    MONITORING_SLEEP = "monitoring_sleep"
    MONITORING_EA = "monitoring_ea"
    MONITORING_COMPLIANCE = "monitoring_compliance"

    # Escalation inter-agents
    ESCALATION_NUTRITION_TO_ENERGY = "escalation_nutrition_to_energy"


class AgentId(str, Enum):
    HEAD = "head"
    ONBOARDING = "onboarding"
    LIFTING = "lifting"
    RUNNING = "running"
    SWIMMING = "swimming"
    BIKING = "biking"
    NUTRITION = "nutrition"
    RECOVERY = "recovery"
    ENERGY = "energy"


class OnboardingBlockType(str, Enum):
    """Blocs d'onboarding couverts par un parcours en délégation."""
    OBJECTIVES = "objectives"
    EXPERIENCE = "experience"
    INJURIES = "injuries"
    CONSTRAINTS = "constraints"
    IDENT_REFINEMENT = "ident_refinement"


class WindowOverrides(BaseModel):
    """Overrides explicites des fenêtres par défaut. None = utiliser la politique."""
    training_logs_days: int | None = Field(None, ge=1, le=365)
    physio_logs_days: int | None = Field(None, ge=1, le=365)
    nutrition_logs_days: int | None = Field(None, ge=1, le=365)
    messages_count: int | None = Field(None, ge=1, le=500)
    messages_days: int | None = Field(None, ge=1, le=180)


class ViewContext(BaseModel):
    """Paramètres dynamiques à l'invocation d'une fonction get_xxx_coach_view."""
    now: datetime
    invocation_trigger: InvocationTrigger

    # Ciblage discipline (coachs disciplines : obligatoire ; autres : ignoré)
    target_discipline: Discipline | None = None

    # Mode de génération de plan
    plan_generation_mode: Literal["baseline", "first_personalized", "block_regen"] | None = None

    # Override des fenêtres par défaut
    window_overrides: WindowOverrides = Field(default_factory=WindowOverrides)

    # Payloads dérivés non persistés (gated par trigger)
    baseline_observations: "BaselineObservations | None" = None
    monitoring_event_payload: "MonitoringEventPayload | None" = None
    escalation_context: "EscalationContext | None" = None

    # Threads courants, injectés par CoordinatorService
    current_chat_thread_id: str | None = None
    current_onboarding_thread_id: str | None = None
    current_recovery_thread_id: str | None = None
    current_followup_thread_id: str | None = None

    # Onboarding block context (gated par trigger ONBOARDING_*)
    onboarding_blocks_to_cover: list[OnboardingBlockType] | None = None
    onboarding_current_block: OnboardingBlockType | None = None

    # --- invariants context ---

    @model_validator(mode="after")
    def _validate_plan_gen_mode(self):
        """VC1 : plan_generation_mode renseigné ssi trigger ∈ PLAN_GEN_DELEGATE_SPECIALISTS ou
        PLAN_GEN_CONSULT_ONBOARDING."""
        requires_mode = {
            InvocationTrigger.PLAN_GEN_DELEGATE_SPECIALISTS,
            InvocationTrigger.PLAN_GEN_CONSULT_ONBOARDING,
        }
        if self.invocation_trigger in requires_mode and self.plan_generation_mode is None:
            raise ValueError(
                f"plan_generation_mode required for trigger {self.invocation_trigger}"
            )
        if self.invocation_trigger not in requires_mode and self.plan_generation_mode is not None:
            raise ValueError(
                f"plan_generation_mode must be None for trigger {self.invocation_trigger}"
            )
        return self

    @model_validator(mode="after")
    def _validate_baseline_observations(self):
        """VC2 : baseline_observations renseigné ssi FOLLOWUP_CONSULT_ONBOARDING."""
        if self.invocation_trigger == InvocationTrigger.FOLLOWUP_CONSULT_ONBOARDING:
            if self.baseline_observations is None:
                raise ValueError("baseline_observations required for FOLLOWUP_CONSULT_ONBOARDING")
        elif self.baseline_observations is not None:
            raise ValueError(
                f"baseline_observations must be None for trigger {self.invocation_trigger}"
            )
        return self

    @model_validator(mode="after")
    def _validate_monitoring_payload(self):
        """VC3 : monitoring_event_payload renseigné ssi trigger ∈ MONITORING_*."""
        is_monitoring = self.invocation_trigger.value.startswith("monitoring_")
        if is_monitoring and self.monitoring_event_payload is None:
            raise ValueError(f"monitoring_event_payload required for {self.invocation_trigger}")
        if not is_monitoring and self.monitoring_event_payload is not None:
            raise ValueError(
                f"monitoring_event_payload must be None for trigger {self.invocation_trigger}"
            )
        return self

    @model_validator(mode="after")
    def _validate_escalation_context(self):
        """VC4 : escalation_context renseigné ssi ESCALATION_NUTRITION_TO_ENERGY."""
        if self.invocation_trigger == InvocationTrigger.ESCALATION_NUTRITION_TO_ENERGY:
            if self.escalation_context is None:
                raise ValueError(
                    "escalation_context required for ESCALATION_NUTRITION_TO_ENERGY"
                )
        elif self.escalation_context is not None:
            raise ValueError(
                f"escalation_context must be None for trigger {self.invocation_trigger}"
            )
        return self

    @model_validator(mode="after")
    def _validate_onboarding_blocks(self):
        """VC5 : onboarding_blocks_to_cover et onboarding_current_block renseignés
        ssi trigger ∈ {ONBOARDING_CONDUCT_BLOCK, ONBOARDING_REENTRY_CONDUCT_BLOCK}."""
        needs_blocks = self.invocation_trigger in {
            InvocationTrigger.ONBOARDING_CONDUCT_BLOCK,
            InvocationTrigger.ONBOARDING_REENTRY_CONDUCT_BLOCK,
        }
        if needs_blocks and (
            self.onboarding_blocks_to_cover is None
            or self.onboarding_current_block is None
        ):
            raise ValueError(
                "onboarding_blocks_to_cover and onboarding_current_block required "
                f"for trigger {self.invocation_trigger}"
            )
        if not needs_blocks and (
            self.onboarding_blocks_to_cover is not None
            or self.onboarding_current_block is not None
        ):
            raise ValueError(
                f"onboarding blocks fields must be None for trigger {self.invocation_trigger}"
            )
        return self
```

### 3.2 Politique de fenêtres par défaut `DEFAULT_WINDOWS`

Table canonique `DEFAULT_WINDOWS: dict[tuple[AgentId, InvocationTrigger], WindowSpec]`. Lue par chaque fonction `get_xxx_coach_view` au début de la construction. Merge avec `context.window_overrides` (override wins).

```python
class WindowSpec(BaseModel):
    """Spécification des fenêtres à injecter pour un (agent, trigger) donné."""
    training_logs_days: int | None = None
    training_logs_format: Literal["raw", "load_history_only", "none"] = "none"
    physio_logs_days: int | None = None
    physio_logs_format: Literal["raw", "summary_only", "none"] = "none"
    nutrition_logs_days: int | None = None
    nutrition_logs_format: Literal["raw", "summary_only", "none"] = "none"
    messages_count: int | None = None
    messages_scope: Literal["global", "current_thread", "none"] = "none"
```

#### Justifications des fenêtres

Les valeurs dérivent de trois contraintes physiologiques / opérationnelles :

**Horizons ACWR / EWMA.** Le raisonnement endurance repose sur le ratio charge aiguë (7j) / chronique (28j). Pour Running, Swimming, Biking, **28j** est la fenêtre canonique.

**Cycles de bloc lifting.** Les landmarks MEV → MAV → MRV s'accumulent sur 4–6 semaines. Lifting Coach prend **42j (6 semaines)** par défaut pour raisonner sur la saturation/progression et planifier un deload.

**Historique HRV / sommeil.** La baseline HRV individuelle se stabilise sur 14–30j. Les patterns de dette de sommeil se lisent sur 14j minimum. Recovery Coach et Energy Coach prennent **30j** par défaut sur physio.

**Horizon EA structurel.** RED-S se manifeste sur des patterns de 4–12 semaines. Energy Coach consulté en `plan_generation` prend **60j** sur load_history et nutrition agrégée.

**Biking à 42j comme Lifting.** Cohérent avec la CTL (Chronic Training Load) Training Peaks canonique sur 42j pour le cyclisme.

#### Table `DEFAULT_WINDOWS` (extrait significatif)

Format compact : `T(days, format) · P(days, format) · N(days, format) · M(count, scope)`. `—` = non injecté.

| Agent | Trigger | Training | Physio | Nutrition | Messages |
|---|---|---|---|---|---|
| Head | CHAT_FREE_QUESTION | 14, raw | 7, summary | 7, summary | 20, current_thread |
| Head | CHAT_DAILY_CHECKIN | 3, raw | 3, raw | 3, raw | 10, current_thread |
| Head | CHAT_SESSION_LOG | 7, raw | 3, summary | — | 10, current_thread |
| Head | CHAT_WEEKLY_REPORT | 7, raw | 14, raw | 14, raw | 30, current_thread |
| Head | CHAT_INJURY_REPORT | 21, raw | 14, raw | — | 10, current_thread |
| Head | CHAT_GOAL_CHANGE | 14, summary | 7, summary | — | 20, current_thread |
| Head | CHAT_CONSTRAINT_CHANGE | 7, summary | — | — | 15, current_thread |
| Head | CHAT_ADJUSTMENT_REQUEST | 14, raw | 7, summary | — | 15, current_thread |
| Head | CHAT_BLOCK_END_TRIGGER | 28, raw | 14, summary | 14, summary | 15, current_thread |
| Head | PLAN_GEN_PRESENT_TO_ATHLETE | 7, summary | 7, summary | — | 30, current_thread |
| Head | PLAN_GEN_REVISE_PLAN | 7, summary | 7, summary | — | 30, current_thread |
| Head | FOLLOWUP_HEAD_COACH_ASK | 14, summary | 7, summary | 7, summary | 30, current_thread |
| Onboarding | ONBOARDING_CONDUCT_BLOCK | — | — | — | 50, current_thread |
| Onboarding | ONBOARDING_REENTRY_CONDUCT_BLOCK | — | — | — | 30, current_thread |
| Onboarding | FOLLOWUP_CONSULT_ONBOARDING | — | — | — | — |
| Lifting | PLAN_GEN_DELEGATE_SPECIALISTS (baseline) | 21, raw | 14, summary | — | — |
| Lifting | PLAN_GEN_DELEGATE_SPECIALISTS (first / block_regen) | 42, raw | 14, summary | — | — |
| Lifting | CHAT_WEEKLY_REPORT | 7, raw | 7, summary | — | — |
| Running | PLAN_GEN_DELEGATE_SPECIALISTS (baseline) | 21, raw | 14, summary | — | — |
| Running | PLAN_GEN_DELEGATE_SPECIALISTS (first / block_regen) | 28, raw | 14, summary | — | — |
| Running | CHAT_WEEKLY_REPORT | 7, raw | 7, summary | — | — |
| Swimming | PLAN_GEN_DELEGATE_SPECIALISTS (baseline) | 21, raw | 14, summary | — | — |
| Swimming | PLAN_GEN_DELEGATE_SPECIALISTS (first / block_regen) | 28, raw | 14, summary | — | — |
| Swimming | CHAT_WEEKLY_REPORT | 7, raw | 7, summary | — | — |
| Biking | PLAN_GEN_DELEGATE_SPECIALISTS (baseline) | 21, raw | 14, summary | — | — |
| Biking | PLAN_GEN_DELEGATE_SPECIALISTS (first / block_regen) | 42, raw | 14, summary | — | — |
| Biking | CHAT_WEEKLY_REPORT | 7, raw | 7, summary | — | — |
| Nutrition | CHAT_DAILY_CHECKIN | 14, load_history | 7, summary | 14, raw | — |
| Nutrition | CHAT_WEEKLY_REPORT | 14, load_history | 14, summary | 14, raw | — |
| Nutrition | PLAN_GEN_DELEGATE_SPECIALISTS (baseline) | 14, load_history | 7, summary | 14, raw | — |
| Nutrition | PLAN_GEN_DELEGATE_SPECIALISTS (first / block_regen) | 28, load_history | 14, summary | 21, raw | — |
| Recovery | CHAT_INJURY_REPORT | 21, raw | 14, raw | 7, summary | 10, current_chat_thread |
| Recovery | RECOVERY_ACTIVATE_FRAME | 28, raw | 30, raw | 14, summary | 20, current_recovery_thread |
| Recovery | RECOVERY_ASSESS_SITUATION | 28, raw | 30, raw | 14, summary | 30, current_recovery_thread |
| Recovery | RECOVERY_PROPOSE_PROTOCOL | 28, raw | 30, raw | 14, summary | 20, current_recovery_thread |
| Recovery | RECOVERY_EVALUATE_READINESS | 14, raw | 14, raw | — | 15, current_recovery_thread |
| Recovery | CHAT_WEEKLY_REPORT | 14, raw | 30, raw | 14, summary | — |
| Recovery | MONITORING_HRV | 14, raw | 14, raw | — | — |
| Recovery | MONITORING_SLEEP | 7, raw | 21, raw | — | — |
| Energy | PLAN_GEN_DELEGATE_SPECIALISTS (baseline) | 21, load_history | 14, summary | 21, raw | — |
| Energy | PLAN_GEN_DELEGATE_SPECIALISTS (first_personalized) | 60, load_history | 30, summary | 60, raw | — |
| Energy | PLAN_GEN_DELEGATE_SPECIALISTS (block_regen) | 60, load_history | 30, summary | 42, raw | — |
| Energy | CHAT_WEEKLY_REPORT | 28, load_history | 21, summary | 28, raw | — |
| Energy | MONITORING_EA | 28, load_history | 14, summary | 28, raw | — |
| Energy | ESCALATION_NUTRITION_TO_ENERGY | 28, load_history | 14, summary | 28, raw | — |

Les valeurs sont indicatives B2. Phase C révisera scientifiquement.

### 3.3 Window models (5 classes)

#### 3.3.1 `TrainingLogsRawWindow`

Consommée par coach discipline propriétaire (filtré sur `target_discipline`), Head Coach (toutes disciplines actives), Recovery Coach (toutes disciplines FULL ∪ TRACKING).

```python
from datetime import date, datetime
from typing import Literal

from resilio.schema.core import (
    Discipline, MuscleGroup, VolumeTarget, VolumeUnit,
)


class SetLog(BaseModel):
    """Détail d'une série. Composant de ExerciseLog pour lifting."""
    set_number: int = Field(..., ge=1)
    reps_prescribed: int | None = Field(None, ge=0)
    reps_realized: int = Field(..., ge=0)
    load_kg: float | None = Field(None, ge=0.0)
    rir_reported: int | None = Field(None, ge=0, le=10)
    rpe_reported: float | None = Field(None, ge=1.0, le=10.0)
    tempo: str | None = None  # ex "3-0-1-0"
    rest_seconds: int | None = Field(None, ge=0)
    completed: bool = True


class ExerciseLog(BaseModel):
    """Détail d'un exercice dans une séance lifting.
    Populé uniquement pour le coach discipline propriétaire
    via hydrate_exercise_details=True."""
    exercise_name: str
    exercise_category: str | None = None  # "squat", "hinge", "push", "pull", etc.
    prescribed: bool
    substitution_of: str | None = None
    sets: list[SetLog]
    notes: str | None = Field(None, max_length=300)


class IntervalLog(BaseModel):
    """Détail d'un intervalle dans une séance endurance (running/swimming/biking).
    Populé uniquement pour le coach discipline propriétaire."""
    interval_number: int = Field(..., ge=1)
    interval_type: Literal[
        "warmup", "work", "recovery", "cooldown", "steady_state"
    ]
    distance_m: float | None = Field(None, ge=0.0)
    duration_seconds: int | None = Field(None, ge=0)
    pace_or_power: dict[str, float] | None = None
    hr_avg_bpm: int | None = Field(None, ge=30, le=220)
    hr_max_bpm: int | None = Field(None, ge=30, le=220)
    rpe_reported: float | None = Field(None, ge=1.0, le=10.0)
    elevation_gain_m: float | None = Field(None, ge=0.0)


class SessionLogLite(BaseModel):
    """Snapshot d'un log de session tel qu'injecté dans une vue.
    Sous-ensemble des colonnes DB."""
    log_id: str
    discipline: Discipline
    session_type: str
    logged_at: datetime
    session_date: date
    duration_minutes: int = Field(..., ge=0)

    volume_realized: VolumeTarget | None = None
    intensity_realized: dict[str, float] | None = None
    rpe_reported: float | None = Field(None, ge=1.0, le=10.0)

    prescribed_session_id: str | None = None
    compliance_status: Literal[
        "on_plan", "modified", "unplanned", "missed", "partial"
    ]

    # Strain contribution snapshot (pas la valeur courante)
    strain_contribution_total: float | None = Field(None, ge=0.0, le=100.0)
    strain_contribution_by_group: dict[MuscleGroup, float] | None = None

    notes: str | None = Field(None, max_length=500)

    # Détails exercice-par-exercice / intervalle-par-intervalle
    # Populés uniquement pour le coach discipline propriétaire.
    # exercise_details pour lifting, interval_details pour endurance.
    exercise_details: list[ExerciseLog] | None = None
    interval_details: list[IntervalLog] | None = None


class TrainingLogsRawWindow(BaseModel):
    discipline: Discipline
    window_start: date
    window_end: date
    sessions: list[SessionLogLite]

    # Dérivés précalculés côté service
    total_sessions_count: int = Field(..., ge=0)
    total_volume_realized: VolumeTarget | None = None
    avg_rpe: float | None = Field(None, ge=1.0, le=10.0)
    compliance_rate: float | None = Field(None, ge=0.0, le=1.0)
    last_session_at: datetime | None = None
    coverage_rate: float = Field(..., ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _validate_window(self):
        # TL1 : window_end >= window_start
        if self.window_end < self.window_start:
            raise ValueError("window_end < window_start")
        # TL2 : sessions triées asc par session_date
        dates = [s.session_date for s in self.sessions]
        if dates != sorted(dates):
            raise ValueError("sessions not sorted by session_date")
        # TL3 : sessions dans la fenêtre
        for s in self.sessions:
            if not (self.window_start <= s.session_date <= self.window_end):
                raise ValueError(f"session {s.log_id} out of window")
        # TL4 : toutes sessions sur discipline window
        if any(s.discipline != self.discipline for s in self.sessions):
            raise ValueError("session discipline mismatch")
        # TL5 : total_sessions_count cohérent
        if self.total_sessions_count != len(self.sessions):
            raise ValueError("total_sessions_count incoherent")
        # TL6 : last_session_at cohérent
        if self.sessions and self.last_session_at is None:
            raise ValueError("last_session_at missing with sessions")
        if not self.sessions and self.last_session_at is not None:
            raise ValueError("last_session_at set with empty sessions")
        # TL7 : cohérence exercise_details / interval_details par discipline
        for s in self.sessions:
            if self.discipline == Discipline.LIFTING:
                if s.interval_details is not None:
                    raise ValueError(f"interval_details set for lifting session {s.log_id}")
            else:
                if s.exercise_details is not None:
                    raise ValueError(
                        f"exercise_details set for {self.discipline.value} session {s.log_id}"
                    )
        return self
```

#### 3.3.2 `TrainingLoadHistoryWindow`

Vue agrégée. Consommée par Nutrition Coach et Energy Coach : ils n'ont pas besoin des paramètres techniques par séance, mais d'un `load` journalier par discipline pour calculer EEE et anticiper les besoins.

```python
class LoadHistoryPoint(BaseModel):
    date: date
    discipline: Discipline
    total_volume: VolumeTarget
    session_count: int = Field(..., ge=0)
    avg_rpe: float | None = Field(None, ge=1.0, le=10.0)
    aggregated_strain_contribution: float | None = Field(None, ge=0.0, le=100.0)
    estimated_eee_kcal: float | None = Field(None, ge=0.0)


class TrainingLoadHistoryWindow(BaseModel):
    scope: Discipline | Literal["all_active_disciplines"]
    window_start: date
    window_end: date
    daily_points: list[LoadHistoryPoint]

    # Résumés
    total_volume: VolumeTarget | None = None
    avg_weekly_strain_contribution: float | None = Field(None, ge=0.0, le=100.0)
    avg_daily_eee_kcal: float | None = Field(None, ge=0.0)
    total_session_count: int = Field(..., ge=0)
    coverage_rate: float = Field(..., ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _validate_window(self):
        if self.window_end < self.window_start:
            raise ValueError("window_end < window_start")
        dates = [p.date for p in self.daily_points]
        if dates != sorted(dates):
            raise ValueError("daily_points not sorted")
        if self.scope != "all_active_disciplines":
            if any(p.discipline != self.scope for p in self.daily_points):
                raise ValueError("point discipline mismatch with scope")
        return self
```

#### 3.3.3 `PhysioLogsWindow`

Deux variantes de format : `raw` (détail quotidien) et `summary_only` (résumés agrégés). Structure unifiée, champs optionnels selon format.

```python
class DailyPhysioPoint(BaseModel):
    date: date
    hrv_rmssd_ms: float | None = Field(None, ge=0.0, le=300.0)
    hrv_deviation_z_score: float | None = None
    sleep_duration_hours: float | None = Field(None, ge=0.0, le=16.0)
    sleep_quality_score: float | None = Field(None, ge=0.0, le=100.0)
    resting_heart_rate_bpm: int | None = Field(None, ge=25, le=120)
    weight_kg: float | None = Field(None, ge=30.0, le=300.0)
    subjective_stress: Literal["low", "moderate", "high", "very_high"] | None = None
    subjective_energy: Literal[
        "very_low", "low", "neutral", "high", "very_high"
    ] | None = None
    morning_checkin_submitted: bool = False


class PhysioLogsSummary(BaseModel):
    """Résumés précalculés sur la fenêtre. Toujours présents."""
    hrv_trend_slope_per_day: float | None = None
    hrv_deviations_count: int = Field(0, ge=0)
    hrv_last_value: float | None = None
    sleep_avg_hours: float | None = Field(None, ge=0.0, le=16.0)
    sleep_debt_cumulative_hours: float | None = None
    sleep_last_quality: float | None = None
    rhr_trend_slope_per_day: float | None = None
    weight_trend_slope_per_week_kg: float | None = None
    last_log_at: datetime | None = None
    coverage_rate: float = Field(..., ge=0.0, le=1.0)


class PhysioLogsWindow(BaseModel):
    window_start: date
    window_end: date
    format: Literal["raw", "summary_only"]
    daily_points: list[DailyPhysioPoint] | None = None
    summary: PhysioLogsSummary

    @model_validator(mode="after")
    def _validate_format(self):
        if self.format == "raw" and self.daily_points is None:
            raise ValueError("daily_points required when format == 'raw'")
        if self.format == "summary_only" and self.daily_points is not None:
            raise ValueError("daily_points must be None when format == 'summary_only'")
        if self.daily_points:
            dates = [p.date for p in self.daily_points]
            if dates != sorted(dates):
                raise ValueError("daily_points not sorted")
            if any(not (self.window_start <= d <= self.window_end) for d in dates):
                raise ValueError("point out of window")
        return self
```

#### 3.3.4 `NutritionLogsWindow`

```python
class DailyNutritionPoint(BaseModel):
    date: date
    calories_kcal: float | None = Field(None, ge=0.0)
    protein_g: float | None = Field(None, ge=0.0)
    carbs_g: float | None = Field(None, ge=0.0)
    fat_g: float | None = Field(None, ge=0.0)
    fiber_g: float | None = Field(None, ge=0.0)
    meal_count: int | None = Field(None, ge=0, le=12)

    target_calories_kcal: float | None = Field(None, ge=0.0)
    target_protein_g: float | None = Field(None, ge=0.0)
    target_carbs_g: float | None = Field(None, ge=0.0)
    target_fat_g: float | None = Field(None, ge=0.0)

    calories_adherence_ratio: float | None = None
    macros_adherence_score: float | None = Field(None, ge=0.0, le=1.0)

    pre_session_meal_logged: bool | None = None
    post_session_meal_logged: bool | None = None
    hydration_status: Literal["adequate", "low", "unknown"] | None = None


class NutritionLogsSummary(BaseModel):
    avg_calories_kcal: float | None = Field(None, ge=0.0)
    avg_protein_g: float | None = Field(None, ge=0.0)
    avg_carbs_g: float | None = Field(None, ge=0.0)
    avg_fat_g: float | None = Field(None, ge=0.0)
    adherence_rate: float | None = Field(None, ge=0.0, le=1.0)
    days_with_log_count: int = Field(..., ge=0)
    coverage_rate: float = Field(..., ge=0.0, le=1.0)
    last_log_at: datetime | None = None


class NutritionLogsWindow(BaseModel):
    window_start: date
    window_end: date
    format: Literal["raw", "summary_only"]
    daily_points: list[DailyNutritionPoint] | None = None
    summary: NutritionLogsSummary

    @model_validator(mode="after")
    def _validate_format(self):
        if self.format == "raw" and self.daily_points is None:
            raise ValueError("daily_points required when format == 'raw'")
        if self.format == "summary_only" and self.daily_points is not None:
            raise ValueError("daily_points must be None when format == 'summary_only'")
        if self.daily_points:
            dates = [p.date for p in self.daily_points]
            if dates != sorted(dates):
                raise ValueError("daily_points not sorted")
        return self
```

#### 3.3.5 `MessagesWindow`

```python
from resilio.schema.core import ClassifiedIntent


class MessageLite(BaseModel):
    message_id: str
    thread_id: str
    timestamp: datetime
    author: Literal[
        "user", "head_coach", "onboarding_coach", "recovery_coach", "system_proactive"
    ]
    content: str
    classified_intent: ClassifiedIntent | None = None


class MessagesWindow(BaseModel):
    scope: Literal["global", "current_thread"]
    thread_id: str | None = None
    window_start: datetime
    window_end: datetime
    messages: list[MessageLite]
    truncated: bool = False
    total_count_in_window: int = Field(..., ge=0)

    @model_validator(mode="after")
    def _validate_scope(self):
        if self.scope == "current_thread" and self.thread_id is None:
            raise ValueError("thread_id required when scope == 'current_thread'")
        if self.scope == "global" and self.thread_id is not None:
            raise ValueError("thread_id must be None when scope == 'global'")
        if self.scope == "current_thread":
            if any(m.thread_id != self.thread_id for m in self.messages):
                raise ValueError("message thread_id mismatch")
        ts = [m.timestamp for m in self.messages]
        if ts != sorted(ts):
            raise ValueError("messages not sorted")
        return self
```

### 3.4 Payloads dérivés non persistés

#### 3.4.1 `BaselineObservations` (Phase 5)

Injecté dans `ViewContext` uniquement pour `FOLLOWUP_CONSULT_ONBOARDING`. Produit par le node `compare_declarative_vs_observed`. Décision B1 : non persisté sur `AthleteState`.

```python
from resilio.schema.core import ClassificationDimension


class DeclarativeVsObservedGap(BaseModel):
    """Un écart identifié entre le déclaratif onboarding et la réalité baseline."""
    dimension: Literal[
        "volume_tolerance",
        "intensity_tolerance",
        "recovery_need",
        "movement_quality",
        "pacing_discipline",
        "session_type_difficulty",
        "frequency_sustainability",
    ]
    discipline: Discipline | None = None
    targeted_classification_dimension: ClassificationDimension | None = None

    declared_snapshot: str
    observed_snapshot: str
    gap_magnitude: Literal[
        "aligned", "minor_gap", "significant_gap", "contradiction"
    ]
    supporting_evidence_session_ids: list[str] = Field(default_factory=list)
    supporting_evidence_summary: str


class BaselineObservations(BaseModel):
    baseline_plan_id: str
    baseline_window_start: date
    baseline_window_end: date

    compliance_rate: float = Field(..., ge=0.0, le=1.0)
    sessions_representative_count: int = Field(..., ge=0)
    sufficient_data_for_analysis: bool

    actual_vs_prescribed_volume_ratio: dict[Discipline, float]
    actual_vs_prescribed_intensity_ratio: dict[Discipline, float]
    avg_rpe_vs_prescribed: dict[Discipline, float]

    gaps: list[DeclarativeVsObservedGap]

    generated_at: datetime

    @model_validator(mode="after")
    def _validate(self):
        if self.baseline_window_end < self.baseline_window_start:
            raise ValueError("window_end < window_start")
        if not self.sufficient_data_for_analysis and self.compliance_rate > 0.6:
            raise ValueError(
                "sufficient_data_for_analysis=False incompatible with high compliance_rate"
            )
        return self
```

#### 3.4.2 `MonitoringEventPayload`

Injecté pour les triggers `MONITORING_*`. Permet à l'agent de savoir ce qui a déclenché son invocation.

```python
class MonitoringEventPayload(BaseModel):
    event_type: Literal[
        "hrv_deviation_2d",
        "hrv_critical_fall_5d",
        "sleep_degraded_persistent",
        "ea_critical",
        "compliance_missed_2_of_7",
        "rpe_systematic_over_3_sessions",
        "ghosting_7d", "ghosting_14d", "ghosting_21d",
    ]
    detected_at: datetime
    severity: Literal["info", "watch", "concern", "critical"]
    detail_metrics: dict[str, float]
    related_log_ids: list[str] = Field(default_factory=list)
    requests_graph: Literal["chat_turn", "recovery_takeover"] | None = None
```

#### 3.4.3 `EscalationContext`

Injecté pour `ESCALATION_NUTRITION_TO_ENERGY`. Payload émis par Nutrition Coach lors d'une escalade vers Energy Coach.

```python
class EscalationContext(BaseModel):
    source_agent: Literal["nutrition_coach"]
    escalated_at: datetime
    nutrition_verdict_summary: str
    detected_patterns: list[str]
    preliminary_flag: Literal["concern", "escalate_to_energy_coach"]
    related_nutrition_log_ids: list[str] = Field(default_factory=list)
```

### 3.5 Fonctions de filtrage

#### 3.5.1 `filter_injuries_for_discipline` et matrice region-discipline

Structure de la matrice spec en B2 ; valeurs Phase C.

```python
from resilio.schema.core import BodyRegion, ContraindicationType, InjuryStatus, InjuryRecord, InjuryHistory


class ImpactSeverity(str, Enum):
    CRITICAL = "critical"
    MODERATE = "moderate"
    MINOR = "minor"
    NONE = "none"


class RegionDisciplineImpact(BaseModel):
    region: BodyRegion
    discipline: Discipline
    impact_severity: ImpactSeverity
    rationale: str
    typical_contraindications: list[ContraindicationType]


class RegionDisciplineImpactTable(BaseModel):
    schema_version: str
    last_reviewed_at: date
    last_reviewed_by: str
    bibliography: list[str]
    impacts: list[RegionDisciplineImpact]

    @model_validator(mode="after")
    def _validate_exhaustiveness(self):
        # RDI1 : toutes les combinaisons (region, discipline) présentes
        expected = {(r, d) for r in BodyRegion for d in Discipline}
        actual = {(i.region, i.discipline) for i in self.impacts}
        if expected != actual:
            missing = expected - actual
            raise ValueError(f"Missing impact entries: {missing}")
        return self


def filter_injuries_for_discipline(
    injury_history: InjuryHistory,
    target_discipline: Discipline,
    impact_table: RegionDisciplineImpactTable,
    include_severities: set[ImpactSeverity] = frozenset({
        ImpactSeverity.CRITICAL, ImpactSeverity.MODERATE,
    }),
) -> list[InjuryRecord]:
    """
    Filtre les injuries pour un coach discipline.
    
    Règles :
    - Toujours inclure les injuries ACTIVE (prudence clinique)
    - Inclure les CHRONIC_MANAGED dont la region a un impact_severity ∈ include_severities
    - Exclure les RESOLVED et HISTORICAL
    """
    filtered = []
    for injury in injury_history.injuries:
        if injury.status == InjuryStatus.ACTIVE:
            filtered.append(injury)
            continue
        if injury.status == InjuryStatus.CHRONIC_MANAGED:
            impact = next(
                (i for i in impact_table.impacts
                 if i.region == injury.region and i.discipline == target_discipline),
                None,
            )
            if impact and impact.impact_severity in include_severities:
                filtered.append(injury)
    return filtered


class DisciplineFilteredInjuryHistory(BaseModel):
    target_discipline: Discipline
    relevant_injuries: list[InjuryRecord]
    has_active_injury_impacting_discipline: bool
    has_chronic_impacting_discipline: bool
    has_avoid_discipline_contraindication: bool
    filtered_at: datetime
    impact_table_version: str
```

#### 3.5.2 `filter_injuries_for_nutrition`

Utilisée par Nutrition Coach et Energy Coach. Même filtre partagé.

```python
def filter_injuries_for_nutrition(
    injury_history: InjuryHistory,
) -> "NutritionFilteredInjuryHistory":
    """Filtre les injuries pour Nutrition et Energy Coach.
    
    Inclut :
    - Injuries ACTIVE (impact sur besoins récupération + TDEE)
    - Antécédents RED-S, fractures de stress
    - Antécédents troubles alimentaires
    
    Exclut :
    - Injuries RESOLVED / HISTORICAL non-RED-S-relatives
    - CHRONIC_MANAGED purement orthopédiques
    
    Note : détection keywords B2. Phase C formalisera annotation structurée
    InjuryRecord.is_red_s_related: bool posée par Recovery Coach.
    """
    STRESS_FRACTURE_REGIONS = {
        BodyRegion.SHIN, BodyRegion.FOOT, BodyRegion.HIP, BodyRegion.LOWER_BACK,
    }
    RED_S_KEYWORDS = {
        "red-s", "reds", "amenorrhea", "osteoporosis",
        "stress fracture", "low energy availability",
    }
    DE_KEYWORDS = {
        "ed-nos", "anorexia", "bulimia", "orthorexia", "disordered eating",
    }

    relevant = []
    has_red_s = False
    has_de = False

    for inj in injury_history.injuries:
        diag_lower = (inj.diagnosis or "").lower()
        is_red_s = (
            any(kw in diag_lower for kw in RED_S_KEYWORDS)
            or (inj.region in STRESS_FRACTURE_REGIONS and "stress" in diag_lower)
            or inj.region == BodyRegion.SYSTEMIC
        )
        is_de = any(kw in diag_lower for kw in DE_KEYWORDS)

        if inj.status == InjuryStatus.ACTIVE:
            relevant.append(inj)
        elif is_red_s or is_de:
            relevant.append(inj)

        if is_red_s:
            has_red_s = True
        if is_de:
            has_de = True

    return NutritionFilteredInjuryHistory(
        relevant_injuries=relevant,
        has_active_injury=injury_history.has_active_injury,
        has_history_of_red_s_or_stress_fracture=has_red_s,
        has_history_of_disordered_eating_flag=has_de,
        filtered_at=datetime.now(timezone.utc),
    )


class NutritionFilteredInjuryHistory(BaseModel):
    relevant_injuries: list[InjuryRecord]
    has_active_injury: bool
    has_history_of_red_s_or_stress_fracture: bool
    has_history_of_disordered_eating_flag: bool
    filtered_at: datetime
```

---

## 4. Les 9 vues agents

### 4.1 `HeadCoachView`

#### Rôle et signature

Hub d'orchestration. Vue la plus large après Recovery en takeover. Façade utilisateur constante hors overlay `recovery_takeover_active`.

```python
def get_head_coach_view(
    state: AthleteState,
    context: ViewContext,
) -> HeadCoachView:
    """
    Préconditions :
    - context.invocation_trigger ∈ HEAD_COACH_TRIGGERS
    - context.target_discipline is None
    - state.recovery_takeover_active == False

    Postconditions :
    - effective_readiness, effective_ea matérialisés (§2.3)
    - Windows injectées selon DEFAULT_WINDOWS[(AgentId.HEAD, trigger)]
    """
```

#### Classe Pydantic

```python
from resilio.schema.core import (
    CyclePhase, Discipline, Domain, ScopeLevel, JourneyPhase,
    ExperienceProfile, ObjectiveProfile, InjuryHistory, PracticalConstraints,
    DimensionClassification, ClassificationDimension, RadarData,
    ActivePlan, BaselinePlan,
    StrainState,
    ReadinessValue, UserReadinessSignal, EffectiveReadiness, PersistentOverridePattern,
    EnergyAvailabilityValue, UserEnergySignal, EffectiveEA,
    AllostaticLoadState,
    ClassifiedIntent,
    ConnectorName, ConnectorStatus, ValidationWarning,
)


class HeadCoachIdentView(BaseModel):
    athlete_id: str
    date_of_birth: date
    biological_sex: Literal["male", "female"]
    height_cm: float
    weight_kg: float
    ffm_kg: float | None
    cycle_active: bool
    cycle_phase: CyclePhase | None
    cycle_day: int | None
    cycle_length_days: int | None
    timezone: str
    locale: str
    unit_preference: Literal["metric", "imperial"]
    age_years: int = Field(..., ge=13, le=100)


class HeadCoachScopeView(BaseModel):
    coaching_scope: dict[Domain, ScopeLevel]
    peer_disciplines_active: list[Discipline]


class HeadCoachJourneyView(BaseModel):
    journey_phase: JourneyPhase
    recovery_takeover_active: bool
    onboarding_reentry_active: bool
    assessment_mode: bool


class HeadCoachSubProfilesView(BaseModel):
    experience_profile: ExperienceProfile | None
    objective_profile: ObjectiveProfile | None
    injury_history: InjuryHistory
    practical_constraints: PracticalConstraints | None


class HeadCoachClassificationView(BaseModel):
    classification: dict[Discipline, DimensionClassification]
    confidence_levels: dict[tuple[Discipline, ClassificationDimension], float]
    radar_data: RadarData | None
    last_classification_update: datetime | None


class HeadCoachPlansView(BaseModel):
    baseline_plan: BaselinePlan | None
    active_plan: ActivePlan | None


class HeadCoachDerivedReadinessView(BaseModel):
    objective_readiness: ReadinessValue | None
    user_readiness_signal: UserReadinessSignal | None
    effective_readiness: EffectiveReadiness
    persistent_override_pattern: PersistentOverridePattern


class HeadCoachDerivedEAView(BaseModel):
    objective_energy_availability: EnergyAvailabilityValue | None
    user_energy_signal: UserEnergySignal | None
    effective_energy_availability: EffectiveEA


class HeadCoachTechnicalView(BaseModel):
    active_onboarding_thread_id: str | None
    active_plan_generation_thread_id: str | None
    active_followup_thread_id: str | None
    active_recovery_thread_id: str | None
    proactive_messages_last_7d: list[datetime]
    connector_status: dict[ConnectorName, ConnectorStatus]
    validation_warnings: list[ValidationWarning]


class HeadCoachConvoView(BaseModel):
    last_classified_intent: ClassifiedIntent | None
    last_message_at: datetime | None
    messages: MessagesWindow


class HeadCoachView(BaseModel):
    """Vue complète Head Coach.
    
    HeadCoachView est un snapshot de AthleteState et ne contient jamais les
    outputs des spokes consultés. Les contrats B3 (RecoveryAssessment,
    NutritionVerdict, Recommendation, etc.) sont passés en input distinct
    à l'appel LLM Head Coach.
    """
    view_built_at: datetime
    invocation_trigger: InvocationTrigger

    ident: HeadCoachIdentView
    scope: HeadCoachScopeView
    journey: HeadCoachJourneyView
    sub_profiles: HeadCoachSubProfilesView
    classification: HeadCoachClassificationView
    plans: HeadCoachPlansView

    strain_state: StrainState | None
    derived_readiness: HeadCoachDerivedReadinessView
    derived_ea: HeadCoachDerivedEAView
    allostatic_load_state: AllostaticLoadState | None

    technical: HeadCoachTechnicalView
    convo: HeadCoachConvoView

    # Windows
    training_logs: dict[Discipline, TrainingLogsRawWindow | TrainingLoadHistoryWindow]
    training_logs_tracking: dict[Discipline, TrainingLogsRawWindow]
    physio_logs: PhysioLogsWindow
    nutrition_logs: NutritionLogsWindow | None
```

#### Règles de filtrage

**Masqués.** Aucune catégorie de `AthleteState` n'est structurellement masquée. Filtrage sur Windows uniquement.

**Partiels.** `training_logs` filtré à disciplines en FULL ; `training_logs_tracking` filtré à disciplines en TRACKING ; `nutrition_logs` None si scope NUTRITION == DISABLED.

**Agrégés.** Aucun — Head Coach voit en raw.

**Dérivés matérialisés.** `ident.age_years`, `derived_readiness.effective_readiness`, `derived_ea.effective_energy_availability`.

#### Windows

Selon politique §3.2 pour `AgentId.HEAD`. Le champ `training_logs` accepte `TrainingLogsRawWindow | TrainingLoadHistoryWindow` selon `training_logs_format` de la politique. Le champ `training_logs_tracking` reste toujours `raw` avec fenêtre 7j fixe.

#### Null-safety

Voir table consolidée §6. Spécifiques Head Coach :
- Tous les sous-profils optionnels (Phase 2 peut ne pas les avoir)
- `strain_state`, index dérivés, plans : Optional selon état journey
- `derived_readiness.effective_readiness`, `derived_ea.effective_energy_availability` : **jamais None** (matérialisés)

#### Relation A3 et contrats de sortie

Écriture directe : messages conversationnels (exception).

Contrats B3 via nodes :
- `LogisticAdjustment` → `apply_logistic_adjustment`
- `OverrideFlagReset` → `reset_override_flag`

Handlers d'intent mutant overlays :
- `handle_injury_report` → `recovery_takeover_active=True`
- `handle_goal_change`, `handle_constraint_change` → `onboarding_reentry_active=True`

#### Triggers admissibles

```python
HEAD_COACH_TRIGGERS: set[InvocationTrigger] = {
    InvocationTrigger.CHAT_FREE_QUESTION,
    InvocationTrigger.CHAT_DAILY_CHECKIN,
    InvocationTrigger.CHAT_SESSION_LOG,
    InvocationTrigger.CHAT_WEEKLY_REPORT,
    InvocationTrigger.CHAT_INJURY_REPORT,
    InvocationTrigger.CHAT_GOAL_CHANGE,
    InvocationTrigger.CHAT_CONSTRAINT_CHANGE,
    InvocationTrigger.CHAT_ADJUSTMENT_REQUEST,
    InvocationTrigger.CHAT_BLOCK_END_TRIGGER,
    InvocationTrigger.PLAN_GEN_PRESENT_TO_ATHLETE,
    InvocationTrigger.PLAN_GEN_REVISE_PLAN,
    InvocationTrigger.FOLLOWUP_HEAD_COACH_ASK,
}
```

#### Invariants de vue

| ID | Invariant | Comportement |
|---|---|---|
| HCV1 | `invocation_trigger ∈ HEAD_COACH_TRIGGERS` | rejet |
| HCV2 | `ident.age_years == floor((view_built_at - date_of_birth).days / 365.25)` | rejet |
| HCV3 | `scope.peer_disciplines_active == {D : coaching_scope[D] == FULL}` | rejet |
| HCV4a | `training_logs.keys() ⊆ {D : coaching_scope[D] == FULL}` | rejet |
| HCV4b | `training_logs_tracking.keys() ⊆ {D : coaching_scope[D] == TRACKING}` | rejet |
| HCV4c | `training_logs.keys() ∩ training_logs_tracking.keys() == ∅` | rejet |
| HCV5 | Vue non constructible si `state.recovery_takeover_active == True` | rejet |
| HCV6 | `derived_readiness.effective_readiness.resolution != None` | rejet |
| HCV7 | Si `derived_readiness.objective_readiness is None`, alors `effective_readiness.resolution == "indeterminate"` et `score is None` | rejet |
| HCV8 | `plans.active_plan` et `plans.baseline_plan` cohérents avec `journey.journey_phase` | soft warn |
| HCV9 | `nutrition_logs is None ↔ coaching_scope[NUTRITION] == DISABLED` | rejet |
| HCV10 | `convo.messages.scope == "current_thread"` → `messages.thread_id` correspond à un thread actif | rejet |
| HCV11 | `technical.validation_warnings` fraîches (`detected_at > view_built_at - 24h`) | coerce |
| HCV12 | `view_built_at == context.now` | rejet |
| HCV13 | Toutes Windows respectent WC1–WC8 | rejet |

---

### 4.2 `DisciplineCoachView` (paramétrée)

#### Rôle et signature

Vue commune aux 4 coachs disciplines (Lifting, Running, Swimming, Biking), paramétrée par `context.target_discipline`. Isolation stricte par discipline sur logs et expérience ; cross-discipline sur strain (sans origine) et allostatic load.

```python
def get_discipline_coach_view(
    state: AthleteState,
    context: ViewContext,
) -> DisciplineCoachView:
    """
    Préconditions :
    - context.target_discipline is not None
    - state.coaching_scope[target_discipline] == ScopeLevel.FULL
    - context.invocation_trigger ∈ DISCIPLINE_COACH_TRIGGERS
    - state.recovery_takeover_active == False
    """
```

#### Classe Pydantic

```python
from resilio.schema.core import (
    CyclePhase, Discipline, ScopeLevel, JourneyPhase,
    DisciplineExperience, ObjectiveProfile, PracticalConstraints,
    DimensionClassification, ClassificationDimension,
    ActivePlan, PlanBlock, PlanComponent, ActivePlanStatus, PlanHorizon,
    BaselineDisciplineSpec, BaselinePlanStatus, TradeOff,
    StrainState, MuscleGroup, StrainHistoryPoint,
    EffectiveReadiness, EffectiveEA, AllostaticLoadState,
    BlockDetailLevel,
)


class DisciplineCoachIdentView(BaseModel):
    date_of_birth: date
    biological_sex: Literal["male", "female"]
    height_cm: float
    weight_kg: float
    ffm_kg: float | None
    cycle_active: bool
    cycle_phase: CyclePhase | None
    age_years: int = Field(..., ge=13, le=100)


class DisciplineCoachScopeView(BaseModel):
    target_discipline_scope: ScopeLevel
    peer_disciplines_active: list[Discipline]  # target exclu


class DisciplineCoachJourneyView(BaseModel):
    journey_phase: JourneyPhase
    assessment_mode: bool


class DisciplineCoachSubProfilesView(BaseModel):
    objective_profile: ObjectiveProfile
    discipline_experience: DisciplineExperience
    practical_constraints: PracticalConstraints
    injury_history_filtered: DisciplineFilteredInjuryHistory


class DisciplineCoachClassificationView(BaseModel):
    target_discipline_classification: DimensionClassification
    target_discipline_confidence: dict[ClassificationDimension, float]


class BaselinePlanSummary(BaseModel):
    plan_id: str
    start_date: date
    effective_end_date: date | None
    disciplines_covered: list[Discipline]
    target_discipline_baseline_spec: BaselineDisciplineSpec | None
    status: BaselinePlanStatus
    shortened_due_to_connector_history: bool


class DisciplineCoachPlansView(BaseModel):
    active_plan_blocks: list[PlanBlock] | None
    active_plan_target_component: PlanComponent | None
    active_plan_trade_offs_relevant: list[TradeOff]
    active_plan_status: ActivePlanStatus | None
    active_plan_generated_at: datetime | None
    active_plan_horizon: PlanHorizon | None
    baseline_plan_summary: BaselinePlanSummary | None


class MuscleGroupStrainWithoutOrigin(BaseModel):
    """Strain par groupe, origine disciplinaire masquée.
    Clone de MuscleGroupStrain sans last_contribution_at."""
    current_value: float = Field(..., ge=0.0, le=100.0)
    peak_24h: float = Field(..., ge=0.0, le=100.0)
    ewma_tau_days: float = Field(..., gt=0.0)


class StrainStateWithoutOrigin(BaseModel):
    by_group: dict[MuscleGroup, MuscleGroupStrainWithoutOrigin]
    aggregate: float = Field(..., ge=0.0, le=100.0)
    history: list[StrainHistoryPoint] = Field(..., max_length=21)
    last_computed_at: datetime
    recompute_trigger: Literal["session_logged", "daily_decay", "manual"]


class DisciplineCoachDerivedView(BaseModel):
    strain_state: StrainStateWithoutOrigin | None
    effective_readiness: EffectiveReadiness
    effective_energy_availability: EffectiveEA
    allostatic_load_state: AllostaticLoadState | None


class DisciplineCoachView(BaseModel):
    """Vue coach discipline paramétrée par target_discipline.
    
    Structure commune aux 4 coachs disciplines. Spécificités prescriptives
    (VDOT, %1RM, FTP, CSS) portées par prompts Phase C.
    """
    view_built_at: datetime
    invocation_trigger: InvocationTrigger
    target_discipline: Discipline
    generation_mode: Literal["baseline", "first_personalized", "block_regen"] | None

    ident: DisciplineCoachIdentView
    scope: DisciplineCoachScopeView
    journey: DisciplineCoachJourneyView
    sub_profiles: DisciplineCoachSubProfilesView
    classification: DisciplineCoachClassificationView
    plans: DisciplineCoachPlansView
    derived: DisciplineCoachDerivedView

    training_logs: TrainingLogsRawWindow  # hydrate_exercise_details=True
    physio_logs: PhysioLogsWindow  # format summary_only
```

#### Règles de filtrage

**Masqués.** `timezone`, `locale`, `unit_preference`, `cycle_day`, `cycle_length_days`. Scopes et classifications des peers. Toutes catégories LOGS_NUTRITION, CONVO, TECHNICAL, radar_data. Overlays journey (vue non constructible si takeover, re-entry non pertinente). Triplets Readiness/EA complets (résultante uniquement).

**Partiels.**
- `active_plan.blocks` : structure macro pour tous les blocs, `block_discipline_specs` uniquement pour le bloc courant et `target_discipline`.
- `trade_offs_disclosed` : filtré à ceux impliquant `target_discipline` ou objectifs HYBRID_*.
- `baseline_plan` : injecté uniquement pour `generation_mode="first_personalized"` ou `journey_phase == baseline_active`.
- `InjuryHistory` : filtrée via `filter_injuries_for_discipline`.

**Agrégés.**
- `StrainStateWithoutOrigin` : 18 groupes exhaustifs, sans `last_contribution_at`.

**Dérivés matérialisés.** `age_years`, `effective_readiness`, `effective_energy_availability`.

#### Windows

Voir politique §3.2. Fenêtre training 21j en baseline, 42j (Lifting/Biking) ou 28j (Running/Swimming) en first_personalized/block_regen. Physio toujours `summary_only`.

`training_logs` est un objet `TrainingLogsRawWindow` unique (pas un dict) car isolation stricte sur `target_discipline`. `hydrate_exercise_details=True` ou `interval_details` populé selon discipline.

#### Null-safety

Voir §6. Spécifiques DisciplineCoach :
- `ExperienceProfile.by_discipline[target]` toujours présent (invariant X6)
- `ObjectiveProfile`, `PracticalConstraints`, `DimensionClassification[target]` toujours présents (post-onboarding)
- `active_plan_*` : None en mode baseline
- `baseline_plan_summary` : None en mode baseline ou block_regen en steady_state

#### Relation A3 et contrats de sortie

Aucune mutation directe. Contrat B3 unique : `Recommendation` (sessions prescrites + block_theme + notes_for_head_coach + flag_for_head_coach). Persisté par `persist_prescribed_sessions` via `build_proposed_plan`.

#### Triggers admissibles

```python
DISCIPLINE_COACH_TRIGGERS: set[InvocationTrigger] = {
    InvocationTrigger.PLAN_GEN_DELEGATE_SPECIALISTS,
    InvocationTrigger.CHAT_WEEKLY_REPORT,
}
```

#### Invariants de vue

| ID | Invariant | Comportement |
|---|---|---|
| DCV1 | `target_discipline is not None` | rejet |
| DCV2 | `scope.target_discipline_scope == ScopeLevel.FULL` | rejet |
| DCV3 | `target_discipline ∉ scope.peer_disciplines_active` | rejet |
| DCV4 | `invocation_trigger ∈ DISCIPLINE_COACH_TRIGGERS` | rejet |
| DCV5 | Vue non constructible si `state.recovery_takeover_active == True` | rejet |
| DCV6 | `generation_mode is not None ↔ invocation_trigger == PLAN_GEN_DELEGATE_SPECIALISTS` | rejet |
| DCV7 | `training_logs.discipline == target_discipline` | rejet |
| DCV8 | Toutes `SessionLogLite` ont `exercise_details` ou `interval_details` populé | rejet |
| DCV9 | `exercise_details` populé ⟷ discipline == LIFTING ; `interval_details` populé ⟷ discipline ∈ {RUNNING, SWIMMING, BIKING} | rejet |
| DCV10 | `sub_profiles.discipline_experience` correspond à `state.experience_profile.by_discipline[target]` | rejet |
| DCV11 | `sub_profiles.injury_history_filtered.target_discipline == target_discipline` | rejet |
| DCV12 | `classification.target_discipline_classification` correspond à `state.classification[target]` | rejet |
| DCV13 | `plans.active_plan_target_component.discipline == target_discipline` si non None | rejet |
| DCV14 | `plans.active_plan_blocks` structure macro cohérente avec state | rejet |
| DCV15 | `derived.strain_state` a 18 groupes exhaustifs | rejet |
| DCV16 | `generation_mode == "baseline"` → `plans.active_plan_* == None ∧ plans.baseline_plan_summary == None` | rejet |
| DCV17 | `generation_mode == "first_personalized"` → `plans.baseline_plan_summary is not None` | rejet |
| DCV18 | `generation_mode == "block_regen"` → `plans.active_plan_target_component is not None` | rejet |
| DCV19 | `view_built_at == context.now` | rejet |
| DCV20 | Toutes Windows respectent WC1–WC8 | rejet |

---

### 4.3 `OnboardingCoachDelegationView`

#### Rôle et signature

Vue Onboarding Coach en mode délégation (Phase 2 initiale, re-entry partielle). L'agent détient le tour conversationnel. Écrit sous-profils via nodes `persist_block`.

```python
def _build_delegation_view(
    state: AthleteState,
    context: ViewContext,
) -> OnboardingCoachDelegationView:
    """
    Préconditions :
    - context.invocation_trigger ∈ {ONBOARDING_CONDUCT_BLOCK, ONBOARDING_REENTRY_CONDUCT_BLOCK}
    - context.current_onboarding_thread_id is not None
    - context.onboarding_blocks_to_cover is not None
    - context.onboarding_current_block is not None
    - state.journey_phase == ONBOARDING OR state.onboarding_reentry_active == True
    - state.recovery_takeover_active == False
    """


def get_onboarding_coach_view(
    state: AthleteState,
    context: ViewContext,
) -> "OnboardingCoachDelegationView | OnboardingCoachConsultationView":
    """Factory dispatchant vers la bonne vue selon context.invocation_trigger."""
    trigger = context.invocation_trigger
    if trigger in {
        InvocationTrigger.ONBOARDING_CONDUCT_BLOCK,
        InvocationTrigger.ONBOARDING_REENTRY_CONDUCT_BLOCK,
    }:
        return _build_delegation_view(state, context)
    if trigger == InvocationTrigger.FOLLOWUP_CONSULT_ONBOARDING:
        return _build_consultation_view(state, context)
    raise ValueError(f"OnboardingCoachView not constructible for trigger {trigger}")
```

#### Classe Pydantic

```python
class OnboardingDelegationIdentView(BaseModel):
    date_of_birth: date
    biological_sex: Literal["male", "female"]
    height_cm: float
    weight_kg: float
    ffm_kg: float | None
    cycle_active: bool
    age_years: int = Field(..., ge=13, le=100)
    # cycle_phase, cycle_day, cycle_length_days MASQUÉS en délégation


class OnboardingDelegationScopeView(BaseModel):
    coaching_scope: dict[Domain, ScopeLevel]
    peer_disciplines_active: list[Discipline]


class OnboardingDelegationJourneyView(BaseModel):
    journey_phase: JourneyPhase
    is_reentry: bool


class OnboardingDelegationSubProfilesView(BaseModel):
    experience_profile: ExperienceProfile | None
    objective_profile: ObjectiveProfile | None
    injury_history: InjuryHistory
    practical_constraints: PracticalConstraints | None


class OnboardingCoachDelegationView(BaseModel):
    view_built_at: datetime
    invocation_trigger: InvocationTrigger
    is_reentry: bool

    # Contexte du parcours onboarding (injecté depuis ViewContext)
    blocks_to_cover: list[OnboardingBlockType]
    current_block: OnboardingBlockType
    blocks_already_completed: list[OnboardingBlockType]
    current_onboarding_thread_id: str

    ident: OnboardingDelegationIdentView
    scope: OnboardingDelegationScopeView
    journey: OnboardingDelegationJourneyView
    sub_profiles: OnboardingDelegationSubProfilesView

    messages: MessagesWindow
```

#### Règles de filtrage

**Masqués.** `timezone`, `locale`, `unit_preference`, `cycle_phase`, `cycle_day`, `cycle_length_days`. Overlays journey (sauf `journey_phase` et `is_reentry`). Toutes catégories CLASSIFICATION, PLANS, LOGS_*, DERIVED_*, TECHNICAL (sauf thread courant).

**Partiels.** Sous-profils `None` tant que bloc pas complété. `messages.scope == "current_thread"` systématiquement.

**Dérivés à la construction.** `age_years`, `blocks_already_completed` (dérivé par inspection des sub_profiles non-None), `is_reentry` (dérivé du trigger).

#### Windows

Uniquement `MessagesWindow`. 50 messages en Phase 2, 30 en re-entry. Scope `current_thread`, thread_id = `context.current_onboarding_thread_id`.

#### Null-safety

Spécifiques Delegation : tous les sous-profils peuvent être `None` en Phase 2 initiale. `injury_history` toujours présent (default liste vide). `ffm_kg` souvent `None` pré-connecteur.

#### Relation A3 et contrats de sortie

Mutations via nodes :
- `persist_block` (4 sous-profils) — bloc complété
- `persist_ident_refinement` — IDENT refinement
- `compute_classification` + `generate_radar` — fin de Phase 2
- `finalize_onboarding` — mute `journey_phase`

Messages conversationnels en écriture directe pendant délégation.

Pas de contrat B3 structuré en délégation (les blocs persistés sont le mécanisme de sortie).

#### Triggers admissibles

```python
ONBOARDING_DELEGATION_TRIGGERS: set[InvocationTrigger] = {
    InvocationTrigger.ONBOARDING_CONDUCT_BLOCK,
    InvocationTrigger.ONBOARDING_REENTRY_CONDUCT_BLOCK,
}
```

#### Invariants de vue

| ID | Invariant | Comportement |
|---|---|---|
| DV1 | `invocation_trigger ∈ ONBOARDING_DELEGATION_TRIGGERS` | rejet |
| DV2 | `is_reentry == (invocation_trigger == ONBOARDING_REENTRY_CONDUCT_BLOCK)` | rejet |
| DV3 | `is_reentry ↔ state.onboarding_reentry_active == True` | rejet |
| DV4 | `¬is_reentry → journey.journey_phase == JourneyPhase.ONBOARDING` | rejet |
| DV5 | Vue non constructible si `state.recovery_takeover_active == True` | rejet |
| DV6 | `current_block ∈ blocks_to_cover` | rejet |
| DV7 | `current_block ∉ blocks_already_completed` | rejet |
| DV8 | `blocks_already_completed ⊆ blocks_to_cover` | rejet |
| DV9 | `messages.scope == "current_thread" ∧ messages.thread_id == current_onboarding_thread_id` | rejet |
| DV10 | `current_onboarding_thread_id == state.active_onboarding_thread_id` | rejet |
| DV11 | Si `is_reentry == True ∧ current_block == OBJECTIVES`, alors `sub_profiles.objective_profile is not None` | rejet |
| DV12 | `view_built_at == context.now` | rejet |

---

### 4.4 `OnboardingCoachConsultationView`

#### Rôle et signature

Vue Onboarding Coach en consultation Phase 5. Reçoit `BaselineObservations`, produit `FollowupQuestionSet`. Ne parle pas au user.

```python
def _build_consultation_view(
    state: AthleteState,
    context: ViewContext,
) -> OnboardingCoachConsultationView:
    """
    Préconditions :
    - context.invocation_trigger == FOLLOWUP_CONSULT_ONBOARDING
    - context.baseline_observations is not None (VC2)
    - state.journey_phase == FOLLOWUP_TRANSITION
    - state.assessment_mode == True
    - state.onboarding_reentry_active == False
    - state.recovery_takeover_active == False
    - Tous les sous-profils présents (post-onboarding)
    """
```

#### Classe Pydantic

```python
class OnboardingConsultationIdentView(BaseModel):
    date_of_birth: date
    biological_sex: Literal["male", "female"]
    height_cm: float
    weight_kg: float
    ffm_kg: float | None
    cycle_active: bool
    cycle_phase: CyclePhase | None  # INJECTÉ en Phase 5 (post-onboarding, peut informer questions)
    age_years: int = Field(..., ge=13, le=100)


class OnboardingConsultationScopeView(BaseModel):
    coaching_scope: dict[Domain, ScopeLevel]
    peer_disciplines_active: list[Discipline]


class OnboardingConsultationJourneyView(BaseModel):
    journey_phase: JourneyPhase
    assessment_mode: bool


class OnboardingConsultationSubProfilesView(BaseModel):
    experience_profile: ExperienceProfile
    objective_profile: ObjectiveProfile
    injury_history: InjuryHistory
    practical_constraints: PracticalConstraints


class OnboardingConsultationClassificationView(BaseModel):
    classification: dict[Discipline, DimensionClassification]
    confidence_levels: dict[tuple[Discipline, ClassificationDimension], float]
    last_classification_update: datetime | None


class OnboardingCoachConsultationView(BaseModel):
    view_built_at: datetime
    invocation_trigger: InvocationTrigger

    ident: OnboardingConsultationIdentView
    scope: OnboardingConsultationScopeView
    journey: OnboardingConsultationJourneyView
    sub_profiles: OnboardingConsultationSubProfilesView
    classification: OnboardingConsultationClassificationView

    baseline_observations: BaselineObservations
```

#### Règles de filtrage

**Masqués.** Toutes catégories PLANS, LOGS_*, DERIVED_*, CONVO, TECHNICAL. Overlays journey.

**Partiels.** Aucun.

**Dérivés à la construction.** `age_years`. `baseline_observations` copié depuis `context`.

#### Windows

Aucune. Les écarts arrivent déjà synthétisés via `baseline_observations`.

#### Null-safety

Tous les sous-profils non-None (post-onboarding). Classification présente. `ffm_kg` peut être None si connecteurs ratés.

#### Relation A3 et contrats de sortie

Aucune mutation directe. Contrat B3 unique : `FollowupQuestionSet` (liste de questions structurées avec targets, rationale, priority). Head Coach pose les questions via `head_coach_ask_question`. Réponses appliquées via `update_profile_deltas` (sans repasser par Onboarding Coach).

#### Triggers admissibles

```python
ONBOARDING_CONSULTATION_TRIGGERS: set[InvocationTrigger] = {
    InvocationTrigger.FOLLOWUP_CONSULT_ONBOARDING,
}
```

#### Invariants de vue

| ID | Invariant | Comportement |
|---|---|---|
| CV1 | `invocation_trigger == FOLLOWUP_CONSULT_ONBOARDING` | rejet |
| CV2 | `journey.journey_phase == JourneyPhase.FOLLOWUP_TRANSITION` | rejet |
| CV3 | `journey.assessment_mode == True` | rejet |
| CV4 | Vue non constructible si `state.onboarding_reentry_active == True` | rejet |
| CV5 | Vue non constructible si `state.recovery_takeover_active == True` | rejet |
| CV6 | `sub_profiles.experience_profile, objective_profile, practical_constraints` tous non-None | rejet |
| CV7 | `experience_profile.by_discipline.keys() == {D : coaching_scope[D] == FULL}` | rejet |
| CV8 | `classification.classification.keys() == {D : coaching_scope[D] == FULL}` | rejet |
| CV9 | `baseline_observations.baseline_plan_id` correspond à un `BaselinePlan` existant | rejet |
| CV10 | `baseline_observations.actual_vs_prescribed_volume_ratio.keys() ⊆ {D : coaching_scope[D] == FULL}` | rejet |
| CV11 | `view_built_at == context.now` | rejet |

---

### 4.5 `NutritionCoachView`

#### Rôle et signature

Nutrition Coach raisonne quotidien (calories, macros, timing). Propriétaire LOGS_NUTRITION et targets quotidiens. Escalade vers Energy Coach sur pattern structurel.

```python
def get_nutrition_coach_view(
    state: AthleteState,
    context: ViewContext,
) -> NutritionCoachView:
    """
    Préconditions :
    - state.coaching_scope[Domain.NUTRITION] == ScopeLevel.FULL
    - state.practical_constraints.meals is not None (invariant PC2)
    - context.invocation_trigger ∈ NUTRITION_COACH_TRIGGERS
    - state.recovery_takeover_active == False
    """
```

#### Classe Pydantic

```python
from resilio.schema.core import (
    MealContext, SleepPattern, WorkContext, GeographicContext,
    DisciplineRoleInPlan, WeeklyVolumePoint, VolumeTarget,
    BaselinePlanStatus,
)


class NutritionCoachIdentView(BaseModel):
    date_of_birth: date
    biological_sex: Literal["male", "female"]
    height_cm: float
    weight_kg: float
    ffm_kg: float | None
    cycle_active: bool
    cycle_phase: CyclePhase | None
    age_years: int = Field(..., ge=13, le=100)


class NutritionCoachScopeView(BaseModel):
    nutrition_scope: ScopeLevel
    peer_disciplines_active: list[Discipline]


class NutritionCoachJourneyView(BaseModel):
    journey_phase: JourneyPhase
    assessment_mode: bool


class NutritionRelevantConstraints(BaseModel):
    """Sous-ensemble de PracticalConstraints pour Nutrition."""
    meals: MealContext
    sleep: SleepPattern
    work: WorkContext
    geographic_context: GeographicContext | None
    financial_budget_flag: Literal["tight", "moderate", "flexible"] | None
    last_updated_at: datetime


class NutritionCoachSubProfilesView(BaseModel):
    objective_profile: ObjectiveProfile
    injury_history_filtered: NutritionFilteredInjuryHistory
    practical_constraints_nutrition: NutritionRelevantConstraints


class DisciplineComponentNutritionSummary(BaseModel):
    """Vue Nutrition d'une composante discipline du plan."""
    discipline: Discipline
    role_in_plan: DisciplineRoleInPlan
    total_volume_arc: list[WeeklyVolumePoint]


class BaselinePlanNutritionSummary(BaseModel):
    plan_id: str
    start_date: date
    effective_end_date: date | None
    disciplines_covered: list[Discipline]
    status: BaselinePlanStatus
    projected_weekly_volume: dict[Discipline, VolumeTarget]


class NutritionCoachPlansView(BaseModel):
    active_plan_blocks: list[PlanBlock] | None
    active_plan_discipline_components_summary: dict[
        Discipline, DisciplineComponentNutritionSummary
    ] | None
    active_plan_trade_offs_relevant: list[TradeOff]
    active_plan_status: ActivePlanStatus | None
    active_plan_horizon: PlanHorizon | None
    baseline_plan_summary: BaselinePlanNutritionSummary | None


class NutritionCoachDerivedReadinessView(BaseModel):
    objective_readiness: ReadinessValue | None
    user_readiness_signal: UserReadinessSignal | None
    effective_readiness: EffectiveReadiness
    persistent_override_pattern: PersistentOverridePattern


class NutritionCoachDerivedEAView(BaseModel):
    objective_energy_availability: EnergyAvailabilityValue | None
    user_energy_signal: UserEnergySignal | None
    effective_energy_availability: EffectiveEA


class StrainStateAggregate(BaseModel):
    """Strain state vu par Nutrition : agrégat seul."""
    aggregate: float = Field(..., ge=0.0, le=100.0)
    aggregate_history_7d: list[float]
    last_computed_at: datetime
    recompute_trigger: Literal["session_logged", "daily_decay", "manual"]


class NutritionCoachView(BaseModel):
    view_built_at: datetime
    invocation_trigger: InvocationTrigger

    ident: NutritionCoachIdentView
    scope: NutritionCoachScopeView
    journey: NutritionCoachJourneyView
    sub_profiles: NutritionCoachSubProfilesView
    plans: NutritionCoachPlansView

    derived_readiness: NutritionCoachDerivedReadinessView
    derived_ea: NutritionCoachDerivedEAView
    strain_state_aggregate: StrainStateAggregate | None
    allostatic_load_state: AllostaticLoadState | None

    nutrition_logs: NutritionLogsWindow  # raw
    training_load_history: TrainingLoadHistoryWindow  # all_active_disciplines
    physio_logs: PhysioLogsWindow  # summary_only

    # Drapeau dérivé : caution élevée si RED-S / fracture / disordered eating / active injury
    caution_elevated: bool
```

#### Règles de filtrage

**Masqués.** `timezone`, `locale`, `unit_preference`, `cycle_day`, `cycle_length_days`. Overlays journey. `ExperienceProfile` complet. Toutes catégories CLASSIFICATION, CONVO, TECHNICAL. Logs training bruts (remplacés par load_history). Strain détaillé (agrégat seul).

**Partiels.** `scope` limité à `nutrition_scope + peer_disciplines_active`. `practical_constraints` filtré via `NutritionRelevantConstraints`. `injury_history` filtré via `filter_injuries_for_nutrition`. Plan par summary filtré sur target nutrition.

**Agrégés.** `StrainStateAggregate` (agrégat + historique 7j, pas de détail par groupe). `TrainingLoadHistoryWindow` all_active_disciplines.

**Dérivés à la construction.** `age_years`, `effective_readiness`, `effective_energy_availability`, `strain_state_aggregate.aggregate_history_7d`, `caution_elevated`.

#### Windows

Voir §3.2. Training en `load_history` partout (incluant TRACKING disciplines dans `scope="all_active_disciplines"`). Nutrition `raw`, physio `summary_only`.

#### Null-safety

Voir §6. Spécifiques Nutrition :
- `objective_profile`, `practical_constraints_nutrition.meals` jamais None (invariants)
- `caution_elevated` jamais None (bool)
- Plans et index dérivés Optional selon état journey

#### Relation A3 et contrats de sortie

Mutations :
- Targets quotidiens via `persist_nutrition_targets` (node)
- Composante nutrition de `active_plan` via `build_proposed_plan`

Contrat B3 : `NutritionVerdict` (status, daily_targets, adjustment_suggestion, flag_for_head_coach, pass_to_energy_coach).

#### Triggers admissibles

```python
NUTRITION_COACH_TRIGGERS: set[InvocationTrigger] = {
    InvocationTrigger.CHAT_DAILY_CHECKIN,
    InvocationTrigger.CHAT_WEEKLY_REPORT,
    InvocationTrigger.PLAN_GEN_DELEGATE_SPECIALISTS,
}
```

#### Invariants de vue

| ID | Invariant | Comportement |
|---|---|---|
| NCV1 | `invocation_trigger ∈ NUTRITION_COACH_TRIGGERS` | rejet |
| NCV2 | `scope.nutrition_scope == ScopeLevel.FULL` | rejet |
| NCV3 | `sub_profiles.practical_constraints_nutrition.meals is not None` | rejet |
| NCV4 | Vue non constructible si `state.recovery_takeover_active == True` | rejet |
| NCV5 | `ident.age_years == floor((view_built_at - date_of_birth).days / 365.25)` | rejet |
| NCV6 | `derived_readiness.effective_readiness.resolution != None` | rejet |
| NCV7 | Si `derived_readiness.objective_readiness is None`, alors `effective_readiness.resolution == "indeterminate"` | rejet |
| NCV8 | `derived_ea.effective_energy_availability.resolution != None` | rejet |
| NCV9 | `plans.active_plan_discipline_components_summary.keys() ⊆ {D : coaching_scope[D] == FULL}` | rejet |
| NCV10 | `training_load_history.scope == "all_active_disciplines"` | rejet |
| NCV11 | Disciplines dans `training_load_history.daily_points` ⊆ coaching_scope FULL ∪ TRACKING | rejet |
| NCV12 | `nutrition_logs.format == "raw"` | rejet |
| NCV13 | `physio_logs.format == "summary_only"` | rejet |
| NCV14 | `strain_state_aggregate.aggregate_history_7d` length ≤ 7 | rejet |
| NCV15 | `caution_elevated == (injury_history_filtered.has_active_injury ∨ has_history_of_red_s_or_stress_fracture ∨ has_history_of_disordered_eating_flag)` | coerce |
| NCV16 | `view_built_at == context.now` | rejet |
| NCV17 | Toutes Windows respectent WC1–WC8 | rejet |

---

### 4.6 `RecoveryCoachView`

#### Rôle et signature

Spécialiste diagnostic clinique et protocoles de récupération. Quatre modes d'invocation : takeover actif, consultation hebdo, monitoring event, injury report initial. Structure de vue unique, fenêtres variant selon trigger.

```python
def get_recovery_coach_view(
    state: AthleteState,
    context: ViewContext,
) -> RecoveryCoachView:
    """
    Préconditions :
    - context.invocation_trigger ∈ RECOVERY_COACH_TRIGGERS
    - Si trigger ∈ RECOVERY_*, alors state.recovery_takeover_active == True
    - Si trigger == CHAT_INJURY_REPORT, state.recovery_takeover_active peut être T ou F
    """
```

#### Classe Pydantic

```python
class RecoveryCoachIdentView(BaseModel):
    date_of_birth: date
    biological_sex: Literal["male", "female"]
    height_cm: float
    weight_kg: float
    ffm_kg: float | None
    cycle_active: bool
    cycle_phase: CyclePhase | None  # INJECTÉ même si cycle_active=False (AMENORRHEA, POST_MENOPAUSE)
    cycle_day: int | None
    cycle_length_days: int | None
    age_years: int = Field(..., ge=13, le=100)


class RecoveryCoachScopeView(BaseModel):
    coaching_scope: dict[Domain, ScopeLevel]
    peer_disciplines_active: list[Discipline]


class RecoveryCoachJourneyView(BaseModel):
    journey_phase: JourneyPhase
    recovery_takeover_active: bool
    onboarding_reentry_active: bool
    assessment_mode: bool


class RecoveryCoachSubProfilesView(BaseModel):
    experience_profile: ExperienceProfile | None
    objective_profile: ObjectiveProfile | None
    injury_history: InjuryHistory  # COMPLET, non filtré (propriétaire)
    practical_constraints: PracticalConstraints | None


class RecoveryCoachClassificationView(BaseModel):
    classification: dict[Discipline, DimensionClassification]
    confidence_levels: dict[tuple[Discipline, ClassificationDimension], float]


class RecoveryCoachPlansView(BaseModel):
    active_plan: ActivePlan | None
    baseline_plan: BaselinePlan | None


class RecoveryCoachDerivedReadinessView(BaseModel):
    objective_readiness: ReadinessValue | None
    user_readiness_signal: UserReadinessSignal | None
    effective_readiness: EffectiveReadiness
    persistent_override_pattern: PersistentOverridePattern


class RecoveryCoachDerivedEAView(BaseModel):
    objective_energy_availability: EnergyAvailabilityValue | None
    user_energy_signal: UserEnergySignal | None
    effective_energy_availability: EffectiveEA


class RecoveryCoachTechnicalView(BaseModel):
    active_recovery_thread_id: str | None
    connector_status: dict[ConnectorName, ConnectorStatus]
    validation_warnings: list[ValidationWarning]


class RecoveryCoachConvoView(BaseModel):
    last_classified_intent: ClassifiedIntent | None
    last_message_at: datetime | None
    messages: MessagesWindow | None  # None si monitoring event ou weekly_report


class RecoveryCoachView(BaseModel):
    view_built_at: datetime
    invocation_trigger: InvocationTrigger
    is_in_takeover: bool  # dérivé du trigger

    ident: RecoveryCoachIdentView
    scope: RecoveryCoachScopeView
    journey: RecoveryCoachJourneyView
    sub_profiles: RecoveryCoachSubProfilesView
    classification: RecoveryCoachClassificationView
    plans: RecoveryCoachPlansView

    strain_state: StrainState | None  # COMPLET avec origine
    derived_readiness: RecoveryCoachDerivedReadinessView
    derived_ea: RecoveryCoachDerivedEAView
    allostatic_load_state: AllostaticLoadState | None

    technical: RecoveryCoachTechnicalView
    convo: RecoveryCoachConvoView

    training_logs: dict[Discipline, TrainingLogsRawWindow]  # FULL ∪ TRACKING, hydrate=False
    physio_logs: PhysioLogsWindow  # raw (seul agent)
    nutrition_logs: NutritionLogsWindow | None  # summary_only si scope FULL

    monitoring_event_payload: MonitoringEventPayload | None
```

#### Règles de filtrage

**Masqués.** `timezone`, `locale`, `unit_preference`. `radar_data`, `last_classification_update`. Catégories TECHNICAL hors `active_recovery_thread_id`, `connector_status`, `validation_warnings`.

**Partiels.** `messages` selon trigger (takeover → recovery_thread ; injury_report → chat_thread ; weekly/monitoring → None). `nutrition_logs` conditionnel sur scope et trigger.

**Dérivés à la construction.** `age_years`, `is_in_takeover`, `effective_readiness`, `effective_energy_availability`. `monitoring_event_payload` copié depuis `context`.

#### Windows

Voir §3.2. Profondeur variable par trigger (28j training + 30j physio en takeover, 14j training + 30j physio en weekly). Physio **raw** systématiquement (seul agent avec ce niveau de détail). `hydrate_exercise_details=False` sur sessions training. `training_logs` inclut FULL ∪ TRACKING.

#### Null-safety

Voir §6. Spécifiques Recovery :
- `strain_state` est `StrainState` complet (avec `last_contribution_at`), pas `StrainStateWithoutOrigin`
- `messages` None en weekly_report et monitoring
- `injury_history` toujours présent (default vide), non filtré

#### Relation A3 et contrats de sortie

Mutations via nodes :
- `activate_clinical_frame` — `recovery_takeover_active=True`, suspend plan
- `persist_injury` — nouveau record dans InjuryHistory
- `flag_override_pattern` — `persistent_override_pattern.active=True`
- `suspend_active_plan` — `active_plan.status=SUSPENDED`
- `handoff_to_baseline` — ferme overlay, mute journey_phase

Contrat B3 en consultation : `RecoveryAssessment` (severity, signal_summary, override_pattern_detected, recommendation, flag_for_head_coach).

En takeover : messages conversationnels directs, pas de contrat structuré.

#### Triggers admissibles

```python
RECOVERY_COACH_TRIGGERS: set[InvocationTrigger] = {
    InvocationTrigger.CHAT_INJURY_REPORT,
    InvocationTrigger.RECOVERY_ACTIVATE_FRAME,
    InvocationTrigger.RECOVERY_ASSESS_SITUATION,
    InvocationTrigger.RECOVERY_PROPOSE_PROTOCOL,
    InvocationTrigger.RECOVERY_EVALUATE_READINESS,
    InvocationTrigger.CHAT_WEEKLY_REPORT,
    InvocationTrigger.MONITORING_HRV,
    InvocationTrigger.MONITORING_SLEEP,
}
```

#### Invariants de vue

| ID | Invariant | Comportement |
|---|---|---|
| RCV1 | `invocation_trigger ∈ RECOVERY_COACH_TRIGGERS` | rejet |
| RCV2 | `is_in_takeover == invocation_trigger.value.startswith("recovery_")` | rejet |
| RCV3 | `is_in_takeover ↔ state.recovery_takeover_active == True` | rejet |
| RCV4 | `is_in_takeover == True` → `technical.active_recovery_thread_id is not None` | rejet |
| RCV5 | `CHAT_INJURY_REPORT` : `state.recovery_takeover_active` peut être True ou False | — |
| RCV6 | Si trigger ∈ `MONITORING_*`, alors `monitoring_event_payload is not None` ET `convo.messages is None` | rejet |
| RCV7 | Si trigger ∈ `RECOVERY_*`, alors `convo.messages.scope == "current_thread"` ET `messages.thread_id == technical.active_recovery_thread_id` | rejet |
| RCV8 | Si trigger == `CHAT_INJURY_REPORT`, alors `convo.messages.scope == "current_thread"` (chat thread) | rejet |
| RCV9 | Si trigger == `CHAT_WEEKLY_REPORT`, alors `convo.messages is None` | rejet |
| RCV10 | `training_logs.keys() == {D : coaching_scope[D] ∈ {FULL, TRACKING}}` | rejet |
| RCV11 | Toutes `SessionLogLite` ont `exercise_details is None ET interval_details is None` | rejet |
| RCV12 | `physio_logs.format == "raw"` | rejet |
| RCV13 | `nutrition_logs is None ↔ (coaching_scope[NUTRITION] != FULL OR trigger ∈ {RECOVERY_EVALUATE_READINESS, MONITORING_HRV, MONITORING_SLEEP})` | rejet |
| RCV14 | `strain_state` est `StrainState` complet (via signature) | rejet |
| RCV15 | Si `persistent_override_pattern.active == True ∧ ¬is_in_takeover`, alors `effective_readiness.resolution == "pattern_neutralized"` | rejet |
| RCV16 | `sub_profiles.injury_history` complet (pas filtré, check par absence de `target_discipline`) | rejet |
| RCV17 | `view_built_at == context.now` | rejet |
| RCV18 | Toutes Windows respectent WC1–WC8 | rejet |

---

### 4.7 `EnergyCoachView`

#### Rôle et signature

Spécialiste équilibre énergétique structurel et modulation hormonale. Horizon long (jusqu'à 60j). Propriétaire sémantique de l'interprétation EA. Escalade Recovery via flag.

```python
def get_energy_coach_view(
    state: AthleteState,
    context: ViewContext,
) -> EnergyCoachView:
    """
    Préconditions :
    - context.invocation_trigger ∈ ENERGY_COACH_TRIGGERS
    - Au moins une discipline en FULL
    - state.recovery_takeover_active == False

    Note : n'exige PAS coaching_scope[NUTRITION] == FULL (Energy fonctionne
    en mode dégradé sans nutrition logs).
    """
```

#### Classe Pydantic

```python
from resilio.schema.core import EAZone


class EnergyCoachIdentView(BaseModel):
    date_of_birth: date
    biological_sex: Literal["male", "female"]
    height_cm: float
    weight_kg: float
    ffm_kg: float | None  # CRITIQUE pour EA
    cycle_active: bool
    cycle_phase: CyclePhase | None  # injecté même si cycle_active=False
    cycle_day: int | None
    cycle_length_days: int | None
    age_years: int = Field(..., ge=13, le=100)


class EnergyCoachScopeView(BaseModel):
    coaching_scope: dict[Domain, ScopeLevel]
    peer_disciplines_active: list[Discipline]
    disciplines_tracked: list[Discipline]
    nutrition_scope: ScopeLevel


class EnergyCoachJourneyView(BaseModel):
    journey_phase: JourneyPhase
    assessment_mode: bool


class EnergyRelevantConstraints(BaseModel):
    meals: MealContext | None  # peut être None si nutrition DISABLED
    sleep: SleepPattern
    work: WorkContext
    geographic_context: GeographicContext | None
    last_updated_at: datetime


class EnergyCoachSubProfilesView(BaseModel):
    objective_profile: ObjectiveProfile
    injury_history_filtered: NutritionFilteredInjuryHistory
    practical_constraints_energy: EnergyRelevantConstraints


class WeeklyVolumePointWithEEE(BaseModel):
    week_number: int = Field(..., ge=1)
    volume: VolumeTarget
    estimated_weekly_eee_kcal: float | None = Field(None, ge=0.0)


class DisciplineComponentEnergyProjection(BaseModel):
    discipline: Discipline
    role_in_plan: DisciplineRoleInPlan
    total_volume_arc: list[WeeklyVolumePointWithEEE]
    projected_total_eee_kcal_over_plan: float | None
    deprioritized_vs_ideal: bool


class BaselinePlanEnergySummary(BaseModel):
    plan_id: str
    start_date: date
    effective_end_date: date | None
    disciplines_covered: list[Discipline]
    status: BaselinePlanStatus
    projected_weekly_eee_kcal: dict[Discipline, float]
    projected_total_eee_kcal: float


class EnergyCoachPlansView(BaseModel):
    active_plan_blocks: list[PlanBlock] | None
    active_plan_discipline_components_projection: dict[
        Discipline, DisciplineComponentEnergyProjection
    ] | None
    active_plan_trade_offs_relevant: list[TradeOff]
    active_plan_status: ActivePlanStatus | None
    active_plan_horizon: PlanHorizon | None
    active_plan_start_date: date | None
    active_plan_end_date: date | None
    baseline_plan_summary: BaselinePlanEnergySummary | None


class EAZoneWeekPoint(BaseModel):
    """Point hebdomadaire de la trajectoire EA."""
    week_start: date
    week_end: date
    avg_ea_kcal_per_kg_ffm: float
    dominant_zone: EAZone
    days_per_zone: dict[EAZone, int]
    days_with_complete_data: int = Field(..., ge=0, le=7)


class EnergyCoachDerivedReadinessView(BaseModel):
    objective_readiness: ReadinessValue | None
    user_readiness_signal: UserReadinessSignal | None
    effective_readiness: EffectiveReadiness
    persistent_override_pattern: PersistentOverridePattern


class EnergyCoachDerivedEAView(BaseModel):
    objective_energy_availability: EnergyAvailabilityValue | None
    user_energy_signal: UserEnergySignal | None
    effective_energy_availability: EffectiveEA
    ea_zone_trajectory: list[EAZoneWeekPoint]  # dérivé


class WeeklyStrainPoint(BaseModel):
    week_start: date
    week_end: date
    avg_aggregate: float = Field(..., ge=0.0, le=100.0)
    peak_aggregate: float = Field(..., ge=0.0, le=100.0)
    days_with_data: int = Field(..., ge=0, le=7)


class EnergyCoachDerivedStrainView(BaseModel):
    """Strain agrégé hebdomadaire pour Energy."""
    current_aggregate: float = Field(..., ge=0.0, le=100.0)
    weekly_aggregates: list[WeeklyStrainPoint]
    last_computed_at: datetime
    recompute_trigger: Literal["session_logged", "daily_decay", "manual"]


class EnergyCoachView(BaseModel):
    view_built_at: datetime
    invocation_trigger: InvocationTrigger

    ident: EnergyCoachIdentView
    scope: EnergyCoachScopeView
    journey: EnergyCoachJourneyView
    sub_profiles: EnergyCoachSubProfilesView
    plans: EnergyCoachPlansView

    strain: EnergyCoachDerivedStrainView | None
    derived_readiness: EnergyCoachDerivedReadinessView
    derived_ea: EnergyCoachDerivedEAView
    allostatic_load_state: AllostaticLoadState | None

    nutrition_logs: NutritionLogsWindow | None  # raw si scope FULL, None sinon
    training_load_history: TrainingLoadHistoryWindow  # all_active_disciplines
    physio_logs: PhysioLogsWindow  # summary_only

    monitoring_event_payload: MonitoringEventPayload | None
    escalation_context: EscalationContext | None
```

#### Règles de filtrage

**Masqués.** `timezone`, `locale`, `unit_preference`. `ExperienceProfile` complet. Toutes catégories CLASSIFICATION, CONVO, TECHNICAL. Logs training bruts (remplacés par load_history). Strain journalier (remplacé par hebdo).

**Partiels.** `scope` structuré en 4 champs. `practical_constraints_energy` filtré. `injury_history` filtré via `filter_injuries_for_nutrition`.

**Agrégés.** `EnergyCoachDerivedStrainView` hebdo. `TrainingLoadHistoryWindow` all_active.

**Dérivés à la construction.** `age_years`, `effective_readiness`, `effective_energy_availability`, `ea_zone_trajectory` (calculé depuis nutrition et training), `weekly_aggregates` (calculé depuis strain_state.history), projections EEE dans `DisciplineComponentEnergyProjection`. `monitoring_event_payload` et `escalation_context` copiés depuis `context`.

#### Windows

Voir §3.2. Training `load_history` partout. Nutrition conditionnel sur scope FULL. Horizons longs (60j en first_personalized, 28j en weekly_report/monitoring).

#### Null-safety

Voir §6. Spécifiques Energy :
- Si `ffm_kg is None`, alors `objective_ea is None` et Energy fonctionne en mode dégradé (signal dans `flag_for_head_coach` du contrat B3)
- `nutrition_logs` None si scope NUTRITION != FULL
- `strain` None si aucun log training

#### Relation A3 et contrats de sortie

Mutations :
- Composante énergie de `active_plan` via `build_proposed_plan`
- Flag escalade Recovery via `flag_for_recovery_coach` dans contrat

Ne mute jamais `DERIVED_EA` (EnergyAvailabilityService).

Contrat B3 : `EnergyAssessment` (ea_status, cycle_context, recommendation avec caloric_adjustment et training_load_modulation et clinical_escalation, flag_for_head_coach, flag_for_recovery_coach).

#### Triggers admissibles

```python
ENERGY_COACH_TRIGGERS: set[InvocationTrigger] = {
    InvocationTrigger.PLAN_GEN_DELEGATE_SPECIALISTS,
    InvocationTrigger.CHAT_WEEKLY_REPORT,
    InvocationTrigger.MONITORING_EA,
    InvocationTrigger.ESCALATION_NUTRITION_TO_ENERGY,
}
```

#### Invariants de vue

| ID | Invariant | Comportement |
|---|---|---|
| ECV1 | `invocation_trigger ∈ ENERGY_COACH_TRIGGERS` | rejet |
| ECV2 | `generation_mode is not None ↔ invocation_trigger == PLAN_GEN_DELEGATE_SPECIALISTS` | rejet |
| ECV3 | Au moins une discipline en FULL (`∃ D : coaching_scope[D] == FULL`) | rejet |
| ECV4 | Vue non constructible si `state.recovery_takeover_active == True` | rejet |
| ECV5 | `ident.age_years == floor((view_built_at - date_of_birth).days / 365.25)` | rejet |
| ECV6 | `derived_readiness.effective_readiness.resolution != None` | rejet |
| ECV7 | `derived_ea.effective_energy_availability.resolution != None` | rejet |
| ECV8 | Si `ident.ffm_kg is None`, alors `derived_ea.objective_energy_availability is None` | rejet |
| ECV9 | `derived_ea.ea_zone_trajectory` : weeks ordonnées asc, pas de chevauchement | rejet |
| ECV10 | `scope.peer_disciplines_active ∩ scope.disciplines_tracked == ∅` | rejet |
| ECV11 | `training_load_history.scope == "all_active_disciplines"` | rejet |
| ECV12 | `nutrition_logs is not None ↔ coaching_scope[NUTRITION] == FULL` | rejet |
| ECV13 | `physio_logs.format == "summary_only"` | rejet |
| ECV14 | `strain.weekly_aggregates` weeks ordonnées asc, pas de chevauchement | rejet |
| ECV15 | Si `trigger == MONITORING_EA`, alors `monitoring_event_payload is not None` | rejet |
| ECV16 | Si `trigger == ESCALATION_NUTRITION_TO_ENERGY`, alors `escalation_context is not None` | rejet |
| ECV17 | `monitoring_event_payload` et `escalation_context` pas tous deux non-None | rejet |
| ECV18 | `sub_profiles.practical_constraints_energy.meals is None` → `coaching_scope[NUTRITION] == DISABLED` | rejet |
| ECV19 | Si `ident.cycle_active == True`, alors `ident.cycle_phase is not None` | rejet |
| ECV20 | `view_built_at == context.now` | rejet |
| ECV21 | Toutes Windows respectent WC1–WC8 | rejet |

---

## 5. Invariants transversaux cross-vues

### 5.1 Cohérence des champs matérialisés (TV1-TV4)

Quand plusieurs vues sont construites pour le même `(state, context.now)` — typiquement `plan_generation.delegate_specialists` invoquant en parallèle plusieurs coachs disciplines + Nutrition + Energy — les champs dérivés matérialisés doivent être identiques.

| ID | Invariant | Comportement |
|---|---|---|
| TV1 | `effective_readiness` identique à travers toutes les vues pour le même `(state, now)` (score, resolution, safeguard_active) | test d'intégration |
| TV2 | `effective_energy_availability` identique à travers toutes les vues | test d'intégration |
| TV3 | `age_years` identique à travers toutes les vues pour le même `(date_of_birth, now)` | rejet |
| TV4 | `peer_disciplines_active` identique à travers toutes les vues qui l'exposent | rejet |

Implémentation : au niveau du node LangGraph qui compose plusieurs vues, après construction, exécuter une passe de vérification comparant les champs pivots. Divergence = bug de construction, fail-fast.

### 5.2 Cohérence des Windows (TV5-TV7)

Les Windows sont des fonctions pures de `(state, window_bounds, format)`, sans biais par agent.

| ID | Invariant | Comportement |
|---|---|---|
| TV5 | Deux `TrainingLogsRawWindow` pour `(same_discipline, same_window)` contiennent les mêmes `SessionLogLite` (à `exercise_details`/`interval_details` près selon `hydrate`) | rejet |
| TV6 | Deux `PhysioLogsWindow` pour la même fenêtre contiennent le même `summary` | rejet |
| TV7 | Deux `NutritionLogsWindow` pour la même fenêtre contiennent les mêmes `daily_points` | rejet |

### 5.3 Cohérence temporelle (TV8-TV10)

| ID | Invariant | Comportement |
|---|---|---|
| TV8 | Toutes les vues dans la même invocation ont `view_built_at == context.now` | rejet |
| TV9 | Toutes les Windows respectent `window_end <= view_built_at` (WC1) | rejet |
| TV10 | Aucune Window ne contient de donnée datée après `view_built_at` | rejet |

### 5.4 Cohérence des triplets (TV11-TV13)

| ID | Invariant | Comportement |
|---|---|---|
| TV11 | Toutes les vues exposant `objective_readiness` l'exposent identique à `state.objective_readiness` | rejet |
| TV12 | Toutes les vues exposant `user_readiness_signal` l'exposent identique à `state.user_readiness_signal` | rejet |
| TV13 | Idem pour `objective_energy_availability`, `user_energy_signal`, `persistent_override_pattern` | rejet |

### 5.5 Cohérence des filtrages disciplines (TV14-TV17)

| ID | Invariant | Comportement |
|---|---|---|
| TV14 | `DisciplineCoachView.sub_profiles.discipline_experience` correspond exactement à `state.experience_profile.by_discipline[target_discipline]` | rejet (DCV10) |
| TV15 | `filter_injuries_for_discipline` idempotente | rejet |
| TV16 | `filter_injuries_for_nutrition` idempotente | rejet |
| TV17 | Disciplines dans `training_logs.keys()` cohérentes avec la politique par vue (FULL seul pour DisciplineCoach et Nutrition ; FULL ∪ TRACKING pour Head, Recovery, Energy) | rejet |

### 5.6 Cohérence freshness `user_readiness_signal` (TV18-TV20)

| ID | Invariant | Comportement |
|---|---|---|
| TV18 | Toutes les vues matérialisant `effective_readiness` utilisent le même `user_signal_freshness_hours` (source unique `knowledge/thresholds.json`) | test d'intégration |
| TV19 | Toutes les vues matérialisant `effective_ea` utilisent le même `user_signal_freshness_hours` EA | test d'intégration |
| TV20 | Si `user_readiness_signal.submitted_at < now - freshness_hours`, alors `effective_readiness.resolution == "no_user_signal"` | rejet (enforcé par fonction pure) |

Les agents distinguent "pas submitted" vs "submitted mais obsolète" via la présence de `user_readiness_signal` (object présent mais stale vs object absent).

### 5.7 Autres invariants transversaux (TV21-TV22)

| ID | Invariant | Comportement |
|---|---|---|
| TV21 | Les contraintes d'overlay sur constructibilité sont enforced individuellement par chaque vue (HCV5, DCV5, NCV4, ECV4, RCV3, CV4-5, DV5) | rejet |
| TV22 | `coverage_rate` présent sur toutes les Windows (`TrainingLogsRawWindow`, `TrainingLoadHistoryWindow`, `PhysioLogsWindow.summary`, `NutritionLogsWindow.summary`) et calculé comme `effective_window_days / requested_window_days` | rejet |

---

## 6. Null-safety consolidée

### 6.1 Table récapitulative

Patterns de nullité à travers les 9 vues.

Légende :
- **R** = toujours présent (Required)
- **O** = Optional, None légitime dans cas définis
- **—** = non présent dans cette vue
- **D** = dérivé (calculé à la construction, jamais None via fonction pure)

| Champ | Head | Disc. | Onbrd. Dlg. | Onbrd. Cons. | Nutr. | Recov. | Energy |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `ident.ffm_kg` | O | O | O | O | O | O | O* |
| `ident.cycle_phase` | O | O | — | O | O | O | O |
| `ident.cycle_day` | O | — | — | — | — | O | O |
| `ident.cycle_length_days` | O | — | — | — | — | O | O |
| `experience_profile` | O | R† | O | R | — | O | — |
| `objective_profile` | O | R | O | R | R | O | R |
| `practical_constraints` | O | R‡ | O | R | R (filt.) | O | R (filt.) |
| `injury_history` | R | R (filt.) | R (empty-ok) | R | R (filt.) | R | R (filt.) |
| `classification` | R | R (filt.) | — | R | — | R | — |
| `active_plan` | O | O§ | — | — | O | O | O |
| `baseline_plan` | O | O§ | — | — | O | O | O |
| `strain_state` | O | O (w/o origin) | — | — | O (aggregate) | O (full) | O (weekly) |
| `objective_readiness` | O | — | — | — | O | O | O |
| `user_readiness_signal` | O | — | — | — | O | O | O |
| `effective_readiness` | **D** | **D** | — | — | **D** | **D** | **D** |
| `persistent_override_pattern` | R | — | — | — | R | R | R |
| `objective_energy_availability` | O | — | — | — | O | O | O |
| `user_energy_signal` | O | — | — | — | O | O | O |
| `effective_energy_availability` | **D** | **D** | — | — | **D** | **D** | **D** |
| `allostatic_load_state` | O | O | — | — | O | O | O |
| `validation_warnings` | R | — | — | — | — | R | — |
| `messages` | R | — | R | — | — | O | — |

Notes :
- **\*** (Energy, ffm_kg) : si None, Energy fonctionne en mode dégradé (Q20).
- **†** (Discipline, experience_profile) : en fait `DisciplineExperience` (filtré à `by_discipline[target]`). Toujours présent post-onboarding (invariant X6).
- **‡** (Discipline, practical_constraints) : complet, toujours présent post-onboarding.
- **§** (Discipline, active_plan / baseline_plan) : `active_plan_*` ou `baseline_plan_summary` selon `generation_mode`, voir DCV16-18.

### 6.2 Cinq règles uniformes N1-N5

**Règle N1 — Fonctions pures de résolution ne retournent jamais None directement.**

`effective_readiness` et `effective_energy_availability` sont toujours présents dans les vues qui les exposent. Si `objective_readiness` est None, alors `effective_readiness.score=None` et `effective_readiness.resolution="indeterminate"`. L'agent détecte l'absence via le champ `resolution`, pas via Optional.

**Règle N2 — Les Optional sur les sous-profils signalent "pas encore construit".**

Un agent qui voit `objective_profile is None` comprend "l'athlète n'a pas encore complété l'onboarding du bloc OBJECTIFS". En Phase 2, normal ; en Phase 6+, état transitionnel (`onboarding_reentry_active=True`).

**Règle N3 — Les Windows sont toujours présentes sauf exceptions explicites.**

`training_logs` est un dict (potentiellement vide), `physio_logs` est une Window (potentiellement `daily_points=[]`). Exceptions :
- `nutrition_logs` : `None` si scope NUTRITION != FULL
- `convo.messages` : `None` dans certains triggers Recovery (MONITORING, CHAT_WEEKLY_REPORT)

**Règle N4 — Les payloads dérivés sont None sauf trigger spécifique.**

`baseline_observations`, `monitoring_event_payload`, `escalation_context` validés par `ViewContext` VC2/VC3/VC4.

**Règle N5 — Les champs dérivés à la construction ne sont jamais None s'ils sont exposés.**

`age_years`, `ea_zone_trajectory`, `weekly_strain_aggregates` ne dépendent que de données présentes dans `state`. Si la donnée source manque, la vue pose des défauts (`ea_zone_trajectory=[]`, `weekly_aggregates=[]`).

---

## 7. Cas limites

### 7.1 `ffm_kg is None` uniformément

Rôle de FFM : divisor pour EA (kcal/kg FFM). Si None :
- `objective_energy_availability = None` (service ne peut pas calculer)
- `effective_energy_availability.score = None, resolution = "indeterminate"`
- Agents prescrivant en fonction d'EA (Nutrition, Energy) adoptent posture dégradée avec signal dans leurs contrats B3

Aucune vue ne cache FFM manquante — toujours visible via `ident.ffm_kg is None`.

### 7.2 `cycle_phase` cliniquement significatif sans `cycle_active`

Décision uniforme : `cycle_phase` injecté même si `cycle_active == False`, pour les valeurs `AMENORRHEA`, `POST_MENOPAUSE`, `HORMONAL_CONTRACEPTION_STABLE`. Applicable à Head, Nutrition, Recovery, Energy, Onboarding Consultation.

Pas à Onboarding Delegation (le cycle est interrogé au bloc santé dédié, pas lu en amont) ni aux coachs disciplines (pas de modulation cycle fine pour prescription discipline).

Un agent qui voit `cycle_active=False, cycle_phase=AMENORRHEA` adopte posture clinique (signal RED-S potentiel même si cycle non "actif" au sens régulier).

### 7.3 Overlays et constructibilité

| Overlay actif | Vue constructible pour | Vue non constructible pour |
|---|---|---|
| `recovery_takeover_active == True` | Recovery Coach (tous triggers) | Head Coach, coachs disciplines, Nutrition, Energy, Onboarding |
| `onboarding_reentry_active == True` | Onboarding Delegation (REENTRY), Head Coach | Autres (rare) |

Contraintes enforced par invariants individuels (HCV5, DCV5, NCV4, ECV4, RCV3, CV4-5, DV5).

### 7.4 Vue pré-onboarding

En `SIGNUP`, `SCOPE_SELECTION`, `ONBOARDING` en cours : tous sous-profils None. Seules vues constructibles :
- Head Coach (tous sub_profiles Optional)
- Onboarding Delegation (c'est son mode d'emploi)

Les autres triggers (plan_generation, weekly_report, etc.) se produisent uniquement en steady_state ou baseline_active → sous-profils garantis présents par invariants structurels.

### 7.5 Fenêtre adaptative sous-dotée en données

Cas : Energy invoqué en `first_personalized` demande 60j `TrainingLoadHistoryWindow`, athlète n'a que 30j.

Politique : la Window ne complète pas artificiellement. `window_start = max(demande, first_log_date)`. Exposition du décalage via `coverage_rate` sur chaque Window.

Invariant TV22 : `coverage_rate` présent sur toutes les Windows.

### 7.6 Snapshot transactionnel

Les fonctions `get_xxx_coach_view` sont atomiques du point de vue de la consistance. La construction se fait sous **snapshot transactionnel** (lecture cohérente par transaction SQL, ou snapshot en mémoire). Une Window ne voit pas d'écriture concurrente entre son `window_start` et son `window_end`.

Garantie d'implémentation (Phase D), pas invariant formel.

---

## 8. Lien vers contrats B3

### 8.1 Table des contrats émis par vue

| Agent | Contrat B3 | Trigger(s) d'émission | Mutations propagées |
|---|---|---|---|
| Head Coach | (pas de contrat structuré) | — | Messages directs, `LogisticAdjustment`, `OverrideFlagReset` |
| Onboarding Delegation | (pas de contrat par bloc) | — | `persist_block`, `persist_ident_refinement`, `persist_classification`, `generate_radar`, `finalize_onboarding` |
| Onboarding Consultation | `FollowupQuestionSet` | FOLLOWUP_CONSULT_ONBOARDING | Head Coach pose ; `update_profile_deltas` applique réponses |
| Discipline Coach | `Recommendation` | PLAN_GEN_DELEGATE_SPECIALISTS, CHAT_WEEKLY_REPORT | `persist_prescribed_sessions` via `build_proposed_plan` |
| Nutrition | `NutritionVerdict` | CHAT_DAILY_CHECKIN, CHAT_WEEKLY_REPORT, PLAN_GEN_DELEGATE_SPECIALISTS | `persist_nutrition_targets`, composante nutrition de `active_plan` |
| Recovery (consultation) | `RecoveryAssessment` | CHAT_INJURY_REPORT, CHAT_WEEKLY_REPORT, MONITORING_HRV, MONITORING_SLEEP | Selon `recommendation.action` : `activate_clinical_frame`, `suspend_active_plan`, `flag_override_pattern` |
| Recovery (takeover) | Messages directs | RECOVERY_* | `activate_clinical_frame`, `persist_injury`, `suspend_active_plan`, `handoff_to_baseline` |
| Energy | `EnergyAssessment` | Tous ENERGY_COACH_TRIGGERS | Composante énergie de `active_plan`, escalade Recovery via `flag_for_recovery_coach` |

### 8.2 Pointeurs vers mutations propagées

Les contrats B3 et leurs spec Pydantic détaillées sont l'objet de la Phase B3. Les `_AGENT_VIEWS` spec'ées ici référencent ces contrats sans les définir.

---

## 9. Résumé des décisions structurantes B2

### Décisions confirmées

1. **`ViewContext` unique + table `DEFAULT_WINDOWS`** — pas de sous-classes par trigger. Séparation données (politique) / code (validators).
2. **9 classes de vue**, dont `DisciplineCoachView` paramétré par `target_discipline` (une classe, 4 disciplines).
3. **Deux vues distinctes pour Onboarding Coach** — `Delegation` et `Consultation`. Factory `get_onboarding_coach_view` dispatche.
4. **Matérialisation systématique de `effective_readiness` et `effective_energy_availability`** via fonctions pures à la construction, non computed_field.
5. **Isolation stricte par discipline** pour les 4 coachs disciplines sur logs, expérience, classification, composante plan.
6. **Cross-discipline sur strain** pour tous sauf Onboarding. Détail avec origine pour Recovery, sans origine pour coachs disciplines, agrégat seul pour Nutrition, hebdo pour Energy.
7. **Exercise details / interval details dans `SessionLogLite`** populés uniquement pour coach discipline propriétaire via `hydrate_exercise_details=True`.
8. **Matrice `BodyRegion → Discipline → ImpactSeverity`** structure en B2, valeurs Phase C. Filtrage `filter_injuries_for_discipline` déterministe.
9. **Filtrage nutrition-pertinent** via `filter_injuries_for_nutrition` partagé entre Nutrition et Energy. Détection keywords B2, annotation structurée Phase C.
10. **Windows comme fonctions pures** de `(state, bounds, format)`, sans biais agent.
11. **5 Window models canoniques** : `TrainingLogsRawWindow`, `TrainingLoadHistoryWindow`, `PhysioLogsWindow`, `NutritionLogsWindow`, `MessagesWindow`.
12. **3 payloads dérivés non persistés** : `BaselineObservations`, `MonitoringEventPayload`, `EscalationContext`. Injectés via `ViewContext`, copiés dans les vues qui les consomment.
13. **Head Coach voit disciplines TRACKING** via champ séparé `training_logs_tracking`.
14. **Recovery voit disciplines FULL ∪ TRACKING** dans `training_logs` unifié.
15. **Nutrition et Energy incluent TRACKING** dans `training_load_history.scope="all_active_disciplines"`.
16. **`cycle_phase` injecté même si `cycle_active=False`** pour Head, Nutrition, Recovery, Energy, Onboarding Consultation.
17. **Head Coach ne reçoit pas les outputs des spokes dans la vue** — les contrats B3 transitent via input distinct du prompt.
18. **Triplets Readiness et EA complets** pour Head, Nutrition, Recovery, Energy. Résultante seule pour coachs disciplines.
19. **Recovery est propriétaire de `persistent_override_pattern`** (set via `flag_override_pattern` node). Head Coach peut le reset via `reset_override_flag`.
20. **Recovery voit `InjuryHistory` complet non filtré** (propriétaire). Coachs disciplines voient filtré par matrice. Nutrition et Energy voient filtré sur antécédents RED-S.
21. **Recovery voit `StrainState` complet avec origine** (`last_contribution_at` par groupe). Coachs disciplines voient `StrainStateWithoutOrigin`.
22. **Physio en `raw` pour Recovery uniquement.** Tous les autres agents : `summary_only`.
23. **Energy fonctionne en mode dégradé sans FFM** — signal dans flag contrat, pas de blocage construction vue.
24. **Aucune classification pour Nutrition ni Energy** (roster A3 explicite).

### Points reportés à phases ultérieures

**Phase B3** : spec Pydantic complète des contrats de sortie des agents (`Recommendation`, `NutritionVerdict`, `RecoveryAssessment`, `EnergyAssessment`, `FollowupQuestionSet`, `PrescribedSession`, `LogisticAdjustment`, `OverrideFlagReset`).

**Phase C** :
- Valeurs numériques de `DEFAULT_WINDOWS` (revue scientifique des fenêtres par agent et trigger)
- Valeurs de la matrice `RegionDisciplineImpactTable` (impact par `(BodyRegion, Discipline)`)
- Annotation structurée `InjuryRecord.is_red_s_related: bool` posée par Recovery Coach (remplace détection keywords)
- Taxonomies `session_types`, `movements_mastered`, `intensity_distribution.zones` par discipline
- Seuils numériques cliniques (`thresholds.json`) : readiness critical, EA zones, allostatic load, `persistent_override_pattern` thresholds
- Tables de prescription : VDOT, %1RM, FTP, CSS, power zones
- Protocoles cliniques Recovery par type de blessure
- Heuristiques de modulation `cycle_phase` pour Energy Coach
- Historique cycle tracking (`CycleHistoryPoint`) pour Energy Coach

**Phase D** :
- Implémentation des 9 fonctions `get_xxx_coach_view`
- Implémentation des services d'injection de Windows avec snapshot transactionnel
- Tests unitaires : chaque invariant `*V{n}` = 1 test. Chaque exemple de construction dans `agent-views-examples.md` = 1 test d'intégration.
- Hydratation à la demande de `exercise_details` / `interval_details` pour coachs disciplines
- Matérialisation des champs dérivés (`age_years`, `ea_zone_trajectory`, `weekly_strain_aggregates`, `ea_zone_trajectory`) côté service
- Caching éventuel des Windows (idempotence TV5-TV7 exploitable)
- Gestion de la concurrence sur construction simultanée de plusieurs vues pour le même `state`

---

## 10. Points reportés (Phase C et ultérieures)

Récapitulatif consolidé des ouvertures :

| Item | Phase cible | Nature |
|---|---|---|
| Valeurs `DEFAULT_WINDOWS` | C | Recalibration scientifique |
| Matrice `RegionDisciplineImpactTable` (valeurs) | C | Revue physiothérapeute |
| `InjuryRecord.is_red_s_related: bool` | C | Refactor AthleteState (mineur) |
| Taxonomies prescriptions par discipline | C | Annotation experts par discipline |
| Seuils cliniques numériques | C | Revue littérature |
| Tables VDOT / %1RM / FTP / CSS | C | Revue scientifique |
| Protocoles cliniques Recovery | C | Revue clinique |
| Historique cycle tracking | C | Ajout AthleteState (mineur) |
| Contrats B3 Pydantic complets | B3 | Spec dédiée |
| Implémentation `get_xxx_coach_view` | D | Code |
| Tests d'intégration construction vues | D | Tests |
| Snapshot transactionnel | D | Implémentation |
| Caching Windows | D | Optimisation |

---

*Document validé B2. Prochaine session : B3 — spec des contrats de sortie structurés par agent (`Recommendation`, `NutritionVerdict`, `RecoveryAssessment`, `EnergyAssessment`, `FollowupQuestionSet`, `PrescribedSession`, `LogisticAdjustment`, `OverrideFlagReset`).*
