# PLAN D'EXÉCUTION — Sessions Parallèles Post-Phase 9
# Resilio+ V2 → V3

> **Prérequis :** Phase 9 terminée, committée et pushée sur `main`.
> **Règle absolue :** Chaque session travaille sur sa propre branche. 
> Ne jamais travailler directement sur `main`.
> **Supervision recommandée :** Maximum 2 sessions simultanées si c'est ta première fois.

---

## VUE D'ENSEMBLE — Ordre d'exécution

```
PHASE 9 TERMINÉE
       │
       ▼
┌─────────────────────────────────────────┐
│  VAGUE 1 — Lancer simultanément         │
│  Session A : Phase 10 (agents+workflow) │
│  Session B : Phase 11 (data+routes)     │
└─────────────────┬───────────────────────┘
                  │ Merger les 2 branches dans main
                  ▼
┌─────────────────────────────────────────┐
│  V2 COMPLÈTE — Créer branche v3         │
│  Lancer simultanément :                 │
│  Session C : V3-AthleteState (base)     │  ← Finir en PREMIER
└─────────────────┬───────────────────────┘
                  │ Merger v3-athletestate dans v3
                  ▼
┌──────────────────────────────────────────────────────┐
│  VAGUE 2 — Lancer simultanément (3 sessions)         │
│  Session D : V3-Energy Coach                         │
│  Session E : V3-Hormonal + EA + Allostatic           │
│  Session F : V3-Knowledge Files JSON                 │
└──────────────────────────┬───────────────────────────┘
                           │ Merger les 3 dans v3
                           ▼
┌──────────────────────────────────────────────────────┐
│  VAGUE 3 — Lancer simultanément (2 sessions)         │
│  Session G : V3-Recovery Coach étendu                │
│  Session H : V3-Frontend (dashboard + énergie)       │
└──────────────────────────┬───────────────────────────┘
                           │ Merger dans v3 → merger v3 dans main
                           ▼
                    V3 COMPLÈTE ✅
```

---

## FICHIERS PAR SESSION — Référence rapide anti-conflit

| Session | Branche | Fichiers EXCLUSIFS — ne pas toucher ailleurs |
|---------|---------|---------------------------------------------|
| A | `feat/phase10` | `backend/app/agents/`, `backend/app/core/` (acwr, periodization, conflict, readiness), `tests/test_agents/`, `tests/test_core/` |
| B | `feat/phase11` | `backend/app/routes/food.py`, `backend/app/routes/workflow.py`, `data/*.json` (7 fichiers V2), `tests/test_routes/` |
| C | `v3-athletestate` | `backend/app/models/athlete_state.py`, `alembic/versions/` (nouvelle migration), `tests/test_models/` |
| D | `v3-energy-coach` | `backend/app/agents/energy_coach/`, `backend/app/core/allostatic.py`, `backend/app/core/energy_availability.py`, `tests/v3/test_energy_coach.py` |
| E | `v3-hormonal-ea` | `backend/app/core/hormonal.py`, `backend/app/agents/*/` (patches ajustements cycle uniquement), `tests/v3/test_hormonal.py`, `tests/v3/test_ea.py` |
| F | `v3-knowledge` | `data/allostatic_weights.json`, `data/hormonal_adjustments.json`, `data/ea_thresholds.json`, `data/energy_coach_check_in_schema.json` |
| G | `v3-recovery-v3` | `backend/app/agents/recovery_coach/` uniquement, `tests/v3/test_recovery_coach_v3.py` |
| H | `v3-frontend` | `frontend/` entier, `tests/test_frontend/` |

---

## SESSION A — Phase 10 : Agents + Workflow

**Terminal :** `Terminal 1`
**Branche :** `feat/phase10`

### Commandes d'ouverture
```bash
cd C:\Users\simon\resilio-plus
git checkout main
git pull origin main
git checkout -b feat/phase10
claude
```

### Prompt à envoyer dans Claude Code
```
Lis dans l'ordre :
1. CLAUDE.md
2. resilio-master-v2.md
3. docs/superpowers/plans/2026-04-10-phase10-*.md

Tu travailles sur la branche feat/phase10.

FICHIERS AUTORISÉS — tu ne touches QU'À CES FICHIERS :
- backend/app/agents/ (tous les agents)
- backend/app/core/acwr.py, periodization.py, conflict.py, 
  readiness.py, goal_analysis.py
- tests/test_agents/
- tests/test_core/

FICHIERS INTERDITS — ne pas toucher :
- backend/app/routes/
- backend/app/models/
- backend/app/db/
- data/
- frontend/
- alembic/

Objectif de cette session :
- Intégration complète des agents avec la logique core
- Workflow end-to-end : onboarding → plan → suivi hebdomadaire
- Tous les tests agents passent

Confirme que tu as lu les documents, vérifie l'état actuel 
des agents, et propose ton plan avant de commencer.
```

