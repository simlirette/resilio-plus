# SESSION PLAN — S-1 ExternalPlan Backend CRUD

**Date:** 2026-04-12  
**Branche:** session/s1-external-plan  
**Basée sur:** main @ 68bf2a2

## Objectif

Implémenter l'ExternalPlanService + 5 routes REST permettant aux athlètes en mode Tracking Only de saisir et gérer manuellement un plan externe.

## Fichiers créés

| Fichier | Rôle |
|---|---|
| `backend/app/schemas/external_plan.py` | Pydantic schemas (Create/Update/Out) |
| `backend/app/services/external_plan_service.py` | ExternalPlanService — 5 méthodes statiques |
| `backend/app/routes/external_plan.py` | FastAPI router — 5 endpoints |
| `tests/backend/services/test_external_plan_service.py` | 14 tests unitaires service |
| `tests/backend/api/test_external_plan.py` | 19 tests API integration |

## Fichiers modifiés

| Fichier | Changement |
|---|---|
| `backend/app/main.py` | +2 lignes : import + include_router external_plan_router |

## Commits

1. `0ccc584` feat(s1): add ExternalPlan Pydantic schemas
2. `5d6c90b` feat(s1): ExternalPlanService — CRUD + XOR invariant (TDD green)
3. `e90d78a` feat(s1): ExternalPlan routes + API tests (TDD green)
4. `84413e7` docs(s1): design spec + implementation plan

## Invariants vérifiés

- pytest tests/ → 1723 passed (≥ 1243) ✅
- 18 failed (pre-existing S-4 / test_energy_patterns.py — hors scope) ✅
- poetry install → OK (aucune nouvelle dépendance) ✅
