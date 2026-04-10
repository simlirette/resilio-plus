# RESILIO HYBRID COACH — Document Maître V2 Complet

> **Ce document remplace et consolide tous les documents précédents.**
> Il contient TOUT ce dont Claude Code a besoin pour construire le projet.
> Focus : Head Coach, Running Coach, Lifting Coach (les autres agents suivront).

---

## TABLE DES MATIÈRES

1. Vision & Architecture
2. Objet Central : AthleteState
3. Analyse du Profil Athlète (style première rencontre)
4. Head Coach — Connaissances & Skills
5. Running Coach — Connaissances, Formules & Output
6. Lifting Coach — Connaissances, Formules & Output
6B. Nutrition Coach — Connaissances, Formules & Output (voir `resilio-nutrition-coach-section.md`)
7. Formats de Sortie (Hevy-compatible, Runna-compatible)
8. Constraint Solver & Circuit Breaker
9. Workflow Complet (Création + Suivi Hebdo)
10. Plan d'exécution Superpowers

---

# 1. VISION & ARCHITECTURE

## 1.1 Concept
Un Head Coach IA orchestre des agents spécialistes pour créer des plans d'entraînement PRESCRIPTIFS — pas des recommandations vagues, mais des workouts exacts :
- Course : "5km easy à 6:15/km" ou "6×800m à 4:05/km avec 90s repos jog"
- Lifting : "Incline DB Press, 3×8-10 @70kg, RPE 7, 120s repos" avec notes de forme
- Nutrition : macros quotidiennes ajustées par type de journée

## 1.2 Écosystème API
| Service | Rôle | Données extraites |
|---------|------|-------------------|
| **Strava** | Course, vélo, natation | GPS, allure, FC, cadence, élévation, puissance, laps |
| **Hevy** | Musculation | Exercices, sets, reps, weight, RPE, durée, supersets, routines |
| **USDA FoodData Central** | Aliments bruts | Macros, micros détaillés, acides aminés — API REST gratuite |
| **Open Food Facts** | Produits commerciaux | Codes-barres, 3M+ produits — API REST gratuite |
| **FCÉN (Santé Canada)** | Aliments canadiens | Marché local Québec/Canada — CSV téléchargeable |
| **Apple Health** | Santé globale | HRV (RMSSD), sommeil (durée, phases), FC repos, poids, pas |

## 1.3 Architecture Agents + Skills
Chaque agent = un cerveau expert (system prompt) + des skills (fonctions Python / Tool Use).
Les agents ne sont PAS des monolithes. Chaque skill a un input/output typé et un fallback.

```
HEAD COACH (orchestre, ne prescrit pas directement)
    │
    ├── RUNNING COACH (prescrit les séances de course exactes)
    │     Skills: fetch_strava, analyze_zones, generate_run_workout, plan_run_mesocycle...
    │
    ├── LIFTING COACH (prescrit les séances de musculation exactes)
    │     Skills: fetch_hevy, calculate_volume, generate_lift_workout, plan_lift_mesocycle...
    │
    ├── SWIMMING COACH (prescrit les séances de natation exactes)
    ├── BIKING COACH (prescrit les séances de vélo exactes)
    ├── NUTRITION COACH (prescrit les macros et repas exacts)
    └── RECOVERY COACH (portier avec droit de veto vert/jaune/rouge)
```

Communication : hub-and-spoke (tout passe par Head Coach) + consultations latérales (les agents lisent le readiness du Recovery Coach AVANT de prescrire).

## 1.4 Contraintes Techniques V1

### Orchestration — LangGraph
- LangGraph est l'orchestrateur officiel du système multi-agents dès la V1.
- Approche "lite" pour la V1 : utiliser uniquement les features core (StateGraph, nodes, edges conditionnels). Ne pas sur-ingénierer avec les features avancés (streaming distribué, persistence externe) avant que la logique métier soit validée.
- La migration vers les features avancés de LangGraph se fera en V2 une fois les agents stables.

### Frontend — FastAPI + Next.js dès le départ
- Pas de prototype intermédiaire (pas de Streamlit ou équivalent).
- Stack : backend **FastAPI** (Python, endpoints RESTful, OpenAPI/Swagger auto-généré) + frontend **Next.js** (React).
- Le backend FastAPI doit être architecturé de façon indépendante du frontend — le frontend n'est qu'un consommateur de l'API.
- Cela permet d'exposer l'API à d'autres clients (mobile, CLI, intégrations tierces) sans refactoring.

### Fallbacks d'Intégration (API fermées)
Toutes les intégrations tierces doivent avoir un fallback — les API ne sont pas garanties :

| Source | Méthode primaire | Fallback |
|--------|-----------------|---------|
| Hevy (lifting) | API (si disponible) | Import CSV export Hevy |
| Garmin / Strava (course, vélo) | API OAuth | Import fichier GPX / FIT |
| Données générales | API | Input manuel JSON structuré |

Le système doit accepter des inputs manuels JSON pour tous les types de données en l'absence d'API fonctionnelle. Les formats JSON d'input manuel sont définis par domaine dans les fichiers de données séparés (`data/`).

### Token Economy — Vues Partielles d'AthleteState
Chaque agent reçoit uniquement la sous-section d'AthleteState pertinente à son domaine (voir section 2.3). Aucun agent (sauf le Head Coach) n'a accès à l'AthleteState complet. Cela réduit les tokens consommés par appel et force une discipline stricte de séparation des responsabilités.

---

# 2. OBJET CENTRAL : AthleteState

L'AthleteState est l'objet vivant qui voyage entre agents. Il persiste en base et s'enrichit à chaque interaction. Tous les agents le lisent via leur vue filtrée (section 2.3), seul le Head Coach l'écrit.

## 2.1 Structure Complète

