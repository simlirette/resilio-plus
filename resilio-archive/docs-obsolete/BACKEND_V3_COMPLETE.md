# BACKEND V3 — ÉTAT COMPLET (2026-04-12)

Ce document consolide l'état final du backend V3 après la clôture des 7 sessions parallèles.

---

## 1. SESSIONS COMPLÉTÉES — HISTORIQUE DE MERGE

| Session | Scope | Commit de merge | Tests ajoutés |
|---|---|---|---|
| **S-1** | ExternalPlan CRUD — 5 endpoints + XOR invariant | `aeecde1` | 33 (14 service + 19 API) |
| **S-2** | Import fichier plan externe (Claude Haiku) | `54e9700` | 15 (8 service + 7 API) |
| **S-3** | Weekly review graph (5 nodes) + CoachingService.weekly_review() | `7c30da1` | 23 (15 graph + 8 API) |
| **S-4** | detect_energy_patterns() + migration 0005 + APScheduler hebdo | `85d2162` | 22 (patterns + scheduler) |
| **S-5** | Frontend check-in + EnergyCard dashboard + vraie API | `e9563ce` | 0 (frontend uniquement) |
| **S-6** | Frontend tracking page + import wizard (stubs S-2) | `364d9fb` | 0 (frontend uniquement) |
| **S-7** | E2E tests 2-volet + stubs remplacés + docs finaux | `d0df1a0` | 35 (4 fichiers E2E) |

**Total tests suite complète :** 1847 passing, 9 skipped

---

## 2. RAPPORTS DE REVIEW TECHNIQUE

| Vague | Fichier | Verdict global |
|---|---|---|
| Vague 1 (S-1, S-3, S-4, S-5) | `REVIEW_VAGUE1.md` | S-1: FIX REQUIRED (cherry-pick + hard-delete doc) — RÉSOLU ✅ |
| Vague 2 (S-2, S-6) | `REVIEW_VAGUE2.md` | S-2: FIX REQUIRED (poetry.lock) — RÉSOLU ✅ |

**Problèmes bloquants résolus :**
- S-1 : cherry-pick propre des 3 commits purs (contamination s3 évitée via merge `aeecde1`)
- S-1 : exception hard-delete `ExternalSession` documentée dans `resilio-master-v3.md` section 12
- S-2 : `poetry.lock` commité avec `anthropic 0.94.0` (commit `3d3b457`)
- S-6 : type `ExternalPlanDraftSession.session_date: string | null` corrigé (commit `8aef5f9`)
- S-6 : stubs `importExternalPlan` / `confirmImportExternalPlan` remplacés (commit `ad6cd91`)

---

## 3. DETTE TECHNIQUE RESTANTE

Ces éléments sont documentés et non bloquants pour le développement frontend avancé.

### Backend

| Item | Sévérité | Détail |
|---|---|---|
| Singleton `_review_service` en mémoire | ⚠️ Moyen | `CoachingService()` dans `workflow.py` est module-level. Incompatible multi-worker (gunicorn). À migrer vers PostgreSQL checkpointer LangGraph en production. |
| `head_coach_messages` non exposés via API | ℹ️ Faible | Les messages générés par `detect_energy_patterns()` sont en DB mais aucun endpoint `GET /athletes/{id}/head-coach-messages` n'existe. À implémenter pour le frontend. |
| Pas de `PATCH /is_read` sur messages | ℹ️ Faible | Impossible de marquer un message comme lu sans nouvel endpoint. |
| `_detect_persistent_divergence` default 50.0 | ℹ️ Faible | Default 50.0 pour scores None peut fausser la détection. Comportement implicite, pas documenté en code. |
| `load_history` dans `weekly_review()` | ℹ️ Faible | Calculé via `sessions_completed` (proxy) plutôt que charges réelles des SessionLogs. |
| Pas de timeout sur l'appel Claude Haiku | ⚠️ Moyen | `PlanImportService.parse_file()` sans timeout explicite — request FastAPI suspendue si réseau échoue. |
| Pas de validation MIME backend sur import | ℹ️ Faible | Seul le frontend filtre `.pdf,.txt,.csv,.ics`. Un utilisateur peut uploader n'importe quel binaire. |

### Frontend

| Item | Sévérité | Détail |
|---|---|---|
| `energy/cycle/page.tsx` données en dur | ℹ️ Faible | Cycle menstruel J18 lutéale codé en dur (démo). À connecter à `GET /athletes/{id}/hormonal-profile`. |
| `coachingMode` localStorage stale | ℹ️ Faible | Changement de mode sur un autre appareil ne met pas à jour la session courante. |
| Pas d'affichage `head_coach_messages` | ℹ️ Faible | Messages proactifs du Head Coach générés en DB mais pas de composant frontend. |

---

## 4. ENDPOINTS DISPONIBLES — INVENTAIRE FINAL

**Total : 35 endpoints**

### Auth + Athlete (5)
- `POST /auth/login`
- `POST /athletes/onboarding`
- `GET /athletes/{id}`
- `PATCH /athletes/{id}`
- `PATCH /athletes/{id}/mode`

