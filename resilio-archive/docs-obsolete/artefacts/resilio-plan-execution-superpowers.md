# PLAN D'EXÉCUTION RESILIO — Adapté pour Superpowers

> Remplace la Section 7 du blueprint original.
> Workflow Superpowers : `/superpowers:brainstorm` → `/superpowers:write-plan` → `/superpowers:execute-plan`

---

## PRÉREQUIS — Installation

```bash
# 1. Cloner Resilio comme base
git clone https://github.com/du-phan/resilio-app.git resilio-hybrid
cd resilio-hybrid

# 2. Ouvrir dans Claude Code
claude

# 3. Installer Superpowers
/plugin marketplace add obra/superpowers-marketplace
/plugin install superpowers@superpowers-marketplace

# 4. Quitter et relancer Claude Code pour activer les skills
exit
claude

# 5. Vérifier l'installation
/help
# Tu devrais voir: /superpowers:brainstorm, write-plan, execute-plan
```

---

## COMMENT UTILISER CE PLAN

Chaque "module" ci-dessous est un cycle Superpowers complet. Tu ne codes RIEN toi-même directement. Tu :

1. **Lances un brainstorm** avec le contexte fourni
2. **Valides le spec** que Claude te propose (chunk par chunk)
3. **Lances write-plan** — Claude crée un plan.md détaillé
4. **Valides le plan** (tu peux demander des ajustements)
5. **Lances execute-plan** — Claude travaille en autonomie avec TDD + code review
6. **Review finale** — tu vérifies, merges, et passes au module suivant

**Important** : Donne le fichier `resilio-hybrid-coach-blueprint.md` à Claude au tout début pour qu'il ait le contexte complet du projet.

---

## PHASE 0 — SETUP & CLAUDE.MD (Session 1)

### Objectif
Préparer le repo, établir le CLAUDE.md du projet, et configurer la structure de base.

### Prompt de départ
```
Lis le fichier resilio-hybrid-coach-blueprint.md à la racine du projet.
C'est le blueprint complet d'un projet de coaching multi-agents pour
athlètes hybrides. Je veux transformer ce repo (Resilio) en ce projet.

Avant de coder quoi que ce soit :
1. Analyse la structure actuelle du repo Resilio
2. Propose un CLAUDE.md adapté au nouveau projet
3. Propose la restructuration du repo selon la section 4 du blueprint

Ne touche à aucun fichier pour l'instant, je veux juste ton analyse.
```

### Après l'analyse, lance :
```
/superpowers:brainstorm
```
**Contexte à donner** : "Je restructure un repo Python de coaching running (Resilio) en plateforme multi-agents pour athlètes hybrides. Backend FastAPI + Frontend Next.js. Le blueprint complet est dans resilio-hybrid-coach-blueprint.md."

**Résultat attendu** : Un spec validé pour la restructuration du repo + le CLAUDE.md

### Puis :
```
/superpowers:write-plan
/superpowers:execute-plan
```

**Livrables Phase 0** :
- CLAUDE.md complet pour le projet
- Structure de dossiers créée (backend/, frontend/, .bmad-core/)
- pyproject.toml mis à jour
- README.md mis à jour
- Git commit propre sur une branche `feat/restructure`

---

## PHASE 1 — SCHÉMAS & MODÈLES DE DONNÉES (Session 2)

### Prompt brainstorm
```
/superpowers:brainstorm
```
**Contexte** : "Je dois créer les modèles de données Pydantic et SQLAlchemy pour le projet Resilio. Les entités principales sont : Athlete (profil, objectifs, historique), TrainingPlan (plan hebdo/mensuel), Workout (session individuelle), NutritionPlan (macros par jour), WeeklyReview (suivi). Voir les sections 4 et 6 du blueprint pour les détails. Le score de fatigue unifié (FatigueScore) est le langage commun entre agents."

**Points clés à valider dans le spec** :
- Schéma Athlete avec toutes les données d'onboarding
- Schéma FatigueScore (local_muscular, cns_load, metabolic_cost, recovery_hours, affected_muscles)
- Schéma TrainingPlan avec slots par jour
- Schéma NutritionPlan avec macros modulées par type de jour
- Relations entre entités

### Puis : write-plan → execute-plan

**Livrables Phase 1** :
- `backend/resilio/schemas/` — Tous les modèles Pydantic
- `backend/resilio/db/models.py` — Modèles SQLAlchemy
- Tests pour chaque schéma (TDD imposé par Superpowers)
- Branche `feat/data-models`

---

## PHASE 2 — CONNECTEURS API (Session 3-4)

### Session 3 : Strava + Hevy

