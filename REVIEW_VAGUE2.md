# Review Vague 2 — Rapport

Date : 2026-04-12
Reviewer : Claude Code (automated)

---

## Branche : session/s2-plan-import

- **Verdict** : FIX REQUIRED
- **Justification** :
  Le scope est livré intégralement et correctement : `PlanImportService` (parse_file + confirm_import), 2 nouvelles routes sur `external_plan.py`, 2 nouveaux schemas Pydantic (`ExternalPlanDraft`, `ExternalPlanDraftSession`), dépendance `anthropic>=0.25`, et 15 tests (8 service + 7 API). Les endpoints respectent `require_tracking_mode`. La logique est non-destructive : `/import` ne touche pas la DB, `/import/confirm` délègue à `ExternalPlanService.create_plan()` avec override `source="file_import"`. L'Anthropic client est correctement mocké dans tous les tests. `resilio-master-v3.md` et `CLAUDE.md` non modifiés ✅.

  **Problème bloquant** : `poetry.lock` n'a pas été commité sur la branche. L'ajout de `anthropic>=0.25,<1.0` dans `pyproject.toml` rend le lock file périmé. Toute tentative d'installation fraîche échoue avec `Run poetry lock to fix the lock file`. Le SESSION_REPORT mentionne "anthropic 0.94.0 installé dans le venv ✅" mais cela reflète l'état du venv local, pas le lock commité.

  Points d'attention (non bloquants) :
  - `anthropic.Anthropic(api_key=api_key)` est instancié à chaque appel `parse_file()`. Pas de bug, mais légèrement inefficace. Acceptable pour MVP.
  - `confirm_import()` écrit `plan.source = "file_import"` en deux phases (create_plan → commit → override source → commit). Fonctionnel mais laisse une fenêtre de temps où `source="manual"`. Acceptable pour MVP.
  - Le `filename` de l'upload est injecté directement dans le prompt Haiku (`f"Filename: {filename}\n\n{truncated}"`). Si un fichier est nommé de façon malicieuse (prompt injection), Haiku pourrait retourner du JSON altéré. Risque faible (le JSON est parsé structurellement), mais à noter.
  - Tests API (`test_external_plan_import.py`) : `test_confirm_creates_plan_and_returns_plan_out` double-patche `PlanImportService.confirm_import` ET `ExternalPlanOut.model_validate`. Ce niveau de mocking rend ce test peu représentatif. Les tests service couvrent l'intégration réelle.

- **Fixes requis** :
  1. **Critique** — Exécuter `poetry lock` puis commiter le `poetry.lock` mis à jour sur la branche avant merge. Sans cela, `poetry install` échoue sur toute installation fraîche.

- **Dette technique notée** :
  - `PlanImportService.parse_file` instancie un nouveau client `anthropic.Anthropic` à chaque appel — à transformer en singleton module-level si la charge monte.
  - `confirm_import()` n'expose pas l'override `source` dans la signature — contrat implicite difficile à tester unitairement via l'interface publique.
  - Pas de retry ou timeout configuré sur l'appel Haiku — un timeout réseau laissera la requête FastAPI suspendue indéfiniment.
  - Pas de validation du type MIME côté backend (seul le frontend filtre `.pdf,.txt,.csv,.ics`) — un utilisateur peut uploader n'importe quel binaire.

---

## Branche : session/s6-frontend-tracking

- **Verdict** : ACCEPT (avec note de dette documentée)
- **Justification** :
  Le scope frontend est livré complet : `tracking/page.tsx` (visualisation plan + PATCH status + formulaire ajout session + formulaire création plan), `tracking/import/page.tsx` (wizard 3 étapes avec drag & drop), TopNav badge TRACKING + lien conditionnel, `auth.tsx` enrichi de `coachingMode`, `api.ts` typé (6 méthodes ExternalPlan + 2 stubs documentés). `npx tsc --noEmit` passe sans erreurs ✅. Aucune nouvelle dépendance npm ✅. `resilio-master-v3.md` et `CLAUDE.md` non modifiés ✅.

  Les stubs S-2 (`api.importExternalPlan` / `api.confirmImportExternalPlan`) sont correctement documentés dans le code (`[STUB] S-2 not implemented`) et dans l'UI (notice amber visible à l'utilisateur). Les SESSION_REPORT documente explicitement l'état stub et le plan de remplacement post-merge S-2.

  **Contamination de scope (non bloquant)** : La branche inclut `backend/app/services/plan_import_service.py` (125 lignes) et `tests/backend/services/test_plan_import_service.py` (278 lignes) dans son diff vs main. Ces fichiers appartiennent au scope S-2. Ils sont identiques bit-pour-bit aux versions de la branche `session/s2-plan-import` (checksums md5 identiques). Cela ne crée pas de conflit de merge si s2 est mergé en premier (git verra les fichiers comme déjà présents). Mais c'est une irrégularité documentaire : le commit `e170771` sur s6 porte le tag `feat(s2):` — c'est un cherry-pick ou une duplication d'un commit s2 sur la branche s6.

  Point d'attention — mismatch type frontend/backend (dette) : `ExternalPlanDraft.sessions` est typé `ExternalSessionCreate[]` dans `api.ts`. Or le backend retourne des sessions où `session_date` peut être `null` (`ExternalPlanDraftSession.session_date: date | None`). Côté frontend, `ExternalSessionCreate.session_date` est `string` (non-optionnel). Quand les stubs sont remplacés par l'API réelle, `formatDate(s.session_date)` dans `tracking/import/page.tsx:170` plantera pour les sessions sans date. À corriger avant d'activer l'endpoint S-2.

  Points positifs :
  - `ProtectedRoute` + redirect `/dashboard` si `coachingMode !== 'tracking_only'` — accès correctement gardé.
  - Bootstrap localStorage de `coachingMode` : rendu immédiat sans flash, puis mise à jour depuis GET /athletes/{id} — pattern correct.
  - Fallback `'full'` dans `fetchCoachingMode()` si erreur réseau — défensif et safe.
  - `Promise` non-await dans `login()` et `useEffect()` pour `fetchCoachingMode` — correct (fire-and-forget, le state se met à jour via `setAuth`).
  - Tri des sessions par date après ajout inline (`localeCompare`) — bon UX.

