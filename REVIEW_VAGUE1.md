# Review Vague 1 — Rapport

Date : 2026-04-12
Reviewer : Claude Code (automated)

---

## Branche : session/s1-external-plan

- **Verdict** : FIX REQUIRED
- **Justification** :
  Le scope prévu (ExternalPlan CRUD : schemas + service + routes + tests) est entièrement livré et correctement implémenté. Les 5 endpoints respectent ModeGuard (`require_tracking_mode`), l'invariant XOR (archivage plutôt que delete) est honoré pour les plans, et les tests passent à 1775 (≥ 1243).

  Cependant, le commit `84413e7` (docs) a accidentellement inclus des artefacts hors-périmètre S-3 dans cette branche :
  - `backend/app/graphs/weekly_review_graph.py` (377 lignes)
  - `backend/app/routes/workflow.py` (100 lignes ajoutées — endpoints review)
  - `backend/app/services/coaching_service.py` (123 lignes ajoutées — weekly_review/resume_review)
  - `tests/backend/api/test_weekly_review_endpoints.py`
  - `tests/backend/graphs/test_weekly_review_graph.py`
  - `docs/superpowers/specs/2026-04-12-s3-weekly-review-graph-design.md`

  Ces fichiers appartiennent à S-3. S'ils sont mergés depuis S-1, ils pollueront main avec une version légèrement inférieure à la version définitive de S-3 (les deux fichiers `.py` diffèrent par 2 commentaires mineurs).

  Problème additionnel : le hard-delete des sessions (`DELETE /external-plan/sessions/{id}`) contredit la règle architecturale "jamais effacer" documentée dans resilio-master-v3.md section 12. Le SESSION_REPORT le documente et justifie l'exception ("données saisies par l'utilisateur"), mais cette décision devrait être explicitement approuvée par le project owner avant merge.

- **Fixes requis** :
  1. **Critique** — Avant merge vers main, isoler les commits S-1 purs : utiliser `git cherry-pick` sur `0ccc584`, `5d6c90b`, `e90d78a` uniquement (ne pas inclure `84413e7` ni `b77e7fd`). Cela exclut les artefacts S-3 contaminants.
  2. **Important** — Documenter formellement l'exception hard-delete sur `ExternalSession` dans resilio-master-v3.md (section 12, règle 3) pour éviter toute ambiguïté future.

- **Dette technique notée** :
  - Absence de `GET /athletes/{id}/external-plan/archived` (liste plans archivés) — utile pour S-6 frontend tracking.
  - Absence de `PATCH /athletes/{id}/external-plan` (titre/dates du plan actif).
  - `ExternalSession` n'a pas de champ `actual_duration_min` pour comparer prévu vs réel en S-3.
  - Ces trois points sont documentés dans SESSION_REPORT comme suggestions hors-scope.

---

## Branche : session/s3-weekly-review

- **Verdict** : ACCEPT
- **Justification** :
  Le scope est livré intégralement : `weekly_review_graph.py` (StateGraph 5 nodes avec MemorySaver + `interrupt_before=["present_review"]`), `CoachingService.weekly_review()` + `resume_review()`, endpoints `POST /plan/review/start` et `POST /plan/review/confirm`, et leurs tests complets. Les tests passent à 1742 (≥ 1243).

  Points positifs :
  - Architecture conforme au master-v3 : state TypedDict JSON-serializable, DB via `config["configurable"]["db"]`, human-in-the-loop préservé.
  - La décision de rendre weekly review mode-agnostique (pas de `require_full_mode`) est documentée et cohérente : un athlète en Tracking Only qui a des logs de sessions doit aussi pouvoir faire une review.
  - `_validate_thread_ownership` via préfixe `{athlete_id}:review:uuid` — protection simple mais efficace.
  - Pas de nouvelles dépendances.

  Points d'attention (non bloquants) :
  - `_review_service = CoachingService()` est un singleton module-level dans `workflow.py`. En multi-worker (gunicorn), chaque worker a sa propre instance et les `_review_graphs` dict sont en mémoire locale. Un service restart entre `weekly_review()` et `resume_review()` perd le contexte (le code gère cela en reconstruisant le graph mais sans le checkpoint MemorySaver — la reprise sera incorrecte). C'est un problème de production connu, documenté dans le SESSION_REPORT.
  - `resume_review()` retourne `None` — `ReviewConfirmResponse.review_id` sera toujours `null`. Acceptable pour l'instant mais le frontend ne peut pas naviguer vers la review persistée.

- **Fixes requis** : Aucun bloquant pour le merge.
- **Dette technique notée** :
  - Singleton `_review_service` en mémoire — incompatible avec multi-worker production. À migrer vers un stockage de checkpoint persistent (PostgreSQL checkpointer LangGraph) dans une session future.
  - `resume_review()` ne retourne pas le `review_id` persisté — frontend ne peut pas faire de lien.
  - `load_history` dans `weekly_review()` est construit à partir de `sessions_completed` des reviews passées (proxy grossier) plutôt que des charges réelles des SessionLogs. Acceptable pour MVP.

