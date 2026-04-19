# RESILIO HYBRID COACH — Blueprint Projet & Guide Claude Code

> **Objectif** : Transformer `resilio-app` (du-phan) en plateforme multi-agents de coaching sportif inspirée de BMAD-METHOD, avec backend Python + frontend web (Next.js).

---

## 1. VISION DU PROJET

### Concept
Un **Head Coach IA** orchestre des agents spécialistes (Running, Lifting, Swimming, Biking, Nutrition, Recovery) pour créer des plans d'entraînement et de nutrition personnalisés pour athlètes hybrides/multisport. Suivi hebdomadaire avec ajustements automatiques basés sur les données réelles des apps connectées.

### Écosystème API
| Service | Rôle | API |
|---------|------|-----|
| **Strava** | Course, vélo, natation (GPS, FC, allure, puissance) | OAuth2 REST — `developers.strava.com` |
| **Hevy** | Musculation (sets, reps, charge, volume) | REST v1 — Hevy Pro requis |
| **FatSecret** | Nutrition détaillée (aliments, macros, micros) | OAuth2 REST — `platform.fatsecret.com` |
| **Apple Health** | Hub de données santé (HRV, sommeil, pas) | Via Terra API ou HealthKit natif |

---

## 2. ARCHITECTURE MULTI-AGENTS (STYLE BMAD)

### Principes empruntés à BMAD-METHOD
- Chaque agent est un fichier `.agent.md` (YAML header + instructions en markdown)
- Les agents ont des **tasks** (tâches) et **templates** (modèles de sortie)
- Le Head Coach orchestre via des **workflows** séquentiels
- Communication inter-agents via un **langage commun** (score de fatigue, charge)
- Slash commands pour invoquer chaque agent dans Claude Code : `/head-coach`, `/run-coach`, `/lift-coach`, etc.

### Structure des agents

```
.bmad-core/
├── agents/
│   ├── head-coach.agent.md          # Orchestrateur principal
│   ├── running-coach.agent.md       # Expert course
│   ├── lifting-coach.agent.md       # Expert musculation
│   ├── swimming-coach.agent.md      # Expert natation
│   ├── biking-coach.agent.md        # Expert vélo route
│   ├── nutrition-coach.agent.md     # Expert nutrition
│   └── recovery-coach.agent.md      # Expert récupération & sommeil
├── tasks/
│   ├── onboarding-brainstorm.md     # Étape 1 : collecte données user
│   ├── athlete-analysis.md          # Étape 2 : analyse profil
│   ├── schedule-negotiation.md      # Étape 3 : temps & équipements
│   ├── plan-creation.md             # Étape 4 : création plan collaboratif
│   ├── plan-confirmation.md         # Étape 5 : validation user
│   ├── api-integration.md           # Étape 6 : push vers apps
│   ├── weekly-review.md             # Étapes 7-8-9 : suivi hebdo
│   └── plan-adaptation.md           # Ajustement des plans
├── templates/
│   ├── training-plan.yaml           # Template plan d'entraînement
│   ├── nutrition-plan.yaml          # Template plan nutritionnel
│   ├── weekly-report.yaml           # Template rapport hebdomadaire
│   └── athlete-profile.yaml         # Template profil athlète
├── data/
│   ├── volume-landmarks.json        # MEV/MAV/MRV par groupe musculaire
│   ├── exercise-database.json       # Exercices classés par profil SFR
│   ├── running-zones.json           # Zones d'entraînement (Daniels/Pfitz)
│   ├── cycling-zones.json           # Zones puissance (PPi)
│   ├── swimming-benchmarks.json     # SWOLF, DPS, efficience propulsive
│   └── nutrition-targets.json       # Macros par type de journée
└── workflows/
    ├── workflow-new-athlete.md       # Onboarding complet (étapes 1-6)
    ├── workflow-weekly-review.md     # Suivi hebdo (étapes 7-8-9)
    └── workflow-plan-renewal.md      # Nouveau plan post-objectif
```

---

## 3. CHEMIN UTILISATEUR (USER FLOW)

