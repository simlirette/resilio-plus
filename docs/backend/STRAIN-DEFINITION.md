# Muscle Strain Index — Définition technique

> Source unique : `backend/app/core/strain.py`  
> Modèle : `backend/app/models/athlete_state.py` → `MuscleStrainScore`

---

## 1. Vue d'ensemble

Le Muscle Strain Index est un score de fatigue par groupe musculaire (0–100) calculé à partir de l'historique des 28 derniers jours d'activités cardio (Strava) et de musculation (Hevy). Il utilise le ratio EWMA aiguë/chronique — analogue à l'ACWR mais appliqué par axe musculaire.

Référence : Impellizzeri et al. (2004) sRPE ; Coggan TSS model ; méthodologie ACWR.

---

## 2. Constantes EWMA

```python
_LAMBDA_7D  = 2 / (7 + 1)   # 0.25     — fenêtre aiguë
_LAMBDA_28D = 2 / (28 + 1)  # ≈ 0.069  — fenêtre chronique
```

Les mêmes λ que `acwr.py`. `_LAMBDA_7D` pondère fortement les jours récents ; `_LAMBDA_28D` lisse sur ~28 jours.

**Implémentation EWMA** (oldest-first, seed = premier élément) :

```python
def _ewma(loads: list[float], lam: float) -> float:
    if not loads:
        return 0.0
    result = loads[0]
    for v in loads[1:]:
        result = v * lam + result * (1 - lam)
    return result
```

---

## 3. Groupes musculaires

```python
MUSCLES: list[str] = [
    "quads",
    "posterior_chain",
    "glutes",
    "calves",
    "chest",
    "upper_pull",
    "shoulders",
    "triceps",
    "biceps",
    "core",
]
```

---

## 4. Formule de charge

### 4.1 Cardio (Strava)

```
IF = perceived_exertion / 10          (TSS-equivalent, methodology.md)
base_au = (duration_seconds / 3600) × IF² × 100
charge_muscle[m] = base_au × SPORT_MUSCLE_MAP[sport_type][m]
```

Normalisé : 1h à seuil (IF=1.0) = 100 AU — cohérent avec le modèle Coggan/TrainingPeaks.

### 4.2 Musculation (Hevy)

```
effective_weight = max(weight_kg if weight_kg is not None else 1.0, 1.0)
set_load = effective_weight × reps × (rpe / 10)
charge_muscle[m] += set_load × EXERCISE_MUSCLE_MAP[exercise.name][m]
```

`effective_weight` est planché à 1.0 pour gérer les exercices au poids de corps (weight_kg == 0).

**RPE fallback** (cascade par set) :

```python
def _rpe_fallback(sets: list[HevySet], exercise_default: float = 7.0) -> list[float]:
    available = [s.rpe for s in sets if s.rpe is not None]
    exercise_avg = sum(available) / len(available) if available else exercise_default
    return [s.rpe if s.rpe is not None else exercise_avg for s in sets]
```

Ordre : RPE du set → moyenne RPE de l'exercice → 7.0.

### 4.3 Score final

```python
acute   = _ewma(daily[m], _LAMBDA_7D)   # λ=0.25
chronic = _ewma(daily[m], _LAMBDA_28D)  # λ≈0.069

if chronic <= 0.0:
    scores[m] = 0.0
else:
    scores[m] = min(100.0, round((acute / chronic) * 100.0, 1))
```

- **0** quand `EWMA_28d == 0` (aucun historique)
- **100** plafonné (ratio > 1 → surcharge aiguë)
- Résolution : 1 décimale

---

## 5. Seuils d'affichage (radar chart)

| Plage  | Couleur |
|--------|---------|
| 0–69   | Vert    |
| 70–84  | Orange  |
| 85–100 | Rouge   |

Définis dans le frontend (non dans strain.py).

---

## 6. Maps de recrutement

### 6.1 Cardio — `SPORT_MUSCLE_MAP`

| Muscle            | Run  | TrailRun | Ride | Swim | `__unknown__` |
|-------------------|------|----------|------|------|---------------|
| quads             | 0.9  | 0.9      | 0.8  | 0.1  | 0.3           |
| posterior_chain   | 0.7  | 0.8      | 0.4  | 0.2  | 0.2           |
| glutes            | 0.6  | 0.7      | 0.5  | 0.1  | 0.2           |
| calves            | 0.8  | 0.9      | 0.5  | 0.0  | 0.1           |
| chest             | 0.0  | 0.0      | 0.0  | 0.6  | 0.1           |
| upper_pull        | 0.0  | 0.0      | 0.1  | 0.9  | 0.1           |
| shoulders         | 0.0  | 0.0      | 0.1  | 0.8  | 0.1           |
| triceps           | 0.0  | 0.0      | 0.0  | 0.5  | 0.1           |
| biceps            | 0.0  | 0.0      | 0.0  | 0.6  | 0.1           |
| core              | 0.3  | 0.4      | 0.2  | 0.5  | 0.3           |

Fallback `__unknown__` appliqué à tout `sport_type` non listé dans la map.

### 6.2 Musculation — `EXERCISE_MUSCLE_MAP` (verbatim)