---

## Branche : session/s4-energy-patterns

- **Verdict** : ACCEPT
- **Justification** :
  Scope livré : migration 0005 (colonnes `legs_feeling`/`stress_level` sur `energy_snapshots` + table `head_coach_messages`), `HeadCoachMessageModel`, persistance des champs dans `submit_checkin()`, `detect_energy_patterns()` avec 4 détecteurs + déduplication 7j, job APScheduler hebdomadaire (cron lundi 06h00), 480 tests unitaires sur les patterns. Tests passent à 1741 (≥ 1243).

  Points positifs :
  - Les 4 fonctions détectrices sont pures (pas de DB) — très testables, bien couvertes.
  - Déduplication via `_has_recent_message()` évite le spam de messages.
  - Gestion timezone-aware + naive (compatibilité SQLite tests / PostgreSQL prod) bien pensée.
  - resilio-master-v3.md et CLAUDE.md mis à jour de façon minimale et précise (seulement les entrées V3-F concernées).
  - `run_energy_patterns_weekly()` isole les exceptions (log warning, pas de crash scheduler).

  Points d'attention :
  - Les modifications de `resilio-master-v3.md` et `CLAUDE.md` sont légitimes (mise à jour de statut V3-F et documentation du job APScheduler). Elles sont minimes et correctes.
  - `_detect_persistent_divergence` defaulte objective/subjective à 50.0 si None — cela peut faussement déclencher ou non-déclencher le pattern pour des snapshots sans scores calculés. Comportement acceptable pour MVP mais mérite un commentaire explicatif.
  - Aucun endpoint pour lire les `head_coach_messages` depuis le frontend — les messages existent en DB mais ne sont pas consommables. À implémenter en S-5 ou S-6.

  Note sur le working tree : le fichier `tests/backend/core/test_sync_scheduler.py` présente une modification dans le working tree (version sans filtre `IntervalTrigger`) qui ferait échouer le test `test_setup_scheduler_all_jobs_every_6h`. Le commit s4 contient la version correcte avec le filtre. Il faut s'assurer que ce fichier n'est pas commité dans cet état lors du merge.

- **Fixes requis** :
  1. **Important** — Vérifier que `tests/backend/core/test_sync_scheduler.py` est bien à l'état du commit s4 (avec filtre `IntervalTrigger`) avant merge. Le working tree montre une régression de ce test.
  2. **Suggestion** — Ajouter un endpoint `GET /athletes/{id}/head-coach-messages` pour rendre les messages consommables côté frontend.

- **Dette technique notée** :
  - `head_coach_messages` ne sont pas exposés via API — les messages générés sont en DB mais aucun frontend ne peut les lire pour l'instant.
  - Pas de mécanisme de marquage `is_read` côté frontend (`PATCH /head-coach-messages/{id}/read`).
  - Default 50.0 pour scores None dans `_detect_persistent_divergence` — comportement implicite, devrait être documenté.

---

## Branche : session/s5-frontend-energy

