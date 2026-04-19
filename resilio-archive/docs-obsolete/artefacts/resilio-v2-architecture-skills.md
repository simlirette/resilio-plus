# RESILIO V2 — Architecture Multi-Agents avec Skills, Constraint Solver & State Machine

> Document définitif pour Claude Code + Superpowers.
> Prérequis : V1 complétée (structure, schémas, connecteurs, agents de base, frontend).

---

## CRITIQUE DE LA V2 INITIALE — 10 FAIBLESSES CORRIGÉES

| # | Faiblesse | Correction |
|---|-----------|------------|
| 1 | Matrice de contraintes statique (posée une fois, jamais mise à jour) | **Matrice vivante** : recalculée chaque semaine par le weekly review |
| 2 | Planification uniquement au niveau de la séance | **3 niveaux** : macrocycle (mois), mésocycle (3-4 sem), microcycle (semaine) |
| 3 | Communication uniquement hub-and-spoke (tout passe par Head Coach) | **Consultations latérales** : Lifting Coach peut lire le readiness du Recovery Coach |
| 4 | Aucun mode dégradé si les API sont down | **Fallback par skill** : chaque skill a un comportement dégradé défini |
| 5 | Recovery Coach purement consultatif | **Recovery Coach = portier** avec droit de veto sur l'intensité |
| 6 | ~10 skills critiques manquantes (ACWR, deload, analytics, etc.) | **37 skills** au total (vs 20 dans la version initiale) |
| 7 | Détection de conflits trop simple (adjacent days seulement) | **3 couches** : conflit jour, conflit musculaire, conflit fatigue cumulée |
| 8 | Résolution par le circuit breaker trop brutale ("coupe le sport #2") | **Menu de résolutions** : swap jours, réduire volume, changer exercices, ajuster intensité |
| 9 | Pas d'objet "état athlète" persistant | **AthleteState** : objet JSON qui voyage entre agents et évolue chaque semaine |
| 10 | Boucle hebdomadaire pas définie | **Weekly Review** complet avec ses propres skills et mise à jour de la matrice |

---

## 1. L'OBJET CENTRAL : AthleteState

Chaque agent lit et enrichit cet objet. Il persiste en base et représente l'état vivant de l'athlète.

```json
{
  "athlete_state": {
    "athlete_id": "user_123",
    "updated_at": "2026-03-25T10:00:00Z",
    
    "profile": {
      "age": 32, "weight_kg": 78, "height_cm": 178, "sex": "M",
      "training_age_years": 5,
      "active_sports": ["lifting", "running", "swimming"],
      "priority_hierarchy": ["hypertrophy", "running_5k", "swimming_technique"],
      "injuries_history": ["shin splints 2024"],
      "equipment": ["gym_full", "pool", "outdoor"],
      "work_type": "desk"
    },
    
    "current_phase": {
      "macrocycle": "base_building",
      "mesocycle_week": 3,
      "mesocycle_length": 4,
      "next_deload": "week_4",
      "target_event": null,
      "target_event_date": null
    },
    
    "constraint_matrix": { },
    
    "fatigue": {
      "acwr": 1.05,
      "acwr_trend": "stable",
      "weekly_fatigue_score": 320,
      "fatigue_by_muscle": {
        "quadriceps": 65, "hamstrings": 50, "chest": 30,
        "back": 35, "shoulders": 25, "calves": 40
      },
      "cns_load_7day_avg": 45,
      "recovery_score_today": 72
    },
    
    "compliance": {
      "last_4_weeks_completion_rate": 0.88,
      "missed_sessions_this_week": ["swimming_tuesday"],
      "nutrition_adherence_7day": 0.75
    },
    
    "performance_trends": {
      "running_pace_trend": "improving",
      "lifting_volume_trend": "stable",
      "weight_trend": "stable",
      "vo2max_estimate": 48.5
    }
  }
}
```

**Règle** : l'AthleteState est en **lecture** pour tous les agents, en **écriture** uniquement par le Head Coach (qui agrège les updates proposés par chaque agent).

---

## 2. PLANIFICATION MULTI-NIVEAUX

