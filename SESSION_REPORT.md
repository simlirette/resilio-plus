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