- **Verdict** : ACCEPT
- **Justification** :
  Scope livré : `api.ts` enrichi (types `CheckInRequest`, `ReadinessResponse`, `EnergySnapshotSummary` + méthodes `submitCheckin`, `getReadiness`, `getEnergyHistory`), `check-in/page.tsx` refactorisé (4 questions obligatoires + vraie API), `EnergyCard` sur dashboard, `energy/page.tsx` migré vers API réelle, `energy/cycle/page.tsx` nettoyé des mocks. `tsc --noEmit` et `npm run build` passent sans erreurs.

  Points positifs :
  - Suppression complète des imports `mock-data/simon` dans les composants touchés — bonne hygiène.
  - Suppression du hack auto-login dev dans `login/page.tsx` — plus robuste.
  - UX progressive du formulaire check-in (chaque question s'active après la précédente) bien implémentée.
  - `Promise.allSettled()` sur `energy/page.tsx` — résilient aux erreurs partielles.
  - `EnergyCard` gère correctement les 3 états (loading / none / loaded).
  - Aucune nouvelle dépendance npm.

  Divergences spec vs livraison (documentées dans SESSION_REPORT) :
  - Route `/checkin` du plan → page existante `/check-in/` (avec tiret) — cohérent avec le routing Next.js existant.
  - `cycle_phase` omis du formulaire — justifié (pas de détection du sexe côté frontend).
  - HRV chart supprimé de `energy/page.tsx` — `EnergySnapshotSummary` ne contient pas HRV.
  - Lien TopNav "Énergie" déjà présent — aucun changement nécessaire.

  Point d'attention : la page `energy/cycle/page.tsx` utilise des constantes locales statiques (cycle J18 lutéale codée en dur) avec une notice "démo". Acceptable pour MVP mais doit être connecté au backend `GET /athletes/{id}/hormonal-profile` dans S-6.

- **Fixes requis** : Aucun bloquant.
- **Dette technique notée** :
  - `energy/cycle/page.tsx` : données de cycle menstruel codées en dur (démo) — à connecter au backend hormonal-profile en S-6.
  - `EnergySnapshotSummary` ne contient pas `hrv_rmssd` — le chart HRV prévu dans la spec a été supprimé. À reconsidérer si le backend expose HRV dans les snapshots.
  - Pas de SESSION_PLAN.md sur cette branche — légère déviation du processus documentaire.
  - `head_coach_messages` pas encore affichés (attend S-4 API endpoint).

---

## Ordre de merge recommandé pour la Vague 1

1. **session/s4-energy-patterns** — Pas de dépendances sur les autres branches. Ajoute la migration 0005 et le scheduler job. Doit passer en premier pour que la migration soit disponible. Vérifier le working tree `test_sync_scheduler.py` avant merge.
2. **session/s3-weekly-review** — Pas de conflit avec s4. Ajoute weekly_review_graph.py + endpoints review. Doit passer avant s1 pour éviter la version contaminée des fichiers s3 présents dans s1.
3. **session/s1-external-plan** — Doit être mergé via `cherry-pick` des 3 commits purs (`0ccc584`, `5d6c90b`, `e90d78a`) pour exclure les artefacts s3 contaminants. NE PAS faire un merge direct de la branche.
4. **session/s5-frontend-energy** — Pas de dépendances backend. Peut être mergé en parallèle avec les 3 autres ou en dernier.

---

## Risques de conflit à anticiper

**Conflit certain : s1 ↔ s3**
- `backend/app/routes/workflow.py` : s1 ajoute 100 lignes (endpoints weekly review) identiques à s3. Si s3 est mergé en premier (recommandé) et s1 est cherry-picked (commits s1 purs seulement), il n'y a pas de conflit sur ce fichier.
- `backend/app/services/coaching_service.py` : même situation — s1 contient les ajouts s3 quasi-identiques. Cherry-pick résout le problème.
- `backend/app/graphs/weekly_review_graph.py` : idem.
- Si les branches sont mergées dans l'ordre recommandé (s3 avant s1 cherry-pick), ces conflits sont évités.

**Conflit probable : s4 ↔ s1 sur `backend/app/db/models.py`**
- s4 ajoute la relation `head_coach_messages` sur `AthleteModel` et importe `HeadCoachMessageModel`.
- s1 ajoute la relation `external_plans` sur `AthleteModel` et importe `ExternalPlanModel`.
- Ces deux modifications touchent les mêmes lignes de fin de fichier. Résolution manuelle requise.

**Conflit probable : s4 ↔ s1 sur `backend/app/models/schemas.py`**
- s4 ajoute `HeadCoachMessageModel` en fin de fichier.
- s1 ajoute `ExternalPlanModel` + `ExternalSessionModel` en fin de fichier.
- Résolution simple : conserver les deux ajouts.

**Pas de conflit attendu : s5 ↔ backend**
- s5 ne touche que `frontend/` et `SESSION_REPORT.md` — pas de collision avec les branches backend.

**Pas de conflit attendu : s3 ↔ s4**
- s3 et s4 touchent des fichiers disjoints.

---

## Notes générales

**Qualité globale** : Bonne. Les 4 sessions ont respecté le principe TDD, les invariants pytest ≥ 1243, et l'architecture 2-volets. Aucune branche n'introduit de nouvelles dépendances suspectes.

**Contamination s1→s3** : Le problème principal de cette Vague 1 est l'inclusion accidentelle des artefacts S-3 dans S-1. La stratégie cherry-pick est la bonne réponse. Le fait que les deux implémentations soient quasi-identiques (2 commentaires de différence dans `weekly_review_graph.py`) confirme que les deux sessions ont travaillé de façon cohérente.

**resilio-master-v3.md** : Modifié uniquement dans s4 (mise à jour de statut V3-F + documentation APScheduler) — modifications légitimes et précises. Non modifié dans s1, s3, s5 — conforme aux règles.

**CLAUDE.md** : Modifié uniquement dans s4 (une ligne : V3-F ✅) — légitime. Non modifié dans s1, s3, s5 — conforme.

**Migration Alembic** : s4 introduit la migration 0005. Il faut s'assurer qu'aucune autre branche en cours ne crée aussi une migration 0005 avec un nom différent (risque de collision Alembic `down_revision`).

**Singleton `_review_service`** : Le pattern module-level singleton pour `CoachingService` dans `workflow.py` est une dette technique à surveiller. En production multi-worker, les threads LangGraph ne survivent pas aux restarts. À adresser dans S-7 ou une session de hardening.