La V2 initiale ne planifiait qu'au niveau session. Un vrai coach planifie à 3 niveaux :

### Macrocycle (3-6 mois)
Le Head Coach détermine les phases d'entraînement annuelles :
- **Base building** (8-12 sem) : volume élevé, intensité modérée, TID pyramidale
- **Build** (6-8 sem) : volume maintenu, intensité augmente, TID mixte
- **Peak** (3-4 sem) : volume réduit, intensité maximale, TID polarisée
- **Race/Test** (1-2 sem) : tapering, volume -40-60%, intensité maintenue
- **Transition** (2-4 sem) : récupération active

Skill responsable : `plan_macrocycle` (Head Coach)

### Mésocycle (3-4 semaines)
Chaque agent spécialiste planifie son bloc de progression avec une semaine de deload intégrée :
- Semaine 1 : charge normale (100%)
- Semaine 2 : surcharge légère (105-110%)
- Semaine 3 : surcharge (110-115%)
- Semaine 4 : deload (-30% volume, maintien intensité)

Skill responsable : `plan_*_mesocycle` (par agent)

### Microcycle (1 semaine)
La matrice de contraintes opère ici. Chaque agent remplit ses créneaux avec des séances optimisées.

Skill responsable : `generate_*_workout` (par agent)

---

## 3. ARCHITECTURE SKILLS COMPLÈTE (37 skills)

### 3.1 Skills partagés — Tous les agents (5 skills)

| Skill | Input | Output | Fallback si API down |
|-------|-------|--------|---------------------|
| `read_apple_health` | metric_type, date_range | JSON metrics | Demander saisie manuelle à l'user |
| `calculate_recovery_score` | sleep, hrv, rhr | score 0-100 + catégorie (vert/jaune/rouge) | Utiliser RPE subjectif de l'user |
| `get_athlete_state` | athlete_id | AthleteState JSON | Charger le dernier state en cache |
| `calculate_acwr` | training_log_28days | float ratio + zone (sweet/danger/under) | Estimation via RPE sessions manuelles |
| `assess_injury_risk` | acwr, fatigue_by_muscle, compliance | risk_level + flags | Appliquer règle conservative (réduire 20%) |

### 3.2 Skills endurance — Run, Swim, Bike Coaches (7 skills)

| Skill | Input | Output | Fallback |
|-------|-------|--------|----------|
| `fetch_strava_activities` | activity_type, date_range | JSON activities | Import CSV/GPX manuel |
| `analyze_time_in_zones` | hr_data, zones_config | JSON % par zone | Estimation via RPE |
| `calculate_training_stress` | duration, intensity, sport | float stress_score | Formule simplifiée durée x RPE |
| `generate_endurance_workout` | sport, target_zone, duration, constraints | JSON séance structurée | — |
| `plan_endurance_mesocycle` | sport, phase, athlete_state, budget | JSON 3-4 semaines | — |
| `evaluate_endurance_progress` | activities_history, targets | JSON tendances + recommandations | — |
| `calculate_race_readiness` | target_event, athlete_state | score 0-100 + gaps | — |

### 3.3 Skills Lifting Coach (7 skills)

| Skill | Input | Output | Fallback |
|-------|-------|--------|----------|
| `fetch_hevy_workouts` | date_range | JSON workouts | Import CSV Hevy |
| `calculate_muscle_volume` | workout_data, muscle_group | JSON vs MEV/MAV/MRV + alerte | — |
| `adjust_rir_and_load` | exercise, prev_performance, readiness | JSON prescription | Maintenir charge si données manquantes |
| `generate_lifting_workout` | muscles, equipment, duration, constraints, readiness | JSON séance | — |
| `plan_lifting_mesocycle` | phase, athlete_state, budget | JSON 3-4 semaines avec deload | — |
| `select_exercises_by_sfr` | muscles, cns_budget, equipment | JSON exercices triés par SFR | — |
| `evaluate_lifting_progress` | hevy_history, targets | JSON tendances (1RM estimés, volume) | — |

### 3.4 Skills Nutrition Coach (7 skills)

