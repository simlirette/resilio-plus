# AthleteState — Modèle de données interne

> **Source** : `backend/app/models/athlete_state.py`
> **Généré le** : 2026-04-16 depuis le code source. Zéro paraphrase — types copiés depuis les classes Pydantic.

---

## Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [AthleteState — schéma racine](#athletestate--schéma-racine)
3. [Sous-modèles détaillés](#sous-modèles-détaillés)
   - [AthleteProfile](#athleteprofile)
   - [AthleteMetrics](#athletemetrics)
   - [MuscleStrainScore](#musclestrainscore)
   - [ConnectorSnapshot](#connectorsnapshot)
   - [PlanSnapshot](#plansnapshot)
   - [RecoveryVetoV3](#recoveryvétov3)
   - [EnergySnapshot](#energysnapshot)
   - [HormonalProfile](#hormonalprofile)
   - [AllostaticSummary](#allostaticsummary)
   - [AllostaticEntry + AllostaticComponents](#allostaticentry--allostaticcomponents)
   - [DailyJournal + EnergyCheckIn](#dailyjournal--energycheckin)
   - [SyncSource](#syncsource)
4. [AgentView — matrice d'accès](#agentview--matrice-daccès)
5. [get_agent_view() — usage](#get_agent_view--usage)
6. [Règles de mise à jour](#règles-de-mise-à-jour)
7. [États typiques](#états-typiques)
8. [Section Strain — formule complète](#section-strain--formule-complète)

---

## Vue d'ensemble

`AthleteState` est le **snapshot unifié** de toutes les données athlete. Il est :

- **Construit** par le `CoachingService` avant chaque appel agent
- **Segmenté** via `get_agent_view()` pour n'exposer à chaque agent que les sections pertinentes
- **Distinct** du schéma API `AthleteResponse` (`schemas/athlete.py`) — c'est la vue interne, pas la réponse REST

```
AthleteState
├── profile          ← AthleteProfile (copie du schéma API)
├── metrics          ← AthleteMetrics (Terra raw + dérivés ACWR/fatigue/strain)
├── connectors       ← ConnectorSnapshot (activités Strava + workouts Hevy récents)
├── plan             ← PlanSnapshot (séances today + semaine)
├── recovery         ← RecoveryVetoV3 (feux tricolores + veto)
├── energy?          ← EnergySnapshot (allostatic + EA + cap intensité)
├── hormonal?        ← HormonalProfile (cycle menstruel)
├── allostatic       ← AllostaticSummary (28 jours + tendance)
└── journal?         ← DailyJournal (check-in du jour)
```

---

## AthleteState — schéma racine

**Fichier** : `backend/app/models/athlete_state.py`

```python
class AthleteState(BaseModel):
    athlete_id: str
    last_synced_at: datetime
    sync_sources: list[SyncSource] = Field(default_factory=list)

    # Sections obligatoires
    profile: AthleteProfile
    metrics: AthleteMetrics
    connectors: ConnectorSnapshot
    plan: PlanSnapshot
    recovery: RecoveryVetoV3

    # Sections optionnelles
    energy: Optional[EnergySnapshot] = None
    hormonal: Optional[HormonalProfile] = None
    allostatic: AllostaticSummary = Field(default_factory=AllostaticSummary)  # jamais None
    journal: Optional[DailyJournal] = None
```

---

## Sous-modèles détaillés

### AthleteProfile

**Source** : `backend/app/schemas/athlete.py` — type alias `AthleteResponse = AthleteProfile`

```python
class AthleteProfile(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    age: int = Field(..., ge=14, le=100)
    sex: Literal["M", "F", "other"]
    weight_kg: float = Field(..., gt=0)
    height_cm: float = Field(..., gt=0)
    sports: list[Sport]
    primary_sport: Sport
    goals: list[str]
    target_race_date: date | None = None
    available_days: list[int]       # 0=Lun … 6=Dim
    hours_per_week: float = Field(..., gt=0)
    equipment: list[str] = Field(default_factory=list)
    # Marqueurs fitness (remplis progressivement)
    max_hr: int | None = None
    resting_hr: int | None = None
    ftp_watts: int | None = None       # Puissance seuil cyclisme (watts)
    vdot: float | None = None          # Capacité aérobie course (Daniels)
    css_per_100m: float | None = None  # Critical Swim Speed (sec/100m)
    # Style de vie
    sleep_hours_typical: float = Field(default=7.0)
    stress_level: int = Field(default=5, ge=1, le=10)
    job_physical: bool = False
    coaching_mode: Literal["full", "tracking_only"] = "full"
```

```python
class Sport(str, Enum):
    RUNNING  = "running"
    LIFTING  = "lifting"
    SWIMMING = "swimming"
    BIKING   = "biking"
```

---

### AthleteMetrics

```python
class AthleteMetrics(BaseModel):
    """Valeurs brutes Terra + métriques calculées pour aujourd'hui."""

    date: date

    # Données brutes Terra
    hrv_rmssd: Optional[float] = None             # ms — RMSSD du matin
    hrv_history_7d: list[float] = Field(default_factory=list)  # 7 derniers RMSSD
    sleep_hours: Optional[float] = None           # heures de sommeil la nuit précédente
    terra_sleep_score: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    resting_hr: Optional[float] = None            # bpm au lever

    # Métriques calculées
    acwr: Optional[float] = None                  # Acute:Chronic Workload Ratio (EWMA)
    acwr_status: Optional[Literal["safe", "caution", "danger"]] = None
                                                  # safe: 0.8–1.3, caution: 1.3–1.5, danger: >1.5
    readiness_score: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    fatigue_score: Optional[FatigueScore] = None  # composite 5 axes
    muscle_strain: Optional[MuscleStrainScore] = None  # 10 groupes musculaires
```

---

### MuscleStrainScore

```python
class MuscleStrainScore(BaseModel):
    """Strain index 0–100 par groupe musculaire.

    Calculé : EWMA_7d / EWMA_28d × 100, plafonné à 100.
    0 = pas de charge récente ou historique insuffisant.
    """

    quads: float = Field(default=0.0, ge=0.0, le=100.0)
    posterior_chain: float = Field(default=0.0, ge=0.0, le=100.0)
    glutes: float = Field(default=0.0, ge=0.0, le=100.0)
    calves: float = Field(default=0.0, ge=0.0, le=100.0)
    chest: float = Field(default=0.0, ge=0.0, le=100.0)
    upper_pull: float = Field(default=0.0, ge=0.0, le=100.0)
    shoulders: float = Field(default=0.0, ge=0.0, le=100.0)
    triceps: float = Field(default=0.0, ge=0.0, le=100.0)
    biceps: float = Field(default=0.0, ge=0.0, le=100.0)
    core: float = Field(default=0.0, ge=0.0, le=100.0)
    computed_at: datetime
```

---

### ConnectorSnapshot

```python
class ConnectorSnapshot(BaseModel):
    """Dernières données connues de tous les connecteurs externes."""

    strava_last_activity: Optional[StravaActivity] = None
    strava_activities_7d: list[StravaActivity] = Field(default_factory=list)
    hevy_last_workout: Optional[HevyWorkout] = None
    hevy_workouts_7d: list[HevyWorkout] = Field(default_factory=list)
```

Voir `backend/app/schemas/strava.py` pour `StravaActivity` et `HevyWorkout` (détaillés dans API-CONTRACT.md §Integrations).

---

### PlanSnapshot

```python
class PlanSnapshot(BaseModel):
    """Séances planifiées aujourd'hui et cette semaine."""

    today: list[WorkoutSlot] = Field(default_factory=list)
    week: list[WorkoutSlot] = Field(default_factory=list)
    week_number: int = 1
    phase: str = "base"    # "base" | "build" | "peak" | "taper" | "recovery"
```

`WorkoutSlot` : voir `backend/app/schemas/plan.py` (détaillé dans API-CONTRACT.md §Plans).

---

### RecoveryVetoV3

```python
class RecoveryVetoV3(BaseModel):
    """Veto élargi du Recovery Coach V3.

    Intègre HRV, ACWR, Energy Availability, charge allostatique et phase cycle.
    """

    status: TrafficLight           # feu global — "green" | "yellow" | "red"
    hrv_component: TrafficLight
    acwr_component: TrafficLight
    ea_component: TrafficLight     # Energy Availability
    allostatic_component: TrafficLight
    cycle_component: Optional[TrafficLight] = None  # None si hormonal désactivé
    final_intensity_cap: float = Field(..., ge=0.0, le=1.0)  # 0.0 = veto complet
    veto_triggered: bool
    veto_reasons: list[str] = Field(default_factory=list)
```

**Règle critique** : quand `veto_triggered=True`, aucun agent ne peut proposer une séance d'intensité > `final_intensity_cap`. Cette règle est non-overridable.

---

### EnergySnapshot

```python
class EnergySnapshot(BaseModel):
    """Snapshot produit par l'Energy Coach après chaque check-in."""

    timestamp: datetime
    allostatic_score: float = Field(..., ge=0.0, le=100.0)
    cognitive_load: float = Field(..., ge=0.0, le=100.0)
    energy_availability: float    # kcal/kg FFM — pas de borne absolue
    cycle_phase: Optional[CyclePhase] = None
    sleep_quality: float = Field(..., ge=0.0, le=100.0)
    recommended_intensity_cap: float = Field(..., ge=0.0, le=1.0)
    veto_triggered: bool
    veto_reason: Optional[str] = None
```

---

### HormonalProfile

```python
class HormonalProfile(BaseModel):
    """Profil du cycle hormonal féminin dans AthleteState."""

    enabled: bool
    cycle_length_days: int = Field(default=28, ge=21, le=45)
    current_cycle_day: Optional[int] = Field(default=None, ge=1, le=45)
    current_phase: Optional[CyclePhase] = None
                   # "menstrual" | "follicular" | "ovulation" | "luteal"
    last_period_start: Optional[date] = None
    tracking_source: TrackingSource = "manual"
                     # "manual" | "apple_health"
    notes: Optional[str] = None
```

---

### AllostaticSummary

```python
class AllostaticSummary(BaseModel):
    """Historique allostatic 28 jours + tendance calculée."""

    history_28d: list[AllostaticEntry] = Field(default_factory=list)
    trend: AllostaticTrend = "stable"
           # "improving" | "stable" | "declining"
    avg_score_7d: float = Field(default=0.0, ge=0.0, le=100.0)
```

---

### AllostaticEntry + AllostaticComponents

```python
class AllostaticEntry(BaseModel):
    """Un enregistrement quotidien dans l'historique allostatic."""

    date: date
    allostatic_score: float = Field(..., ge=0.0, le=100.0)
    components: AllostaticComponents
    intensity_cap_applied: float = Field(..., ge=0.0, le=1.0)

class AllostaticComponents(BaseModel):
    """Six sous-scores contribuant au score allostatic quotidien (chacun 0–100)."""

    hrv: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    sleep: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    work: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    stress: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    cycle: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    ea: Optional[float] = Field(default=None, ge=0.0, le=100.0)  # Energy Availability
```

---

### DailyJournal + EnergyCheckIn

```python
class DailyJournal(BaseModel):
    """Journal quotidien : check-in structuré + commentaire libre."""

    date: date
    check_in: Optional[EnergyCheckIn] = None
    comment: Optional[str] = Field(default=None, max_length=2000)
    mood_score: Optional[int] = Field(default=None, ge=1, le=10)

class EnergyCheckIn(BaseModel):
    """Données brutes du check-in quotidien."""

    work_intensity: Literal["light", "normal", "heavy", "exhausting"]
    stress_level: Literal["none", "mild", "significant"]
    cycle_phase: Optional[CyclePhase] = None
```

---

### SyncSource

```python
SyncSourceName = Literal["strava", "hevy", "terra", "manual"]
SyncStatus = Literal["ok", "error", "stale"]

class SyncSource(BaseModel):
    name: SyncSourceName
    last_synced_at: datetime
    status: SyncStatus
```

---

## AgentView — matrice d'accès

`AgentView` est la **vue filtrée** fournie à chaque agent — seules les sections autorisées sont peuplées, les autres sont `None`.

```python
class AgentView(BaseModel):
    model_config = ConfigDict(extra="forbid")  # interdit l'accès aux sections non autorisées

    agent: str
    profile: Optional[AthleteProfile] = None
    metrics: Optional[AthleteMetrics] = None
    connectors: Optional[ConnectorSnapshot] = None
    plan: Optional[PlanSnapshot] = None
    energy: Optional[EnergySnapshot] = None
    recovery: Optional[RecoveryVetoV3] = None
    hormonal: Optional[HormonalProfile] = None
    allostatic: Optional[AllostaticSummary] = None
    journal: Optional[DailyJournal] = None
```

### Matrice `_AGENT_VIEWS`

| Section | head_coach | running | lifting | swimming | biking | nutrition | recovery | energy |
|---------|:----------:|:-------:|:-------:|:--------:|:------:|:---------:|:--------:|:------:|
| `profile` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `metrics` | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | ✅ |
| `connectors` | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | — |
| `plan` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| `energy` | ✅ | — | — | — | — | ✅ | ✅ | ✅ |
| `recovery` | ✅ | — | — | — | — | — | ✅ | ✅ |
| `hormonal` | ✅ | ✅ | ✅ | — | — | ✅ | ✅ | ✅ |
| `allostatic` | ✅ | — | — | — | — | — | ✅ | ✅ |
| `journal` | ✅ | — | — | — | — | — | ✅ | ✅ |

**Légende** : ✅ = peuplé · — = `None`

---

## get_agent_view() — usage

```python
# backend/app/models/athlete_state.py

_AGENT_VIEWS: dict[str, set[str]] = {
    "head_coach": {"profile", "metrics", "connectors", "plan", "energy", "recovery", "hormonal", "allostatic", "journal"},
    "running":    {"profile", "metrics", "connectors", "plan", "hormonal"},
    "lifting":    {"profile", "metrics", "connectors", "plan", "hormonal"},
    "swimming":   {"profile", "metrics", "connectors", "plan"},
    "biking":     {"profile", "metrics", "connectors", "plan"},
    "nutrition":  {"profile", "plan", "energy", "hormonal"},
    "recovery":   {"profile", "metrics", "connectors", "plan", "energy", "recovery", "hormonal", "allostatic", "journal"},
    "energy":     {"profile", "metrics", "energy", "recovery", "hormonal", "allostatic", "journal"},
}

def get_agent_view(state: AthleteState, agent: str) -> AgentView:
    """Retourne la vue filtrée pour l'agent donné.
    - Agent connu → sections peuplées selon _AGENT_VIEWS
    - Agent inconnu → AgentView avec toutes les sections None
    """
    allowed = _AGENT_VIEWS.get(agent, set())
    return AgentView(
        agent=agent,
        **{k: getattr(state, k) for k in allowed},
    )
```

**Usage dans CoachingService** :
```python
view = get_agent_view(state, "running")
assert view.connectors is not None  # autorisé
assert view.allostatic is None       # non autorisé → None
```

---

## Règles de mise à jour

| Section | Mis à jour par | Déclencheur | Fréquence |
|---------|----------------|-------------|-----------|
| `profile` | API REST (`PUT /athletes/{id}`, `POST /athletes/onboarding`) | Action utilisateur | À la demande |
| `metrics.hrv_rmssd`, `metrics.sleep_hours`, `metrics.resting_hr` | Job Terra (`terra_sync_job`) | Sync horaire automatique ou `POST /connectors/terra/sync` | 6h en bg, manuel |
| `metrics.acwr`, `metrics.acwr_status` | `compute_jobs.py` (`compute_acwr_job`) | Après chaque sync activité | Post-sync |
| `metrics.fatigue_score` | `HeadCoach.build_week()` | Génération/révision du plan | À chaque plan |
| `metrics.muscle_strain` | `compute_jobs.py` + `compute_muscle_strain()` | Post-sync Hevy ou Strava | Post-sync |
| `connectors.strava_*` | Job Strava (`strava_sync_job`) | Sync auto 1h ou `POST /integrations/strava/sync` | 1h en bg, manuel |
| `connectors.hevy_*` | Job Hevy (`hevy_sync_job`) | Sync auto 6h ou `POST /connectors/hevy/sync` | 6h en bg, manuel |
| `plan` | `CoachingService` via `workflow.py` (`/workflow/create-plan` → approve) | Approbation du plan | À chaque plan/semaine |
| `recovery` | `RecoveryCoach` | Après check-in ou sync Terra | Post check-in |
| `energy` | `EnergyCoach` | Après check-in (`POST /athletes/{id}/checkin`) | Quotidien |
| `hormonal` | API REST (`PATCH /athletes/{id}/hormonal-profile`) | Action utilisateur | À la demande |
| `allostatic` | Job cron global (`daily_snapshot_job`, 4h UTC) | Quotidien automatique | 1×/jour |
| `journal` | `POST /athletes/{id}/checkin` | Check-in quotidien | 1×/jour max |
| `sync_sources` | Chaque job sync réussi | Post-sync de chaque connecteur | À chaque sync |

---

## États typiques

### 1. Athlete frais (onboarding récent)

```python
AthleteState(
    athlete_id="3fa85f64-...",
    last_synced_at=datetime(2026, 4, 16, 9, 0),
    sync_sources=[],
    profile=AthleteProfile(
        name="Simon", age=34, sex="M",
        weight_kg=78, height_cm=180,
        sports=["running", "lifting"], primary_sport="running",
        vdot=None, ftp_watts=None,  # non encore renseigné
        coaching_mode="full",
    ),
    metrics=AthleteMetrics(
        date=date(2026, 4, 16),
        hrv_rmssd=None,        # Terra non connecté
        acwr=None,             # pas d'historique
        acwr_status=None,
        muscle_strain=None,
    ),
    connectors=ConnectorSnapshot(),  # listes vides
    plan=PlanSnapshot(
        today=[WorkoutSlot(...)],
        week=[...],
        week_number=1, phase="base",
    ),
    recovery=RecoveryVetoV3(
        status="green",
        hrv_component="green", acwr_component="green",
        ea_component="green", allostatic_component="green",
        final_intensity_cap=1.0, veto_triggered=False,
    ),
    energy=None,
    hormonal=None,
    allostatic=AllostaticSummary(),  # history_28d=[], trend="stable"
    journal=None,
)
```

**Comportement agent** : `running` reçoit `metrics.acwr=None` → utilise `profile.vdot` s'il existe, sinon propose une estimation conservatrice.

---

### 2. Athlete fatigué (surcharge)

```python
metrics=AthleteMetrics(
    date=date(2026, 4, 16),
    hrv_rmssd=38.0,           # -25% vs baseline 7j → "red"
    hrv_history_7d=[55, 50, 48, 43, 40, 39, 38],
    sleep_hours=5.5,           # sous la norme
    acwr=1.48,                 # zone "caution" (> 1.3)
    acwr_status="caution",
    readiness_score=32.0,
    muscle_strain=MuscleStrainScore(
        quads=87.0, posterior_chain=91.0,  # rouge
        calves=72.0,                        # orange
        ...
    ),
),
recovery=RecoveryVetoV3(
    status="yellow",
    hrv_component="red",
    acwr_component="yellow",
    ea_component="green",
    allostatic_component="yellow",
    final_intensity_cap=0.7,   # cap à 70% de l'intensité prévue
    veto_triggered=False,
    veto_reasons=["HRV 25% sous baseline 7j"],
),
energy=EnergySnapshot(
    allostatic_score=68.0,
    energy_availability=38.5,  # kcal/kg FFM — en dessous de 45 = zone RED-S
    recommended_intensity_cap=0.6,
    veto_triggered=False,
),
```

**Comportement agent** : `running` voit `recovery.final_intensity_cap=0.7` → réduit l'intensité de 30%, passe les intervalles en récupération active.

---

### 3. Athlete en veto (blessé / RED-S)

```python
recovery=RecoveryVetoV3(
    status="red",
    hrv_component="red",
    acwr_component="red",
    ea_component="red",
    final_intensity_cap=0.0,   # VETO COMPLET
    veto_triggered=True,
    veto_reasons=[
        "ACWR > 1.5 (danger zone)",
        "Energy Availability < 30 kcal/kg FFM (RED-S threshold)",
    ],
),
energy=EnergySnapshot(
    allostatic_score=89.0,
    energy_availability=24.0,  # < 30 → RED-S signal
    recommended_intensity_cap=0.0,
    veto_triggered=True,
    veto_reason="RED-S : EA < 30 kcal/kg FFM",
),
```

**Comportement agent** : tous les agents reçoivent `recovery.veto_triggered=True` → aucune séance d'entraînement prescrite. Le Recovery Coach produit uniquement des recommandations de repos et nutrition.

---

### 4. Athlete en phase lutéale

```python
hormonal=HormonalProfile(
    enabled=True,
    cycle_length_days=28,
    current_cycle_day=22,
    current_phase="luteal",    # jours 15–28 du cycle
    last_period_start=date(2026, 4, 1),
    tracking_source="manual",
),
recovery=RecoveryVetoV3(
    status="yellow",
    cycle_component="yellow",  # phase lutéale → risque accru de fatigue
    final_intensity_cap=0.85,
    veto_triggered=False,
),
energy=EnergySnapshot(
    cycle_phase="luteal",
    allostatic_score=55.0,
    recommended_intensity_cap=0.85,
    veto_triggered=False,
),
```

**Comportement agent** :
- `running` voit `hormonal.current_phase="luteal"` → réduit les séances de haute intensité, préfère tempo court
- `nutrition` voit `hormonal` → augmente apport en fer et glucides complexes pour la phase lutéale
- `recovery` → recommande sommeil + 30 min supplémentaires, hydratation accrue

---

## Section Strain — formule complète

**Fichier** : `backend/app/core/strain.py`

### Inputs

| Source | Données | Transformation |
|--------|---------|----------------|
| Strava (`StravaActivity`) | `duration_seconds`, `perceived_exertion` (RPE 1–10), `sport_type` | `base_au = (duration_s / 3600) × IF² × 100` où `IF = RPE / 10` |
| Hevy (`HevyWorkout`, `HevySet`) | `weight_kg`, `reps`, `rpe`, `exercise.name` | `set_load = max(weight_kg, 1.0) × reps × (rpe / 10)` |

### Distribution musculaire

Chaque session est distribuée aux groupes musculaires via des coefficients de recrutement :

```python
# Cardio (Strava) — SPORT_MUSCLE_MAP
"Run":  { "quads": 0.9, "posterior_chain": 0.7, "glutes": 0.6, "calves": 0.8, "core": 0.3, ... }
"Ride": { "quads": 0.8, "posterior_chain": 0.4, "glutes": 0.5, "calves": 0.5, "core": 0.2, ... }
"Swim": { "chest": 0.6, "upper_pull": 0.9, "shoulders": 0.8, "triceps": 0.5, "biceps": 0.6, "core": 0.5, ... }

# Force (Hevy) — EXERCISE_MUSCLE_MAP (exemples)
"Squat":    { "quads": 1.0, "glutes": 0.9, "posterior_chain": 0.5, "core": 0.3 }
"Deadlift": { "posterior_chain": 1.0, "glutes": 0.9, "quads": 0.5, "core": 0.4 }
```

### Algorithme EWMA

```python
# Constantes
_LAMBDA_7D  = 2 / (7 + 1)   # = 0.25   — fenêtre aiguë
_LAMBDA_28D = 2 / (28 + 1)  # ≈ 0.069  — fenêtre chronique

# Pour chaque groupe musculaire g, pour chaque jour j :
EWMA_7d[g][j]  = load[g][j] × λ_7  + EWMA_7d[g][j-1]  × (1 - λ_7)
EWMA_28d[g][j] = load[g][j] × λ_28 + EWMA_28d[g][j-1] × (1 - λ_28)

# Score final
if EWMA_28d[g] == 0:
    score[g] = 0.0   # historique insuffisant
else:
    score[g] = min(100.0, EWMA_7d[g] / EWMA_28d[g] × 100)
```

### Outputs

```python
MuscleStrainScore(
    quads=72.5,              # 0–100, float
    posterior_chain=85.0,    # ≥ 85 → rouge
    ...
    computed_at=datetime.utcnow(),
)
```

### Seuils d'interprétation (radar chart)

| Score | Couleur | Signification |
|-------|---------|---------------|
| 0–69 | 🟢 Vert | Charge aiguë < charge chronique — récupération en cours |
| 70–84 | 🟠 Orange | Charge aiguë approche baseline — surveiller |
| 85–100 | 🔴 Rouge | Charge aiguë = ou > baseline — risque de surcharge |

**Note** : un score de 100 n'est pas nécessairement dangereux — il signifie que la charge aiguë 7j correspond exactement à la moyenne chronique 28j (ACWR = 1.0). Le danger survient quand l'EWMA_7d **dépasse** l'EWMA_28d, ce qui pousse le ratio > 1.0 (score > 100 plafonné à 100). Croiser avec `metrics.acwr_status` pour l'interprétation complète.

### Références

- Impellizzeri et al. (2004) — session-RPE pour quantifier la charge d'entraînement
- Coggan TSS model — `base_au = hours × IF² × 100`
- ADR complet : `docs/backend/STRAIN-DEFINITION.md`
