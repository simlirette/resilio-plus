# SESSION S-6 — Frontend Tracking Page

**Date :** 2026-04-12
**Branche :** session/s6-frontend-tracking
**Commits :** 5 (feat × 4 + docs × 1)

## Ce qui a été fait

### 1. api.ts — Types + méthodes ExternalPlan
- `AthleteProfile`, `ExternalPlanOut`, `ExternalSessionOut`
- `ExternalPlanCreate`, `ExternalSessionCreate`, `ExternalSessionUpdate`
- `ExternalPlanDraft` (type stub S-2)
- `api.getAthleteProfile()`, `api.getExternalPlan()`, `api.createExternalPlan()`
- `api.addExternalSession()`, `api.updateExternalSession()`, `api.deleteExternalSession()`
- **STUBS** : `api.importExternalPlan()`, `api.confirmImportExternalPlan()` → mock data

### 2. auth.tsx — coachingMode dans le contexte
- `coachingMode: 'full' | 'tracking_only' | null` ajouté à `AuthState`
- Fetch `GET /athletes/{id}` au chargement et au login
- localStorage key `coaching_mode` pour bootstrap rapide

### 3. top-nav.tsx — Badge mode + lien conditionnel
- Badge `TRACKING` (amber) affiché si `coaching_mode === "tracking_only"`
- Lien "Tracking" → `/tracking` visible uniquement en mode tracking_only

### 4. tracking/page.tsx — Visualisation plan externe
- `ProtectedRoute` + redirect `/dashboard` si `coachingMode !== 'tracking_only'`
- GET `/athletes/{id}/external-plan` → affiche plan + sessions
- Marquage séance : PATCH status=completed / skipped
- Formulaire ajout séance (inline)
- Formulaire création plan si 404

### 5. tracking/import/page.tsx — Wizard import fichier
- Drag & drop / sélection fichier (PDF/TXT/CSV/ICS)
- Étape 1 : upload → `api.importExternalPlan()` (STUB)
- Étape 2 : preview draft (sessions + warnings)
- Étape 3 : confirmation → `api.confirmImportExternalPlan()` (STUB)
- Notice de démo visible dans l'UI

## Invariants
- `npx tsc --noEmit` → ✅ aucune erreur
- `npm run build` → ✅ 19 pages générées (dont /tracking + /tracking/import)

## Stubs S-2 documentés

| Méthode | Endpoint réel | Comportement stub |
|---|---|---|
| `api.importExternalPlan()` | `POST /athletes/{id}/external-plan/import` | Mock draft 3 séances après 800ms |
| `api.confirmImportExternalPlan()` | `POST /athletes/{id}/external-plan/import/confirm` | Mock ExternalPlanOut après 500ms |

Ces stubs seront remplacés quand S-2 sera mergé sur main.

---

# SESSION S-5 — Frontend Check-in + Energy Card

**Date :** 2026-04-12
**Branche :** session/s5-frontend-energy
**Commits :** 2 (feat + docs)

## Ce qui a été fait

### 1. api.ts — Types + méthodes energy
- `CheckInRequest` (5 champs obligatoires + cycle_phase + comment optionnels)
- `ReadinessResponse` (mappage exact du backend V3-C)
- `EnergySnapshotSummary`
- `api.submitCheckin()`, `api.getReadiness()`, `api.getEnergyHistory()`

### 2. check-in/page.tsx — Formulaire 5 questions
- Ancienne version : 2 questions, pas d'appel API réel
- Nouvelle version : 4 questions obligatoires (work_intensity, stress_level, legs_feeling, energy_global) + 1 comment optionnel (140 chars)
- UI progressive : chaque question s'active après la précédente
- Submit : POST `/athletes/{id}/checkin` via `useAuth().athleteId`
- Confirmation : affiche la vraie `ReadinessResponse` (traffic_light, final_readiness, insights, intensity_cap)

### 3. dashboard/page.tsx — EnergyCard
- Chargement parallèle `getReadiness()` + `getWeekStatus()`
- 3 états : loading / pas de check-in (404 → CTA) / chargé (score + dot couleur + 2 insights)

### 4. energy/page.tsx — Vraie API
- Import `mock-data/simon` (inexistant) → supprimé
- Chargement `getReadiness()` + `getEnergyHistory(7)` via `Promise.allSettled()`
- Chart allostatic 7 jours, stat cards readiness + intensity_cap
- États loading / no-check-in / erreur