### Plans Coaching V3-D (3)
- `POST /athletes/{id}/workflow/create-plan` [full_mode]
- `POST /athletes/{id}/workflow/plans/{thread_id}/approve` [full_mode]
- `POST /athletes/{id}/workflow/plans/{thread_id}/revise` [full_mode]

### Plans Legacy (2)
- `GET /athletes/{id}/plans`
- `GET /athletes/{id}/plan`

### Review Hebdomadaire S-3 (2)
- `POST /athletes/{id}/plan/review/start`
- `POST /athletes/{id}/plan/review/confirm`

### ExternalPlan S-1 + S-2 (7)
- `POST /athletes/{id}/external-plan` [tracking_only]
- `GET /athletes/{id}/external-plan` [tracking_only]
- `POST /athletes/{id}/external-plan/sessions` [tracking_only]
- `PATCH /athletes/{id}/external-plan/sessions/{id}` [tracking_only]
- `DELETE /athletes/{id}/external-plan/sessions/{id}` [tracking_only]
- `POST /athletes/{id}/external-plan/import` [tracking_only]
- `POST /athletes/{id}/external-plan/import/confirm` [tracking_only]

### Energy Cycle V3-C (4)
- `POST /athletes/{id}/checkin`
- `GET /athletes/{id}/readiness`
- `GET /athletes/{id}/energy/history`
- `PATCH /athletes/{id}/hormonal-profile`

### Sessions + History (5)
- `GET /athletes/{id}/sessions`
- `POST /athletes/{id}/sessions`
- `GET /athletes/{id}/sessions/{id}`
- `PATCH /athletes/{id}/sessions/{id}`
- `POST /athletes/{id}/sessions/{id}/log`

### Connectors (8)
- `POST /athletes/{id}/connectors/strava` + `/sync`
- `POST /athletes/{id}/connectors/hevy` + `/sync`
- `POST /athletes/{id}/connectors/terra` + `/sync`
- `DELETE /athletes/{id}/connectors/{provider}`
- `GET /athletes/{id}/connectors`

### Divers (3)
- `POST /athletes/{id}/review`
- `GET /athletes/{id}/analytics`
- `GET /athletes/{id}/workflow/status`

---

## 5. ARCHITECTURE 2-VOLETS — VALIDÉE PAR LES TESTS E2E

### Invariants prouvés

| Invariant | Test | Fichier |
|---|---|---|
| Volet 2 fonctionne sans plan actif | `test_04_checkin_without_coaching_plan` | `test_volet2_standalone.py` |
| Volet 2 ne touche jamais LangGraph | `test_09_volet2_never_invokes_langgraph` | `test_volet2_standalone.py` |
| Volet 2 accessible en mode tracking_only | `test_08_volet2_works_in_tracking_only_mode` | `test_volet2_standalone.py` |
| Mode switch archive les plans (ne supprime pas) | `test_04_training_plans_archived_after_switch` | `test_mode_switch.py` |
| head_coach_messages préservés après switch | `test_10_head_coach_messages_preserved_after_mode_switch` | `test_mode_switch.py` |
| ModeGuard bloque create-plan en tracking_only | `test_02_full_mode_plan_creation_blocked` | `test_tracking_only_workflow.py` |
| ModeGuard bloque external-plan en full | `test_09_tracking_route_blocked_after_switch_back` | `test_mode_switch.py` |

### Principe fondamental
```
Volet 1 (Full Coaching) ← indépendant → Volet 2 (Energy Cycle)
        ↓                                          ↓
  LangGraph graph                         EnergyCycleService
  CoachingService                         EnergySnapshotModel
  TrainingPlanModel                       HormonalProfileModel
                                          HeadCoachMessageModel
```

Flux **unidirectionnel** uniquement : `apply_energy_snapshot` dans le graph lit le snapshot du Volet 2, jamais l'inverse.

---

## 6. PRÊT POUR LE DÉVELOPPEMENT FRONTEND AVANCÉ

### Ce qui est stable et consommable

| Fonctionnalité | Endpoints | Status |
|---|---|---|
| Authentification | POST /login, POST /onboarding | ✅ Stable |
| Profil athlète | GET/PATCH /athletes/{id} | ✅ Stable |
| Switch de mode | PATCH /athletes/{id}/mode | ✅ Stable |
| Plan IA (Full mode) | workflow/create-plan + approve | ✅ Stable (mocked OK en tests) |
| Plan externe (Tracking) | /external-plan CRUD + import | ✅ Stable |
| Energy Cycle check-in | POST /checkin + GET /readiness | ✅ Stable |
| Historique énergie | GET /energy/history | ✅ Stable |
| Sessions logging | GET+POST+PATCH /sessions/{id} + /log | ✅ Stable |
| Weekly review | POST /plan/review/start + confirm | ✅ Stable |
| Connectors | /connectors/strava + hevy + terra | ✅ Stable |

### Ce qui manque (opportunités desktop/mobile)
- **Notifications proactives** : `GET /athletes/{id}/head-coach-messages` (messages générés par `detect_energy_patterns` — en DB, pas d'endpoint)
- **Profil hormonal** : `GET /athletes/{id}/hormonal-profile` (PATCH existe, GET manquant)
- **Analytics avancés** : ACWR détaillé, sport breakdown par semaine
- **Plan actif status** : endpoint pour savoir si un plan est en attente d'approbation (thread_id actif)
