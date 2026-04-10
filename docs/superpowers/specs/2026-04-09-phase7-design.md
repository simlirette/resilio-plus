# Phase 7 — Agents manquants : Design Spec

**Date:** 2026-04-09  
**Statut:** Approuvé

---

## Objectif

Compléter le système multi-agents en ajoutant les 4 agents manquants du blueprint : BikingCoach, SwimmingCoach, NutritionCoach, RecoveryCoach. Remplacer le budget horaire hardcodé par une allocation dynamique pilotée par les objectifs de l'athlète.

---

## Décision architecturale clé — Budget piloté par les goals

### Problème avec le code actuel

RunningCoach et LiftingCoach calculent leur budget horaire avec une règle hardcodée :
- RunningCoach : 60% si sport primaire ≠ LIFTING, sinon 40%
- LiftingCoach : 40% si sport primaire ≠ LIFTING, sinon 60%

Ce modèle ne scale pas à 4 sports et ignore totalement les objectifs de l'athlète.

### Solution

Nouveau module `backend/app/core/goal_analysis.py` :

```python
def analyze_goals(athlete: AthleteProfile) -> dict[Sport, float]:
    """
    Interprète les goals textuels + target_race_date + sports
    et retourne un budget horaire par sport.
    Garantie : sum(values) == athlete.hours_per_week.
    Floor : chaque sport actif reçoit min 0.33h (20min).
    """
```

**Logique de mapping goals → weights :**

| Mots-clés dans goals | Sport boosté |
|---|---|
| "marathon", "5K", "trail", "course à pied", "running" | RUNNING ↑↑ |
| "FTP", "triathlon", "vélo", "gravel", "cyclisme", "biking" | BIKING ↑↑ |
| "force", "squat", "hypertrophie", "musculation", "lifting" | LIFTING ↑↑ |
| "triathlon", "natation", "open water", "swimming" | SWIMMING ↑ |
| "rester en forme", "général", "santé" | parts égales |

Si `target_race_date` est dans moins de 12 semaines et qu'un sport est détecté dans les goals → weight × 1.5 pour ce sport (phase de peak).

**Exemples :**
- Goals: ["préparer un marathon en juin"], sports: [running, lifting], 10h/sem → running=7h, lifting=3h
- Goals: ["améliorer FTP vélo", "maintenir force"], sports: [biking, lifting, running], 9h/sem → biking=4.5h, lifting=2.7h, running=1.8h
- Goals: ["triathlon sprint en août"], sports: [running, biking, swimming, lifting], 12h/sem → biking=4.2h, running=3.6h, swimming=3.0h, lifting=1.2h

### Intégration dans AgentContext

```python
# base.py — AgentContext reçoit un nouveau champ
sport_budgets: dict[str, float] = field(default_factory=dict)
# ex: {"running": 3.5, "lifting": 2.0, "biking": 2.5}
```

```python
# HeadCoach.build_week() — avant d'appeler les agents
budgets = analyze_goals(context.athlete)
context = dataclasses.replace(
    context,
    sport_budgets={s.value: h for s, h in budgets.items()}
)
recommendations = [a.analyze(context) for a in self.agents]
```

```python
# Chaque agent coach (pattern uniforme)
hours_budget = context.sport_budgets.get(self.name, 0.0)
```

---

## Les 4 nouveaux agents

### BikingCoach

**Fichiers :**
- `backend/app/core/biking_logic.py`
- `backend/app/agents/biking_coach.py`

**Input :** `context.strava_activities` filtrées à `sport_type in ("Ride", "VirtualRide")`

**FTP estimation :**
```python
def estimate_ftp(activities: list[StravaActivity]) -> float:
    """
    Cherche avg_watts dans les activités Ride des 60 derniers jours.
    Prend le 95e percentile de la puissance moyenne (approximation FTP).
    Retourne 200.0 (cold start) si pas de données power.
    """
```

**Data file utilisé :** `.bmad-core/data/cycling-zones.json` (zones Coggan, déjà présent)

**Sessions générées** (selon phase + hours_budget) :
- `Z2_endurance_ride` — aérobie long, 56-75% FTP
- `Z3_tempo_ride` — muscular endurance, 76-90% FTP
- `Z4_threshold_intervals` — sweetspot/FTP, 91-105% FTP, format: 3×10min

**Fatigue :**
```python
def compute_biking_fatigue(rides: list[StravaActivity]) -> FatigueScore:
    # local_muscular: proportion rides Z4+ (avg_watts > 90% FTP)
    # cns_load: 0 (vélo = faible impact CNS vs running)
    # metabolic_cost: based on total distance + elevation_gain
```

**`BikingCoach.name`** = `"biking"`

---

### SwimmingCoach

