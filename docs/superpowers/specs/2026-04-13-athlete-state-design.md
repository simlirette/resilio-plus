# AthleteState V1 — Source de Vérité Définitive

**Date:** 2026-04-13
**Statut:** Approuvé
**Contexte:** Stabilisation de `AthleteState` comme agrégat unique avant connexion frontend.

---

## Objectif

Faire de `AthleteState` la source de vérité unique et définitive pour toutes les données d'un athlète. Le modèle est un snapshot persisté, rafraîchi à chaque sync (live), avec fallback sur le dernier snapshot connu en cas d'indisponibilité des sources.

Le frontend consomme `AthleteState` directement. Les agents reçoivent une vue filtrée typée via `get_agent_view()`.

---

## Architecture — Modèle composé (Approche 2)

`AthleteState` est un modèle racine Pydantic v2 qui agrège 9 sections indépendantes par domaine.

### Modèle racine

```python
class AthleteState(BaseModel):
    athlete_id: str
    last_synced_at: datetime
    sync_sources: list[SyncSource]

    profile: AthleteProfile
    metrics: AthleteMetrics
    connectors: ConnectorSnapshot
    plan: PlanSnapshot
    energy: Optional[EnergySnapshot] = None
    recovery: RecoveryVetoV3
    hormonal: Optional[HormonalProfile] = None
    allostatic: AllostaticSummary
    journal: Optional[DailyJournal] = None
```

---

## Sous-modèles

### `SyncSource`
```python
class SyncSource(BaseModel):
    name: Literal["strava", "hevy", "terra", "manual"]
    last_synced_at: datetime
    status: Literal["ok", "error", "stale"]
```

### `AthleteMetrics` — valeurs brutes + calculées du jour
```python
class AthleteMetrics(BaseModel):
    date: date
    hrv_rmssd: Optional[float] = None              # brut Terra (ms)
    hrv_history_7d: list[float] = Field(default_factory=list)
    sleep_hours: Optional[float] = None            # brut Terra
    sleep_quality_score: Optional[float] = None    # 0–100 Terra
    resting_hr: Optional[float] = None             # brut Terra
    acwr: Optional[float] = None                   # calculé EWMA
    acwr_status: Optional[Literal["safe", "caution", "danger"]] = None
    readiness_score: Optional[float] = None        # 0–100 calculé
    fatigue_score: Optional[FatigueScore] = None   # dernière fatigue agrégée
```

### `ConnectorSnapshot` — dernière synchro des connecteurs
```python
class ConnectorSnapshot(BaseModel):
    strava_last_activity: Optional[StravaActivity] = None
    strava_activities_7d: list[StravaActivity] = Field(default_factory=list)
    hevy_last_workout: Optional[HevyWorkout] = None
    hevy_workouts_7d: list[HevyWorkout] = Field(default_factory=list)
    terra_last_sync: Optional[datetime] = None
    strava_last_sync: Optional[datetime] = None
    hevy_last_sync: Optional[datetime] = None
```

### `PlanSnapshot` — plan du jour + semaine
```python
class PlanSnapshot(BaseModel):
    today: list[WorkoutSlot] = Field(default_factory=list)
    week: list[WorkoutSlot] = Field(default_factory=list)
    week_number: int = 1
    phase: str = "base"
```

### `AllostaticSummary` — historique + tendance
```python
class AllostaticSummary(BaseModel):
    history_28d: list[AllostaticEntry] = Field(default_factory=list)
    trend: Literal["improving", "stable", "declining"] = "stable"
    avg_score_7d: float = 0.0
```

### `DailyJournal` — check-in structuré + commentaire libre
```python
class DailyJournal(BaseModel):
    date: date
    check_in: Optional[EnergyCheckIn] = None
    comment: Optional[str] = None
    mood_score: Optional[int] = Field(None, ge=1, le=10)
```

### Modèles réutilisés (inchangés)
- `AthleteProfile` — `backend/app/schemas/athlete.py`
- `EnergySnapshot` — `backend/app/models/athlete_state.py`
- `RecoveryVetoV3` — `backend/app/models/athlete_state.py`
- `HormonalProfile` — `backend/app/models/athlete_state.py`
- `AllostaticEntry` — `backend/app/models/athlete_state.py`
- `EnergyCheckIn` — `backend/app/agents/energy_coach/agent.py`