---

## SESSION B — Phase 11 : Data Files + Routes

**Terminal :** `Terminal 2`
**Branche :** `feat/phase11`

### Commandes d'ouverture
```bash
cd C:\Users\simon\resilio-plus
git checkout main
git pull origin main
git checkout -b feat/phase11
claude
```

### Prompt à envoyer dans Claude Code
```
Lis dans l'ordre :
1. CLAUDE.md
2. resilio-master-v2.md
3. docs/superpowers/plans/2026-04-10-phase11-*.md

Tu travailles sur la branche feat/phase11.

FICHIERS AUTORISÉS — tu ne touches QU'À CES FICHIERS :
- backend/app/routes/food.py (créer)
- backend/app/routes/workflow.py (créer)
- data/vdot_paces.json
- data/volume_landmarks.json
- data/muscle_overlap.json
- data/agent_view_map.json
- data/nutrition_targets.json
- data/running_zones.json
- data/food_database_cache.json
- tests/test_routes/test_food.py
- tests/test_routes/test_workflow.py

FICHIERS INTERDITS — ne pas toucher :
- backend/app/agents/
- backend/app/core/
- backend/app/models/
- frontend/
- alembic/

Objectif de cette session :
- S'assurer que les 7 fichiers JSON data/ sont complets 
  et conformes à resilio-master-v2.md
- Créer les routes food.py et workflow.py manquantes
- Tests pour les nouvelles routes

Confirme que tu as lu les documents et propose ton plan 
avant de commencer.
```

---

## ⚠️ CHECKPOINT V2 — Avant de lancer la Vague 2

Avant de continuer, exécuter dans le terminal principal :

```bash
cd C:\Users\simon\resilio-plus
git checkout main
git merge feat/phase10 --no-ff -m "feat: phase 10 - agents and workflow integration"
git merge feat/phase11 --no-ff -m "feat: phase 11 - data files and routes"
git push origin main

# Vérifier que tous les tests passent
cd backend && python -m pytest tests/ -v
```

Si tous les tests passent → créer la branche V3 base :

```bash
git checkout -b v3
git push origin v3
```

---

## SESSION C — V3 AthleteState (À FINIR AVANT D ET E)

**Terminal :** `Terminal 1`
**Branche :** `v3-athletestate` (depuis `v3`)

### Commandes d'ouverture
```bash
cd C:\Users\simon\resilio-plus
git checkout v3
git pull origin v3
git checkout -b v3-athletestate
claude
```

### Prompt à envoyer dans Claude Code
```
Lis dans l'ordre :
1. CLAUDE.md
2. resilio-master-v2.md
3. docs/resilio-v3-master.md — sections 3 et 7 en priorité

Tu travailles sur la branche v3-athletestate.
Cette session BLOQUE les sessions D et E — elle doit 
être terminée et mergée en premier.

FICHIERS AUTORISÉS — tu ne touches QU'À CES FICHIERS :
- backend/app/models/athlete_state.py (ajouter champs V3)
- alembic/versions/ (nouvelle migration V3)
- backend/app/models/schemas.py (nouveaux schémas Pydantic)
- tests/test_models/test_athlete_state_v3.py (créer)

FICHIERS INTERDITS — ne pas toucher :
- backend/app/agents/
- backend/app/core/
- backend/app/routes/
- data/
- frontend/

Objectif de cette session :
Ajouter ces nouveaux champs à AthleteState (section 7 du v3-master) :
- EnergySnapshot (Pydantic model complet)
- HormonalProfile (Pydantic model complet)
- AllostaticEntry (Pydantic model complet)
- RecoveryVetoV3 (Pydantic model complet)
- Mettre à jour get_agent_view() avec les nouvelles vues
- Migration Alembic pour les nouveaux champs
- Tests unitaires pour tous les nouveaux modèles

Quand terminé, dis-le moi — je vais merger dans v3 
avant de lancer les sessions D et E.
```

---

## ⚠️ CHECKPOINT V3-1 — Merger AthleteState avant Vague 2

