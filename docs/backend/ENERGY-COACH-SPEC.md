# Energy Coach — Spécification technique

> Sources :  
> - `backend/app/core/energy_availability.py`  
> - `backend/app/core/allostatic.py`  
> - `backend/app/core/energy_patterns.py`  
> - `backend/app/models/schemas.py` (tables V3)  
> - `data/ea_thresholds.json` (seuils EA)  
> - `data/allostatic_weights.json` (poids composantes)

---

## 1. Vue d'ensemble

L'"Energy Coach" n'est pas un `BaseAgent` subclass. Il se décompose en trois couches :

1. **Energy Availability (EA)** — formule clinique de disponibilité énergétique
2. **Allostatic Load Score** — score composite de charge allostatique (6 composantes)
3. **Energy Pattern Detection** — détection proactive de 4 patterns sur 7 jours glissants

---

## 2. Energy Availability

### 2.1 Formule

```python
def calculate_energy_availability(
    caloric_intake: float,
    exercise_energy: float,
    ffm_kg: float,
) -> float:
```

```
EA = (caloric_intake − exercise_energy) / ffm_kg
```

- `caloric_intake` : apport calorique total du jour (kcal)
- `exercise_energy` : énergie dépensée à l'entraînement — EAT (kcal)
- `ffm_kg` : Fat-Free Mass, masse maigre (kg) — `> 0` obligatoire, lève `ValueError` sinon
- Résultat : kcal/kg FFM, peut être négatif si apport < EAT

### 2.2 Seuils cliniques

Chargés depuis `data/ea_thresholds.json` au démarrage du module :

```python
_OPTIMAL_MIN: float  # 45 — identique M/F
_CRITICAL_F:  float  # 30 — femme
_CRITICAL_M:  float  # 25 — homme
_REDS_DAYS:   int    # 3  — jours consécutifs sous seuil critique → RED-S
```

```python
def get_ea_status(ea_value: float, sex: str = "F") -> EaStatus:
    if ea_value >= _OPTIMAL_MIN:     return "optimal"
    if ea_value < critical_threshold: return "critical"
    return "suboptimal"
```

| Statut      | Condition (femme)        | Condition (homme)        |
|-------------|--------------------------|--------------------------|
| `optimal`   | EA ≥ 45                  | EA ≥ 45                  |
| `suboptimal`| 30 ≤ EA < 45             | 25 ≤ EA < 45             |
| `critical`  | EA < 30                  | EA < 25                  |

### 2.3 Détection RED-S

```python
def detect_reds_risk(ea_history: list[float], sex: str = "F") -> bool:
```

- Évalue les valeurs en ordre inverse (les plus récentes en dernier)
- Retourne `True` si EA < seuil critique pendant `_REDS_DAYS` (3) jours **consécutifs**
- Retourne `False` si `len(ea_history) < _REDS_DAYS`

---

## 3. Score de charge allostatique

### 3.1 Composantes et calcul

```python
def calculate_allostatic_score(
    hrv_deviation: float,    # % déviation vs baseline — négatif = dégradation
    sleep_quality: float,    # 0–100, 100 = parfait
    work_intensity: str,     # "light"|"normal"|"heavy"|"exhausting"
    stress_level: str,       # "none"|"mild"|"significant"
    cycle_phase: Optional[str],  # "menstrual"|"follicular"|"ovulation"|"luteal"|None
    ea_status: str,          # "optimal"|"suboptimal"|"critical"
) -> float:  # 0.0–100.0
```

Calcul des scores individuels avant pondération :

```python
hrv_score   = min(100.0, max(0.0, -hrv_deviation * 2.0))  # -15% → score 30
sleep_score = 100.0 - sleep_quality                         # inverse qualité
work_score  = float(_WORK_SCORES[work_intensity])           # lookup JSON
stress_score = float(_STRESS_SCORES[stress_level])          # lookup JSON
cycle_score = float(_CYCLE_SCORES.get(cycle_key, _CYCLE_SCORES["null"]))
ea_score    = float(_EA_SCORES[ea_status])                  # lookup JSON
```