### Étape 1 — Onboarding (Brainstorm)
Le Head Coach mène un brainstorm conversationnel :
- Données physiques : taille, poids, âge, sexe
- Historique sportif : sports pratiqués, niveaux, blessures passées
- Objectifs : performance (temps, distance), composition corporelle, santé
- Contexte de vie : travail physique/bureau, stress, sommeil typique
- Question ouverte finale : "Y a-t-il autre chose que tu aimerais ajouter ?"

### Étape 2 — Analyse du profil
Chaque agent spécialiste pertinent analyse les données :
- Running Coach évalue le niveau aérobie (via historique Strava si dispo)
- Lifting Coach évalue le niveau de force (via historique Hevy si dispo)
- Nutrition Coach calcule les besoins caloriques de base (TDEE)
- Recovery Coach évalue la capacité de récupération

### Étape 3 — Négociation du temps
- Heures disponibles par semaine/jour
- Jours disponibles et jours prioritaires
- Jour de début de semaine
- Équipements disponibles (gym, piscine, vélo, extérieur)

### Étape 4 — Création collaborative du plan
Chaque agent produit ses recommandations → le Head Coach :
1. Détecte les conflits (ex: jambes lourdes le mardi + fractionné le mercredi)
2. Calcule la charge globale via un score de fatigue unifié
3. Arbitre et synchronise en un plan cohérent
4. Le Nutrition Coach adapte les macros jour par jour selon le plan d'activité

### Étape 5 — Confirmation
- Présentation du plan complet à l'utilisateur
- Modifications possibles avant validation
- Choix du jour de suivi hebdomadaire

### Étape 6 — Intégration API
- Push des workouts dans Hevy (si API le permet)
- Push des entraînements dans Strava (calendrier)
- Sync du plan nutritionnel avec FatSecret

### Étapes 7-8-9 — Boucle hebdomadaire (répétée)
7. **Collecte** : Pull des données des apps + demande de commentaires au user
8. **Analyse** : Comparaison prévu vs réalisé, détection de fatigue, ajustements
9. **Présentation** : Changements proposés → confirmation ou modification

---

## 4. STRUCTURE DU CODE (BACKEND + FRONTEND)

### Monorepo recommandé

```
resilio-hybrid/
├── .bmad-core/                    # Agents, tasks, templates (voir section 2)
├── CLAUDE.md                      # Instructions pour Claude Code
├── AGENTS.md                      # Instructions pour Codex
│
├── backend/                       # Python (FastAPI)
│   ├── resilio/
│   │   ├── agents/                # Logique des agents IA
│   │   │   ├── base.py            # Classe Agent de base
│   │   │   ├── head_coach.py      # Orchestrateur
│   │   │   ├── running_coach.py
│   │   │   ├── lifting_coach.py
│   │   │   ├── swimming_coach.py
│   │   │   ├── biking_coach.py
│   │   │   ├── nutrition_coach.py
│   │   │   └── recovery_coach.py
│   │   ├── api/                   # Endpoints FastAPI
│   │   │   ├── routes/
│   │   │   │   ├── auth.py        # OAuth flows (Strava, Hevy, FatSecret)
│   │   │   │   ├── athletes.py    # Profil athlète
│   │   │   │   ├── plans.py       # Plans d'entraînement
│   │   │   │   ├── reviews.py     # Suivis hebdos
│   │   │   │   └── chat.py        # Interface conversationnelle
│   │   │   └── deps.py            # Dépendances (DB, auth)
│   │   ├── connectors/            # Intégrations API externes
│   │   │   ├── strava.py
│   │   │   ├── hevy.py
│   │   │   ├── fatsecret.py
│   │   │   └── apple_health.py    # Via Terra API
│   │   ├── core/                  # Logique métier
│   │   │   ├── fatigue.py         # Score de fatigue unifié
│   │   │   ├── periodization.py   # Périodisation (linéaire, ondulatoire, blocs)
│   │   │   ├── conflict.py        # Détection de conflits inter-agents
│   │   │   └── progression.py     # Règles de surcharge progressive
│   │   ├── schemas/               # Pydantic models
│   │   │   ├── athlete.py
│   │   │   ├── plan.py
│   │   │   ├── workout.py
│   │   │   └── nutrition.py
│   │   └── db/                    # Persistance
│   │       ├── models.py          # SQLAlchemy / SQLite
│   │       └── migrations/
│   ├── tests/
│   ├── pyproject.toml
│   └── Dockerfile
│
├── frontend/                      # Next.js (React)
│   ├── src/
│   │   ├── app/                   # App Router
│   │   │   ├── page.tsx           # Landing / Dashboard
│   │   │   ├── onboarding/        # Flow d'onboarding (étapes 1-3)
│   │   │   ├── plan/              # Visualisation du plan
│   │   │   ├── review/            # Suivi hebdomadaire
│   │   │   └── chat/              # Interface conversationnelle
│   │   ├── components/
│   │   │   ├── Calendar.tsx       # Calendrier d'entraînement
│   │   │   ├── WeeklyPlan.tsx     # Vue semaine
│   │   │   ├── WorkoutCard.tsx    # Détail d'un workout
│   │   │   ├── NutritionDay.tsx   # Plan nutrition du jour
│   │   │   ├── ProgressChart.tsx  # Graphiques de progression
│   │   │   └── ChatInterface.tsx  # Chat avec le Head Coach
│   │   └── lib/
│   │       └── api.ts             # Client API backend
│   ├── package.json
│   └── Dockerfile
│
├── docker-compose.yml
└── README.md
```

