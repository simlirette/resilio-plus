# Review Vague 3 — Rapport

Date : 2026-04-12
Reviewer : Claude Code (automated)
Branche analysée : session/s7-e2e-finalisation
Statut de la branche : déjà mergée sur main (via `d0df1a0 Merge branch 'session/s7-e2e-finalisation'`)

---

## Verdict : ACCEPT (avec réserves documentées)

---

## Justification

Le périmètre de S-7 est livré en 3 commits propres et atomiques :

1. `4081e8c` — 4 fichiers E2E, 33 nouveaux tests, tous passants
2. `ad6cd91` — Remplacement des stubs S-2 dans `api.ts` (multipart FormData + JSON confirm)
3. `ca4de12` — Mise à jour CLAUDE.md + resilio-master-v3.md + SESSION_REPORT.md

### Vérifications critiques — résultats

| Critère | Résultat |
|---|---|
| 4 fichiers tests/e2e/ présents | ✅ test_full_mode_workflow.py, test_tracking_only_workflow.py, test_mode_switch.py, test_volet2_standalone.py |
| `poetry run pytest tests/e2e/ -v` | ✅ **104 passed** (33 nouveaux + 71 existants) |
| `poetry run pytest --collect-only -q` | ✅ **1854 tests collectés** (≥ 1825 demandé) |
| `npx tsc --noEmit` | ✅ silencieux |
| CLAUDE.md V3-E→V3-H marquées ✅ | ✅ sections correctement mises à jour |
| resilio-master-v3.md cohérent | ✅ section 11 "NON IMPLÉMENTÉ" vidée, section 12 sessions ✅ |
| BACKEND_V3_COMPLETE.md présent | ❌ absent sur cette branche (ajouté dans S-7b post-merge) |
| Aucun fichier docs/ supprimé | ✅ aucune suppression |

---

## Analyse des 4 scénarios E2E

### test_full_mode_workflow.py (7 tests)
Couvre le happy path complet en mode `full` : onboarding → checkin → readiness → create-plan (CoachingService mocké) → approve. Fixtures réalistes (dates dynamiques, VDOT cohérent). La dépendance `patch("app.routes.workflow.CoachingService")` dans test_05 et test_06 est un compromis acceptable — le LangGraph est coûteux à invoquer en E2E ; le mock valide la plomberie HTTP sans tester l'orchestration interne (déjà couverte par les tests backend dédiés).

### test_tracking_only_workflow.py (9 tests)
Couvre le flux complet tracking_only : onboarding → 403 sur create-plan → ExternalPlan CRUD complet (create/get/add-session/update-session/delete-session) → checkin → readiness. Valide ModeGuard et la séparation des deux volets. Fixtures correctes, assertions sur `source="manual"`, `status="active"`, `sessions=[]`.

### test_mode_switch.py (9 tests)
Couvre le switch bidirectionnel full ↔ tracking_only. Valide :
- Plans archivés (status=archived) après switch → tracking_only
- `create-plan` bloqué (403) en tracking_only
- `external-plan` bloqué (403) au retour en full
- Volet 2 (checkin) non bloqué dans les deux modes
Couverture complète du comportement documenté dans resilio-master-v3.md.

### test_volet2_standalone.py (8 tests)
Valide que le Volet 2 (Energy Cycle) opère sans aucune interaction avec le Volet 1 (coaching_graph). Couvre : checkin sans plan → readiness 404 avant checkin → readiness 200 après → 409 si double checkin → history → mode switch ne bloque pas readiness.

**Réserve technique** : le fichier ne contient **aucun mock strict du coaching_graph**. Le SESSION_PLAN annonçait un `patch("app.graphs.coaching_graph")` avec assertion `call_count == 0` pour prouver formellement qu'aucun appel LangGraph n'a lieu lors des opérations Volet 2. Cette preuve formelle est absente. L'invariant de modularité est prouvé par absence d'erreur (les endpoints Volet 2 fonctionnent sans plan actif), mais pas par assertion explicite d'isolation. Ce point a été partiellement adressé dans S-7b (`be76271 test(s7): enhance E2E tests with architectural invariants`).

---

## Respect du périmètre

### Modifications autorisées — conformes
- `tests/e2e/` : 4 nouveaux fichiers — scope S-7 ✅
- `CLAUDE.md` : uniquement les sections "V3-E/V3-G/V3-H ❌ → ✅" et compteur tests/e2e — ✅
- `resilio-master-v3.md` : sections 11 et 12 — ✅
- `SESSION_REPORT.md` : ajout section S-7 en tête — ✅
- `frontend/src/lib/api.ts` : remplacement stubs S-2 — scope S-7 ✅
- `frontend/src/app/tracking/import/page.tsx` : suppression notice demo — ✅

### Hors-périmètre — aucune pollution détectée ✅
Aucun fichier de production backend modifié. Aucun fichier `docs/` supprimé. Aucune dépendance ajoutée.

---

## Dette technique adressée depuis REVIEW_VAGUE1 + REVIEW_VAGUE2