### 5. energy/cycle/page.tsx — Static data
- Import `mock-data/simon` → remplacé par constantes locales `CYCLE_PHASES` + `PHASE_DESCRIPTIONS`
- Notice démo : cycle J18 lutéale (pas de GET hormonal-profile côté backend)

### 6. login/page.tsx
- Import `mock-data/simon` supprimé
- Auto-login dev supprimé → redirect si token existant

## Invariants
- `npx tsc --noEmit` → ✅ aucune erreur
- `npm run build` → ✅ clean (17 pages)

## Divergences spec → code
| Spec S-5 | Réalité |
|---|---|
| `/checkin` (sans tiret) | Page à `/check-in/` (déjà existante) |
| Lien TopNav "Énergie" | Déjà présent dans top-nav.tsx — aucun changement |
| cycle_phase dans formulaire | Omis — pas de détection du sexe côté frontend |
| HRV chart dans energy/page | Supprimé — EnergySnapshotSummary ne contient pas HRV |

---

# SESSION 0 — Rapport de Consolidation V3

**Date :** 2026-04-12
**Branche :** main
**Durée :** Session de consolidation (doc only, aucun code fonctionnel modifié)

---

## Ce qui a été fait

### 1. Artifacts en attente commités
- `poetry.lock` (dépendances LangGraph ajoutées en v3d)
- `docs/superpowers/plans/2026-04-11-v3d-langgraph-coaching-graph.md` (plan v3d — toutes tâches ✅)

### 2. resilio-master-v3.md créé
Fichier : `resilio-master-v3.md` (racine repo)

Consolidation complète de :
- Architecture 2-volets (Full / Tracking Only) depuis spec 2026-04-11
- AthleteCoachingState réel (avec suffixe _dict — JSON-serializable pour MemorySaver)
- get_agent_view() — 8 agents avec leurs vues autorisées
- 11 nodes LangGraph + topologie complète
- EnergyCycleService + ReadinessResponse
- Pipeline Terra → Energy Coach
- Table complète des endpoints existants (30 endpoints)
- Infrastructure : PostgreSQL sync + 4 migrations Alembic
- État d'implémentation : V3-A → V3-D ✅, V3-E → V3-H ❌

### 3. resilio-master-v2.md archivé
Déplacé vers : `docs/archive/resilio-master-v2_archived_2026-04-12.md`

### 4. CLAUDE.md mis à jour
- Tech stack : SQLite → PostgreSQL + LangGraph
- Référence master : pointe vers `resilio-master-v3.md`
- Phase status : V3-A → V3-D marquées ✅, V3-E → V3-H marquées ❌

---

## Divergences spec → code (à connaître pour les sessions parallèles)

| Spec originale (v3 design) | Réalité du code |
|---|---|
| PostgreSQL async (asyncpg) | PostgreSQL sync (psycopg2) — migration asyncpg = future |
| AthleteCoachingState avec objets ORM | State avec suffixe `_dict` (tout sérialisé en JSON) |
| Terra sync toutes les 4h | Sync toutes les 6h (unifié avec Strava/Hevy) |
| weekly_review graph implémenté | NON implémenté — scope V3-D bis |
| ExternalPlan dans migration 0003 | Tables créées, mais pas de service ni routes |

---

## Backlog Backend Ordonné — 7 Sessions Parallèles

### Démarrage immédiat (pas de dépendances mutuelles)

#### S-1 : ExternalPlan backend — CRUD saisie manuelle
**Périmètre :**
- `ExternalPlanService` : create_plan, add_session, update_session, delete_session, get_active_plan
- Route `POST /athletes/{id}/external-plan` [require_tracking_mode]
- Route `POST /athletes/{id}/external-plan/sessions`
- Route `PATCH /athletes/{id}/external-plan/sessions/{session_id}`
- Route `DELETE /athletes/{id}/external-plan/sessions/{session_id}`
- Règle : un seul plan actif (ExternalPlan OU TrainingPlan, pas les deux)
- TDD obligatoire, invariant ≥ 1243 tests

**Tables déjà créées** (migration 0003) : `external_plans`, `external_sessions` — pas besoin de migration.