| Skill | Input | Output | Fallback |
|-------|-------|--------|----------|
| `fetch_fatsecret_diary` | date | JSON journal alimentaire | Saisie manuelle macros |
| `calculate_tdee` | weight, bf%, activity, training_plan | float kcal | Formule Mifflin-St Jeor + multiplicateur |
| `adjust_macros_for_day` | base_macros, day_type, sessions | JSON macros du jour | Template par type de jour |
| `generate_meal_plan` | macros, preferences, restrictions | JSON repas | — |
| `plan_nutrition_periodization` | training_plan, athlete_state | JSON nutrition sur le mésocycle | — |
| `calculate_hydration_needs` | weight, session_type, temperature | JSON ml/h + sodium | — |
| `evaluate_nutrition_compliance` | diary_history, targets | JSON adhérence + recommandations | — |

### 3.5 Skills Recovery Coach (5 skills)

| Skill | Input | Output | Fallback |
|-------|-------|--------|----------|
| `calculate_readiness` | hrv, sleep, rhr, prev_session_rpe | score + catégorie + veto_flag | RPE subjectif seul |
| `gate_session_intensity` | planned_session, readiness | approved/modified/blocked + raison | Règle conservative |
| `recommend_recovery_protocol` | fatigue_state, available_tools | JSON protocole (CWI, compression, etc.) | Repos passif |
| `detect_overtraining_signals` | acwr_trend, hrv_trend, compliance, mood | alert_level + indicators | — |
| `plan_sleep_strategy` | training_plan, event_date | JSON heures cibles + sleep banking | — |

### 3.6 Skills Head Coach — Orchestration (6 skills)

| Skill | Input | Output |
|-------|-------|--------|
| `build_constraint_matrix` | athlete_state, brainstorm_data | constraint_matrix JSON |
| `update_constraint_matrix` | current_matrix, weekly_review_data | updated_matrix JSON |
| `delegate_to_agent` | agent_name, task, context, constraints | agent_response JSON |
| `detect_systemic_conflict` | all_agent_plans, athlete_state | conflicts[] avec résolutions proposées |
| `merge_and_validate_plan` | agent_plans, constraint_matrix | unified_plan JSON ou conflicts |
| `generate_weekly_report` | athlete_state, actual_vs_planned, comments | report JSON |

---

## 4. COMMUNICATION INTER-AGENTS

### Hub-and-spoke + consultations latérales

La V2 initiale forçait TOUT à passer par le Head Coach. Le Lifting Coach a besoin du readiness score AVANT de prescrire des squats lourds, pas après.

```
                    ┌─────────────┐
                    │  HEAD COACH │ ◄── seul à parler au User
                    │ (orchestre) │ ◄── seul à écrire AthleteState
                    └──────┬──────┘
                           │
              Délègue ──── │ ──── Collecte
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
   ┌─────────┐      ┌──────────┐      ┌───────────┐
   │ LIFTING │ ───► │ RECOVERY │ ◄─── │  RUNNING  │
   │  COACH  │ lit  │  COACH   │ lit  │   COACH   │
   └─────────┘      └──────────┘      └───────────┘
                     readiness              │
        ┌──────────────────┼────────────────┘
        ▼                  ▼
   ┌──────────┐     ┌───────────┐
   │ SWIMMING │     │ NUTRITION │ ◄── reçoit le plan VALIDÉ
   │  COACH   │     │   COACH   │     (séquentiel, pas parallèle)
   └──────────┘     └───────────┘
```

### Règles de consultation latérale
| Agent source | Peut lire (READ) | Ne peut PAS |
|--------------|------------------|-------------|
| Lifting Coach | Recovery readiness, fatigue musculaire | Plans des autres coaches |
| Running Coach | Recovery readiness, fatigue musculaire | Plans Lifting/Swim |
| Swimming Coach | Recovery readiness | Plans des autres coaches |
| Biking Coach | Recovery readiness | Plans des autres coaches |
| Nutrition Coach | Plan d'entraînement VALIDÉ, poids, TDEE | Plans en cours de création |
| Recovery Coach | Toutes les données de fatigue et sommeil | Aucune restriction en lecture |