| Item dette | Source | Statut S-7 |
|---|---|---|
| CRITIQUE: cherry-pick S-1/S-3 artifacts | REVIEW_VAGUE1 | ✅ Résolu par ordre de merge (branches mergées séparément) |
| IMPORTANT: documenter exception hard-delete | REVIEW_VAGUE1 | ✅ Résolu — resilio-master-v3.md:567 "Exception approuvée (S-1)" |
| CRITIQUE: poetry.lock manquant S-2 | REVIEW_VAGUE2 | ✅ Résolu — commit `3d3b457 fix(s2): commit poetry.lock` |
| IMPORTANT: ExternalPlanDraftSession.session_date nullable | REVIEW_VAGUE2 | ✅ Résolu dans S-7 — `ExternalPlanDraftSession.session_date: string | null` + `formatDate(iso: string | null)` |

---

## Dette technique restante (non résolue ou nouvelle)

### Héritée — non adressée par S-7

1. **SESSION_REPORT.md incomplet** : les sections S-1, S-2, et S-4 sont absentes de `SESSION_REPORT.md`. Ces sessions ont été mergées sur main mais leurs rapports n'ont pas été accumulés (conflit de merge non résolu lors des merges parallèles). Le fichier contient S-3, S-5, S-6, S-7 + Session 0, mais pas S-1, S-2, S-4. Accepté pour MVP — l'historique complet est reconstituable via `git log` — mais crée une incohérence documentaire.

2. **`head_coach_messages` non exposés** : absence de `GET /head-coach-messages`. Reporté depuis S-7, toujours ouvert.

3. **Singleton `_review_service`** : dans `workflow.py`, incompatible multi-worker production. Reporté depuis S-7, toujours ouvert.

4. **`energy/cycle/page.tsx` cycle menstruel** : codé en dur (démo), non connecté au backend. Reporté depuis S-7, toujours ouvert.

5. **Pas de `GET /external-plan/archived`** : reporté depuis REVIEW_VAGUE1, toujours ouvert.

### Nouvelle dette introduite par S-7

6. **Invariant modularité non prouvé formellement** : `test_volet2_standalone.py` ne contient pas de mock strict de `coaching_graph`. L'isolation LangGraph en Volet 2 est démontrée empiriquement mais pas par assertion (`assert coaching_graph.call_count == 0`). Partiellement mitigé par S-7b.

7. **`importExternalPlan` expose le token JWT** en clair depuis `localStorage` dans `api.ts:305` (pattern `localStorage.getItem('token')`). Cohérent avec le reste de l'app (même pattern que `request()`), mais l'implémentation manuelle du fetch multipart duplique la logique d'auth au lieu de réutiliser `request()`. Ce n'est pas un bug, mais une incohérence architecturale mineure.

---

## BACKEND_V3_COMPLETE.md — Note

Ce fichier est **absent sur la branche `session/s7-e2e-finalisation`**. Il a été créé dans la session complémentaire S-7b (`a3c4b1e`, branche `session/s7b-finalisation-complete`) et est présent sur `main`. Les 7 sessions y sont consolidées avec leurs commits de merge, conformément à l'état réel du git log. Le document est cohérent avec l'historique `git log --merges`.

---

## État global du backend post-merge

### Ce qui est réellement complet ✅
- Architecture 2-volets opérationnelle : ModeGuard (V3-B), ExternalPlan CRUD (S-1), import Haiku (S-2), weekly review graph (S-3), Energy Cycle complet (V3-C + S-4), mode switch avec archivage (V3-B)
- 35 tests E2E (33 S-7 + 2 invariants S-7b) sur 1854 collectés
- TypeScript propre (tsc --noEmit clean)
- PostgreSQL + Alembic (4 migrations + migration 0005)
- LangGraph CoachingService avec human-in-the-loop

### Ce qui n'est PAS complet (limitations réelles)
- **Pas de test LangGraph en conditions réelles** : les tests `create-plan` et `approve` E2E utilisent `patch("app.routes.workflow.CoachingService")`. LangGraph est testé unitairement (tests backend dédiés) mais pas dans une session E2E end-to-end réelle (nécessiterait un modèle LLM en test, coûteux).
- **Singleton production** : `_review_service` non safe pour déploiement multi-worker.
- **Pas d'endpoint `head_coach_messages`** : les messages du Head Coach ne sont pas exposés via API.

### Verdict technique
Le backend V3 est **complet pour un MVP single-instance**. Les limitations ci-dessus sont documentées et ne bloquent pas un déploiement développement/staging.

---

## Prêt pour frontend desktop/mobile

**Oui, avec conditions** :

| Condition | Statut |
|---|---|
| API ExternalPlan (CRUD + import + confirm) | ✅ Opérationnelle |
| API Energy Cycle (checkin + readiness + history) | ✅ Opérationnelle |
| API coaching workflow (create-plan + approve + weekly review) | ✅ Opérationnelle |
| Mode switch PATCH /mode | ✅ Opérationnel |
| TypeScript types alignés backend/frontend | ✅ (ExternalPlanDraftSession.session_date nullable corrigé) |
| Auth JWT stable | ✅ |
| Stubs frontend remplacés par vrais endpoints | ✅ (ad6cd91) |

**Conditions à respecter avant déploiement production** :
1. Remplacer le singleton `_review_service` par injection de dépendance (bloquant multi-worker)
2. Exposer `GET /head-coach-messages` si le frontend doit afficher les messages du Head Coach
3. Connecter `energy/cycle/page.tsx` au vrai endpoint backend (retirer le hardcode du cycle menstruel)

Le frontend desktop/mobile peut démarrer sa propre session de développement. L'API est contractuellement stable.