```
/superpowers:brainstorm
```
**Contexte** : "Le repo Resilio a déjà un connecteur Strava fonctionnel dans resilio/. Je dois le migrer vers backend/resilio/connectors/strava.py et ajouter un connecteur Hevy (API REST v1, nécessite Hevy Pro). Le connecteur Hevy doit pouvoir : récupérer l'historique des workouts, les routines, les exercices, et filtrer par date. Voir la doc Hevy API. Le connecteur Strava existant gère déjà l'OAuth et le rate limiting."

### Session 4 : FatSecret + Apple Health

```
/superpowers:brainstorm
```
**Contexte** : "J'ai besoin d'un connecteur FatSecret (OAuth2 REST, platform.fatsecret.com) pour la nutrition détaillée et d'un connecteur Apple Health via Terra API pour les données de santé (HRV, sommeil). FatSecret doit pouvoir lire le journal alimentaire complet avec macros/micros. Terra API agit comme pont universel pour Apple Health."

**Livrables Phase 2** :
- `backend/resilio/connectors/strava.py` (migré + amélioré)
- `backend/resilio/connectors/hevy.py` (nouveau)
- `backend/resilio/connectors/fatsecret.py` (nouveau)
- `backend/resilio/connectors/apple_health.py` (nouveau, via Terra)
- Tests pour chaque connecteur
- Branches `feat/connectors-strava-hevy` et `feat/connectors-nutrition-health`

---

## PHASE 3 — SYSTÈME D'AGENTS (Session 5-6-7)

C'est le cœur du projet. Chaque session = un cycle brainstorm → plan → execute.

### Session 5 : Agent de base + Head Coach

```
/superpowers:brainstorm
```
**Contexte** : "Je construis le système multi-agents. D'abord la classe Agent de base (dans backend/resilio/agents/base.py) puis le Head Coach (orchestrateur). Le Head Coach : reçoit les recommandations de chaque agent spécialiste, calcule un score de fatigue global, détecte les conflits (ex: jambes lourdes + fractionné le lendemain), et arbitre pour synchroniser le plan. Voir sections 5.1 et 6 du blueprint. Le score de fatigue unifié est décrit en section 6."

### Session 6 : Running Coach + Lifting Coach

```
/superpowers:brainstorm
```
**Contexte** : "Deux agents spécialistes. Le Running Coach reprend la méthodologie Resilio existante (Daniels, Pfitzinger, 80/20, FIRST) et ajoute la prévention blessures et la durabilité biomécanique. Le Lifting Coach est nouveau : il gère l'hypertrophie via les Volume Landmarks (MEV/MAV/MRV), le RIR 1-3, le ratio SFR, et sait réduire le volume jambes de 30-50% quand la course est intense. Voir sections 5.2 et 5.3 du blueprint. Les tables de vérité sont dans .bmad-core/data/volume-landmarks.json et exercise-database.json."

### Session 7 : Swimming + Biking + Nutrition + Recovery

```
/superpowers:brainstorm
```
**Contexte** : "Les 4 agents restants. Swimming Coach optimise le SWOLF et la DPS (pas le volume). Biking Coach utilise le PPi au lieu du TSS. Nutrition Coach fait la périodisation des glucides par type de jour (4-5g/kg force, 6-7g/kg endurance). Recovery Coach utilise le RMSSD matinal pour guider l'intensité. Voir sections 5.4 à 5.7 du blueprint."

**Livrables Phase 3** :
- `backend/resilio/agents/base.py`
- `backend/resilio/agents/head_coach.py`
- `backend/resilio/agents/running_coach.py`
- `backend/resilio/agents/lifting_coach.py`
- `backend/resilio/agents/swimming_coach.py`
- `backend/resilio/agents/biking_coach.py`
- `backend/resilio/agents/nutrition_coach.py`
- `backend/resilio/agents/recovery_coach.py`
- `backend/resilio/core/fatigue.py`
- `backend/resilio/core/conflict.py`
- `.bmad-core/data/*.json` (tables de vérité)
- Tests complets pour chaque agent
- Branches par session

---

## PHASE 4 — WORKFLOWS & API (Session 8-9)

### Session 8 : Workflow d'onboarding + Création de plan

```
/superpowers:brainstorm
```
**Contexte** : "Le workflow utilisateur complet : Étape 1 (brainstorm données user), Étape 2 (analyse profil par agents), Étape 3 (négociation temps/équipements), Étape 4 (création collaborative du plan avec arbitrage Head Coach), Étape 5 (confirmation user). Voir section 3 du blueprint. Ceci doit être exposé comme une API FastAPI avec endpoints conversationnels."

### Session 9 : Boucle de suivi hebdomadaire + API complète

```
/superpowers:brainstorm
```
**Contexte** : "La boucle répétitive : Étape 7 (pull données des apps + commentaires user), Étape 8 (analyse prévu vs réalisé, détection de fatigue), Étape 9 (présentation des changements). Plus les routes FastAPI complètes : auth OAuth, CRUD athletes/plans, endpoint chat streaming, sync API."

