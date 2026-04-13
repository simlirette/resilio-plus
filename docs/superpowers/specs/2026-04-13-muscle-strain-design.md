# Muscle Strain Index — Design Spec

**Date:** 2026-04-13
**Statut:** Approuvé
**Contexte:** Ajout d'un index de fatigue musculaire par groupe (10 axes) dans `AthleteMetrics`, complémentaire à `FatigueScore` (per-session). Destiné à alimenter un radar chart côté frontend et les décisions de charge des agents coaching.

---

## Objectif

Calculer un score de strain normalisé 0–100 par groupe musculaire, représentant la charge aiguë récente (EWMA 7j) relative à la baseline individuelle de l'athlète (EWMA 28j max glissant). Chaque axe du radar chart = % de la charge typique de l'athlète sur ce groupe.

---

## Architecture

### Nouveaux fichiers

| Fichier | Rôle |
|---|---|
| `backend/app/core/strain.py` | Formule, tables de recrutement, `compute_muscle_strain()` |
| `tests/test_core/test_strain.py` | Tests unitaires avec données synthétiques |
| `tests/test_models/test_muscle_strain.py` | Tests de validation Pydantic |
| `docs/backend/STRAIN-DEFINITION.md` | Document de décision architecturale |

### Fichiers modifiés

| Fichier | Modification |
|---|---|
| `backend/app/models/athlete_state.py` | Ajout `MuscleStrainScore`, champ `muscle_strain` dans `AthleteMetrics` |

---

## Modèle de données

### `MuscleStrainScore`

```python
class MuscleStrainScore(BaseModel):
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

### `AthleteMetrics` — ajout

```python
muscle_strain: Optional[MuscleStrainScore] = None
```

None si pas encore calculé (athlète sans historique suffisant).

---

## Formule

### Entrées

| Source | Champs utilisés |
|---|---|
| `HevyWorkout` | `exercises[].name`, `sets[].weight_kg`, `sets[].reps`, `sets[].rpe` |
| `StravaActivity` | `sport_type`, `duration_seconds`, `perceived_exertion` |
| `SessionLog` | `actual_duration_min`, `rpe` |

### Fallback RPE (cascade, Hevy)

1. RPE du set (`set.rpe`) si disponible
2. Sinon : moyenne des RPE disponibles du même exercice dans la session
3. Sinon : RPE 7 par défaut (hypothèse "séance standard loggée")

### Formule lifting (Hevy) — par set

```
rpe_coeff  = rpe / 10
set_load   = weight_kg × reps × rpe_coeff
```

Chaque set est distribué aux groupes musculaires via `EXERCISE_MUSCLE_MAP[exercise_name]` :
```
muscle_load[m] += set_load × EXERCISE_MUSCLE_MAP[exercise][m]
```

### Formule cardio (Strava / SessionLog) — par session

```
IF         = perceived_exertion / 10
base_au    = (duration_seconds / 3600) × IF² × 100
muscle_au[m] = base_au × SPORT_MUSCLE_MAP[sport_type][m]
```

Cohérent avec le modèle TSS-equivalent existant (`methodology.md`).

### Normalisation — score 0–100

```
ewma_7d[m]  = EWMA(daily_loads[m], λ = 2/(7+1))
ewma_28d_max[m]  = max EWMA 28j observé historiquement (baseline individuelle)

strain_score[m] = ewma_7d[m] / ewma_28d_max[m] × 100  si baseline > 0
                = 0.0                                   si baseline = 0
