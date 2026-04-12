# SESSION_PLAN — S-7 E2E Tests + Finalisation

**Date :** 2026-04-12
**Branche :** session/s7-e2e-finalisation → session/s7b-finalisation-complete

## Objectif

Clore le cycle V3 en ajoutant :
1. 4 fichiers de tests E2E couvrant l'architecture 2-volets
2. Invariants architecturaux explicites (modularité, jamais effacer)
3. Remplacement des stubs frontend S-2
4. Documentation finale (master-v3, CLAUDE.md, BACKEND_V3_COMPLETE.md)

## Prérequis vérifiés

- [x] 6 sessions Vague 1-2 mergées sur main (s1, s3, s4, s5, s2, s6)
- [x] pytest baseline = 1812 passed avant S-7
- [x] npx tsc --noEmit clean

## Plan d'implémentation

### Tâche 1 — test_full_mode_workflow.py (7 tests)
- onboarding(full) → checkin → readiness → workflow/create-plan (mocked) → approve
- Valide : ModeGuard full_mode, ReadinessResponse shape, CoachingService mock pattern

### Tâche 2 — test_tracking_only_workflow.py (9 tests)
- onboarding(tracking_only) → 403 on full-mode routes → ExternalPlan CRUD → checkin → readiness
- Valide : require_tracking_mode, ExternalPlan lifecycle, Volet 2 mode-agnostique

### Tâche 3 — test_mode_switch.py (10 tests)
- Full → switch → plans archivés → routes inversées → switch back
- Extra : test_10 vérifie head_coach_messages preserved via direct DB access
- Valide : NEVER DELETE rule, bidirectional switch, ModeGuard reset

### Tâche 4 — test_volet2_standalone.py (9 tests)
- Volet 2 sans plan, 409 double-checkin, history
- Extra : test_09 patches CoachingService et vérifie 0 appel LangGraph
- Valide : modularité architecturale critique

### Tâche 5 — Fix stubs frontend
- api.ts : importExternalPlan et confirmImportExternalPlan → vrais appels HTTP
- tracking/import/page.tsx : notice démo retirée

### Tâche 6 — Documentation
- resilio-master-v3.md : NON IMPLÉMENTÉ vidé, section 12 sessions complètes
- CLAUDE.md : V3-E → V3-H ✅
- BACKEND_V3_COMPLETE.md : consolidation complète
- SESSION_REPORT.md : section S-7 ajoutée

## Résultat final

- 1847 tests passing (1812 baseline + 35 nouveaux)
- 4 fichiers E2E, 35 tests au total
- npx tsc --noEmit clean
- BACKEND_V3_COMPLETE.md créé