Score final = `min(100.0, max(0.0, Σ(_WEIGHTS[k] × scores[k])))`.

Les poids `_WEIGHTS`, `_WORK_SCORES`, `_STRESS_SCORES`, `_CYCLE_SCORES`, `_EA_SCORES` sont chargés depuis `data/allostatic_weights.json`.

### 3.2 Cap d'intensité

```python
def intensity_cap_from_score(allostatic_score: float) -> float:
    if allostatic_score <= 60.0: return 1.0
    if allostatic_score <= 80.0: return 0.85
    return 0.70
```

| Score allostatique | Cap d'intensité |
|--------------------|-----------------|
| 0–60               | 1.00 (plan normal) |
| 61–80              | 0.85 (−15%)     |
| 81–100             | 0.70 (séance légère seulement) |

---

## 4. Détection des patterns énergétiques

### 4.1 Quatre patterns

Fonctions pures — opèrent sur la liste des `EnergySnapshotModel` d'un athlète.

```python
def detect_heavy_legs(snapshots: list) -> bool:
    # legs_feeling in ("heavy", "dead") sur >= 3 des 7 derniers jours
    recent = _last_7_days(snapshots)
    count = sum(1 for s in recent if s.legs_feeling in ("heavy", "dead"))
    return count >= 3

def detect_chronic_stress(snapshots: list) -> bool:
    # stress_level == "significant" sur >= 4 des 7 derniers jours
    recent = _last_7_days(snapshots)
    count = sum(1 for s in recent if s.stress_level == "significant")
    return count >= 4

def detect_persistent_divergence(snapshots: list) -> bool:
    # |objective_score - subjective_score| > 30 pendant >= 3 jours CONSÉCUTIFS
    recent = sorted(_last_7_days(snapshots), key=lambda s: s.timestamp, reverse=True)
    consecutive = 0
    for snap in recent:
        obj = float(snap.objective_score) if snap.objective_score is not None else 50.0
        subj = float(snap.subjective_score) if snap.subjective_score is not None else 50.0
        if abs(obj - subj) > 30.0:
            consecutive += 1
            if consecutive >= 3: return True
        else:
            consecutive = 0
    return False

def detect_reds_signal(snapshots: list) -> bool:
    # energy_availability < 30.0 sur >= 3 des 7 derniers jours
    recent = _last_7_days(snapshots)
    count = sum(1 for s in recent if float(s.energy_availability) < 30.0)
    return count >= 3
```

### 4.2 Messages proactifs

```python
_PATTERN_MESSAGES: dict[str, str] = {
    "heavy_legs": (
        "Tes jambes sont lourdes depuis 3 jours ou plus. "
        "Ton Head Coach recommande une seance de recuperation active ou un jour de repos complet."
    ),
    "chronic_stress": (
        "Ton niveau de stress est eleve depuis 4 jours ou plus. "
        "Ton Head Coach recommande de reduire l'intensite et de prioriser le sommeil."
    ),
    "persistent_divergence": (
        "Tes donnees objectives et subjectives divergent fortement depuis 3 jours consecutifs. "
        "Ton ressenti compte — ton Head Coach ajuste l'intensite a la baisse."
    ),
    "reds_signal": (
        "Ta disponibilite energetique est basse depuis 3 jours ou plus. "
        "Ton Head Coach recommande d'augmenter les apports caloriques et de reduire le volume."
    ),
}
```

### 4.3 Déduplication (anti-spam 7 jours)

```python
def _has_recent_message(athlete_id: str, pattern_type: str, db: Session) -> bool:
```

Un message `HeadCoachMessageModel` de même `pattern_type` créé dans les 7 derniers jours bloque la création d'un nouveau.

### 4.4 Scanner global

```python
def detect_energy_patterns(db: Session) -> dict:
    # Scanne TOUS les athlètes
    # Returns: {"athletes_scanned": N, "messages_created": M}
```

Appelé par le job cron `energy-patterns` (lundi 6h UTC) via `backend/app/jobs/scheduler.py`.

---

## 5. Modèles de base de données (V3)

### 5.1 `EnergySnapshotModel` — table `energy_snapshots`