```bash
cd C:\Users\simon\resilio-plus
git checkout v3
git merge v3-athletestate --no-ff -m "feat(v3): AthleteState V3 - EnergySnapshot, HormonalProfile, AllostaticEntry"
git push origin v3

# Vérifier les tests
cd backend && python -m pytest tests/test_models/ -v
```

Si tests OK → lancer Sessions D, E, F simultanément.

---

## SESSION D — V3 Energy Coach

**Terminal :** `Terminal 1`
**Branche :** `v3-energy-coach` (depuis `v3`)

### Commandes d'ouverture
```bash
cd C:\Users\simon\resilio-plus
git checkout v3
git pull origin v3
git checkout -b v3-energy-coach
claude
```

### Prompt à envoyer dans Claude Code
```
Lis dans l'ordre :
1. CLAUDE.md
2. docs/resilio-v3-master.md — section 3 (Energy Coach)
3. .bmad-core/agents/energy-coach.agent.md (system prompt)

Tu travailles sur la branche v3-energy-coach.

FICHIERS AUTORISÉS — tu ne touches QU'À CES FICHIERS :
- backend/app/agents/energy_coach/ (créer dossier complet)
  - __init__.py
  - agent.py
  - prescriber.py (EnergySnapshot builder)
- backend/app/core/allostatic.py (créer)
- backend/app/core/energy_availability.py (créer)
- tests/v3/test_energy_coach.py (créer)
- tests/v3/test_allostatic.py (créer)

FICHIERS INTERDITS — ne pas toucher :
- backend/app/agents/recovery_coach/ (Session G)
- backend/app/agents/head_coach/
- backend/app/agents/running_coach/
- backend/app/agents/lifting_coach/
- backend/app/core/hormonal.py (Session E)
- data/ (Session F)
- frontend/

Les modèles Pydantic (EnergySnapshot, HormonalProfile) 
sont déjà définis dans models/athlete_state.py — utilise-les,
ne les redéfinis pas.

Les seuils allostatic sont dans data/allostatic_weights.json 
et data/ea_thresholds.json — lis ces fichiers pour tes calculs.

Objectif :
- Energy Coach agent complet avec 5 skills (section 3.4 du v3-master)
- calculate_allostatic_score() conforme à la formule section 5.2
- calculate_energy_availability() conforme section 6.1
- Output : EnergySnapshot structuré exact (section 3.2)
- Tests : score allostatic, EA, cas limites RED-S

Confirme que tu as lu les documents et propose ton plan.
```

---

## SESSION E — V3 Cycle Hormonal + EA + Recovery étendu (logique)

**Terminal :** `Terminal 2`
**Branche :** `v3-hormonal-ea` (depuis `v3`)

### Commandes d'ouverture
```bash
cd C:\Users\simon\resilio-plus
git checkout v3
git pull origin v3
git checkout -b v3-hormonal-ea
claude
```

### Prompt à envoyer dans Claude Code
```
Lis dans l'ordre :
1. CLAUDE.md
2. docs/resilio-v3-master.md — sections 4 et 6
3. docs/v3-knowledge-files-specs.md

Tu travailles sur la branche v3-hormonal-ea.

FICHIERS AUTORISÉS — tu ne touches QU'À CES FICHIERS :
- backend/app/core/hormonal.py (créer)
- backend/app/core/energy_availability.py 
  ATTENTION : Si Session D l'a déjà créé, ajoute seulement
  la logique RED-S et les alertes. Ne pas réécrire le calcul EA.
- backend/app/agents/lifting_coach/agent.py 
  (ajouter UNIQUEMENT les ajustements par phase cycle)
- backend/app/agents/running_coach/agent.py 
  (ajouter UNIQUEMENT les ajustements par phase cycle)
- backend/app/agents/nutrition_coach/agent.py 
  (ajouter UNIQUEMENT les ajustements nutritionnels par phase)
- tests/v3/test_hormonal.py (créer)
- tests/v3/test_ea_reds.py (créer)

FICHIERS INTERDITS — ne pas toucher :
- backend/app/agents/energy_coach/ (Session D)
- backend/app/agents/recovery_coach/ (Session G)
- backend/app/core/allostatic.py (Session D)
- data/ (Session F)
- frontend/
- alembic/

Les règles par phase sont dans data/hormonal_adjustments.json
Les seuils EA sont dans data/ea_thresholds.json

Objectif :
- hormonal.py : logique de détection de phase, calcul du 
  cycle day, ajustements par phase (section 4.2 du v3-master)
- Patches dans lifting_coach, running_coach, nutrition_coach :
  lire la phase du cycle dans AthleteState et appliquer les 
  ajustements du fichier hormonal_adjustments.json
- RED-S detection : 3 jours consécutifs EA < seuil → flag
- Tests pour chaque phase et cas limites

Confirme que tu as lu les documents et propose ton plan.
```