```json
{
  "athlete_state": {
    "athlete_id": "user_123",
    "updated_at": "2026-03-30T10:00:00Z",

    "profile": {
      "first_name": "Simon",
      "age": 32,
      "sex": "M",
      "weight_kg": 78.5,
      "height_cm": 178,
      "body_fat_percent": 16.5,
      "resting_hr": 58,
      "max_hr_measured": 188,
      "max_hr_formula": 190,

      "training_history": {
        "total_years_training": 5,
        "years_running": 2,
        "years_lifting": 4,
        "years_swimming": 0.5,
        "current_weekly_volume_hours": 7,
        "longest_run_ever_km": 15,
        "current_5k_time_min": 28.5,
        "current_10k_time_min": null,
        "current_half_marathon_min": null,
        "estimated_1rm": {
          "squat": 120,
          "bench_press": 85,
          "deadlift": 140,
          "overhead_press": 55
        }
      },

      "injuries_history": [
        {
          "type": "shin_splints",
          "year": 2024,
          "duration_weeks": 6,
          "side": "bilateral",
          "recurrent": false,
          "notes": "Augmentation trop rapide du volume de course"
        }
      ],

      "lifestyle": {
        "work_type": "desk_sedentary",
        "work_hours_per_day": 8,
        "commute_active": false,
        "sleep_avg_hours": 7.2,
        "stress_level": "moderate",
        "alcohol_per_week": 2,
        "smoking": false
      },

      "goals": {
        "primary": "run_sub_25_5k",
        "secondary": "maintain_muscle_mass",
        "tertiary": "improve_swimming_technique",
        "timeline_weeks": 16,
        "priority_hierarchy": ["running_5k", "hypertrophy_maintenance", "swimming_technique"]
      },

      "equipment": {
        "gym_access": true,
        "gym_equipment": ["barbell", "dumbbells", "cables", "machines", "pull_up_bar"],
        "pool_access": true,
        "pool_type": "25m_indoor",
        "outdoor_running": true,
        "treadmill": false,
        "heart_rate_monitor": true,
        "gps_watch": "garmin_forerunner_265",
        "power_meter_bike": false
      },

      "active_sports": ["running", "lifting"],
      "available_days": {
        "monday": {"available": true, "max_hours": 1.5, "preferred_time": "morning"},
        "tuesday": {"available": true, "max_hours": 1.5, "preferred_time": "evening"},
        "wednesday": {"available": true, "max_hours": 1.0, "preferred_time": "morning"},
        "thursday": {"available": true, "max_hours": 1.5, "preferred_time": "evening"},
        "friday": {"available": false, "max_hours": 0, "preferred_time": null},
        "saturday": {"available": true, "max_hours": 2.5, "preferred_time": "morning"},
        "sunday": {"available": true, "max_hours": 2.0, "preferred_time": "morning"}
      }
    },

    "current_phase": {
      "macrocycle": "base_building",
      "mesocycle_week": 3,
      "mesocycle_length": 4,
      "next_deload": "week_4",
      "target_event": "local_5k_race",
      "target_event_date": "2026-07-15"
    },

    "running_profile": {
      "vdot": 38.2,
      "training_paces": {
        "easy_min_per_km": "6:24",
        "easy_max_per_km": "7:06",
        "marathon_pace_per_km": "5:42",
        "threshold_pace_per_km": "5:18",
        "interval_pace_per_km": "4:48",
        "repetition_pace_per_km": "4:24",
        "long_run_pace_per_km": "6:36"
      },
      "weekly_km_current": 22,
      "weekly_km_target": 35,
      "max_long_run_km": 12,
      "cadence_avg": 168,
      "preferred_terrain": "road"
    },

    "lifting_profile": {
      "training_split": "upper_lower",
      "sessions_per_week": 3,
      "current_volume_per_muscle": {
        "quadriceps": 8,
        "hamstrings": 6,
        "chest": 10,
        "back": 12,
        "shoulders": 8,
        "biceps": 6,
        "triceps": 6,
        "calves": 4
      },
      "volume_landmarks": {
        "quadriceps": {"mev": 6, "mav": 10, "mrv_hybrid": 12},
        "hamstrings": {"mev": 4, "mav": 8, "mrv_hybrid": 10},
        "chest": {"mev": 6, "mav": 14, "mrv_hybrid": 18},
        "back": {"mev": 6, "mav": 14, "mrv_hybrid": 20},
        "shoulders": {"mev": 6, "mav": 12, "mrv_hybrid": 16},
        "biceps": {"mev": 4, "mav": 10, "mrv_hybrid": 14},
        "triceps": {"mev": 4, "mav": 8, "mrv_hybrid": 12},
        "calves": {"mev": 4, "mav": 8, "mrv_hybrid": 6}
      },
      "weekly_km_equiv": 0,
      "progression_model": "double_progression",
      "rir_target_range": [1, 3]
    },

    "swimming_profile": {
      "reference_times": {},
      "technique_level": "beginner",
      "weekly_volume_km": 0
    },

    "biking_profile": {
      "ftp_watts": null,
      "weekly_volume_km": 0
    },

    "nutrition_profile": {
      "tdee_estimated": 2800,
      "macros_target": {
        "protein_g": 160,
        "carbs_g": 300,
        "fat_g": 80
      },
      "supplements_current": ["creatine_5g"],
      "dietary_restrictions": [],
      "allergies": []
    },

    "fatigue": {
      "acwr": 1.05,
      "acwr_trend": "stable",
      "acwr_by_sport": {
        "running": 1.08,
        "lifting": 1.02,
        "biking": null,
        "swimming": null
      },
      "weekly_fatigue_score": 320,
      "fatigue_by_muscle": {
        "quadriceps": 65, "hamstrings": 50, "chest": 30,
        "back": 35, "shoulders": 25, "calves": 40
      },
      "cns_load_7day_avg": 45,
      "recovery_score_today": 72,
      "hrv_rmssd_today": 58,
      "hrv_rmssd_baseline": 62,
      "sleep_hours_last_night": 7.1,
      "sleep_quality_subjective": 7,
      "fatigue_subjective": 3
    },

    "compliance": {
      "last_4_weeks_completion_rate": 0.88,
      "missed_sessions_this_week": [],
      "nutrition_adherence_7day": 0.75
    }
  }
}
```

## 2.2 Champs de Volume Hebdo par Sport (calculés)

Ces champs sont dérivés automatiquement et exposés aux agents qui en ont besoin (notamment le Recovery Coach et le Nutrition Coach) sans avoir à leur passer l'intégralité des profils techniques :

```json
{
  "weekly_volumes": {
    "running_km": 22,
    "lifting_sessions": 3,
    "swimming_km": 0,
    "biking_km": 0,
    "total_training_hours": 6.5
  }
}
```

## 2.3 Token Economy — Vues Partielles par Agent

**Principe :** La fonction `get_agent_view(athlete_state, agent_type)` est la seule responsable de filtrer l'état avant de le passer à chaque agent. Les agents ne reçoivent jamais l'AthleteState brut directement.

```python
def get_agent_view(athlete_state: AthleteState, agent: AgentType) -> dict:
    """Filtre l'AthleteState selon les permissions de l'agent."""
    views = AGENT_VIEW_MAP[agent]
    return extract_fields(athlete_state, views)
```

**Table des vues autorisées par agent :**

| Agent | Champs reçus |
|-------|-------------|
| **Head Coach** | AthleteState complet |
| **Running Coach** | `profile.identity` + `profile.goals` + `profile.constraints` + `profile.equipment` + `profile.available_days` + `running_profile` (complet) + `fatigue.acwr_by_sport.running` + `fatigue.hrv_rmssd_today` + `fatigue.recovery_score_today` + `current_phase` |
| **Lifting Coach** | `profile.identity` + `profile.goals` + `profile.constraints` + `profile.equipment` + `profile.available_days` + `lifting_profile` (complet) + `fatigue.acwr_by_sport.lifting` + `fatigue.fatigue_by_muscle` + `fatigue.cns_load_7day_avg` + `fatigue.recovery_score_today` + `current_phase` |
| **Swimming Coach** | `profile.identity` + `profile.goals` + `profile.constraints` + `profile.equipment` + `swimming_profile` (complet) + `fatigue.hrv_rmssd_today` + `fatigue.recovery_score_today` + `current_phase` |
| **Biking Coach** | `profile.identity` + `profile.goals` + `profile.constraints` + `profile.equipment` + `biking_profile` (complet) + `fatigue.acwr_by_sport.biking` + `fatigue.hrv_rmssd_today` + `fatigue.recovery_score_today` + `current_phase` |
| **Nutrition Coach** | `profile.identity` + `profile.goals` + `profile.constraints` + `nutrition_profile` (complet) + `weekly_volumes` (tous sports) + `current_phase` |
| **Recovery Coach** | `profile.identity` + `profile.constraints` + `fatigue` (complet) + `weekly_volumes` (tous sports) + `compliance` + `current_phase` |

**Note sur le Recovery Coach :** Il reçoit les volumes hebdomadaires de tous les sports (mais pas les détails techniques de chaque discipline) pour exercer son rôle de gatekeeper sur la charge totale et calculer l'ACWR global.

---

# 3. ANALYSE DU PROFIL ATHLÈTE — Première Rencontre

## 3.1 Le Head Coach mène une évaluation approfondie en 7 blocs

Ce n'est PAS un formulaire à remplir. C'est une conversation structurée où le Head Coach pose des questions, rebondit sur les réponses, et approfondit les points critiques.