Le Head Coach reste le seul qui a une **vue globale** de tous les plans simultanément.

---

## 5. RECOVERY COACH = PORTIER (GATE KEEPER)

Le Recovery Coach n'est plus consultatif, il a un pouvoir de veto.

### Mécanisme du gate

```python
async def gate_session(recovery_coach, planned_session, athlete_state):
    readiness = recovery_coach.calculate_readiness(athlete_state)
    
    if readiness.score >= 75:  # VERT
        return {"decision": "approved", "session": planned_session}
    
    elif readiness.score >= 50:  # JAUNE
        modified = recovery_coach.gate_session_intensity(
            planned_session, 
            readiness,
            modification="reduce_intensity_15_percent"
        )
        return {"decision": "modified", "session": modified, "reason": readiness.flags}
    
    else:  # ROUGE — veto
        if planned_session.type in ["Z1_easy", "technique", "mobility"]:
            return {"decision": "approved", "session": planned_session}
        else:
            return {
                "decision": "blocked",
                "alternative": "rest_or_Z1_only",
                "reason": readiness.flags,
                "notify_head_coach": True
            }
```

**Quand le gate s'active** : AVANT chaque séance de la journée. Le frontend appelle le Recovery Coach pour valider que la séance prévue est appropriée selon l'état du jour.

---

## 6. DÉTECTION DE CONFLITS — 3 COUCHES

### Couche 1 : Conflit de planification (scheduling)
- Deux séances intenses le même jour sans 6h d'écart
- Plus de sessions que le max autorisé par la matrice
- Sport planifié sur un jour verrouillé

### Couche 2 : Conflit musculaire (overlap)
Table de chevauchement musculaire entre sports :
```json
{
  "running": ["quadriceps", "hamstrings", "calves", "glutes", "hip_flexors"],
  "cycling": ["quadriceps", "hamstrings", "glutes", "calves"],
  "swimming": ["lats", "shoulders", "triceps", "core"],
  "lifting_legs": ["quadriceps", "hamstrings", "glutes", "calves"],
  "lifting_push": ["chest", "shoulders", "triceps"],
  "lifting_pull": ["back", "biceps", "forearms"]
}
```
Un conflit musculaire = même groupe sollicité à haute intensité < 24h d'écart.

### Couche 3 : Conflit de fatigue cumulée (systémique)
- ACWR > 1.3 → aucune augmentation de charge cette semaine
- ACWR > 1.5 → réduction de volume obligatoire de 20%
- Fatigue musculaire d'un groupe > 80 → pas d'exercice ciblant ce groupe pendant 48h
- CNS load > 70 → pas d'exercice composé lourd (Tier 3)
- Recovery score < 50 → gate du Recovery Coach activé (veto)

### Menu de résolutions graduées
Pour chaque conflit, le Head Coach choisit par ordre de préférence :

1. **Swap de jours** : déplacer une séance à un autre créneau libre
2. **Changer le split musculaire** : transformer un Leg Day en Upper Body
3. **Réduire l'intensité** : passer de Z3/Z4 à Z2, ou de Tier 3 à Tier 1
4. **Réduire le volume** : -20-30% de séries, maintenir l'intensité
5. **Substituer des exercices** : remplacer les exercices à haut CNS par des machines
6. **Supprimer la séance** (dernier recours uniquement)

---

## 7. MATRICE DE CONTRAINTES VIVANTE

### Création initiale (onboarding)
Le Head Coach la crée après le brainstorm avec l'user. Exemple :