```

Score plafonné à 100. Si activité intense inhabituelle (dépassement baseline) → cap 100, ne monte pas au-delà.

---

## Tables de recrutement

### `SPORT_MUSCLE_MAP`

| Sport (`sport_type`) | quads | post_chain | glutes | calves | chest | upper_pull | shoulders | triceps | biceps | core |
|---|---|---|---|---|---|---|---|---|---|---|
| `Run` | 0.9 | 0.7 | 0.6 | 0.8 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.3 |
| `TrailRun` | 0.9 | 0.8 | 0.7 | 0.9 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.4 |
| `Ride` | 0.8 | 0.4 | 0.5 | 0.5 | 0.0 | 0.1 | 0.1 | 0.0 | 0.0 | 0.2 |
| `Swim` | 0.1 | 0.2 | 0.1 | 0.0 | 0.6 | 0.9 | 0.8 | 0.5 | 0.6 | 0.5 |
| `WeightTraining` | via `EXERCISE_MUSCLE_MAP` | — |
| Inconnu | 0.3 | 0.2 | 0.2 | 0.1 | 0.1 | 0.1 | 0.1 | 0.1 | 0.1 | 0.3 |

### `EXERCISE_MUSCLE_MAP` (extrait — 30 exercices Hevy courants)

| Exercice | Primaires (0.8–1.0) | Secondaires (0.3–0.5) |
|---|---|---|
| `Squat` | quads 1.0, glutes 0.9 | posterior_chain 0.5, core 0.3 |
| `Deadlift` | posterior_chain 1.0, glutes 0.9 | quads 0.5, core 0.4 |
| `Romanian Deadlift` | posterior_chain 1.0, glutes 0.8 | core 0.3 |
| `Bench Press` | chest 1.0, triceps 0.7 | shoulders 0.5 |
| `Incline Bench Press` | chest 0.9, shoulders 0.6 | triceps 0.5 |
| `Pull-up` | upper_pull 1.0, biceps 0.7 | shoulders 0.4 |
| `Lat Pulldown` | upper_pull 1.0, biceps 0.7 | shoulders 0.3 |
| `Barbell Row` | upper_pull 1.0, biceps 0.6 | posterior_chain 0.4 |
| `Overhead Press` | shoulders 1.0, triceps 0.6 | upper_pull 0.3 |
| `Leg Press` | quads 1.0, glutes 0.6 | calves 0.3 |
| `Leg Curl` | posterior_chain 1.0 | glutes 0.3 |
| `Leg Extension` | quads 1.0 | — |
| `Calf Raise` | calves 1.0 | — |
| `Dumbbell Curl` | biceps 1.0 | — |
| `Barbell Curl` | biceps 1.0 | shoulders 0.2 |
| `Tricep Pushdown` | triceps 1.0 | — |
| `Skull Crusher` | triceps 1.0 | — |
| `Dips` | chest 0.7, triceps 0.8 | shoulders 0.5 |
| `Face Pull` | shoulders 0.8, upper_pull 0.6 | biceps 0.3 |
| `Lateral Raise` | shoulders 1.0 | — |
| `Hip Thrust` | glutes 1.0, posterior_chain 0.6 | quads 0.3 |
| `Plank` | core 1.0 | shoulders 0.2 |
| `Ab Rollout` | core 1.0 | shoulders 0.3 |
| `Cable Crunch` | core 1.0 | — |
| `Lunge` | quads 0.9, glutes 0.8 | calves 0.3, core 0.3 |
| `Step-up` | quads 0.8, glutes 0.8 | calves 0.4 |
| `Good Morning` | posterior_chain 1.0 | glutes 0.5, core 0.4 |
| `Push-up` | chest 0.9, triceps 0.7 | shoulders 0.5, core 0.3 |
| `Seated Row` | upper_pull 1.0, biceps 0.5 | posterior_chain 0.3 |
| Exercice inconnu | core 0.3 (fallback conservateur) | — |

Tables stockées comme constantes Python dans `strain.py`. Extensibles sans migration DB.

---

## Propagation aux agents

Aucune modification de `get_agent_view()` ni de `_AGENT_VIEWS` requise — `metrics` est déjà accessible à tous les agents concernés.

| Agent | Utilisation de `muscle_strain` |
|---|---|
| `RecoveryCoach` | Détecte groupes > 80% → renforce recommandation repos ciblé |
| `LiftingCoach` | `posterior_chain > 80` → évite deadlifts ; `quads > 85` → réduit volume squat |
| `RunningCoach` | `quads > 85` ou `calves > 85` → module séance intense |

Les 3 agents lisent `AthleteView.metrics.muscle_strain` (Optional — gèrent None). Aucune obligation de recalculer Strain dans les agents.

---

## Seuils radar (orientation frontend)

| Score | Couleur | Interprétation |
|---|---|---|
| 0–69% | Vert | Charge normale ou sous-stimulation |
| 70–84% | Orange | Charge élevée — surveiller |
| 85–100% | Rouge | Proche du maximum — récupération recommandée |

---

## Stratégie de tests

### `tests/test_models/test_muscle_strain.py`
- Instanciation valide avec tous les champs à 0.0
- Champ > 100.0 → `ValidationError`
- Champ < 0.0 → `ValidationError`
- `computed_at` présent et est un `datetime`
- `AthleteMetrics.muscle_strain = None` par défaut

### `tests/test_core/test_strain.py` — données synthétiques

| Scénario | Assertion |
|---|---|
| Squat 5×5 @100kg RPE 8 | `quads > 0`, `glutes > 0`, `posterior_chain > 0`, `chest == 0` |
| Pull-up 3×8 RPE 7 | `upper_pull > 0`, `biceps > 0`, `quads == 0` |
| Run 60min RPE 6 | `quads > 0`, `calves > 0`, `chest == 0`, `biceps == 0` |
| Hevy sans RPE | Fallback RPE 7 appliqué, résultat non-zero |
| Exercice inconnu Hevy | `core > 0` (fallback) |
| Baseline = 0 (athlète nouveau) | Tous scores = 0.0 |
| Session identique répétée 2 semaines | Score augmente (EWMA accumule) |
| Session identique × 4 semaines stable | Score se stabilise (convergence EWMA) |

---

## Invariants

- `poetry install` doit passer
- `pytest tests/` doit passer (≥2001 tests existants + nouveaux)
- `MuscleStrainScore` tous champs bornés [0.0, 100.0]
- Aucun agent existant n'est modifié sauf ajout de lecture optionnelle de `muscle_strain`
- `.backup` avant toute modification de `athlete_state.py`