---

## 5. BASE DE CONNAISSANCES PAR AGENT

### 5.1 Head Coach (Orchestrateur)

**Rôle** : Synchronise tous les agents, gère la charge globale, résout les conflits.

**Concepts clés** :
- Interférence moléculaire mTOR vs AMPK : séparer stimuli force/endurance de 6-24h
- Distribution de l'intensité (TID) : pyramidale en prépa, polarisée en compétition
- HIFT : gains simultanés VO2max (+8-15%) et force (+10-20%)
- Masters (>40 ans) : ratio charge/récup 2:1, déclin VO2max limitable à -5%/décennie
- Score de fatigue unifié : langage commun entre agents

**Sources** :
- High-Intensity Functional Training in Hybrid Competitions (ResearchGate 395815634)
- Training Periodization, Methods, Intensity Distribution (IJSPP 17/6 p.820)
- VO2max Changes of Masters Athletes (encyclopedia.pub/entry/27007)
- Concurrent Training Enhances Athletes' Strength
- Effects of concurrent training on elite female triathletes

### 5.2 Lifting Coach

**Rôle** : Optimisation neuromusculaire, hypertrophie contrôlée, surcharge progressive.

**Règles d'affaires** :
- Charges lourdes >80% 1RM avec intention de vélocité maximale
- Toutes les séries entre 1-3 RIR (jamais à l'échec total pour hybride)
- Fourchette de reps : 5-30 (jamais <5 pour hybride : trop coûteux nerveusement)
- Volume : respecter MEV/MAV/MRV par groupe musculaire
- MRV jambes réduit de 30-50% quand volume course élevé
- Privilégier exercices à haut ratio Stimulus/Fatigue (SFR)
- Exercices stables (machines, câbles) quand kilométrage élevé
- Étirement sous charge (stretch-mediated hypertrophy) prioritaire
- Surcharge progressive : si haut de fourchette atteint au RIR cible → +2-5% charge
- Fréquence optimale : 2 séances/semaine minimum, >24 séances pour résultats
- Conflit avec course intense : réduire volume jambes 30-50%, maintenir intensité

**Auteurs de référence** : Brad Schoenfeld (hypertrophie), Mike Israetel (volume), Eric Helms (autorégulation RPE/RIR), Chris Beardsley (biomécanique), NSCA, ACSM.

**Sources** :
- Strength Training for Middle/Long-Distance Performance Meta-Analysis (ResearchGate 316615049)
- Maximal Strength Training Improves Cycling Economy (ResearchGate 38034737)
- Plyometric Training for Cyclists
- Concurrent Strength and Endurance Training Impact
- Effect of Strength and Endurance Training Sequence

### 5.3 Running Coach

**Rôle** : Économie de course, durabilité biomécanique, prévention blessures.

**Règles d'affaires** :
- Durabilité biomécanique : sorties longues ≥90 min limitent dégradation RE à +3.1%
- Zones d'entraînement basées sur Daniels/Pfitzinger/80-20/FIRST
- Renforcement obligatoire des rotateurs externes de hanche (prévention)
- Progression du kilométrage : meilleur prédicteur de performance marathon
- Super shoes (plaques carbone) : ~2% gain d'économie de course

**Sources** :
- Durability of Running Economy (PubMed 40878015)
- Biomechanical risk factors for running-related injuries (PMC 11532757)
- Running Biomechanics and Running Economy (PMC 12913831)
- Training volume on marathon performance
- Advanced footwear technology analysis

### 5.4 Biking Coach

**Rôle** : Quantification de la charge cycliste, puissance, aérodynamisme.

**Règles d'affaires** :
- Remplacer TSS par Power Profile Index (PPi) : 6 zones basées sur TTE, pondération exponentielle (K=3.9)
- Suivi fatigue submaximale : ratio puissance/FC
- Pliométrie complémentaire : -3% coût en O2

**Sources** :
- The Power Profile Index (MDPI 2076-3417/12/21/11020)
- Monitoring cyclist training load sub-maximal test (sciencetosport.com)
- Load Monitoring Methods for Controlling Training
- From Amateur to Professional Cycling

### 5.5 Swimming Coach

**Rôle** : Hydrodynamisme, efficience propulsive, technique.

**Règles d'affaires** :
- Efficience propulsive : nageurs 61% vs triathlètes 44% → optimiser DPS, pas le volume
- Métrique principale : SWOLF (temps longueur + coups de bras)
- Eau libre vs piscine : fréquence bras ↑, longueur cycle ↓ en eau libre
- Dry-land training : 2-4 séances/semaine, 80-90% 1RM + pliométrie
- Drafting eau libre : -11% consommation O2

**Sources** :
- Propelling efficiency competitive swimmers vs triathletes (PubMed 2381311)
- Swimming Performance Elite Triathletes Open Water vs Pool (ResearchGate 382495813)
- Dry-land strength and conditioning training (ResearchGate 327675673)
- SWOLF in swimming
- Pacing profile in open-water swimming

### 5.6 Nutrition Coach

**Rôle** : Périodisation nutritionnelle, macros, suppléments, ravitaillement.

**Règles d'affaires** :
- Glucides modulés par type de jour :
  - Force pure : 4-5 g/kg/jour
  - Endurance longue : 6-7 g/kg/jour
  - Repos : 3-4 g/kg/jour
  - Intra-effort >75 min : 30-60 g/h (jusqu'à 90 g/h ratio glucose:fructose)
- Protéines : ~1.8 g/kg/jour, doses 20-40g toutes les 3-4h
- Caséine pré-sommeil : 30-40g
- Récupération express (<4h entre sessions) : ratio 3:1 glucides:protéines
- Entraînement gastro-intestinal pour tolérer hauts volumes glucides en course

**Sources** :
- Protein needs of endurance athletes (PMC 12152099)
- Hybrid Athlete Nutrition Guide 2026 (findyouredge.app)
- ISSN position stand nutrient timing (PMC 2575187)
- Nutritional strategies for minimizing GI symptoms (PubMed 40650376)

### 5.7 Recovery & Sleep Coach

**Rôle** : Récupération autonomique, sommeil, prévention surentraînement.

**Règles d'affaires** :
- HRV : RMSSD matinal (60 sec) comme standard d'or
- 3-5 enregistrements pour calibrer la baseline hebdomadaire
- Entraînement guidé par HRV > plan statique
- Sommeil : jusqu'à 10h/nuit sous forte charge
- Sleep banking : extension 6.8h → 8.4h la semaine pré-compétition
- Siestes tactiques quand charge allostatic élevée

**Sources** :
- Monitoring Training Adaptation and Recovery HRV (PMC 12787763)
- HRV-Guided Training Recreational Athletes (apcz.umk.pl QS/69713)
- Sleep and the athlete expert consensus (BJSM 55/7/356)
- Sleep in physical and cognitive performance ultra-endurance (PMC 10666701)

---

## 6. SCORE DE FATIGUE UNIFIÉ (LANGAGE COMMUN)

Le Head Coach a besoin d'un score normalisé pour comparer l'impact de chaque type d'entraînement. Proposition :

```python
# Chaque agent produit un "Fatigue Score" normalisé 0-100
# Le Head Coach additionne et compare au budget hebdomadaire

class FatigueScore:
    local_muscular: float    # Impact musculaire local (0-100)
    cns_load: float          # Charge système nerveux central (0-100)
    metabolic_cost: float    # Coût métabolique (0-100)
    recovery_hours: float    # Heures estimées de récupération
    affected_muscles: list   # Groupes musculaires impactés

# Exemples de mapping :
# - Course Z2 60min → local=20, cns=10, metabolic=30
# - Fractionné 10x400m → local=50, cns=40, metabolic=60
# - Squat lourd 5x5 → local=70, cns=60, metabolic=20
# - Natation technique 45min → local=15, cns=10, metabolic=25
```

---

## 7. PLAN D'EXÉCUTION AVEC CLAUDE CODE

### Phase 0 — Setup (Jour 1)

```bash
# 1. Cloner Resilio comme base
git clone https://github.com/du-phan/resilio-app.git resilio-hybrid
cd resilio-hybrid

# 2. Installer BMAD-METHOD pour référence
npx bmad-method install
# (Examiner la structure .bmad-core/ générée)

# 3. Ouvrir dans Claude Code
# Dire : "Lis CLAUDE.md et le blueprint du projet"
```

### Phase 1 — Fondations (Semaine 1-2)
1. Restructurer le repo selon la structure section 4
2. Créer les fichiers `.agent.md` pour chaque agent (section 2)
3. Adapter le CLAUDE.md existant de Resilio pour le nouveau projet
4. Configurer les connecteurs API (Strava existe déjà, ajouter Hevy + FatSecret)
5. Créer les schémas Pydantic (athlete, plan, workout, nutrition)
6. Mettre en place la DB SQLite avec SQLAlchemy

### Phase 2 — Agents Backend (Semaine 3-4)
1. Implémenter la classe Agent de base
2. Coder le Head Coach (orchestration, détection conflits, score fatigue)
3. Coder le Running Coach (reprendre la logique Resilio existante)
4. Coder le Lifting Coach (nouveau, basé sur les règles section 5.2)
5. Coder les autres agents (swimming, biking, nutrition, recovery)
6. Implémenter le workflow d'onboarding (étapes 1-3)
7. Implémenter le workflow de création de plan (étape 4)

### Phase 3 — API & Intégrations (Semaine 5-6)
1. FastAPI routes pour auth OAuth (Strava, Hevy, FatSecret)
2. Endpoints CRUD pour profils athlètes et plans
3. Endpoint chat conversationnel (streaming)
4. Sync bidirectionnelle avec les apps
5. Webhook/cron pour le suivi hebdomadaire

### Phase 4 — Frontend Web (Semaine 7-8)
1. Setup Next.js + Tailwind + shadcn/ui
2. Pages d'onboarding (formulaire conversationnel)
3. Dashboard principal (calendrier, plan semaine, stats)
4. Interface de chat avec le Head Coach
5. Vue détaillée des workouts et nutrition
6. Page de suivi hebdomadaire

### Phase 5 — Boucle de suivi (Semaine 9-10)
1. Automated weekly review pipeline
2. Comparaison prévu vs réalisé
3. Algorithme d'adaptation des plans
4. Notifications et rappels
5. Tests E2E et polish

---

## 8. COMMANDES CLAUDE CODE RECOMMANDÉES

Quand tu ouvres le projet dans Claude Code, utilise ces prompts :

```
# Phase 0
"Lis ce blueprint et le CLAUDE.md existant de Resilio.
Restructure le repo selon la section 4 du blueprint."

# Phase 1
"Crée les fichiers .agent.md pour chaque coach selon la structure
BMAD dans .bmad-core/agents/. Utilise les connaissances de la section 5."

# Phase 2
"Implémente la classe Agent de base dans backend/resilio/agents/base.py
puis le Head Coach avec le système de score de fatigue unifié."

# Phase 3
"Configure FastAPI avec les routes OAuth pour Strava, Hevy et FatSecret.
Réutilise le connecteur Strava de Resilio original."

# Phase 4
"Setup le frontend Next.js avec le dashboard principal,
le calendrier d'entraînement et l'interface de chat."
```

---

## 9. DONNÉES DE RÉFÉRENCE (TABLES DE VÉRITÉ)

### volume-landmarks.json (extrait)
```json
{
  "quadriceps": { "MEV": 6, "MAV": 12, "MRV_standard": 18, "MRV_hybrid_runner": 10 },
  "hamstrings": { "MEV": 4, "MAV": 10, "MRV_standard": 16, "MRV_hybrid_runner": 8 },
  "chest": { "MEV": 6, "MAV": 14, "MRV_standard": 22, "MRV_hybrid_runner": 22 },
  "back": { "MEV": 6, "MAV": 14, "MRV_standard": 22, "MRV_hybrid_runner": 22 },
  "shoulders": { "MEV": 6, "MAV": 12, "MRV_standard": 20, "MRV_hybrid_runner": 20 },
  "biceps": { "MEV": 4, "MAV": 10, "MRV_standard": 16, "MRV_hybrid_runner": 16 },
  "triceps": { "MEV": 4, "MAV": 8, "MRV_standard": 14, "MRV_hybrid_runner": 14 },
  "calves": { "MEV": 4, "MAV": 8, "MRV_standard": 14, "MRV_hybrid_runner": 6 }
}
```

### exercise-sfr-profiles.json (extrait)
```json
{
  "high_sfr_stable": [
    {"name": "Leg Press", "muscles": ["quadriceps"], "profile": "stretch", "stability": "high"},
    {"name": "Romanian Deadlift (DB)", "muscles": ["hamstrings"], "profile": "stretch", "stability": "medium"},
    {"name": "Cable Fly", "muscles": ["chest"], "profile": "stretch", "stability": "high"},
    {"name": "Overhead Tricep Extension", "muscles": ["triceps"], "profile": "stretch", "stability": "high"},
    {"name": "Leg Curl (seated)", "muscles": ["hamstrings"], "profile": "stretch", "stability": "high"}
  ],
  "high_sfr_compound": [
    {"name": "Barbell Squat", "muscles": ["quadriceps", "glutes"], "profile": "stretch", "stability": "low", "cns_cost": "high"},
    {"name": "Deadlift", "muscles": ["posterior_chain"], "profile": "mixed", "stability": "low", "cns_cost": "very_high"}
  ]
}
```

---

## 10. SUPPLÉMENT DE CONNAISSANCES (v2)

**Voir le fichier `resilio-knowledge-supplement-v2.md`** pour les 21 sources additionnelles et les concepts manquants critiques ajoutés à chaque agent, incluant :
- Head Coach : ACWR (Acute:Chronic Workload Ratio), séquençage force/endurance, périodisation macro-annuelle
- Running Coach : Zones d'entraînement formalisées (Daniels/Seiler), protocoles de séances clés, tapering
- Lifting Coach : Périodisation ondulatoire (DUP) pour hybrides, Velocity-Based Training, exercices Tier 1/2/3
- Biking Coach : Zones de puissance Coggan, protocoles FTP, métriques TSS/CTL/ATL/TSB
- Swimming Coach : Critical Swim Speed (CSS), zones basées sur CSS, séances types
- Nutrition Coach : Hydratation, supplémentation niveau A (créatine, caféine, beta-alanine, nitrate), péri-compétition
- Recovery Coach : Protocoles de récupération actifs, Readiness Score quotidien

---

## 11. NOTES IMPORTANTES

### Ce qui existe déjà dans Resilio
- Connecteur Strava fonctionnel (OAuth, sync, rate-limit handling)
- Méthodologie running solide (Daniels, Pfitzinger, 80/20, FIRST)
- CLI avec Poetry (typer)
- Schémas Pydantic
- Persistance locale YAML/JSON
- CLAUDE.md et AGENTS.md configurés

### Ce qui doit être ajouté
- Tous les nouveaux agents (Lifting, Swimming, Biking, Nutrition, Recovery)
- Connecteurs Hevy et FatSecret
- Le système d'orchestration Head Coach
- Le score de fatigue unifié
- Le workflow d'onboarding conversationnel
- Le frontend web complet
- La boucle de suivi hebdomadaire

### Risques et considérations
- **Hevy API en beta** : structure de données pourrait évoluer
- **FatSecret OAuth** : flow d'autorisation user requis
- **Apple Health** : pas d'API directe web, nécessite Terra API (~payant) ou app native
- **Rate limits** : Strava (100 req/15min), Hevy (à vérifier), FatSecret (libéral)
- **Conflits inter-agents** : le Head Coach doit avoir la priorité absolue