**Fichiers :**
- `backend/app/core/swimming_logic.py`
- `backend/app/agents/swimming_coach.py`

**Input :** `context.strava_activities` filtrées à `sport_type == "Swim"`

**CSS estimation :**
```python
def estimate_css(activities: list[StravaActivity]) -> float:
    """
    CSS = (dist_400m - dist_200m) / (t_400 - t_200) en m/s.
    Cherche paires d'activités Swim ~200m et ~400m dans les 90 derniers jours.
    Retourne 0.952 m/s (cold start = 1:45/100m) si pas de données.
    """
```

**Data file utilisé :** `.bmad-core/data/swimming-benchmarks.json` (zones CSS, déjà présent)

**Sessions générées** (selon phase + hours_budget) :
- `Z1_technique` — drills, échauffement, récupération active
- `Z2_endurance_swim` — aérobie, 85-95% CSS pace
- `Z3_threshold_set` — 5×200m @ CSS pace, 15s rest

**Fatigue :**
```python
def compute_swimming_fatigue(swims: list[StravaActivity]) -> FatigueScore:
    # local_muscular: shoulder/lat volume (distance * intensity factor)
    # cns_load: faible sauf séances Z4+
    # metabolic_cost: based on total distance
```

**`SwimmingCoach.name`** = `"swimming"`

---

### NutritionCoach

**Fichiers :**
- `backend/app/core/nutrition_logic.py`
- `backend/app/agents/nutrition_coach.py`
- `backend/app/routes/nutrition.py`

**Particularité :** Ne génère pas de `WorkoutSlot`. Produit des directives nutritionnelles.

**Input :**
- `context.fatsecret_days` — données actuelles de l'athlète (macros réels)
- Sessions planifiées par les autres agents (via `context` ou `AgentContext`)
- `athlete.weight_kg`, `athlete.goals`

**Logique :**
```python
def compute_nutrition_directives(
    athlete: AthleteProfile,
    planned_sessions: list[WorkoutSlot],
    fatsecret_days: list[FatSecretDay],
) -> NutritionWeek:
    """
    Pour chaque jour de la semaine :
    1. Détecter type de jour : strength_day / endurance_short / endurance_long / rest
       (basé sur les WorkoutSlots planifiés ce jour)
    2. Appliquer carbs_g_per_kg[day_type] × athlete.weight_kg
    3. Protéines fixes : 1.8g/kg, toutes les 3-4h, 20-40g/dose
    4. Intra-effort si session > 75min : 30-60g/h glucides
    5. Suppléments evidence-A si goals incluent performance
    """
```

**Data file utilisé :** `.bmad-core/data/nutrition-targets.json` (carbs/protein targets, déjà présent)

**Output dans AgentRecommendation :**
- `suggested_sessions` = [] (aucune session physique)
- `weekly_load` = 0.0
- `readiness_modifier` = 1.0 (nutrition ne modifie pas le readiness)
- `notes` = directives formatées (JSON stringifié ou texte structuré)