**Livrables Phase 4** :
- `backend/resilio/api/routes/` (tous les endpoints)
- `backend/resilio/core/periodization.py`
- `backend/resilio/core/progression.py`
- Workflows d'onboarding et de suivi testés
- Branche `feat/workflows-api`

---

## PHASE 5 — FRONTEND NEXT.JS (Session 10-11-12)

### Session 10 : Setup + Dashboard + Calendrier

```
/superpowers:brainstorm
```
**Contexte** : "Frontend Next.js avec App Router + Tailwind + shadcn/ui. Page principale = dashboard athlète avec calendrier d'entraînement (vue semaine), stats clés (volume, fatigue, progression), et résumé du plan actif. Le calendrier montre chaque workout planifié avec un code couleur par sport."

### Session 11 : Interface de chat + Onboarding

```
/superpowers:brainstorm
```
**Contexte** : "Interface de chat avec le Head Coach (streaming). L'onboarding est conversationnel (pas un formulaire classique). Le chat utilise l'API streaming du backend. L'onboarding guide l'user à travers les étapes 1-3 du workflow."

### Session 12 : Suivi hebdo + Pages détail

```
/superpowers:brainstorm
```
**Contexte** : "Page de suivi hebdomadaire (comparaison prévu vs réalisé, graphiques de progression, zone de commentaires). Pages détail pour les workouts individuels et le plan nutrition du jour. Graphiques avec Recharts."

**Livrables Phase 5** :
- `frontend/` complet avec toutes les pages
- Connexion au backend API
- Branche `feat/frontend`

---

## PHASE 6 — INTÉGRATION & POLISH (Session 13)

```
/superpowers:brainstorm
```
**Contexte** : "Intégration finale : docker-compose pour backend + frontend + DB, tests E2E du workflow complet (onboarding → plan → suivi), edge cases (rate limits API, données manquantes, conflits d'agents), et documentation utilisateur."

**Livrables Phase 6** :
- `docker-compose.yml`
- Tests E2E
- Documentation utilisateur
- README complet
- Tag v1.0.0

---

## RÉSUMÉ DU FLOW PAR SESSION

| Session | Module | Commandes Superpowers |
|---------|--------|----------------------|
| 1 | Setup & CLAUDE.md | brainstorm → write-plan → execute-plan |
| 2 | Schémas & DB | brainstorm → write-plan → execute-plan |
| 3 | Connecteurs Strava + Hevy | brainstorm → write-plan → execute-plan |
| 4 | Connecteurs FatSecret + Health | brainstorm → write-plan → execute-plan |
| 5 | Agent base + Head Coach | brainstorm → write-plan → execute-plan |
| 6 | Running + Lifting Coach | brainstorm → write-plan → execute-plan |
| 7 | Swimming + Biking + Nutrition + Recovery | brainstorm → write-plan → execute-plan |
| 8 | Workflows onboarding + plan | brainstorm → write-plan → execute-plan |
| 9 | Boucle suivi + API | brainstorm → write-plan → execute-plan |
| 10 | Frontend dashboard + calendrier | brainstorm → write-plan → execute-plan |
| 11 | Frontend chat + onboarding | brainstorm → write-plan → execute-plan |
| 12 | Frontend suivi + détails | brainstorm → write-plan → execute-plan |
| 13 | Intégration & polish | brainstorm → write-plan → execute-plan |

---

## CONSEILS IMPORTANTS

### Au début de CHAQUE session
Dis à Claude : "Lis resilio-hybrid-coach-blueprint.md et le CLAUDE.md du projet pour le contexte complet."

### Quand Superpowers te pose des questions
Réponds en référençant les sections du blueprint. Exemple :
- "Pour les règles du Lifting Coach, voir section 5.2 du blueprint"
- "Le score de fatigue est décrit en section 6"

### Si un plan est trop gros
Superpowers peut le découper en batches de ~5 min. Laisse-le faire. Le plan est persisté en fichier .md, donc tu ne perds jamais le contexte entre les batches.

### Après chaque execute-plan
Superpowers te propose : merge, PR, continuer, ou jeter. En général :
- **Merge** si tout est vert et que tu veux passer au module suivant
- **Continuer** si tu veux ajouter des choses au même module
- **PR** si tu veux review plus tard

### Le TDD est ton ami
Superpowers force le cycle RED → GREEN → REFACTOR. Ça veut dire que chaque agent aura des tests avant même d'avoir du code. C'est exactement ce qu'il faut pour un système multi-agents complexe.

### N'oublie pas /revise-claude-md
À la fin de chaque session importante, lance `/revise-claude-md` pour que le CLAUDE.md capture les patterns et décisions découverts pendant la session. Ton CLAUDE.md s'enrichit au fil du projet.