#### S-3 : Weekly review graph (5 nodes)
**Périmètre :**
- `backend/app/graphs/weekly_review_graph.py` — StateGraph 5 nodes
- Nodes : `analyze_actual_vs_planned` → `compute_new_acwr` → `update_athlete_state` → [INTERRUPT] `present_review` → `apply_adjustments`
- `CoachingService.weekly_review(athlete_id, db) -> str` (retourne thread_id)
- `CoachingService.resume_review(thread_id, approved, db) -> None`
- Endpoints : `POST /athletes/{id}/plan/review/start` + `POST /athletes/{id}/plan/review/confirm`

#### S-4 : detect_energy_patterns() + challenges proactifs
**Périmètre :**
- `detect_energy_patterns(db)` dans `core/sync_scheduler.py`
- Patterns : jambes lourdes récurrentes ≥3/7j, stress chronique ≥4/7j, divergence persistante ≥3j consécutifs, RED-S signal ≥3j
- Messages stockés dans un champ `head_coach_messages` (JSON) sur AthleteModel ou table dédiée
- Job APScheduler hebdomadaire (tous les lundis matin)
- TDD sur les 4 patterns

#### S-5 : Frontend check-in + energy card dashboard
**Périmètre :**
- `frontend/src/app/checkin/page.tsx` — formulaire 5 questions (< 60s), submit → POST /checkin
- `frontend/src/app/dashboard/page.tsx` — ajouter `EnergyCard` : traffic_light, final_readiness, insights
- `frontend/src/lib/api.ts` — `submitCheckin()`, `getReadiness()`, `getEnergyHistory()`
- TopNav : lien "Énergie"

### Après S-1 terminée

#### S-2 : Import fichier plan externe (Claude Haiku)
**Périmètre :**
- `POST /athletes/{id}/external-plan/import` — multipart (PDF/TXT/CSV/ICS), Claude Haiku parse → retourne `ExternalPlanDraft`
- `POST /athletes/{id}/external-plan/import/confirm` — sauvegarde définitive après review athlète
- `ExternalPlanDraft` : { title, sessions_parsed, sessions[], parse_warnings[] }
- Dépend : `anthropic>=0.25` (vérifier présence dans pyproject.toml)

#### S-6 : Frontend tracking page (Tracking Only)
**Périmètre :**
- `frontend/src/app/tracking/page.tsx` — affiche plan externe actif + sessions
- `frontend/src/app/tracking/import/page.tsx` — upload fichier → preview draft → confirmer
- Routes protégées : affichées uniquement si `coaching_mode === "tracking_only"`
- Dashboard : badge mode en TopNav

### Après S-1 → S-4 terminées

#### S-7 : E2E tests 2-volet + CLAUDE.md final
**Périmètre :**
- `tests/e2e/test_full_mode_workflow.py` — onboarding Full → create_plan → approve → checkin → readiness
- `tests/e2e/test_tracking_only_workflow.py` — onboarding Tracking Only → external-plan CRUD → checkin → readiness
- `tests/e2e/test_mode_switch.py` — Full → switch → Tracking Only (vérifier archivage plan)
- `tests/e2e/test_volet2_standalone.py` — checkin + readiness sans plan actif (Volet 2 seul)
- Mise à jour `CLAUDE.md` : marquer V3-E → V3-H ✅ si tout passe

---

## S-1 — ExternalPlan Backend CRUD (2026-04-12)

**Branche :** `session/s1-external-plan`  
**Statut :** ✅ Terminé

### Ce qui a été fait

| Composant | Fichier | Tests |
|---|---|---|
| Pydantic schemas | `backend/app/schemas/external_plan.py` | — |
| ExternalPlanService | `backend/app/services/external_plan_service.py` | 14 tests unitaires ✅ |
| Routes FastAPI (5 endpoints) | `backend/app/routes/external_plan.py` | 19 tests API ✅ |
| Router enregistré | `backend/app/main.py` (+2 lignes) | — |

**Endpoints livrés :**
- `POST /athletes/{id}/external-plan` [require_tracking_mode]
- `GET /athletes/{id}/external-plan` [require_tracking_mode]
- `POST /athletes/{id}/external-plan/sessions` [require_tracking_mode]
- `PATCH /athletes/{id}/external-plan/sessions/{session_id}` [require_tracking_mode]
- `DELETE /athletes/{id}/external-plan/sessions/{session_id}` [require_tracking_mode]

### Invariants vérifiés