```json
{
  "constraint_matrix": {
    "session_budget": {
      "lifting": 4, "running": 3, "swimming": 2, "biking": 0,
      "total_max_per_week": 9
    },
    "day_locks": {
      "monday":    {"available": true,  "max_sessions": 1, "locked_sports": []},
      "tuesday":   {"available": true,  "max_sessions": 1, "locked_sports": ["swimming"]},
      "wednesday": {"available": true,  "max_sessions": 1, "locked_sports": []},
      "thursday":  {"available": true,  "max_sessions": 1, "locked_sports": []},
      "friday":    {"available": true,  "max_sessions": 1, "locked_sports": []},
      "saturday":  {"available": true,  "max_sessions": 2, "locked_sports": ["swimming"]},
      "sunday":    {"available": true,  "max_sessions": 2, "locked_sports": []}
    },
    "priority_hierarchy": ["hypertrophy", "running_endurance", "swimming_technique"],
    "hard_rules": [
      "Pas de squat lourd la veille de fractionné course",
      "Minimum 1 jour de repos complet par semaine",
      "Natation UNIQUEMENT mardi et samedi",
      "Maximum 2 entraînements par jour (samedi et dimanche seulement)"
    ],
    "fatigue_budget_weekly": {
      "total_fatigue_score_max": 450,
      "cns_load_max_per_day": 70
    }
  }
}
```

### Mise à jour hebdomadaire (weekly review)
Le skill `update_constraint_matrix` ajuste la matrice selon :

- **Compliance < 70%** → réduire total_sessions de 1 (plan trop ambitieux)
- **ACWR > 1.3** → plafonner intensité à Z2 pour la semaine (consolidation)
- **Plateau > 3 semaines** → déclencher changement de phase (mesocycle suivant)
- **Créneau manqué 2+ fois** → retirer le créneau de la matrice (réalisme)
- **Blessure signalée** → verrouiller le sport/groupe musculaire concerné

Les agents n'ont JAMAIS le droit de modifier la matrice. Seul le Head Coach le fait, et seulement lors du weekly review.

---

## 8. CIRCUIT BREAKER AMÉLIORÉ

```python
MAX_REVISIONS = 2

async def resolve_plan(head_coach, agents, constraint_matrix, athlete_state):
    for iteration in range(MAX_REVISIONS + 1):
        # 1. Chaque agent consulte Recovery Coach puis crée son plan
        agent_plans = {}
        for agent in agents:
            readiness = await recovery_coach.calculate_readiness(athlete_state)
            plan = await agent.plan_microcycle(
                constraint_matrix=constraint_matrix,
                athlete_state=athlete_state,
                readiness=readiness,
                iteration=iteration
            )
            agent_plans[agent.name] = plan
        
        # 2. Détection de conflits 3 couches
        conflicts = head_coach.detect_systemic_conflict(
            agent_plans, athlete_state,
            checks=["scheduling", "muscular_overlap", "cumulative_fatigue"]
        )
        
        if not conflicts:
            return head_coach.merge_and_validate_plan(agent_plans)
        
        if iteration < MAX_REVISIONS:
            # 3. Résolution intelligente avec directives PRÉCISES
            for conflict in conflicts:
                resolution = head_coach.select_best_resolution(
                    conflict=conflict,
                    strategies=["swap_days", "change_split", "reduce_intensity",
                                "reduce_volume", "substitute_exercises", "remove_session"],
                    priority_hierarchy=constraint_matrix["priority_hierarchy"]
                )
                await head_coach.delegate_to_agent(
                    agent_name=conflict.agent_to_revise,
                    task="revise_plan",
                    context=resolution.directive
                )
        else:
            # 4. Circuit breaker : résolution GRADUÉE (pas juste couper)
            return head_coach.force_resolve_gradual(
                agent_plans, conflicts,
                priority=constraint_matrix["priority_hierarchy"],
                # Essaie les résolutions douces avant de couper
                strategy_preference=[
                    "swap_days", "reduce_intensity", 
                    "reduce_volume", "remove_session"
                ]
            )
```

---

## 9. WORKFLOW V2 COMPLET