---

## SESSION F — V3 Knowledge Files JSON

**Terminal :** `Terminal 3`
**Branche :** `v3-knowledge` (depuis `v3`)

### Commandes d'ouverture
```bash
cd C:\Users\simon\resilio-plus
git checkout v3
git pull origin v3
git checkout -b v3-knowledge
claude
```

### Prompt à envoyer dans Claude Code
```
Lis dans l'ordre :
1. CLAUDE.md
2. docs/v3-knowledge-files-specs.md — document complet

Tu travailles sur la branche v3-knowledge.
Cette session ne touche QU'AUX FICHIERS DATA.

FICHIERS AUTORISÉS — tu ne touches QU'À CES FICHIERS :
- data/allostatic_weights.json (créer)
- data/hormonal_adjustments.json (créer)
- data/ea_thresholds.json (créer)
- data/energy_coach_check_in_schema.json (créer)

FICHIERS INTERDITS — ne pas toucher :
- backend/ (tout)
- frontend/ (tout)
- alembic/ (tout)
- CLAUDE.md
- Les 7 fichiers JSON V2 existants dans data/

Les specs exactes (structure JSON, valeurs, sources) sont 
dans docs/v3-knowledge-files-specs.md.

Objectif :
Créer les 4 fichiers JSON exactement selon les specs.
Chaque fichier doit inclure :
- version: "1.0"
- Toutes les valeurs définies dans les specs
- sources: [] avec les références scientifiques

Aucun test requis pour cette session — les tests 
sont dans les sessions D et E qui lisent ces fichiers.

Commence directement. C'est une session courte (~1h).
```

---

## ⚠️ CHECKPOINT V3-2 — Merger Vague 2

```bash
cd C:\Users\simon\resilio-plus
git checkout v3

# Merger dans l'ordre
git merge v3-knowledge --no-ff -m "feat(v3): knowledge files - allostatic, hormonal, EA, check-in"
git merge v3-energy-coach --no-ff -m "feat(v3): Energy Coach agent + allostatic + EA calculation"
git merge v3-hormonal-ea --no-ff -m "feat(v3): hormonal cycle integration + RED-S detection"

git push origin v3

# Tests complets
cd backend && python -m pytest tests/v3/ -v
```

Si tests OK → lancer Sessions G et H simultanément.

---

## SESSION G — V3 Recovery Coach étendu

**Terminal :** `Terminal 1`
**Branche :** `v3-recovery-coach` (depuis `v3`)

### Commandes d'ouverture
```bash
cd C:\Users\simon\resilio-plus
git checkout v3
git pull origin v3
git checkout -b v3-recovery-coach
claude
```

### Prompt à envoyer dans Claude Code
```
Lis dans l'ordre :
1. CLAUDE.md
2. docs/resilio-v3-master.md — sections 2.2 et 6

Tu travailles sur la branche v3-recovery-coach.

FICHIERS AUTORISÉS — tu ne touches QU'À CES FICHIERS :
- backend/app/agents/recovery_coach/agent.py
- backend/app/agents/recovery_coach/prescriber.py
- tests/v3/test_recovery_coach_v3.py (créer)

FICHIERS INTERDITS — ne pas toucher :
- backend/app/agents/energy_coach/ (terminé)
- backend/app/core/ (terminé)
- data/ (terminé)
- frontend/ (Session H)
- alembic/

Les modèles RecoveryVetoV3 sont dans models/athlete_state.py.
L'EnergySnapshot est produit par l'Energy Coach et disponible 
dans AthleteState.energy_snapshot — lis-le, ne le recalcule pas.
Les seuils EA sont dans data/ea_thresholds.json.
Les ajustements cycle sont dans data/hormonal_adjustments.json.

Objectif :
Étendre le Recovery Coach pour que son veto intègre 5 composantes
(section 2.2 du v3-master) :
- hrv_component (existant V2)
- acwr_component (existant V2)
- ea_component (nouveau V3 — lire energy_snapshot.ea_status)
- allostatic_component (nouveau V3 — lire energy_snapshot.allostatic_score)
- cycle_component (nouveau V3 — lire hormonal_profile.current_phase)

La pire composante détermine le cap final.
Output : RecoveryVetoV3 complet avec toutes les composantes.

Tests : veto vert/jaune/rouge pour chaque combinaison 
de composantes, cas limite EA critique.

Confirme que tu as lu les documents et propose ton plan.
```