- `pytest tests/` → 1723 passed ≥ 1243 ✅
- 18 failed = pré-existants (test_energy_patterns.py, S-4 hors scope) ✅
- Aucune nouvelle dépendance ajoutée ✅
- Volet 2 indépendant du Volet 1 : ExternalPlanService ne touche pas au coaching graph ✅

### Décisions notables

1. **Hard-delete des sessions** : Les sessions sont de la donnée saisie par l'utilisateur. Le DELETE HTTP supprime physiquement. La règle "jamais effacer" s'applique aux plans (ExternalPlanModel reste en DB avec status="archived"), pas aux séances individuelles.
2. **XOR invariant au niveau service** : `create_plan()` archive toute ExternalPlan active avant d'en créer une nouvelle. Pas de cross-check TrainingPlan nécessaire — ModeGuard garantit l'exclusion mutuelle à la couche HTTP.
3. **GET active plan → 404 si absent** : Sentinel propre pour le frontend (pas d'ambiguïté entre "pas de plan" et "erreur").
4. **source="manual" systématique** : L'import fichier est S-2 scope.

### Dette technique

- Le commit `84413e7` (docs) a accidentellement inclus des fichiers S-3 (`weekly_review_graph.py`, tests weekly_review) présents dans le working tree d'une session parallèle. Ces fichiers sont maintenant sur la branche S-1. Ils ne cassent aucun test mais sont hors-périmètre.
  - **Recommandation** : lors du merge final S-1 → main, utiliser `git cherry-pick` sur les 3 commits de code (0ccc584, 5d6c90b, e90d78a) plutôt que merge direct pour éviter de polluer main avec ces fichiers.

### Suggestions hors-scope (→ SESSION_NOTES)

- **GET /athletes/{id}/external-plan/archived** : liste des plans archivés (utile pour l'historique frontend S-6)
- **PATCH /athletes/{id}/external-plan** : modifier le titre/dates du plan actif sans créer un nouveau plan
- **ExternalSession.actual_duration_min** : champ pour tracker la durée réelle vs planifiée (utile pour la weekly review S-3)

---

## Invariants à respecter dans chaque session

1. `pytest tests/` doit passer (≥ 1243 tests)
2. `npx tsc --noEmit` doit passer (frontend)
3. `poetry install` doit réussir
4. Chaque session produit des commits atomiques fréquents
5. Volet 2 doit fonctionner sans Volet 1 (tester en isolation)
6. `resilio-master-v3.md` fait autorité — toute décision qui s'en écarte doit être documentée

---

## Session S-4 — detect_energy_patterns() + Challenges Proactifs

**Date :** 2026-04-12
**Branche :** `session/s4-energy-patterns`
**Statut :** ✅ Terminé

### Ce qui a été fait

#### Migration 0005 (`alembic/versions/0005_energy_patterns.py`)
- Ajout de `legs_feeling` (String, nullable) et `stress_level` (String, nullable) sur `energy_snapshots`
- Création de la table `head_coach_messages` (id, athlete_id, pattern_type, message, created_at, is_read)
- Downgrade fonctionnel : `DROP TABLE head_coach_messages` + `DROP COLUMN` sur les 2 nouveaux champs

#### HeadCoachMessageModel (`backend/app/models/schemas.py`)
- Nouveau modèle ORM avec relationship → `AthleteModel.head_coach_messages`
- Pattern type : `"heavy_legs"` | `"chronic_stress"` | `"persistent_divergence"` | `"reds_signal"`

#### EnergyCycleService.submit_checkin() (`backend/app/services/energy_cycle_service.py`)
- Persiste maintenant `legs_feeling` et `stress_level` dans `EnergySnapshotModel`

#### detect_energy_patterns(db) (`backend/app/core/sync_scheduler.py`)
- 4 fonctions détecteur pures (testables sans DB) :
  - `_detect_heavy_legs` — `legs_feeling in ("heavy","dead")` ≥3/7j
  - `_detect_chronic_stress` — `stress_level == "significant"` ≥4/7j
  - `_detect_persistent_divergence` — divergence >30pts sur ≥3j consécutifs
  - `_detect_reds_signal` — `energy_availability < 30.0` ≥3/7j
- Gestion timezone SQLite/PostgreSQL : `_last_7_days()` compare naive vs aware
- Déduplication : pas de message créé si même `pattern_type` dans les 7 derniers jours
- Retourne `{"athletes_scanned": N, "messages_created": M}`

#### APScheduler weekly job
- `run_energy_patterns_weekly()` wrapper avec `SessionLocal()` + error handling
- Job `energy_patterns_weekly` : `trigger="cron"`, `day_of_week="mon"`, `hour=6`, `misfire_grace_time=3600`
- Test existant `test_setup_scheduler_all_jobs_every_6h` corrigé pour ignorer les CronTrigger

### Décision architecturale documentée : table dédiée vs champ JSON

**Choix : table `head_coach_messages`**

**Justification :** les messages sont une donnée time-series (un message par pattern par semaine par athlète). Un champ JSON sur AthleteModel grandirait sans borne, sans métadonnées par message (lu/non lu, pattern_type, created_at), et sans capacité de requête. La table dédiée est cohérente avec `energy_snapshots` et `allostatic_entries` qui suivent le même pattern.

### Tests ajoutés
- `tests/backend/core/test_energy_patterns.py` — **22 tests TDD** couvrant :
  - ORM colonnes + table existence (4 tests)
  - submit_checkin() persistance (2 tests)
  - 4 pattern detectors × 2-3 cas chacun (9 tests)
  - detect_energy_patterns() intégration + déduplication (5 tests)
  - APScheduler job (2 tests)
- `tests/backend/core/test_sync_scheduler.py` — fix `test_setup_scheduler_all_jobs_every_6h`

### Invariants vérifiés
- `pytest tests/` : **1741 passed, 9 skipped** ✅ (≥ 1243)
- Branche : `session/s4-energy-patterns` poussée ✅

---

# SESSION S-3 — Weekly Review Graph

**Date :** 2026-04-12
**Branche :** session/s3-weekly-review
**Commit :** 2ed803f

## Ce qui a été fait

### 1. `backend/app/graphs/weekly_review_graph.py` — nouveau fichier

StateGraph 5 nodes avec MemorySaver, `interrupt_before=["present_review"]`.

**Pipeline :**
```
analyze_actual_vs_planned → compute_new_acwr → update_athlete_state
  → [INTERRUPT] present_review → apply_adjustments → END
```

- Node 1 : compare SessionLog réels vs weekly_slots_json du plan
- Node 2 : recompute ACWR depuis load_history via `core.acwr.compute_acwr`
- Node 3 : assemble review_summary_dict (readiness + recommandations)
- Node 4 : no-op — déclenche l'interrupt (human-in-the-loop)
- Node 5 : persiste `WeeklyReviewModel` en DB si `human_approved=True`

Pattern importlib (`app.models.schemas` + `app.db.models`) pour éviter la double-registration SQLAlchemy — identique à `nodes.py`.

### 2. `backend/app/services/coaching_service.py` — ajouts en fin de fichier

- `weekly_review(athlete_id, db) -> tuple[str, dict | None]`
- `resume_review(thread_id, approved, db) -> None`
- `_review_graphs: dict` — stocke les instances graph per thread_id

### 3. `backend/app/routes/workflow.py` — ajouts en fin de fichier

- `POST /athletes/{id}/plan/review/start` → `ReviewStartResponse`
- `POST /athletes/{id}/plan/review/confirm` → `ReviewConfirmResponse`
- Protégé par `_require_own`, vérifie `_validate_thread_ownership`

### 4. Tests — 23 nouveaux, tous verts

- `tests/backend/graphs/test_weekly_review_graph.py` (15 tests)
- `tests/backend/api/test_weekly_review_endpoints.py` (8 tests)

## Invariants

| Invariant | Résultat |
|---|---|
| `pytest tests/` ≥ 1243 | ✅ 1748 passing (16 fails = S-4 pre-existants) |
| Aucun code existant supprimé | ✅ |
| Human-in-the-loop non négociable | ✅ interrupt_before=["present_review"] |
| MemorySaver pattern identique à coaching_graph | ✅ |

## Divergences spec → code

| Spec | Code | Raison |
|---|---|---|
| `weekly_review(athlete_id, db) -> str` | retourne `tuple[str, dict \| None]` | Plus utile de retourner aussi le summary pour l'endpoint |
| thread_id dans path `/confirm/{thread_id}` | thread_id dans le body | Cohérent avec le pattern approve/revise existant dans workflow.py |