```python
class EnergySnapshotModel(Base):
    __tablename__ = "energy_snapshots"
    id                       = Column(String, primary_key=True)
    athlete_id               = Column(String, ForeignKey("athletes.id"), nullable=False)
    timestamp                = Column(DateTime(timezone=True), nullable=False)
    allostatic_score         = Column(Float, nullable=False)
    cognitive_load           = Column(Float, nullable=False)
    energy_availability      = Column(Float, nullable=False)
    cycle_phase              = Column(String, nullable=True)
    sleep_quality            = Column(Float, nullable=False)
    recommended_intensity_cap= Column(Float, nullable=False)
    veto_triggered           = Column(Boolean, nullable=False, default=False)
    veto_reason              = Column(Text, nullable=True)
    objective_score          = Column(Float, nullable=True)
    subjective_score         = Column(Float, nullable=True)
    legs_feeling             = Column(String, nullable=True)  # "fresh"|"normal"|"heavy"|"dead"
    stress_level             = Column(String, nullable=True)  # "none"|"mild"|"significant"
    created_at               = Column(DateTime(timezone=True), nullable=False, ...)
```

### 5.2 `HormonalProfileModel` — table `hormonal_profiles` (1:1 par athlète)

```python
class HormonalProfileModel(Base):
    __tablename__ = "hormonal_profiles"
    id                  = Column(String, primary_key=True)
    athlete_id          = Column(String, ForeignKey("athletes.id"), nullable=False, unique=True)
    enabled             = Column(Boolean, nullable=False, default=False)
    cycle_length_days   = Column(Integer, nullable=False, default=28)
    current_cycle_day   = Column(Integer, nullable=True)
    current_phase       = Column(String, nullable=True)
    last_period_start   = Column(Date, nullable=True)
    tracking_source     = Column(String, nullable=False, default="manual")
    notes               = Column(Text, nullable=True)
```

### 5.3 `AllostaticEntryModel` — table `allostatic_entries`

```python
class AllostaticEntryModel(Base):
    __tablename__ = "allostatic_entries"
    id                    = Column(String, primary_key=True)
    athlete_id            = Column(String, ForeignKey("athletes.id"), nullable=False)
    entry_date            = Column(Date, nullable=False)
    allostatic_score      = Column(Float, nullable=False)
    components_json       = Column(Text, nullable=False, default="{}")  # JSON dict composantes
    intensity_cap_applied = Column(Float, nullable=False, default=1.0)
    # UniqueConstraint("athlete_id", "entry_date")
```

### 5.4 `HeadCoachMessageModel` — table `head_coach_messages`

```python
class HeadCoachMessageModel(Base):
    __tablename__ = "head_coach_messages"
    id           = Column(String, primary_key=True)
    athlete_id   = Column(String, ForeignKey("athletes.id"), nullable=False)
    pattern_type = Column(String, nullable=False)
    # "heavy_legs"|"chronic_stress"|"persistent_divergence"|"reds_signal"
    message      = Column(Text, nullable=False)
    created_at   = Column(DateTime(timezone=True), nullable=False, ...)
    is_read      = Column(Boolean, nullable=False, default=False)
```

---

## 6. Flux d'intégration

```
Check-in athlète
  └─► POST /check-in (energy_snapshot) → EnergySnapshotModel
         ├── calculate_energy_availability() → EA value → get_ea_status()
         ├── calculate_allostatic_score() → allostatic_score
         └── intensity_cap_from_score() → recommended_intensity_cap

Cron lundi 6h UTC
  └─► detect_energy_patterns(db)
         ├── detect_heavy_legs()
         ├── detect_chronic_stress()
         ├── detect_persistent_divergence()
         └── detect_reds_signal()
               └── _maybe_create_message() → HeadCoachMessageModel (si non-dupliqué 7j)
```

---

## 7. Veto RED-S (Recovery Coach)

Le veto RED-S est appliqué par le Recovery Coach (non l'Energy Coach directement). Déclencheur : `detect_reds_risk()` retourne `True`. Le veto est absolu — documenté dans `docs/backend/AGENT-SPECS.md` section Recovery Coach.