```python
EXERCISE_MUSCLE_MAP: dict[str, dict[str, float]] = {
    "Squat":                {"quads": 1.0, "glutes": 0.9, "posterior_chain": 0.5, "core": 0.3},
    "Deadlift":             {"posterior_chain": 1.0, "glutes": 0.9, "quads": 0.5, "core": 0.4},
    "Romanian Deadlift":    {"posterior_chain": 1.0, "glutes": 0.8, "core": 0.3},
    "Bench Press":          {"chest": 1.0, "triceps": 0.7, "shoulders": 0.5},
    "Incline Bench Press":  {"chest": 0.9, "shoulders": 0.6, "triceps": 0.5},
    "Pull-up":              {"upper_pull": 1.0, "biceps": 0.7, "shoulders": 0.4},
    "Lat Pulldown":         {"upper_pull": 1.0, "biceps": 0.7, "shoulders": 0.3},
    "Barbell Row":          {"upper_pull": 1.0, "biceps": 0.6, "posterior_chain": 0.4},
    "Overhead Press":       {"shoulders": 1.0, "triceps": 0.6, "upper_pull": 0.3},
    "Leg Press":            {"quads": 1.0, "glutes": 0.6, "calves": 0.3},
    "Leg Curl":             {"posterior_chain": 1.0, "glutes": 0.3},
    "Leg Extension":        {"quads": 1.0},
    "Calf Raise":           {"calves": 1.0},
    "Dumbbell Curl":        {"biceps": 1.0},
    "Barbell Curl":         {"biceps": 1.0, "shoulders": 0.2},
    "Tricep Pushdown":      {"triceps": 1.0},
    "Skull Crusher":        {"triceps": 1.0},
    "Dips":                 {"chest": 0.7, "triceps": 0.8, "shoulders": 0.5},
    "Face Pull":            {"shoulders": 0.8, "upper_pull": 0.6, "biceps": 0.3},
    "Lateral Raise":        {"shoulders": 1.0},
    "Hip Thrust":           {"glutes": 1.0, "posterior_chain": 0.6, "quads": 0.3},
    "Plank":                {"core": 1.0, "shoulders": 0.2},
    "Ab Rollout":           {"core": 1.0, "shoulders": 0.3},
    "Cable Crunch":         {"core": 1.0},
    "Lunge":                {"quads": 0.9, "glutes": 0.8, "calves": 0.3, "core": 0.3},
    "Step-up":              {"quads": 0.8, "glutes": 0.8, "calves": 0.4},
    "Good Morning":         {"posterior_chain": 1.0, "glutes": 0.5, "core": 0.4},
    "Push-up":              {"chest": 0.9, "triceps": 0.7, "shoulders": 0.5, "core": 0.3},
    "Seated Row":           {"upper_pull": 1.0, "biceps": 0.5, "posterior_chain": 0.3},
    "__unknown__":          {"core": 0.3},
}
```

---

## 7. Signature de la fonction publique

```python
def compute_muscle_strain(
    strava_activities: list[StravaActivity],
    hevy_workouts: list[HevyWorkout],
    reference_date: date | None = None,
) -> MuscleStrainScore:
```

- `strava_activities` : activités filtrées sur 28j (delta calculé en interne)
- `hevy_workouts` : idem
- `reference_date` : par défaut `date.today()`
- Retourne `MuscleStrainScore(computed_at=datetime.now(tz=timezone.utc), ...)`

---

## 8. Modèle de sortie — `MuscleStrainScore`

```python
class MuscleStrainScore(BaseModel):
    quads: float
    posterior_chain: float
    glutes: float
    calves: float
    chest: float
    upper_pull: float
    shoulders: float
    triceps: float
    biceps: float
    core: float
    computed_at: datetime
```

Source : `backend/app/models/athlete_state.py`.

---

## 9. Cas limites

| Situation | Comportement |
|-----------|-------------|
| `EWMA_28d == 0` (aucun historique) | `score = 0.0` |
| Ratio > 1 (surcharge aiguë) | `min(100.0, ...)` → plafonné à 100 |
| `weight_kg == None` ou `0` (poids de corps) | `effective_weight = 1.0` |
| `reps is None` | Set ignoré (`continue`) |
| `sport_type` inconnu | Fallback `SPORT_MUSCLE_MAP["__unknown__"]` |
| `exercise.name` inconnu | Fallback `EXERCISE_MUSCLE_MAP["__unknown__"] = {"core": 0.3}` |
| Activité hors fenêtre 28j | Ignorée (`not (0 <= delta < 28)`) |

---

## 10. Bases scientifiques

- **Formule cardio** : TSS-equivalent (Coggan 1997) étendu aux groupes musculaires via coefficients de recrutement par sport. IF = RPE/10 (méthode session-RPE, Impellizzeri et al. 2004).
- **Formule musculation** : Volume load (poids × reps) pondéré par intensité relative (RPE/10). Aligné avec Zourdos et al. (2016) échelle RPE modifiée.
- **Fenêtres EWMA** : Ratio aigu 7j / chronique 28j — recommandation Gabbett (2016) pour détection de pics de charge.

---

## 11. Intégration dans `AthleteMetrics`

```python
class AthleteMetrics(BaseModel):
    # ...
    muscle_strain: Optional[MuscleStrainScore] = None
```

Peuplé par `compute_muscle_strain()` lors de la construction de l'`AthleteState` avant chaque appel coaching.