---

## get_agent_view() — Matrice d'accès

`get_agent_view()` retourne un `AgentView` Pydantic typé avec uniquement les sections autorisées. Les sections non autorisées sont `None`.

### `AgentView`
```python
class AgentView(BaseModel):
    model_config = ConfigDict(extra="forbid")

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

### Matrice

| Section       | head_coach | running | lifting | swimming | biking | nutrition | recovery | energy |
|---------------|:----------:|:-------:|:-------:|:--------:|:------:|:---------:|:--------:|:------:|
| `profile`     | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `metrics`     | ✅ | ✅ | ✅ | ✅ | ✅ | —  | ✅ | ✅ |
| `connectors`  | ✅ | ✅ | ✅ | ✅ | ✅ | —  | ✅ | —  |
| `plan`        | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | —  |
| `energy`      | ✅ | —  | —  | —  | —  | ✅ | ✅ | ✅ |
| `recovery`    | ✅ | —  | —  | —  | —  | —  | ✅ | ✅ |
| `hormonal`    | ✅ | ✅ | ✅ | —  | —  | ✅ | ✅ | ✅ |
| `allostatic`  | ✅ | —  | —  | —  | —  | —  | ✅ | ✅ |
| `journal`     | ✅ | —  | —  | —  | —  | —  | ✅ | ✅ |

### Implémentation
```python
_AGENT_VIEWS: dict[str, set[str]] = {
    "head_coach": {"profile","metrics","connectors","plan","energy","recovery","hormonal","allostatic","journal"},
    "running":    {"profile","metrics","connectors","plan","hormonal"},
    "lifting":    {"profile","metrics","connectors","plan","hormonal"},
    "swimming":   {"profile","metrics","connectors","plan"},
    "biking":     {"profile","metrics","connectors","plan"},
    "nutrition":  {"profile","plan","energy","hormonal"},
    "recovery":   {"profile","metrics","connectors","plan","energy","recovery","hormonal","allostatic","journal"},
    "energy":     {"profile","metrics","energy","recovery","hormonal","allostatic","journal"},
}

def get_agent_view(state: AthleteState, agent: str) -> AgentView:
    allowed = _AGENT_VIEWS.get(agent, set())
    return AgentView(
        agent=agent,
        **{k: getattr(state, k) for k in allowed},
    )
```

Agent inconnu → `AgentView` avec toutes les sections à `None`.

---

## Stratégie de tests

### Fichiers
```
tests/test_models/
  test_athlete_state.py     # modèle racine + sous-modèles
  test_agent_views.py       # get_agent_view() — matrice complète
```

### `test_athlete_state.py`
- Instanciation minimale valide
- Validation des bounds sur chaque sous-modèle
- `AllostaticSummary.trend` invalide → `ValidationError`
- `DailyJournal.mood_score` hors [1–10] → `ValidationError`
- `SyncSource.status` invalide → `ValidationError`
- `AthleteMetrics.acwr_status` invalide → `ValidationError`

### `test_agent_views.py`
- Paramétrique sur les 8 agents : sections présentes ≠ None, sections absentes == None
- Agent inconnu → toutes sections None
- `extra="forbid"` : aucun champ non déclaré ne passe

### Migration
`tests/test_models/test_athlete_state_v3.py` reste intact — couvre les sous-modèles V3 existants.

---

## Fichiers impactés

| Fichier | Action |
|---|---|
| `backend/app/models/athlete_state.py` | Refactor — ajouter `AthleteState`, `AgentView`, sous-modèles, nouvelle `get_agent_view()`. Garder V3 existants. |
| `tests/test_models/test_athlete_state.py` | Créer |
| `tests/test_models/test_agent_views.py` | Créer |
| `tests/test_models/test_athlete_state_v3.py` | Conserver intact |

---

## Invariants

- `poetry install` doit passer
- `pytest tests/` doit passer (≥1847 tests existants + nouveaux)
- Aucun modèle existant (`EnergySnapshot`, `HormonalProfile`, `AllostaticEntry`, `RecoveryVetoV3`) n'est modifié
- `.backup` avant tout refactor de `athlete_state.py`