```
═══════════════════════════════════════════════════════════════
                    FLUX DE CRÉATION DU PLAN
═══════════════════════════════════════════════════════════════

ÉTAPE 1: Brainstorm (Head Coach <-> User)
   │  Données : physique, objectifs, sports, historique, vie quotidienne
   │  Hiérarchie de priorité des sports/objectifs
   │  Question ouverte finale
   v
ÉTAPE 2: Analyse & Profil (Head Coach)
   │  Skill: get_athlete_state (création initiale)
   │  Skill: calculate_acwr (si données historiques disponibles)
   │  Détermine: phase du macrocycle, agents à activer
   │  Questions supplémentaires si nécessaire
   v
ÉTAPE 3: Matrice de Contraintes (Head Coach)
   │  Skill: build_constraint_matrix
   │  INPUT: athlete_state + brainstorm
   │  OUTPUT: budget sessions, jours verrouillés, règles, priorités
   │  Présentation à l'user pour validation de la matrice
   v
ÉTAPE 4: Planification Méso (Head Coach -> Agents)
   │  Skill: delegate_to_agent (x N agents actifs)
   │  Chaque agent reçoit: matrice + athlete_state + phase du macrocycle
   │  Chaque agent appelle: plan_*_mesocycle (3-4 semaines)
   │  Les agents consultent le Recovery Coach (readiness) en latéral
   v
ÉTAPE 5: Planification Micro — Semaine 1 (Agents)
   │  Chaque agent remplit ses créneaux de la semaine
   │  Skills: generate_*_workout, select_exercises_by_sfr, etc.
   │  OUTPUT: plan partiel par agent (JSON)
   v
ÉTAPE 6: Audit & Résolution (Head Coach)
   │  Skill: detect_systemic_conflict (3 couches)
   │  Si conflit -> résolution intelligente (menu de stratégies)
   │  Boucle max 2 révisions -> circuit breaker gradué
   │  Skill: merge_and_validate_plan
   │  OUTPUT: plan d'entraînement unifié semaine 1
   v
ÉTAPE 7: Nutrition (Nutrition Coach — SÉQUENTIEL)
   │  Reçoit le plan d'entraînement VALIDÉ
   │  Skill: plan_nutrition_periodization (sur le mésocycle)
   │  Skill: adjust_macros_for_day (jour par jour selon les séances)
   │  Skill: calculate_hydration_needs (par séance)
   │  OUTPUT: plan nutritionnel superposé au plan d'entraînement
   v
ÉTAPE 8: Validation Finale (Head Coach <-> User)
   │  Présente le plan complet (entraînement + nutrition)
   │  User approuve OU demande modifications
   │  Si modifications mineures -> Head Coach ajuste directement
   │  Si modifications majeures -> retour étape 5 avec nouvelles directives
   v
ÉTAPE 9: Déploiement (Head Coach)
   │  Skill: push_final_plan_to_db
   │  Sync vers Hevy / Strava / FatSecret
   │  Mise à jour de l'AthleteState

═══════════════════════════════════════════════════════════════
                    BOUCLE HEBDOMADAIRE (répétée)
═══════════════════════════════════════════════════════════════

ÉTAPE H1: Collecte de données (jour de suivi choisi)
   │  Skills: fetch_strava_activities, fetch_hevy_workouts, fetch_fatsecret_diary
   │  Skill: read_apple_health (HRV, sommeil, poids)
   │  Skill: calculate_acwr (mise à jour)
   │  Skill: calculate_readiness
   v
ÉTAPE H2: Analyse comparative (Head Coach + Agents)
   │  Chaque agent évalue son domaine : prévu vs réalisé
   │  Skills: evaluate_*_progress (par agent)
   │  Skill: evaluate_nutrition_compliance
   │  Skill: detect_overtraining_signals
   │  OUTPUT: rapport par agent avec recommandations
   v
ÉTAPE H3: Synthèse & Ajustements (Head Coach)
   │  Skill: generate_weekly_report
   │  Skill: update_constraint_matrix (matrice vivante)
   │  Décision: maintenir le plan OU ajuster
   │  Si fin de mésocycle -> déclencher nouveau plan_*_mesocycle
   │  Si deload semaine -> appliquer automatiquement -30% volume
   v
ÉTAPE H4: Feedback (Head Coach <-> User)
   │  Présente le rapport + les changements proposés
   │  Demande commentaires subjectifs (humeur, douleurs, motivation)
   │  User approuve les ajustements
   v
ÉTAPE H5: Planification semaine suivante
   │  Retour à étape 5 (micro) avec matrice mise à jour
   │  Recovery Coach gate chaque séance le jour même
   │
   └──── BOUCLE -> retour à H1 la semaine suivante
```

