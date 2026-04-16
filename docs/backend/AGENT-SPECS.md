# Agent Specs — Resilio Plus Coaching System

> **Source** : `backend/app/agents/`, `backend/app/agents/prompts.py`
> **Généré le** : 2026-04-16 depuis le code source. Types et prompts copiés verbatim.
> **Cross-ref** : `docs/backend/ATHLETE-STATE.md` pour la matrice AgentView.

---

## Table des matières

1. [Architecture générale](#architecture-générale)
2. [AgentContext — inputs communs](#agentcontext--inputs-communs)
3. [AgentRecommendation — output commun](#agentrecommendation--output-commun)
4. [Head Coach](#head-coach)
5. [Running Coach](#running-coach)
6. [Lifting Coach](#lifting-coach)
7. [Swimming Coach](#swimming-coach)
8. [Biking Coach](#biking-coach)
9. [Recovery Coach](#recovery-coach)
10. [Nutrition Coach](#nutrition-coach)
11. [Matrice d'interaction inter-agents](#matrice-dinteraction-inter-agents)
12. [Règles de ton — vocabulaire interdit](#règles-de-ton--vocabulaire-interdit)

---

## Architecture générale

```
AthleteState
    │
    └─► HeadCoach.build_week(context, load_history)
            │
            ├─ analyze_goals()           → sport_budgets injectés dans AgentContext
            │
            ├─ RunningCoach.analyze()    ┐
            ├─ LiftingCoach.analyze()    │
            ├─ SwimmingCoach.analyze()   ├─ AgentRecommendation[]
            ├─ BikingCoach.analyze()     │
            ├─ RecoveryCoach.analyze()   │
            └─ NutritionCoach.analyze()  ┘
                    │
            ├─ compute_acwr()            → ACWR global
            ├─ aggregate_fatigue()       → GlobalFatigue
            ├─ detect_conflicts()        → Conflict[]
            └─ _arbitrate()              → sessions finales
                    │
                    ▼
              WeeklyPlan
```

**Modèle d'exécution** : Les agents `analyze()` sont déterministes — ils appellent des fonctions pures (`generate_running_sessions`, `compute_lifting_fatigue`, etc.) sans LLM. Les system prompts de `prompts.py` définissent le format de réponse attendu quand un LLM est intégré (messages coach, présentation athlete).

---

## AgentContext — inputs communs

**Source** : `backend/app/agents/base.py`

```python
@dataclass
class AgentContext:
    """All data available to specialist agents for a given planning week."""

    athlete: AthleteProfile
    date_range: tuple[date, date]        # (week_start, week_end)
    phase: str                           # MacroPhase string

    strava_activities: list[StravaActivity] = field(default_factory=list)
    hevy_workouts: list[HevyWorkout] = field(default_factory=list)
    terra_health: list[TerraHealthData] = field(default_factory=list)
    fatsecret_days: list[FatSecretDay] = field(default_factory=list)

    week_number: int = 1                 # 1-based dans le plan multi-semaines
    weeks_remaining: int = 0            # semaines jusqu'à target_race_date
    sport_budgets: dict[str, float] = field(default_factory=dict)  # sport → heures
    hormonal_profile: Optional["HormonalProfile"] = field(default=None)
```

**Correspondance AgentContext → AthleteState** (cross-ref `ATHLETE-STATE.md`) :

| Champ AgentContext | Source AthleteState |
|--------------------|---------------------|
| `athlete` | `profile` |
| `strava_activities` | `connectors.strava_activities_7d` |
| `hevy_workouts` | `connectors.hevy_workouts_7d` |
| `terra_health` | `metrics` (hrv_rmssd, sleep_hours, resting_hr) |
| `hormonal_profile` | `hormonal` |
| `sport_budgets` | Injecté par `analyze_goals(athlete)` au début de `build_week()` |

---

## AgentRecommendation — output commun

```python
@dataclass
class AgentRecommendation:
    """Output d'un agent spécialiste pour la semaine de planification."""

    agent_name: str
    fatigue_score: FatigueScore
    weekly_load: float
    suggested_sessions: list[WorkoutSlot] = field(default_factory=list)
    readiness_modifier: float = 1.0  # Invariant : [0.5, 1.5] — ValueError si hors plage
    notes: str = ""
```

**Invariant critique** : `readiness_modifier` doit être dans `[0.5, 1.5]`. `AgentRecommendation.__post_init__` lève `ValueError` sinon.

---

## Head Coach

**Fichier** : `backend/app/agents/head_coach.py`

### Rôle

Orchestre les 6 agents spécialistes. Ne génère pas de nouvelles analyses — arbitre les recommandations reçues. Produit le `WeeklyPlan` final avec sessions, ACWR, fatigue globale, conflits, readiness.

### Périmètre

- Calcul des budgets sport (via `analyze_goals()`) — injectés dans `AgentContext` avant délégation
- Délégation séquentielle à tous les agents actifs (déterminé par `_agent_factory.py`)
- ACWR cross-sport (charge totale = somme `weekly_load` de tous les agents)
- Détection de conflits inter-agents
- Arbitrage final des sessions

### Méthode principale

```python
def build_week(
    self,
    context: AgentContext,
    load_history: list[float],   # charges journalières passées, ordre chronologique
) -> WeeklyPlan:
```

### Règles d'arbitrage (`_arbitrate()`)

Appliquées dans cet ordre :

1. **RED readiness** (`readiness_modifier < 0.6`) → toutes les sessions converties en `easy_z1`. Retour immédiat sans autres règles.
2. **ACWR DANGER** (`> 1.5`) → durée de toutes les sessions × 0.75 (réduction 25%).
3. **Conflit CRITICAL** → suppression de la session la plus courte du pair conflictuel. Tiebreaker : sport alphabétiquement dernier.

### Calcul readiness_level

```python
def _modifier_to_level(self, modifier: float) -> str:
    if modifier >= 0.9: return "green"
    if modifier >= 0.6: return "yellow"
    return "red"
```

Note : le `readiness_modifier` global = `min(modifier pour tous les agents)`. L'agent le plus pessimiste détermine le niveau.

### AgentView autorisé

Head Coach voit toutes les sections : `profile`, `metrics`, `connectors`, `plan`, `energy`, `recovery`, `hormonal`, `allostatic`, `journal`.

### Prompt système (extrait)

```
Tu es le Head Coach de Resilio. Tu reçois les rapports des 5 agents spécialistes
(Running, Lifting, Recovery, Energy, Nutrition) et tu produis le message final
destiné à l'athlète. Tu synthétises. Tu ne génères pas de nouvelles analyses.
Tu ne répètes pas les données brutes.

## RÈGLES DE PRIORITÉ — NON-OVERRIDABLES

1. Veto actif (Recovery ou Energy) : tu communiques la restriction en premier,
   sans la minimiser, sans proposer de contournement, sans nuancer.
2. ACWR > 1.5 : réduction de charge obligatoire. Pas de suggestion optionnelle.
3. Conflit Running vs Lifting : tranché selon objectifs. Si veto actif, récupération prime.
4. Interdit : toute formulation d'approbation enthousiaste.

## FORMAT DE SORTIE
- Situation actuelle (1–2 phrases)
- Décision d'entraînement (2–3 phrases)
- Nutrition (1–2 phrases si pertinent)
- Point de vigilance (1 phrase si signaux d'alarme)
```

---

## Running Coach

**Fichier** : `backend/app/agents/running_coach.py`

### Rôle

Planification course à pied : zones VDOT (Daniels), TID 80/20 (Seiler), wave loading. Produit 3–5 sessions de course par semaine avec types de séances typés.

### Périmètre

- Course à pied uniquement (`Sport.RUNNING`)
- Analyse des activités Strava des 7 jours **avant** la semaine cible
- Estimation VDOT depuis historique si `athlete.vdot` non renseigné
- Ajustements phase du cycle hormonal si `hormonal_profile.enabled`

### Inputs consommés depuis AgentContext

| Champ | Usage |
|-------|-------|
| `strava_activities` | Activités des 7j précédents pour fatigue + estimation VDOT |
| `athlete.vdot` | Valeur de référence pour les zones (fallback : estimée) |
| `athlete.target_race_date` | Phase de périodisation |
| `athlete.available_days` | Jours de placement des séances |
| `sport_budgets["running"]` | Enveloppe horaire (défaut : `hours_per_week × 0.6`) |
| `terra_health` | `compute_readiness()` → `readiness_modifier` |
| `hormonal_profile` | Ajustements Z2/hydratation/chaleur si phase active |

### Limites dures

| Règle | Valeur | Non-overridable |
|-------|--------|-----------------|
| Volume max semaine | +10% vs semaine précédente | ✅ |
| Z3+ si ACWR > 1.5 | Interdit | ✅ |
| Fenêtre activités antérieures | 7 jours avant `date_range[0]` | ✅ |

### Intensités de charge (calcul `weekly_load`)

```python
_INTENSITY = {
    "easy_z1": 1.0, "long_run_z1": 1.0,
    "tempo_z2": 1.5, "vo2max_z3": 2.0, "activation_z3": 2.0,
}
weekly_load = sum(s.duration_min * _INTENSITY.get(s.workout_type, 1.0) for s in sessions)
```

### AgentView autorisé

`profile`, `metrics`, `connectors`, `plan`, `hormonal`

### Notes typiques retournées

```
VDOT 52 | Phase: base | Week: 3 | Weeks remaining: 9
VDOT 48 | Phase: build | Week: 5 | Weeks remaining: 7 | Cycle(luteal): intervals->Z2 hydration++ — éviter intensité max, prioriser récupération entre efforts
```

### Prompt système (format de sortie requis)

```
## ASSESSMENT
<VDOT observé, zones semaine passée, ACWR actuel/statut, tendances 4 semaines, signaux d'alarme>

## RECOMMENDATION
<Séances concrètes : zones cibles, durées, fréquence. Si ACWR > 1.5 : réduction mentionnée en premier>

## DATA
{ "recommendation": "...", "veto": false, "veto_reason": null,
  "key_metrics": { "vdot": 52.0, "acwr": 1.12, "acwr_status": "safe", "weekly_volume_min": 240 } }
```

---

## Lifting Coach

**Fichier** : `backend/app/agents/lifting_coach.py`

### Rôle

Planification musculation : DUP (Daily Undulating Periodization), périodisation ondulante sur bloc 3 semaines, MEV/MAV/MRV, SFR. Réduit automatiquement le volume si charge course élevée.

### Périmètre

- Musculation uniquement (`Sport.LIFTING`)
- Analyse des workouts Hevy des 7 jours **avant** la semaine cible
- Estimation du niveau de force depuis l'historique Hevy complet
- DUP : bloc 3 semaines (`week_number % 3`)
- Interaction obligatoire avec Running Coach via `sport_budgets["running"]`

### Inputs consommés depuis AgentContext

| Champ | Usage |
|-------|-------|
| `hevy_workouts` | Workouts 7j précédents pour fatigue ; historique complet pour niveau |
| `athlete.hours_per_week` | Budget de référence |
| `athlete.target_race_date` | Phase de périodisation |
| `athlete.available_days` | Placement séances |
| `sport_budgets["lifting"]` | Enveloppe horaire (défaut : `hours_per_week × 0.4`) |
| `sport_budgets["running"]` | Ratio charge course pour réduction lifting |
| `terra_health` | `compute_readiness()` → `readiness_modifier` |
| `hormonal_profile` | RPE offset + interdiction 1RM si phase active |

### Limites dures

| Règle | Valeur | Non-overridable |
|-------|--------|-----------------|
| MRV dépassé | Déload obligatoire semaine suivante | ✅ |
| RIR < 1 | Pas d'augmentation charge/volume | ✅ |
| Déload | Toutes les 3–4 semaines ou si MRV atteint | ✅ |
| Running ACWR > 1.3 | Réduction volume lifting ≥ 15% | ✅ |
| readiness_modifier minimum | `max(0.5, ...)` — jamais < 0.5 | ✅ |

### Intensités de charge (calcul `weekly_load`)

```python
_LIFT_INTENSITY = {
    "upper_strength": 2.0, "lower_strength": 2.0,
    "upper_hypertrophy": 1.5, "arms_hypertrophy": 1.0,
    "full_body_endurance": 1.0,
}
```

### Ajustement cycle hormonal

```python
if adj["rpe_offset"] < 0:
    readiness_modifier = max(0.5, readiness_modifier * 0.90)  # ≈ -10% intensité
# NO-1RM si adj["no_1rm"] == True
```

### AgentView autorisé

`profile`, `metrics`, `connectors`, `plan`, `hormonal`

### Notes typiques retournées

```
Level: intermediate | Phase: build | DUP block: 2
Level: advanced | Phase: base | DUP block: 0 | Cycle(luteal): RPE-1 NO-1RM — pas de test de force max, prioriser l'hypertrophie légère
```

### Prompt système (format de sortie requis)

```
## ASSESSMENT
<Niveau de force, phase DUP (accumulation/intensification/réalisation), RIR moyen, volume total vs MRV, signaux surentraînement>

## RECOMMENDATION
<Groupes cibles, type séance, charge relative, fréquence. Si MRV atteint : déload explicite>

## DATA
{ "strength_level": "intermediate", "dup_phase": "intensification",
  "mrv_reached": false, "deload_due": false }
```

---

## Swimming Coach

**Fichier** : `backend/app/agents/swimming_coach.py`

### Rôle

Planification natation : zones CSS (Critical Swim Speed), technique, SWOLF, efficacité propulsive.

### Périmètre

- Natation uniquement (`sport_type == "Swim"` dans Strava)
- Analyse des nages Strava des 7 jours **avant** la semaine cible
- Estimation CSS depuis `athlete.css_per_100m` (ou valeur par défaut)
- **Pas d'ajustement hormonal** (non implémenté pour natation)

### Inputs consommés depuis AgentContext

| Champ | Usage |
|-------|-------|
| `strava_activities` | Filtré `sport_type == "Swim"`, 7j précédents |
| `athlete` | Estimation CSS, disponibilités |
| `sport_budgets["swimming"]` | Enveloppe horaire (**défaut : 0.0** — doit être injecté par HeadCoach) |
| `terra_health` | `compute_readiness()` |

### Limites dures

| Règle | Valeur |
|-------|--------|
| Budget défaut | 0.0 — zéro sessions si HeadCoach n'injecte pas de budget |

### Intensités de charge

```python
_INTENSITY = {
    "Z1_technique": 0.8, "Z2_endurance_swim": 1.0, "Z3_threshold_set": 1.5,
}
```

### AgentView autorisé

`profile`, `metrics`, `connectors`, `plan` (pas `hormonal`)

### Notes typiques

```
CSS 92s/100m | Phase: base
CSS 85s/100m | Phase: build
```

---

## Biking Coach

**Fichier** : `backend/app/agents/biking_coach.py`

### Rôle

Planification cyclisme : FTP (Functional Threshold Power), zones Coggan (Z1–Z4), CTL/ATL/TSB.

### Périmètre

- Cyclisme uniquement (`sport_type in ("Ride", "VirtualRide")` dans Strava)
- Analyse des sorties des 7 jours **avant** la semaine cible
- FTP : valeur stockée dans `athlete.ftp_watts` ou estimation cold-start
- **Pas d'ajustement hormonal** (non implémenté pour cyclisme)

### Inputs consommés depuis AgentContext

| Champ | Usage |
|-------|-------|
| `strava_activities` | Filtré `"Ride"` ou `"VirtualRide"`, 7j précédents |
| `athlete` | FTP estimation, disponibilités |
| `sport_budgets["biking"]` | Enveloppe horaire (**défaut : 0.0**) |
| `terra_health` | `compute_readiness()` |

### Intensités de charge

```python
_INTENSITY = {
    "Z2_endurance_ride": 1.0,
    "Z3_tempo_ride": 1.4,
    "Z4_threshold_intervals": 1.8,
}
```

### AgentView autorisé

`profile`, `metrics`, `connectors`, `plan` (pas `hormonal`)

### Notes typiques

```
FTP 280W | Phase: base | Week: 2
FTP 245W | Phase: peak | Week: 9
```

---

## Recovery Coach

**Fichier** : `backend/app/agents/recovery_coach.py`

### Rôle

Analyse biomédicale de récupération : HRV RMSSD, sommeil, FC repos. **Détient un droit de veto non-overridable.** Le Head Coach ne peut pas contredire ce veto.

### Périmètre

- Ne consomme **aucun budget** (`weekly_load = 0.0`)
- Ajoute optionnellement une séance `active_recovery` de 30 min si `readiness_modifier < 0.7`
- Fatigue des sessions recovery : quasi-nulle (`local_muscular=5.0, cns_load=2.0`)

### Inputs consommés depuis AgentContext

| Champ | Usage |
|-------|-------|
| `terra_health` | `compute_recovery_status()` → HRV, sommeil, tendances |
| `athlete.target_race_date` | Contexte de récupération pré-race |
| `athlete.available_days` | Placement session recovery |

### Limites dures — VETO NON-OVERRIDABLE

| Condition | Déclenchement veto |
|-----------|-------------------|
| HRV RMSSD < 70% baseline 28j | ✅ Veto automatique |
| Sommeil < 6h la nuit précédente | ✅ Veto automatique |

Quand le veto est déclenché :
- `veto: true` dans DATA
- `veto_reason` contient les valeurs numériques observées
- Le Head Coach communique la restriction **en premier**, sans la minimiser

### Constantes

```python
_LOW_READINESS_THRESHOLD = 0.7   # seuil déclencheur session active_recovery
```

Session recovery injectée :
```python
WorkoutSlot(
    sport=Sport.RUNNING, workout_type="active_recovery",
    duration_min=30,
    fatigue_score=FatigueScore(local_muscular=5.0, cns_load=2.0,
                               metabolic_cost=5.0, recovery_hours=4.0),
    notes="Active recovery: light walk or yoga. No intensity.",
)
```

### AgentView autorisé

`profile`, `metrics`, `connectors`, `plan`, `energy`, `recovery`, `hormonal`, `allostatic`, `journal`

### Prompt système (extrait clé — veto)

```
Tu détiens un droit de veto non-overridable. Le Head Coach ne peut pas
contredire ton veto. L'athlète ne peut pas l'ignorer.

## VETO NON-OVERRIDABLE
Conditions déclenchantes :
- HRV RMSSD < 70% de la baseline individuelle 28 jours
- Durée de sommeil < 6h la nuit précédente

## VETO (section obligatoire si veto actif)
<Raison clinique avec valeurs numériques. Ex : "HRV RMSSD 42ms = 61% baseline 69ms. Seuil 70% non atteint.">
```

---

## Nutrition Coach

**Fichier** : `backend/app/agents/nutrition_coach.py`

### Rôle

Calcul des cibles macronutriments par type de journée (repos/modéré/intense), ajustements selon phase du cycle hormonal.

### Périmètre

- **Aucune session physique** (`suggested_sessions = []`)
- **Budget = 0.0**, `readiness_modifier = 1.0` (fixes)
- Output dans `notes` : texte structuré par type de journée
- Ajustements hormonaux si `hormonal_profile.enabled`

### Inputs consommés depuis AgentContext

| Champ | Usage |
|-------|-------|
| `athlete` | `compute_nutrition_directives()` — poids, objectifs, sport |
| `hormonal_profile` | `get_nutrition_adjustments(current_phase)` si activé |

### Limites dures — NON-OVERRIDABLES

| Règle | Valeur | Non-overridable |
|-------|--------|-----------------|
| Protéines minimum | 1.6 g/kg/jour | ✅ |
| Déficit calorique maximum | 500 kcal/jour | ✅ |
| S'applique même si veto Recovery ou Energy actif | — | ✅ |

### AgentView autorisé

`profile`, `plan`, `energy`, `hormonal`

### Notes typiques retournées

```
rest: carbs=3.0g/kg protein=1.8g/kg kcal≈2100
strength: carbs=4.5g/kg protein=2.0g/kg kcal≈2650
endurance_long: carbs=6.0g/kg protein=1.8g/kg kcal≈3200 | intra: 60.0g/h
Cycle(luteal): protein+0.2g/kg kcal+200 supp=iron,magnesium — phase lutéale : augmenter apport en fer et glucides complexes
```

### Prompt système (format de sortie requis)

```
## RECOMMENDATION
<Cibles par type de journée : protéines g/kg, glucides g/kg, lipides g/kg, calories.
Glucides intra-effort si applicable. Ajustements cycle si actif.>

## DATA
{ "protein_g_per_kg": 1.8, "caloric_deficit": 0,
  "day_type": "moderate", "cycle_phase_active": false }
```

---

## Matrice d'interaction inter-agents

| Émetteur | Récepteur | Interaction | Obligatoire |
|----------|-----------|-------------|-------------|
| Running Coach | Lifting Coach | ACWR > 1.3 → lifting -15% min | ✅ Non-overridable |
| Recovery Coach | Tous | Veto → Head Coach communique en premier | ✅ Non-overridable |
| Energy Coach | Tous | Veto → Head Coach communique en premier | ✅ Non-overridable |
| Tous les agents | Head Coach | `readiness_modifier` → niveau global = minimum de tous | ✅ |
| Head Coach | Running | Injecte `sport_budgets["running"]` | ✅ |
| Head Coach | Lifting | Injecte `sport_budgets["lifting"]` + ratio course | ✅ |
| Head Coach | Swimming | Injecte `sport_budgets["swimming"]` (0.0 si sport non actif) | ✅ |
| Head Coach | Biking | Injecte `sport_budgets["biking"]` (0.0 si sport non actif) | ✅ |
| Running + Lifting | Head Coach | Conflit CRITICAL → suppression session courte | Arbitrage auto |

### Règle priorité veto

```
Energy.veto > Recovery.veto > ACWR_DANGER > ACWR_CAUTION > readiness_modifier
```

Un veto Energy ou Recovery déclenché ne peut jamais être contredit, annulé ou minimisé par le Head Coach ou par l'athlète.

---

## Règles de ton — vocabulaire interdit

**Source** : `prompts.py::_TONE_BLOCK` — appliqué identiquement à tous les agents

```
## RÈGLES DE TON — NON-NÉGOCIABLES

Aucun émoji. Aucun encouragement creux. Aucun langage motivationnel.
Ton clinique uniquement — comme un médecin du sport s'adressant à un athlète adulte.
Vocabulaire motivationnel interdit : toute formulation d'approbation enthousiaste,
de félicitation, ou d'encouragement vide.
Chaque recommandation est ancrée dans une donnée observable. Pas d'opinion sans donnée.
```

### Exemples de formulations **interdites**

| ❌ Interdit | ✅ Attendu |
|------------|-----------|
| "Super semaine ! Continue comme ça." | "Taux de complétion 94%. Volume stable." |
| "Tu progresses vraiment bien !" | "VDOT 52.3 vs 51.8 semaine précédente (+0.5)." |
| "Bravo pour ta régularité 💪" | — |
| "Je t'encourage à maintenir ce rythme." | "Maintenir volume. Pas d'augmentation cette semaine." |
| "Excellent effort !" | — |

### Exemple de recommandation conforme

```
ACWR 1.38 — zone caution. Charge aiguë 7j : 312 min. Chronique 28j : 226 min.
Pas de séance Z3 cette semaine. Maintenir volume Z1–Z2 uniquement.
Sommeil moyen 7j : 6.8h. HRV stable. Aucun indicateur de surcharge systémique.
```