**Nouveau schema :** `backend/app/schemas/nutrition.py` (vérifier s'il existe déjà — si oui, étendre)

**Nouveau endpoint :**
```
GET /athletes/{id}/nutrition-directives   Bearer auth
→ NutritionWeekResponse : directives par jour (carbs_g, protein_g, intra_effort_g_per_h, supplements)
```

**`NutritionCoach.name`** = `"nutrition"`

---

### RecoveryCoach

**Fichiers :**
- `backend/app/core/recovery_logic.py`
- `backend/app/agents/recovery_coach.py`
- `backend/app/routes/recovery.py`

**Input :** `context.terra_health` (hrv_rmssd, sleep_duration_hours, sleep_score)

**Logique :** Étend `compute_readiness()` de `core/readiness.py` avec sleep banking :
```python
def compute_recovery_status(
    terra_data: list[TerraHealthData],
    target_race_date: date | None,
    week_start: date,
) -> RecoveryStatus:
    """
    readiness_modifier : délègue à compute_readiness() existant
    sleep_banking : si target_race_date dans 1-2 semaines → recommande +1.5h/nuit
    hrv_trend : "improving" | "stable" | "declining" (3-point slope sur 7 jours)
    recovery_recommendation : texte structuré
    """
```

**Output dans AgentRecommendation :**
- `suggested_sessions` : si `readiness_modifier < 0.7` → ajoute session `active_recovery` (yoga/marche, 30min) sur le jour le plus chargé de la semaine
- `weekly_load` = 0.0 (les sessions de récupération ne comptent pas comme charge)
- `readiness_modifier` = valeur calculée — HeadCoach prend le min de tous les agents

**Nouveau endpoint :**
```
GET /athletes/{id}/recovery-status   Bearer auth
→ RecoveryStatusResponse : readiness_modifier, hrv_trend, sleep_avg_h, sleep_banking_active, recommendation
```

**`RecoveryCoach.name`** = `"recovery"`

---

## Instanciation conditionnelle

Dans `onboarding.py` et `plans.py`, remplacer la création hardcodée par une factory :

```python
# backend/app/routes/_agent_factory.py (nouveau fichier utilitaire)
from ..agents.biking_coach import BikingCoach
from ..agents.lifting_coach import LiftingCoach
from ..agents.nutrition_coach import NutritionCoach
from ..agents.recovery_coach import RecoveryCoach
from ..agents.running_coach import RunningCoach
from ..agents.swimming_coach import SwimmingCoach
from ..schemas.athlete import AthleteProfile, Sport

def build_agents(athlete: AthleteProfile) -> list:
    agents = []
    if Sport.RUNNING in athlete.sports:
        agents.append(RunningCoach())
    if Sport.LIFTING in athlete.sports:
        agents.append(LiftingCoach())
    if Sport.BIKING in athlete.sports:
        agents.append(BikingCoach())
    if Sport.SWIMMING in athlete.sports:
        agents.append(SwimmingCoach())
    agents.append(NutritionCoach())   # toujours présent
    agents.append(RecoveryCoach())    # toujours présent
    return agents
```

---

## File Map complet

| Fichier | Action | Rôle |
|---------|--------|------|
| `backend/app/core/goal_analysis.py` | Créer | Goals → sport budget allocation |
| `backend/app/core/biking_logic.py` | Créer | FTP estimation, sessions vélo, fatigue |
| `backend/app/core/swimming_logic.py` | Créer | CSS estimation, sessions natation, fatigue |
| `backend/app/core/nutrition_logic.py` | Créer | Directives nutritionnelles par type de jour |
| `backend/app/core/recovery_logic.py` | Créer | RecoveryStatus, sleep banking, HRV trend |
| `backend/app/agents/biking_coach.py` | Créer | Wrapper BikingCoach : BaseAgent |
| `backend/app/agents/swimming_coach.py` | Créer | Wrapper SwimmingCoach : BaseAgent |
| `backend/app/agents/nutrition_coach.py` | Créer | Wrapper NutritionCoach : BaseAgent |
| `backend/app/agents/recovery_coach.py` | Créer | Wrapper RecoveryCoach : BaseAgent |
| `backend/app/routes/_agent_factory.py` | Créer | Factory conditionnelle build_agents() |
| `backend/app/routes/nutrition.py` | Créer | GET /athletes/{id}/nutrition-directives |
| `backend/app/routes/recovery.py` | Créer | GET /athletes/{id}/recovery-status |
| `backend/app/agents/base.py` | Modifier | Ajouter sport_budgets dans AgentContext |
| `backend/app/agents/head_coach.py` | Modifier | Appeler analyze_goals() avant les agents |
| `backend/app/agents/running_coach.py` | Modifier | Lire sport_budgets au lieu de hardcode |
| `backend/app/agents/lifting_coach.py` | Modifier | Lire sport_budgets au lieu de hardcode |
| `backend/app/routes/onboarding.py` | Modifier | Utiliser build_agents() |
| `backend/app/routes/plans.py` | Modifier | Utiliser build_agents() |
| `backend/app/main.py` | Modifier | Inclure nutrition + recovery routers |
| `tests/backend/core/test_goal_analysis.py` | Créer | Tests mapping goals → budgets |
| `tests/backend/core/test_biking_logic.py` | Créer | Tests FTP, sessions, fatigue |
| `tests/backend/core/test_swimming_logic.py` | Créer | Tests CSS, sessions, fatigue |
| `tests/backend/core/test_nutrition_logic.py` | Créer | Tests directives par type de jour |
| `tests/backend/core/test_recovery_logic.py` | Créer | Tests RecoveryStatus, sleep banking |
| `tests/backend/agents/test_biking_coach.py` | Créer | Tests intégration BikingCoach |
| `tests/backend/agents/test_swimming_coach.py` | Créer | Tests intégration SwimmingCoach |
| `tests/backend/agents/test_nutrition_coach.py` | Créer | Tests intégration NutritionCoach |
| `tests/backend/agents/test_recovery_coach.py` | Créer | Tests intégration RecoveryCoach |

---

## Ce qui n'est PAS dans le scope

- Frontend pour nutrition/recovery (Phase 11)
- Connecteurs Hevy/FatSecret/Terra complets (Phase 9)
- VBT (Velocity-Based Training) pour le Lifting Coach (future itération)
- Calcul FTP depuis fichiers .fit / power meter externe (Phase 9)