---

## 10. STRUCTURE DE FICHIERS V2

```
backend/resilio/
├── agents/
│   ├── base.py                    # Classe Agent avec skill loading
│   ├── registry.py                # Registre agents + permissions skills
│   ├── head_coach.py
│   ├── running_coach.py
│   ├── lifting_coach.py
│   ├── swimming_coach.py
│   ├── biking_coach.py
│   ├── nutrition_coach.py
│   └── recovery_coach.py
│
├── skills/
│   ├── __init__.py
│   ├── registry.py                # Registre skills + schémas Tool Use
│   ├── shared/                    # 5 skills
│   ├── endurance/                 # 7 skills
│   ├── lifting/                   # 7 skills
│   ├── nutrition/                 # 7 skills
│   ├── recovery/                  # 5 skills
│   └── orchestration/             # 6 skills
│
├── core/
│   ├── athlete_state.py           # AthleteState model + persistence
│   ├── conflict_engine.py         # Détection 3 couches + résolutions
│   ├── constraint_solver.py       # Matrice vivante + updates
│   ├── circuit_breaker.py         # Boucle résolution max retries
│   ├── fatigue.py                 # Score de fatigue unifié (V1)
│   ├── periodization.py           # Macro/méso/micro cycle logic
│   └── muscle_overlap.py          # Chevauchement musculaire entre sports
```

---

## 11. PLAN D'EXÉCUTION V2 AVEC SUPERPOWERS (7 sessions)

### Session V2-1 : AthleteState + Skill Registry
```
/superpowers:brainstorm
```
**Contexte** : "Créer le modèle AthleteState (objet central persistant qui voyage entre agents, section 1) et le Skill Registry (système qui enregistre chaque skill avec son schéma JSON Tool Use et ses permissions par agent, section 3). L'AthleteState est en lecture pour tous les agents, en écriture uniquement par le Head Coach."

### Session V2-2 : Skills partagés + Recovery Gate
```
/superpowers:brainstorm
```
**Contexte** : "Implémenter les 5 skills partagés (section 3.1) et les 5 skills Recovery (section 3.5). Le Recovery Coach devient un portier avec droit de veto vert/jaune/rouge sur chaque séance (section 5). Inclure le fallback pour chaque skill."

### Session V2-3 : Skills par agent spécialiste
```
/superpowers:brainstorm
```
**Contexte** : "Implémenter les skills endurance (7), lifting (7), et nutrition (7) des sections 3.2, 3.3, 3.4. Chaque skill est une fonction Python avec schéma JSON conforme au Tool Use Anthropic. Inclure le fallback si API externe down."

### Session V2-4 : Constraint Solver vivant + Conflict Engine
```
/superpowers:brainstorm
```
**Contexte** : "Implémenter la matrice de contraintes vivante (section 7) et le moteur de conflits 3 couches (section 6) : scheduling, muscular overlap, cumulative fatigue. Le menu de 6 résolutions graduées (swap > reduce > cut). Inclure la table de chevauchement musculaire entre sports."

### Session V2-5 : Circuit Breaker + Planification multi-niveaux
```
/superpowers:brainstorm
```
**Contexte** : "Implémenter le circuit breaker amélioré (section 8) avec résolution graduée et la planification 3 niveaux : macrocycle (phases), mésocycle (3-4 sem + deload), microcycle (semaine). Section 2."

### Session V2-6 : Orchestration Head Coach + Workflow complet
```
/superpowers:brainstorm
```
**Contexte** : "Implémenter les 6 skills d'orchestration (section 3.6), le système de consultations latérales (section 4), et câbler le workflow 9 étapes de création + boucle hebdomadaire H1-H5 (section 9)."

### Session V2-7 : Intégration Tool Use API Anthropic + Tests E2E
```
/superpowers:brainstorm
```
**Contexte** : "Connecter tous les skills au Tool Use API Anthropic. Chaque agent = invocation Claude avec tools=[ses skills autorisés]. Tester le workflow E2E complet : onboarding -> matrice -> plan -> audit -> nutrition -> validation -> weekly review."