- **Fixes requis** : Aucun bloquant pour le merge.
  - **Important (avant activation endpoint S-2)** — Créer un type dédié `ExternalPlanDraftSession` dans `api.ts` (avec `session_date: string | null`) et l'utiliser dans `ExternalPlanDraft.sessions` au lieu de `ExternalSessionCreate[]`. Corriger `tracking/import/page.tsx:170` pour gérer `session_date` nullable dans `formatDate`.

- **Dette technique notée** :
  - Type `ExternalPlanDraft.sessions: ExternalSessionCreate[]` incorrect — devrait être `ExternalPlanDraftSession[]` avec `session_date: string | null`. Sera un bug runtime dès l'activation de l'endpoint S-2.
  - Stubs `importExternalPlan` / `confirmImportExternalPlan` dans `api.ts` — à remplacer par les vrais appels après merge S-2.
  - `coachingMode` dans localStorage peut être périmé si l'athlète change de mode depuis un autre appareil ou session. La mise à jour au login/mount est correcte mais ne couvre pas le changement mid-session. Acceptable pour MVP.
  - `tracking/page.tsx` n'expose pas la liste des plans archivés (ni de lien vers un historique) — la dette notée dans REVIEW_VAGUE1.md pour `GET /external-plan/archived` reste ouverte.
  - `backend/app/services/plan_import_service.py` est présent dans s6 mais appartient à s2 — à supprimer proprement de s6 via cherry-pick si l'intégrité de branche est exigée.

---

## Ordre de merge recommandé pour la Vague 2

1. **session/s2-plan-import** — Après correction du `poetry.lock` (fix critique). Fournit le backend `PlanImportService` + endpoints `/import` + `/import/confirm`. Doit passer avant s6 pour que les stubs puissent être remplacés. Pas de conflit avec quoi que ce soit sur main actuel.
2. **session/s6-frontend-tracking** — Après merge s2. Apporte le frontend complet. Les fichiers `plan_import_service.py` et `test_plan_import_service.py` inclus dans s6 seront déjà sur main après s2 merge — git les verra comme "already up to date", aucun conflit. Avant activation des stubs, corriger le type `ExternalPlanDraftSession` dans `api.ts`.

---

## Risques de conflit à anticiper

**Pas de conflit sur les fichiers backend** :
- `plan_import_service.py` est identique dans s2 et s6 (md5 identiques). Peu importe l'ordre de merge, pas de conflit.
- `external_plan.py` n'est touché que par s2, pas par s6 (s6 n'ajoute pas de routes backend).
- `pyproject.toml` : seul s2 ajoute `anthropic>=0.25` — pas touché par s6. Pas de conflit.

**Pas de conflit sur les fichiers frontend** :
- `api.ts` et `auth.tsx` ne sont touchés que par s6 — pas par s2. Pas de conflit.
- `top-nav.tsx`, `tracking/page.tsx`, `tracking/import/page.tsx` — uniquement dans s6. Pas de conflit.

**Conflit potentiel : s2/s6 ↔ branches Vague 1 non encore mergées** :
- Si les branches Vague 1 n'ont pas encore été toutes mergées sur main, `external_plan.py` dans s2 inclut les 5 routes S-1 déjà sur main + 2 nouvelles routes S-2. Si S-1 n'est pas sur main, le merge de s2 apporterait aussi les routes S-1. Vérifier que `merge(s1)` est bien sur main avant de merger s2 (le log main montre `aeecde1 merge(s1):` — S-1 est déjà mergé ✅).
- `SESSION_REPORT.md` est modifié par les deux branches (s2 et s6 y ajoutent chacune leur section). Il y aura un conflit de merge classique sur ce fichier — résolution triviale (conserver les deux sections).

---

## Notes générales

**Qualité globale** : Bonne. Les deux sessions sont cohérentes avec la roadmap V3-E. S-2 livre le service backend IA de façon propre et testée. S-6 livre le frontend complet avec stubs bien documentés.

**Problème principal Vague 2** : Le seul bloquant est le `poetry.lock` non commité dans s2. Sans cela, l'installation fraîche de l'environnement échoue. Correction triviale (une commande + un commit).

**Contamination s6→s2 backend** : Similaire au problème s1→s3 de Vague 1 mais moins grave ici, car les fichiers sont identiques (pas de divergence). Le risque de pollution est nul en pratique si s2 est mergé en premier. La recommandation de cherry-pick n'est pas nécessaire cette fois.

**Stubs frontend** : Le pattern stub → API réelle est bien documenté. La seule action requise post-merge S-2 est (1) remplacer 2 méthodes dans `api.ts` par les vrais appels HTTP et (2) corriger le type `ExternalPlanDraftSession`. Travail estimé : ~30 minutes dans une session dédée ou en micro-tâche lors du merge.

**resilio-master-v3.md** : Non modifié dans les deux branches ✅. V3-E reste marqué ❌ sur main — à mettre à jour lors du merge des deux branches (hors scope de cette review).

**CLAUDE.md** : Non modifié dans les deux branches ✅.