---

## SESSION H — V3 Frontend

**Terminal :** `Terminal 2`
**Branche :** `v3-frontend` (depuis `v3`)

### Commandes d'ouverture
```bash
cd C:\Users\simon\resilio-plus
git checkout v3
git pull origin v3
git checkout -b v3-frontend
claude
```

### Prompt à envoyer dans Claude Code
```
Lis dans l'ordre :
1. CLAUDE.md
2. docs/resilio-v3-master.md — section 9 (session V3-7)

Tu travailles sur la branche v3-frontend.
Tu touches UNIQUEMENT au frontend — aucun fichier backend.

FICHIERS AUTORISÉS — tu ne touches QU'À CES FICHIERS :
- frontend/ (entier)
- tests/test_frontend/ (si existant)

FICHIERS INTERDITS — ne pas toucher :
- backend/ (tout)
- data/ (tout)
- alembic/ (tout)
- CLAUDE.md

DIRECTION UI :
- Style : Sobre, clinique, pro-athlete. Inspiré de Whoop + 
  TrainingPeaks. Dark mode par défaut.
- Stack : Next.js App Router + Tailwind + shadcn/ui (déjà installé)
- Données : Utilise des mock data réalistes pour Simon 
  (athlète hybride : course + musculation + vélo) — 
  on branche l'API après que le design est validé

NOUVELLES PAGES V3 à créer :
1. /energy — Dashboard énergie quotidien
   - Allostatic Score (gauge 0-100 avec zones couleur)
   - Energy Availability (kcal/kg FFM vs seuil)
   - HRV + sommeil du jour
   - Historique 7 jours (line chart)

2. /check-in — Check-in quotidien
   - 2-3 questions max (journée de travail, stress)
   - Si profil hormonal activé : question phase cycle
   - Durée estimée affichée : "~30 secondes"
   - Confirmation visuelle après soumission

3. /energy/cycle — Vue cycle hormonal (si profil activé)
   - Calendrier du cycle avec phases colorées
   - Phase actuelle mise en évidence
   - Ajustements actifs du jour (ex: "RPE cible -1 aujourd'hui")

PAGES V2 EXISTANTES à polisher :
- Audit visuel de toutes les pages existantes
- Appliquer le design system cohérent
- S'assurer que mobile (375px) est correct

Commence par créer un fichier frontend/mock-data/simon.ts 
avec des données réalistes, puis construis les pages 
dans l'ordre ci-dessus.

Confirme que tu as lu les documents et commence.
```

---

## ⚠️ CHECKPOINT FINAL — Merger tout dans v3 puis main

```bash
cd C:\Users\simon\resilio-plus
git checkout v3

git merge v3-recovery-coach --no-ff -m "feat(v3): Recovery Coach V3 - 5-component veto"
git merge v3-frontend --no-ff -m "feat(v3): Frontend V3 - energy dashboard, check-in, cycle view"

git push origin v3

# Tests E2E complets
cd backend && python -m pytest tests/ -v

# Si tout est vert
git checkout main
git merge v3 --no-ff -m "release: V3 complete - Energy Coach, hormonal cycle, allostatic load"
git push origin main
```

---

## RÉSUMÉ VISUEL — Qui fait quoi

```
Phase 9 terminée
      │
      ├── Terminal 1 : Session A (Phase 10 — agents/core)
      └── Terminal 2 : Session B (Phase 11 — data/routes)
                │
          Merger dans main
                │
      └── Terminal 1 : Session C (V3 AthleteState) ← SEUL, finir avant la suite
                │
          Merger dans v3
                │
      ├── Terminal 1 : Session D (Energy Coach)
      ├── Terminal 2 : Session E (Hormonal + EA)
      └── Terminal 3 : Session F (JSON files)
                │
          Merger dans v3
                │
      ├── Terminal 1 : Session G (Recovery Coach V3)
      └── Terminal 2 : Session H (Frontend V3)
                │
          Merger dans v3 → merger dans main
                │
            V3 COMPLÈTE ✅
```