### BLOC 1 : Identité & Données Biométriques
Questions :
- Prénom, âge, sexe
- Taille, poids actuel
- Estimation du % de graisse corporelle (si connu, sinon estimation visuelle)
- Fréquence cardiaque au repos (mesurée au réveil idéalement)
- FC max connue (test d'effort ou course récente tout-out)
- Latéralité (droitier/gaucher — pertinent pour les déséquilibres)

### BLOC 2 : Historique Sportif Complet
Questions (le coach DOIT aller en profondeur) :
- Combien d'années de pratique sportive totale ?
- Sports pratiqués et à quel niveau (récréatif, compétitif, élite) ?
- Pour CHAQUE sport actif :
  - Depuis combien de temps ?
  - Fréquence actuelle (sessions/semaine) ?
  - Volume actuel (km/semaine pour la course, heures/semaine pour le lifting) ?
  - Meilleurs résultats/records personnels ?
    - Course : temps au 5k, 10k, semi, marathon ?
    - Lifting : 1RM estimé squat, bench, deadlift, OHP ? (ou charge × reps récentes)
    - Natation : temps au 100m, 400m ? SWOLF si connu ?
  - Ressenti actuel : en progression, en plateau, en régression ?
- Historique d'activité physique passée (ex: "j'ai joué au hockey jusqu'à 25 ans")
- Périodes d'inactivité significatives (>3 mois sans entraînement)

### BLOC 3 : Historique Médical & Blessures
Questions (CRITIQUE pour la prévention) :
- Blessures passées liées au sport :
  - Type (tendinopathie, fracture de stress, entorse, lombalgie, etc.)
  - Localisation précise (genou gauche, épaule droite, fascia plantaire...)
  - Année et durée de la blessure
  - Mécanisme (augmentation trop rapide de volume, chute, surentraînement)
  - Récurrente ? (oui/non, combien de fois)
  - Traitée par un professionnel ? (physio, chiro, etc.)
  - Résiduelle ? (douleur occasionnelle, faiblesse perçue)
- Chirurgies passées
- Conditions chroniques (asthme, diabète, hypertension, problèmes cardiaques)
- Médicaments actuels
- Douleurs actuelles même mineures (genoux qui craquent, épaule qui tire...)
- Évaluation posturale subjective : des déséquilibres connus ? (ex: "un physio m'a dit que j'ai une hanche plus haute")

### BLOC 4 : Style de Vie & Récupération
Questions :
- Type de travail : bureau sédentaire, debout, physique/manuel ?
- Heures de travail par jour
- Déplacement actif (marche, vélo) ou voiture ?
- Sommeil : heures moyennes par nuit, qualité subjective (1-10), réveil naturel ou alarme ?
- Utilisation d'un tracker de sommeil ? (Oura, Apple Watch, Garmin, Whoop)
- Niveau de stress général (bas, modéré, élevé, très élevé)
- Sources de stress identifiées (travail, famille, finances, etc.)
- Consommation d'alcool par semaine
- Tabac / vapotage
- Consommation de caféine (type et quantité)

### BLOC 5 : Objectifs SMART & Motivation
Questions (le coach transforme les souhaits vagues en objectifs mesurables) :
- Quel est ton objectif PRINCIPAL ? (être très spécifique)
  - Exemples acceptés : "Courir un 5k en moins de 25 minutes", "Squatter 1.5× mon poids corporel"
  - Exemples à raffiner : "Être en meilleure shape" → le coach DOIT creuser : pourquoi ? performance ? esthétique ? santé ?
- Objectif secondaire ?
- Timeline : dans combien de temps veux-tu atteindre l'objectif principal ?
- Y a-t-il un événement cible (course, compétition) ? Date ?
- Hiérarchie de priorité si les objectifs entrent en conflit (ex: force vs endurance)
- Motivation profonde : pourquoi cet objectif est important pour toi ?
- Expérience passée avec des plans d'entraînement : qu'est-ce qui a fonctionné ? échoué ? pourquoi tu as arrêté ?

### BLOC 6 : Disponibilité, Équipement & Préférences
Questions :
- Combien de jours par semaine peux-tu t'entraîner ?
- Pour chaque jour disponible :
  - Quelle plage horaire ? (matin, midi, soir)
  - Combien de temps maximum par session ?
- Jour(s) préféré(s) pour la séance longue (course) ?
- Jour(s) de repos OBLIGATOIRE ?
- Accès à un gym ? Quel équipement ? (barbell, machines, câbles, haltères, rack à squat...)
- Accès à une piscine ? Type (25m, 50m, eau libre) ?
- Terrain de course disponible : route, trail, piste d'athlétisme, tapis roulant ?
- Montre GPS / cardiofréquencemètre ? Modèle ?
- Capteur de puissance vélo ?
- Préférences d'exercices : exercices que tu ADORES / que tu DÉTESTES / que tu ne peux PAS faire (ex: "le overhead press me donne mal à l'épaule")
- Alimentation : régime particulier ? (végétarien, sans gluten, halal, etc.) Allergies/intolérances ?

### BLOC 7 : Question Ouverte
"Y a-t-il quelque chose d'autre que tu aimerais me mentionner ? Une inquiétude, une contrainte, un souhait particulier ?"

## 3.2 Calculs d'Analyse Post-Questionnaire

Après le brainstorm, le Head Coach calcule automatiquement :

### Pour la course :
```python
# VDOT estimé à partir du temps de course le plus récent
# Table de Daniels : ex. 5k en 28:30 = VDOT ~38
vdot = daniels_vdot_table[race_distance][race_time]

# Allures d'entraînement dérivées du VDOT
paces = {
    "easy":       daniels_pace(vdot, "E"),    # Ex: 6:24-7:06/km
    "marathon":   daniels_pace(vdot, "M"),    # Ex: 5:42/km
    "threshold":  daniels_pace(vdot, "T"),    # Ex: 5:18/km
    "interval":   daniels_pace(vdot, "I"),    # Ex: 4:48/km
    "repetition": daniels_pace(vdot, "R"),    # Ex: 4:24/km
}

# FC max (si non mesurée) : formule Tanaka
max_hr = 208 - (0.7 * age)

# Zones FC basées sur les seuils (modèle Seiler 3 zones)
zones_hr = {
    "Z1_below_LT1": [0.60 * max_hr, 0.77 * max_hr],
    "Z2_between_thresholds": [0.77 * max_hr, 0.90 * max_hr],
    "Z3_above_LT2": [0.90 * max_hr, 1.00 * max_hr]
}
```

### Pour le lifting :
```python
# 1RM estimé via formule Epley (si pas de test 1RM direct)
estimated_1rm = weight * (1 + reps / 30)

# Ou formule Brzycki (plus conservatrice pour reps < 10)
estimated_1rm = weight / (1.0278 - 0.0278 * reps)

# Charges de travail dérivées
working_loads = {
    "strength":    0.85 * estimated_1rm,   # 3-5 reps
    "hypertrophy": 0.70 * estimated_1rm,   # 8-12 reps
    "endurance":   0.55 * estimated_1rm,   # 15-20 reps
}

# Volume actuel vs landmarks
for muscle in athlete.muscles:
    status = classify_volume(
        current=athlete.current_volume[muscle],
        mev=landmarks[muscle].mev,
        mav=landmarks[muscle].mav,
        mrv=landmarks[muscle].mrv_hybrid
    )
    # "under_mev", "in_mev_mav", "in_mav_mrv", "over_mrv"
```

### TDEE (dépense énergétique) :
```python
# Mifflin-St Jeor (le plus précis pour population générale)
if sex == "M":
    bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) + 5
else:
    bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) - 161

# Multiplicateur d'activité (Harris-Benedict modifié)
activity_multipliers = {
    "sedentary": 1.2,          # Bureau, pas d'exercice
    "lightly_active": 1.375,   # 1-3 sessions/semaine
    "moderately_active": 1.55, # 3-5 sessions/semaine
    "very_active": 1.725,      # 6-7 sessions/semaine (athlète hybride typique)
    "extremely_active": 1.9    # 2x/jour ou travail physique + sport
}

tdee = bmr * activity_multipliers[activity_level]
```

---

# 4. HEAD COACH — Connaissances & Skills

## 4.1 Rôle
Le Head Coach NE prescrit PAS de séances. Il orchestre, arbitre, et communique avec l'utilisateur. C'est un chef d'orchestre, pas un musicien.

## 4.2 Connaissances Fondamentales

### Entraînement concurrent (interférence)
- La voie mTOR (hypertrophie) et AMPK (endurance) sont antagonistes au niveau moléculaire
- L'interférence est RÉELLE mais GÉRABLE avec une bonne périodisation
- Règles de séquençage :
  - Force AVANT endurance (préserve les gains de puissance)
  - Minimum 3h entre force et endurance dans la même journée
  - L'endurance à faible intensité (Zone 1/2) ne cause PAS d'interférence significative
  - HIIT + force le même jour = interférence MAXIMALE → à éviter absolument
  - Natation = moins d'interférence que la course (moins de dommages musculaires)
  - Chez les femmes : l'interférence sur la force des membres inférieurs est absente (méta-analyse Huiberts 2024)
  - Chez les débutants (<2 ans) : l'interférence est quasi inexistante

### ACWR (Acute:Chronic Workload Ratio)
- ACWR = charge des 7 derniers jours / moyenne des 28 derniers jours
- Sweet spot : 0.8-1.3 → risque de blessure minimal
- Danger zone : >1.5 → risque ×2-4 dans les 7 jours suivants
- Undertraining : <0.8 → déconditionnement
- Utiliser EWMA (Exponentially Weighted Moving Average) plutôt que Rolling Average
- Règle du 10% : ne jamais augmenter la charge totale de >10%/semaine
- L'ACWR doit être calculé SUR TOUS LES SPORTS COMBINÉS (charge unifiée)

### Périodisation multi-niveaux
Le Head Coach gère 3 niveaux de planification :

**Macrocycle (12-24 semaines) :**
- Phase 1 — Base Building (6-8 sem) : TID pyramidale, volume ↑, intensité modérée
- Phase 2 — Build/Specific (4-6 sem) : TID mixte→polarisée, intensité ↑, volume maintenu
- Phase 3 — Peak (2-3 sem) : TID polarisée, intensité max, volume ↓
- Phase 4 — Taper (1-2 sem) : volume -40-60%, intensité maintenue, fraîcheur maximale
- Phase 5 — Race : compétition
- Phase 6 — Transition (2-4 sem) : récupération active

**Mésocycle (3-4 semaines) :**
- Semaine 1 : 100% charge
- Semaine 2 : 105-110% charge
- Semaine 3 : 110-115% charge
- Semaine 4 : Deload — 70% du volume, 100% de l'intensité

La transition pyramidale → polarisée (PYR→POL) produit les meilleurs résultats :
+3% VO2max, +1.5% performance 5K (Casado et al.)

**Microcycle (1 semaine) :**
- Matrice de contraintes stricte (budget sessions, jours verrouillés)
- Hard day → easy day alternance
- Jamais 2 séances de haute intensité consécutives sans 48h de récupération

### Distribution de l'intensité (TID)
| Modèle | Z1 (sous LT1) | Z2 (entre seuils) | Z3 (au-dessus LT2) | Quand l'utiliser |
|--------|---------------|-------|-------|-----|
| Pyramidal | 75-80% | 10-15% | 5-10% | Phase base/préparatoire |
| Polarisé | 75-80% | 0-5% | 15-20% | Phase compétition |
| Threshold | 50-60% | 25-35% | 10-15% | Courte durée spécifique |

### Gestion des athlètes Masters (>40 ans)
- Ratio charge/récupération 2:1 au lieu de 3:1
- 2-3 jours entre les sessions haute intensité
- Déclin VO2max limitable à -5%/décennie si volume/intensité maintenus
- Priorité au travail de force pour préserver la masse musculaire et la densité osseuse

## 4.3 Skills du Head Coach (6 skills)

| Skill | Quand | Input | Output |
|-------|-------|-------|--------|
| `build_constraint_matrix` | Après le profiling | athlete_state + brainstorm | constraint_matrix JSON |
| `update_constraint_matrix` | Weekly review | current_matrix + review_data | updated_matrix |
| `delegate_to_agent` | Création de plan | agent_name, task, constraints | agent_response |
| `detect_systemic_conflict` | Après réception des plans | all_agent_plans, athlete_state | conflicts[] + résolutions |
| `merge_and_validate_plan` | Quand 0 conflit | agent_plans, matrix | unified_plan |
| `generate_weekly_report` | Weekly review | athlete_state, actual_vs_planned | report |

## 4.4 Constraint Matrix — Exemple Concret

```json
{
  "constraint_matrix": {
    "athlete_id": "user_123",
    "week_of": "2026-04-06",
    "phase": "base_building",

    "session_budget": {
      "running": 3,
      "lifting": 3,
      "swimming": 0,
      "total_max": 6
    },

    "schedule": {
      "monday":    {"available": true, "max_sessions": 1, "assigned": ["lifting_upper"]},
      "tuesday":   {"available": true, "max_sessions": 1, "assigned": ["running_easy"]},
      "wednesday": {"available": true, "max_sessions": 1, "assigned": ["lifting_lower"]},
      "thursday":  {"available": true, "max_sessions": 1, "assigned": ["running_intervals"]},
      "friday":    {"available": false},
      "saturday":  {"available": true, "max_sessions": 2, "assigned": ["lifting_upper", "running_long"]},
      "sunday":    {"available": true, "max_sessions": 1, "assigned": ["rest_or_active_recovery"]}
    },

    "priority_hierarchy": ["running_5k", "hypertrophy_maintenance"],

    "hard_rules": [
      "Pas de lifting legs <24h avant running intervals/tempo",
      "Pas de lifting legs <24h après running long",
      "Max 1 séance haute intensité course par semaine en phase base",
      "Min 1 jour repos complet par semaine",
      "Running long TOUJOURS le samedi matin"
    ],

    "acwr_limits": {
      "sweet_spot": [0.8, 1.3],
      "hard_cap": 1.5,
      "weekly_fatigue_max": 450,
      "daily_cns_max": 70
    }
  }
}
```

## 4.5 Détection de Conflits — 3 Couches

### Couche 1 : Scheduling
- Deux séances haute intensité le même jour sans 6h d'écart
- Session sur un jour indisponible
- Dépassement du budget sessions

### Couche 2 : Overlap Musculaire
```json
{
  "overlap_table": {
    "running": ["quadriceps", "hamstrings", "calves", "glutes", "hip_flexors"],
    "running_intervals": ["quadriceps", "hamstrings", "calves", "glutes", "hip_flexors", "cns_high"],
    "running_easy": ["calves_low", "hip_flexors_low"],
    "cycling": ["quadriceps", "hamstrings", "glutes", "calves"],
    "swimming": ["lats", "shoulders", "triceps", "core"],
    "lifting_legs": ["quadriceps", "hamstrings", "glutes", "calves"],
    "lifting_push": ["chest", "shoulders", "triceps"],
    "lifting_pull": ["back", "biceps", "forearms"]
  }
}
```
Conflit = même groupe sollicité à haute intensité <24h d'écart.

### Couche 3 : Fatigue Cumulée
- ACWR > 1.3 → aucune augmentation de charge cette semaine
- ACWR > 1.5 → réduction obligatoire 20%
- Fatigue musculaire d'un groupe > 80/100 → pas de travail ciblé pendant 48h
- CNS load > 70/100 → pas d'exercice Tier 3 (barbell compounds lourds)
- Recovery score < 50 → Recovery Coach veto activé

### Menu de Résolutions (par ordre de préférence)
1. **Swap de jours** : déplacer la séance à un créneau libre
2. **Changer le split** : transformer Legs Day en Upper Body
3. **Réduire l'intensité** : Z3→Z2, ou Tier 3→Tier 1
4. **Réduire le volume** : -20-30% séries, garder l'intensité
5. **Substituer exercices** : barbell squat → leg press (réduire le CNS)
6. **Supprimer la séance** : dernier recours uniquement

### Circuit Breaker
- Maximum 2 itérations de révision entre Head Coach et agents
- Si le conflit persiste → résolution d'autorité GRADUÉE selon priority_hierarchy
- Le Head Coach essaie TOUJOURS les résolutions douces avant de couper

---

# 5. RUNNING COACH — Connaissances Complètes & Output Exact

## 5.1 Rôle
Le Running Coach prescrit des séances de course EXACTES avec allure, distance, intervalles, récupération, échauffement et retour au calme. Format compatible Runna/Garmin Connect.

## 5.2 Connaissances Fondamentales

### Système de Zones (Modèle Daniels VDOT)
La base de TOUTE prescription de course. Le VDOT est calculé à partir du meilleur temps récent sur une distance de course.

**Table VDOT → Allures (extrait) :**

| VDOT | Easy (E) /km | Marathon (M) /km | Threshold (T) /km | Interval (I) /km | Repetition (R) /400m |
|------|-------------|-----------------|-------------------|------------------|---------------------|
| 30 | 7:30-8:18 | 6:51 | 6:24 | 5:51 | 2:18 |
| 33 | 7:00-7:45 | 6:24 | 5:57 | 5:27 | 2:09 |
| 35 | 6:42-7:24 | 6:09 | 5:42 | 5:12 | 2:03 |
| 38 | 6:18-6:57 | 5:42 | 5:18 | 4:48 | 1:54 |
| 40 | 6:06-6:45 | 5:33 | 5:09 | 4:39 | 1:50 |
| 42 | 5:54-6:33 | 5:24 | 5:00 | 4:33 | 1:47 |
| 45 | 5:36-6:12 | 5:09 | 4:48 | 4:21 | 1:42 |
| 48 | 5:18-5:54 | 4:54 | 4:33 | 4:09 | 1:37 |
| 50 | 5:09-5:42 | 4:45 | 4:24 | 4:00 | 1:34 |
| 55 | 4:48-5:18 | 4:24 | 4:06 | 3:42 | 1:27 |
| 60 | 4:27-4:57 | 4:06 | 3:48 | 3:27 | 1:21 |

**L'agent DOIT avoir la table VDOT complète (VDOT 20-85) en fichier JSON.**
Fichier : `data/vdot_paces.json`

### Types de Séances de Course (7 types)

**1. Easy Run (E)**
- Allure : Easy pace (VDOT)
- Durée : 30-75 min
- Objectif : base aérobie, récupération active
- Fréquence : 2-4× par semaine (backbone du programme)
- Règle : tu dois pouvoir tenir une conversation

**2. Long Run (L)**
- Allure : Easy pace à Long Run pace (légèrement plus lent que Easy)
- Durée : 60-150 min (20-33% du volume hebdomadaire)
- Objectif : durabilité biomécanique, adaptation musculo-squelettique
- Fréquence : 1× par semaine
- Progression : +1-2 km par semaine, max +10% du volume hebdo

**3. Tempo Run (T)**
- Allure : Threshold pace (VDOT T-pace)
- Structure : 20-40 min continu OU Cruise Intervals (ex: 3×10min @ T-pace, 2min jog)
- Objectif : améliorer le seuil lactique
- Fréquence : 1× par semaine (phase build)
- Règle : confortablement difficile, tu peux dire quelques mots mais pas converser

**4. Interval (I)**
- Allure : Interval pace (VDOT I-pace)
- Structure : 5-6 × 3-5min @ I-pace, repos = durée de l'intervalle en jog
- Objectif : VO2max
- Fréquence : 1× par semaine (phase build/peak)
- Règle : respiration lourde mais contrôlée, pas de sprint total

**5. Repetition (R)**
- Allure : Repetition pace (VDOT R-pace)
- Structure : 8-12 × 200-400m @ R-pace, repos complet (60-90s marche/jog)
- Objectif : économie de course, vitesse, recrutement fibres rapides
- Fréquence : 1× par semaine max
- Règle : rapide et relâché, pas tendu

**6. Progression Run (PR)**
- Structure : commence en Easy, termine les derniers 20-30% en T-pace ou M-pace
- Ex: 10km total — 7km @ Easy, 3km @ M-pace
- Objectif : simulation de fatigue de course, confiance mentale
- Fréquence : 1× par semaine ou aux 2 semaines

**7. Recovery Run (RR)**
- Allure : plus lent que Easy (ajouter 15-30 sec/km au Easy pace)
- Durée : 20-30 min max
- Objectif : circulation, récupération active
- Fréquence : lendemain d'une séance difficile

### Règles de Progression Course
- Règle du 10% : ne jamais augmenter le km hebdomadaire de plus de 10%
- Deload toutes les 3-4 semaines : -20-30% du volume
- Augmenter d'abord la fréquence → puis la durée → puis l'intensité
- Max 20% du volume hebdomadaire en Z3+ (allure I-pace ou plus rapide)
- Min 80% du volume en Zone 1 (allure Easy)
- La séance longue ne dépasse jamais 33% du volume hebdomadaire total

### Prévention des Blessures
- Renforcement OBLIGATOIRE des rotateurs externes de hanche (protection valgus genou)
- Cadence cible : 170-180 pas/min (réduit l'impact par foulée)
- Si shin splints passés → progression de volume extra conservatrice (7% max/semaine)
- Transition chaussures minimalistes : maximum 10% du volume initial, augmenter sur 8-12 semaines

### Durabilité Biomécanique
- Coureurs avec sorties longues ≥90 min : dégradation RE limitée à +3.1% (vs +6.0% sans sorties longues)
- Volume d'entraînement = meilleur prédicteur de performance marathon
- Pour chaque +1km/semaine dans les 12-4 mois pré-course : -0.6 min au marathon

## 5.3 Format de Sortie — Séance de Course (Runna-compatible)

Chaque séance de course est un JSON structuré avec des blocs séquentiels :

```json
{
  "run_workout": {
    "id": "run_w3_intervals",
    "name": "Intervalles VO2max",
    "type": "intervals",
    "day": "thursday",
    "week": 3,
    "phase": "base_building",

    "estimated_duration_min": 48,
    "estimated_distance_km": 8.2,
    "estimated_tss": 65,

    "blocks": [
      {
        "type": "warmup",
        "distance_km": 1.5,
        "pace_target": "7:00/km",
        "pace_zone": "recovery",
        "notes": "Jog très facile, augmente graduellement"
      },
      {
        "type": "strides",
        "repetitions": 4,
        "distance_m": 100,
        "pace_target": "4:30/km",
        "recovery_type": "walk",
        "recovery_duration_sec": 60,
        "notes": "Accélérations progressives, relâché"
      },
      {
        "type": "interval",
        "repetitions": 5,
        "distance_m": 800,
        "pace_target": "4:48/km",
        "pace_zone": "I-pace",
        "recovery_type": "jog",
        "recovery_duration_sec": 180,
        "recovery_pace": "7:00/km",
        "notes": "Respiration contrôlée, pas de sprint. Si le 4ème rep est >5s plus lent que le 1er, arrête."
      },
      {
        "type": "cooldown",
        "distance_km": 1.5,
        "pace_target": "7:00/km",
        "pace_zone": "recovery",
        "notes": "Jog progressivement plus lent + 5min étirements"
      }
    ],

    "coaching_notes": [
      "Hydrate-toi 500ml dans les 2h avant la séance",
      "Si tes jambes sont lourdes du lifting de mercredi, réduis à 4 reps au lieu de 5",
      "La constance de pace entre les reps est plus importante que la vitesse absolue"
    ],

    "sync_target": "garmin_structured_workout"
  }
}
```

### Exemples de séances types par phase

**Phase Base — Semaine type (3 courses) :**
- Mardi : Easy Run — 6km @ 6:30/km (40min)
- Jeudi : Easy Run avec Strides — 5km @ 6:30/km + 6×100m strides
- Samedi : Long Run — 12km @ 6:45/km (80min)

**Phase Build — Semaine type (4 courses) :**
- Lundi : Easy Run — 5km @ 6:20/km
- Mercredi : Tempo — 2km warmup + 20min @ 5:18/km + 1.5km cooldown
- Vendredi : Easy Run — 6km @ 6:20/km
- Dimanche : Long Run avec finish fast — 14km (11km @ 6:40, 3km @ 5:42 M-pace)

**Phase Peak — Semaine type (4 courses) :**
- Lundi : Recovery Run — 4km @ 7:00/km
- Mercredi : Intervals — 2km warmup + 5×1000m @ 4:48/km (2min jog) + 1.5km cooldown
- Vendredi : Easy Run — 5km @ 6:20/km
- Dimanche : Long Run — 16km (12km easy, 4km @ T-pace 5:18/km)

---

# 6. LIFTING COACH — Connaissances Complètes & Output Exact

## 6.1 Rôle
Le Lifting Coach prescrit des séances de musculation EXACTES avec exercice, sets, reps/rep range, charge en kg, RPE cible, temps de repos, supersets, et notes de forme. Format compatible Hevy.

## 6.2 Connaissances Fondamentales

### Principes d'hypertrophie pour athlète hybride
L'objectif N'EST PAS l'hypertrophie maximale (bodybuilder), mais :
1. Maintenir la masse musculaire pendant les phases d'endurance élevée
2. Développer les adaptations neurales (économie de locomotion)
3. Prévenir les blessures via le renforcement ciblé
4. Développer la force-puissance sans prendre de masse non fonctionnelle

### Mécanismes d'hypertrophie (Schoenfeld)
1. **Tension mécanique** : le facteur #1. Charge suffisante × amplitude × intention de vélocité
2. **Stress métabolique** : accumulation de métabolites (la "brûlure"). Secondaire.
3. **Dommages musculaires** : à MINIMISER chez l'hybride (détruit la biomécanique de course)

### Volume Landmarks (Israetel/RP) — Adapté Hybride

**Table complète (séries effectives/semaine) :**

| Groupe musculaire | MEV | MAV | MRV standard | MRV hybride (avec course) | Notes |
|-------------------|-----|-----|-------------|--------------------------|-------|
| Quadriceps | 6 | 10 | 18 | 8-12 | Course = volume additionnel gratuit |
| Hamstrings | 4 | 8 | 16 | 6-10 | Course = volume additionnel |
| Glutes | 0 | 4 | 12 | 2-6 | Souvent suffisamment stimulés par course + squat |
| Calves | 4 | 8 | 14 | 4-6 | Course = beaucoup de volume |
| Chest | 6 | 14 | 22 | 14-20 | Non impacté par la course |
| Back (lats) | 6 | 14 | 22 | 14-20 | Non impacté par la course |
| Shoulders (lateral) | 6 | 12 | 20 | 10-16 | Non impacté par la course |
| Biceps | 4 | 10 | 16 | 8-14 | Non impacté par la course |
| Triceps | 4 | 8 | 14 | 6-12 | Non impacté par la course |
| Core | 0 | 4 | 10 | 2-6 | Running + compounds = beaucoup de volume indirect |

**Règle critique :** Si le volume de course augmente (phase build), le MRV jambes BAISSE. L'agent doit automatiquement réduire le volume des membres inférieurs.

### Autorégulation : RIR et RPE
| RPE | RIR | Description | Usage hybride |
|-----|-----|-------------|---------------|
| 10 | 0 | Échec absolu | JAMAIS chez un hybride |
| 9.5 | 0-1 | Presque l'échec | Rarement, tests seulement |
| 9 | 1 | 1 rep de plus possible | Séries top sets, composés |
| 8 | 2 | 2 reps de plus | Zone optimale hypertrophie hybride |
| 7 | 3 | 3 reps de plus | Zone optimale force hybride |
| 6 | 4 | 4+ reps de plus | Échauffement, deload, technique |

**Règle : toutes les séries de travail entre RPE 7-9 (RIR 1-3). Jamais à l'échec.**
L'échec total (RPE 10) génère des DOMS disproportionnés qui détruisent la biomécanique de course 48-72h.

### Exercice Tier System (Ratio Stimulus/Fatigue)

**Tier 1 — Haut SFR, Bas CNS (priorité hybride) :**
Machines et câbles. Fatigue locale élevée, fatigue systémique quasi nulle.
- Leg Press, Hack Squat, Leg Extension, Seated Leg Curl
- Machine Chest Press, Cable Fly, Pec Deck
- Lat Pulldown, Cable Row, Machine Row
- Cable Lateral Raise, Machine Shoulder Press
- Cable Tricep Pushdown, Overhead Cable Extension
- Incline DB Curl, Machine Preacher Curl

**Tier 2 — SFR Modéré, CNS Modéré :**
Haltères et mouvements unilatéraux. Bon compromis.
- Bulgarian Split Squat, Romanian Deadlift (DB), Walking Lunges
- Dumbbell Bench Press, Incline DB Press
- Dumbbell Row, Chest-Supported Row
- DB Overhead Press, DB Lateral Raise
- Pull-ups, Dips

**Tier 3 — Bas SFR, Haut CNS (utiliser avec parcimonie) :**
Barbell compounds lourds. Fatigue systémique massive.
- Barbell Back Squat, Barbell Front Squat
- Conventional Deadlift, Sumo Deadlift
- Barbell Bench Press, Barbell Overhead Press
- Barbell Row, Power Clean

**Règle d'utilisation :**
- Phase base (volume course bas) : Tier 1-2-3 tous autorisés
- Phase build (volume course moyen) : Tier 1-2 principalement, Tier 3 limité à 1-2 exercices/semaine
- Phase peak (volume course élevé) : Tier 1 principalement, Tier 2 accessoire, Tier 3 interdit

### Surcharge Progressive — Double Progression
```
Protocole "Double Progression" pour hybrides :

Prescription : 3 × 8-10 reps @ RPE 8

Session 1 : 70kg × 8, 8, 7 (pas encore à 10 reps sur toutes les séries → garder la charge)
Session 2 : 70kg × 9, 8, 8 (progression → garder la charge)
Session 3 : 70kg × 10, 10, 9 (presque toutes à 10 → garder encore)
Session 4 : 70kg × 10, 10, 10 (toutes les séries au haut de la fourchette → AUGMENTER)
Session 5 : 72.5kg × 8, 8, 7 (nouveau cycle avec +2.5kg)

Règle : quand TOUTES les séries atteignent le haut de la rep range au RPE cible,
augmenter la charge de 2.5kg (haut du corps) ou 5kg (bas du corps).
```

### Périodisation Ondulatoire (DUP) pour Hybride
Alterner le stimulus au sein de la semaine :
- Jour A (Force) : 3-5 reps × 4 séries, RPE 7-8, repos 3-4min
- Jour B (Hypertrophie) : 8-12 reps × 3 séries, RPE 8-9, repos 90-120s
- Jour C (Endurance musculaire, optionnel) : 15-20 reps × 2 séries, RPE 7, repos 60s

Pour un hybride qui lifts 3×/semaine :
- Lundi : Upper A (Force) — bench 4×4, row 4×4
- Mercredi : Lower (Hypertrophie) — leg press 3×10, RDL 3×10, leg curl 3×12
- Samedi : Upper B (Hypertrophie) — incline DB 3×10, pulldown 3×10, lateral raise 3×15

## 6.3 Format de Sortie — Séance de Musculation (Hevy-compatible)

```json
{
  "lifting_workout": {
    "id": "lift_w3_upper_a",
    "name": "Upper A — Force",
    "type": "upper_force",
    "day": "monday",
    "week": 3,
    "phase": "base_building",

    "estimated_duration_min": 55,
    "estimated_fatigue_score": {
      "local_chest": 35,
      "local_back": 35,
      "local_shoulders": 20,
      "local_triceps": 15,
      "local_biceps": 15,
      "cns": 40
    },

    "exercises": [
      {
        "order": 1,
        "exercise_name": "Barbell Bench Press",
        "hevy_exercise_id": "D04AC939",
        "tier": 3,
        "muscle_primary": "chest",
        "muscle_secondary": ["shoulders", "triceps"],
        "superset_id": null,
        "note": "Arque le dos légèrement. Omoplates serrées. Descends à 2-3cm du torse.",
        "sets": [
          {"type": "warmup", "weight_kg": 40, "reps": 10, "rpe_target": null, "rest_sec": 60},
          {"type": "warmup", "weight_kg": 55, "reps": 5, "rpe_target": null, "rest_sec": 90},
          {"type": "normal", "weight_kg": 72.5, "reps_range": [4, 6], "rpe_target": 7, "rest_sec": 180},
          {"type": "normal", "weight_kg": 72.5, "reps_range": [4, 6], "rpe_target": 8, "rest_sec": 180},
          {"type": "normal", "weight_kg": 72.5, "reps_range": [4, 6], "rpe_target": 8, "rest_sec": 180},
          {"type": "normal", "weight_kg": 70, "reps_range": [6, 8], "rpe_target": 8, "rest_sec": 180}
        ]
      },
      {
        "order": 2,
        "exercise_name": "Barbell Row",
        "hevy_exercise_id": "85ADE148",
        "tier": 2,
        "muscle_primary": "back",
        "muscle_secondary": ["biceps", "forearms"],
        "superset_id": null,
        "note": "Buste à 45°, tire vers le nombril. Pas d'élan.",
        "sets": [
          {"type": "warmup", "weight_kg": 40, "reps": 8, "rpe_target": null, "rest_sec": 60},
          {"type": "normal", "weight_kg": 65, "reps_range": [5, 7], "rpe_target": 7, "rest_sec": 150},
          {"type": "normal", "weight_kg": 65, "reps_range": [5, 7], "rpe_target": 8, "rest_sec": 150},
          {"type": "normal", "weight_kg": 65, "reps_range": [5, 7], "rpe_target": 8, "rest_sec": 150}
        ]
      },
      {
        "order": 3,
        "exercise_name": "Incline Dumbbell Press",
        "hevy_exercise_id": "3A72B1D0",
        "tier": 2,
        "muscle_primary": "chest",
        "muscle_secondary": ["shoulders", "triceps"],
        "superset_id": 0,
        "note": "Banc à 30°. Descends jusqu'à l'étirement complet du pec.",
        "sets": [
          {"type": "normal", "weight_kg": 28, "reps_range": [8, 10], "rpe_target": 8, "rest_sec": null},
          {"type": "normal", "weight_kg": 28, "reps_range": [8, 10], "rpe_target": 8, "rest_sec": null},
          {"type": "normal", "weight_kg": 28, "reps_range": [8, 10], "rpe_target": 9, "rest_sec": null}
        ]
      },
      {
        "order": 4,
        "exercise_name": "Cable Row (Seated)",
        "hevy_exercise_id": "F198B2A3",
        "tier": 1,
        "muscle_primary": "back",
        "muscle_secondary": ["biceps"],
        "superset_id": 0,
        "note": "Prise neutre. Tire vers le bas du sternum. Pause 1s en contraction.",
        "sets": [
          {"type": "normal", "weight_kg": 55, "reps_range": [8, 10], "rpe_target": 8, "rest_sec": 120},
          {"type": "normal", "weight_kg": 55, "reps_range": [8, 10], "rpe_target": 8, "rest_sec": 120},
          {"type": "normal", "weight_kg": 55, "reps_range": [8, 10], "rpe_target": 9, "rest_sec": 120}
        ]
      },
      {
        "order": 5,
        "exercise_name": "Cable Lateral Raise",
        "hevy_exercise_id": "B5C12E87",
        "tier": 1,
        "muscle_primary": "shoulders",
        "superset_id": 1,
        "note": "Légère flexion du coude. Monte jusqu'à parallèle. Contrôle la descente.",
        "sets": [
          {"type": "normal", "weight_kg": 7.5, "reps_range": [12, 15], "rpe_target": 8, "rest_sec": null},
          {"type": "normal", "weight_kg": 7.5, "reps_range": [12, 15], "rpe_target": 9, "rest_sec": null},
          {"type": "normal", "weight_kg": 7.5, "reps_range": [12, 15], "rpe_target": 9, "rest_sec": null}
        ]
      },
      {
        "order": 6,
        "exercise_name": "Overhead Cable Tricep Extension",
        "hevy_exercise_id": "A1D3F456",
        "tier": 1,
        "muscle_primary": "triceps",
        "superset_id": 1,
        "note": "Coudes fixes au-dessus de la tête. Étirement complet en bas. Long chef du triceps.",
        "sets": [
          {"type": "normal", "weight_kg": 20, "reps_range": [10, 12], "rpe_target": 8, "rest_sec": 90},
          {"type": "normal", "weight_kg": 20, "reps_range": [10, 12], "rpe_target": 8, "rest_sec": 90},
          {"type": "normal", "weight_kg": 20, "reps_range": [10, 12], "rpe_target": 9, "rest_sec": 90}
        ]
      }
    ],

    "coaching_notes": [
      "C'est un jour Force — les charges sont lourdes mais les reps sont basses. Concentre-toi sur la qualité de chaque rep.",
      "Les supersets (3-4 et 5-6) sauvent du temps sans compromettre la récupération car ils ciblent des muscles opposés.",
      "Si tu n'atteins pas le bas de la fourchette de reps au RPE cible, réduis la charge de 2.5kg la prochaine fois.",
      "Tu cours demain — cette séance upper body n'impacte pas tes jambes, c'est voulu."
    ],

    "progression_rules": {
      "protocol": "double_progression",
      "increase_weight_when": "all_sets_at_top_of_rep_range_at_target_rpe",
      "increase_amount_kg": 2.5,
      "deload_trigger": "2_consecutive_sessions_below_bottom_of_rep_range"
    },

    "sync_target": "hevy_routine"
  }
}
```

### Exemples de semaine type Lifting pour hybride (3 sessions)

**Lundi — Upper A (Force) :**
1. Barbell Bench Press — 1×10 warmup, 4×4-6 @RPE 7-8, 180s repos
2. Barbell Row — 1×8 warmup, 3×5-7 @RPE 7-8, 150s repos
3. Incline DB Press / Cable Row — SS — 3×8-10 @RPE 8, 120s repos
4. Cable Lateral Raise / OH Tricep Extension — SS — 3×12-15 @RPE 8-9, 90s repos

**Mercredi — Lower (Hypertrophie, adapté course) :**
1. Leg Press — 1×12 warmup, 3×8-12 @RPE 8, 150s repos (PAS de squat barbell car intervals jeudi)
2. Romanian Deadlift (DB) — 3×8-10 @RPE 8, 120s repos
3. Seated Leg Curl — 3×10-12 @RPE 8-9, 90s repos
4. Standing Calf Raise — 2×12-15 @RPE 8, 60s repos
5. Ab Wheel Rollout — 2×8-12, 60s repos

**Samedi — Upper B (Hypertrophie) :**
1. Incline DB Press — 3×8-10 @RPE 8, 120s repos
2. Lat Pulldown — 3×8-10 @RPE 8, 120s repos
3. Cable Fly / Face Pull — SS — 3×12-15 @RPE 8-9, 90s repos
4. Incline DB Curl / Cable Pushdown — SS — 3×10-12 @RPE 8-9, 75s repos
5. Hip External Rotation (band) — 2×15 chaque côté (prévention blessures course)

---

# 7. RECOVERY COACH — Portier avec Veto

## 7.1 Mécanisme de Gate

Le Recovery Coach évalue l'état AVANT chaque séance :

| Score Readiness | Couleur | Action |
|-----------------|---------|--------|
| ≥ 75 | VERT | Séance approuvée telle quelle |
| 50-74 | JAUNE | Séance modifiée (-15% intensité) |
| < 50 | ROUGE | Séance bloquée → repos ou Z1 uniquement |

Inputs : HRV RMSSD (matinal, 60s), qualité de sommeil, durée de sommeil, FC repos, RPE de la veille, humeur subjective.

## 7.2 Signaux de surentraînement
L'agent alerte si :
- RMSSD en baisse >15% vs la baseline sur 5+ jours
- FC repos en hausse >5 bpm vs la baseline
- ACWR > 1.5
- Sommeil < 6h pendant 3+ nuits consécutives
- RPE rapporté > 8 pendant 3+ séances consécutives
- L'utilisateur mentionne : "fatigué", "pas envie", "douleur", "malade"

---

# 8. WORKFLOW COMPLET

## 8.1 Création du Plan (étapes 1-9)

```
ÉTAPE 1: Profiling approfondi (Head Coach ↔ User)
   │  7 blocs de questions (section 3)
   │  OUTPUT: AthleteState complet
   v
ÉTAPE 2: Calculs automatiques (Head Coach)
   │  VDOT + allures, 1RM estimés, TDEE, zones FC, volume landmarks
   │  Détermination de la phase du macrocycle
   │  Agents à activer selon les sports choisis
   v
ÉTAPE 3: Matrice de Contraintes (Head Coach)
   │  Budget sessions, jours assignés, hard rules
   │  Présentation à l'user pour validation
   v
ÉTAPE 4: Planification Mésocycle (Agents)
   │  Chaque agent planifie 3-4 semaines dans son budget
   │  Consultent Recovery Coach pour le readiness
   v
ÉTAPE 5: Planification Semaine 1 — Séances Exactes (Agents)
   │  Running Coach : séances avec allures exactes (format Runna)
   │  Lifting Coach : séances avec exercices/sets/reps/charges (format Hevy)
   │  OUTPUT: plans partiels par agent
   v
ÉTAPE 6: Audit & Résolution (Head Coach)
   │  Détection conflits 3 couches
   │  Résolution graduée (swap > réduire > couper)
   │  Circuit breaker si nécessaire (max 2 itérations)
   │  OUTPUT: plan unifié
   v
ÉTAPE 7: Nutrition (Nutrition Coach — séquentiel)
   │  Reçoit le plan VALIDÉ
   │  Macros ajustées jour par jour
   v
ÉTAPE 8: Validation Finale (Head Coach ↔ User)
   │  Présente le plan complet avec séances exactes
   │  User approuve ou demande modifications
   v
ÉTAPE 9: Déploiement
   │  Push vers Hevy (routines), Strava/Garmin (structured workouts)
   │  Début du suivi
```

## 8.2 Boucle Hebdomadaire (H1-H5)

```
H1: Collecte — Pull Strava, Hevy, USDA/OFF, Apple Health
H2: Analyse — Prévu vs réalisé, par agent
H3: Synthèse — ACWR update, matrice update, ajustements
H4: Feedback — Rapport à l'user, commentaires subjectifs
H5: Planification semaine suivante → retour à H1
```

Le Recovery Coach gate chaque séance en temps réel (pas seulement au weekly review).

---

# 9. PLAN D'EXÉCUTION SUPERPOWERS

## Prérequis
```bash
git clone https://github.com/simlirette/resilio-plus.git resilio-hybrid
cd resilio-hybrid
claude
/plugin install superpowers@claude-plugins-official
exit && claude  # Relancer pour activer
```

Copier ce document maître + les fichiers JSON de données dans le repo.

## Premier message à Claude Code
```
Lis le fichier resilio-master-v2.md dans son intégralité.
C'est le document maître complet du projet Resilio Hybrid Coach.
Il contient l'architecture, les connaissances des agents, les formats
de sortie exacts (Hevy et Runna compatible), et le plan d'exécution.

Analyse la structure actuelle du repo resilio-plus/ et confirme
que tu es prêt pour la Phase 0. Ne touche à aucun fichier.
```

## Sessions Superpowers (13 sessions)

| # | Module | Focus |
|---|--------|-------|
| 1 | Setup | Restructurer le repo, créer CLAUDE.md |
| 2 | Schémas | AthleteState + Pydantic models + DB |
| 3 | Connecteurs | Strava (migrer) + Hevy (nouveau) + fallbacks CSV/JSON |
| 4 | Connecteurs | USDA/Open Food Facts + Apple Health + fallbacks GPX/FIT |
| 5 | Agents base | Agent base class + Head Coach + Constraint Solver + `get_agent_view()` |
| 6 | Running Coach | Toutes les connaissances + VDOT + output format |
| 7 | Lifting Coach | Toutes les connaissances + exercise DB + output format |
| 8 | Recovery Coach | Gate keeper + readiness score |
| 9 | Workflow | Onboarding + création de plan + audit |
| 10 | Workflow | Boucle hebdomadaire + matrice vivante |
| 11 | Frontend | FastAPI endpoints + OpenAPI docs |
| 12 | Frontend | Next.js — Dashboard + calendrier + chat |
| 13 | Frontend | Next.js — Suivi hebdo + pages détail |
| 14 | Intégration | Docker + tests E2E + polish |
| 15 | Nutrition Coach | USDA/OFF/FCÉN + NLP input + macros + notifications + race-week |

Pour chaque session : `/superpowers:brainstorm` → valider le spec → `/superpowers:write-plan` → valider le plan → `/superpowers:execute-plan`

À la fin de chaque session : `/revise-claude-md` pour enrichir le CLAUDE.md.

---

# 10. FICHIERS DE DONNÉES JSON

## 10.1 Fichiers EXISTANTS dans `resilio_docs/resilio_docs/` (créés avec Gemini)

| Fichier | Agent | Contenu |
|---------|-------|---------|
| `head_coach_acwr_rules.json` | Head Coach | Règles ACWR, prévention blessures, entraînement en force préventif |
| `head_coach_interference_rules.json` | Head Coach | Entraînement concurrent, interférence HIIT/résistance |
| `running_coach_tid_rules.json` | Running Coach | Distribution d'intensité polarisée/pyramidale |
| `lifting_coach_volume_rules.json` | Lifting Coach | Drop-sets, volume hebdo, créatine, BFR, VBT |
| `biking_coach_power_rules.json` | Biking Coach | HIIT vs MVICT, bike fitting, caféine cyclisme |
| `swimming_coach_biomechanics_rules.json` | Swimming Coach | Drafting, coût énergétique en brasse |
| `nutrition_coach_fueling_rules.json` | Nutrition Coach | Glucides intra-effort, épargne glycogène, stratégies GI |
| `recovery_coach_hrv_rules.json` | Recovery Coach | HRV indicateur parasympathique, CWI, techniques récup |
| `recovery_coach_sleep_cns_rules.json` | Recovery Coach | Sommeil, extension pré-compétition, siestes tactiques |

## 10.2 Fichiers À CRÉER dans `data/` (par les skills)

| Fichier | Contenu | Utilisé par |
|---------|---------|-------------|
| `data/vdot_paces.json` | Table VDOT complète (20-85) avec toutes les allures | Running Coach |
| `data/exercise_database.json` | 400+ exercices avec Hevy IDs, muscles, tier, SFR | Lifting Coach |
| `data/volume_landmarks.json` | MEV/MAV/MRV par muscle (standard + hybride) | Lifting Coach |
| `data/muscle_overlap.json` | Table chevauchement musculaire entre sports | Head Coach |
| `data/nutrition_targets.json` | Macros par type de jour (force, endurance, repos) | Nutrition Coach |
| `data/running_zones.json` | Zones FC par modèle (Seiler 3-zone, Daniels 5-zone) | Running Coach |
| `data/food_database_cache.json` | Cache local aliments fréquents (USDA + FCÉN) | Nutrition Coach |
| `data/agent_view_map.json` | Mapping des champs autorisés par agent (Token Economy) | Orchestrateur |

## 10.3 APIs alimentaires (remplacent FatSecret)

| API | URL | Clé requise | Usage |
|-----|-----|-------------|-------|
| USDA FoodData Central | `api.nal.usda.gov/fdc/v1/` | Gratuite (inscription) | Aliments bruts, référence scientifique |
| Open Food Facts | `world.openfoodfacts.org/api/v2/` | Aucune | Produits commerciaux, codes-barres |
| FCÉN (Santé Canada) | Téléchargement CSV | Aucune | Marché canadien |
