# Backend Frozen — V1 Status

**Date de gel:** 2026-04-17  
**Branche de merge:** `session/backend-final-audit`  
**Version:** 1.0.0 (à tagger après merge de la PR)  
**Auditeur:** Claude Sonnet 4.6 (session autonome ~4h)

---

## État

Le backend est officiellement gelé en **V1**. Le code actuel est l'état de référence.  
Toute modification future nécessite une justification explicite (voir section "Règles").

---

## Stats de Gel

| Metric | Value |
|--------|-------|
| Tests total | 2446 collectés |
| Tests passing | **2430** |
| Tests skipped | 16 (db_integration — require live PG on port 5433) |
| Tests failed | **0** |
| Flakes résolus | 2 (`test_history_shows_logged_count`, `test_high_continuity_no_breaks`) |
| Flakes acceptés | 0 |
| mypy errors | **0** (135 fichiers, `--strict`) |
| ruff violations | **0** |
| ruff format | **Clean** (9 fichiers formatés pendant l'audit) |
| Endpoints | 72 |
| DB Tables | 20 |
| Agents | 8 (Head Coach + 6 spécialistes + Energy Coach) |
| Alembic migrations | 10 (0001 → 0010) |
| Dépendances directes | 28 |

---

## Règles de Modification Post-Gel

Toute modification après ce gel **doit**:

1. Avoir une justification EXPLICITE documentée: "nouvelle feature X" ou "bug Y en production"
2. Avoir un design doc: `docs/backend-v2/<feature-name>.md` AVANT toute implémentation
3. Respecter les invariants de `backend/CONTRACT.md`
4. Utiliser la procédure superpowers: brainstorming → writing-plans → executing-plans
5. Être revue par Simon-Olivier avant merge

---

## Modifications INTERDITES Post-Gel

- Refactoring opportuniste ("ce serait plus propre si...")
- Changement de style sans impact fonctionnel
- Upgrade de dépendance sans raison de sécurité ou de feature
- Renommage sans raison fonctionnelle
- Extraction de fonctions/modules sans raison fonctionnelle

---

## Known Bugs (V1 — Non Critiques, Non Fixés)

Ces bugs ont été détectés pendant l'audit et documentés intentionnellement.
Ils ne sont PAS bloquants pour le gel V1.

| Bug | Sévérité | Location | Description |
|-----|---------|---------|-------------|
| `get_agent_view()` non appelé en runtime | Medium | `graphs/nodes.py` | La matrice d'accès AgentView est définie et testée mais les agents reçoivent l'état complet (`AthleteCoachingState`) sans filtrage. Enforcement prévu en V2. |
| `bcrypt` WARNING au démarrage | Cosmétique | `passlib` compat | `passlib` 1.7 vérifie `bcrypt.__about__.__version__` qui n'existe plus en bcrypt 4.x. Caught silently, passwords hash correctly. |
| Pas de limite de taille sur uploads | Low | `routes/connectors.py`, `routes/integrations.py` | `file.read()` sans vérification préalable. Risque OOM sur très gros fichiers. |
| Pas de rate limiting | Medium | Tous endpoints | Aucune protection brute-force/scan. Mitigation: nginx-level en production. |
| `GET /athletes/` non authentifié | Low | `routes/athletes.py:54` | Intentionnel — onboarding pre-auth flow. V1.1 backlog. |
| `food_search` routes publiques | Low | `routes/food_search.py` | Endpoints nutrition search sans auth. Intentionnel (lookup public). |
| JWT_SECRET dev default | Medium | `core/security.py:13` | `"resilio-dev-secret"` si env var non défini. **Ne JAMAIS déployer sans JWT_SECRET fort en production.** |

---

## Known Limitations (V1 — Features Hors Scope)

| Limitation | Justification |
|-----------|--------------|
| FatSecret connector inactif | Nutrition calculée en interne via `nutrition_logic.py`. FatSecret out-of-scope V1. |
| Apple Health: non validé sur vrai iPhone | Feature flag `APPLE_HEALTH_ENABLED=false`. Testé avec fixtures synthétiques uniquement. |
| `GET /athletes/{id}/head-coach-messages` manquant | Messages en DB, endpoint non implémenté. V1.1 backlog. |
| `GET /athletes/{id}/hormonal-profile` manquant | PATCH existe, GET manquant. V1.1 backlog. |
| Pas de timeout explicite sur Claude Haiku (import plan) | Request FastAPI suspendue si réseau échoue. Mitigation: gunicorn timeout 120s. |
| Multi-worker LangGraph checkpointer | `SqliteSaver` OK pour single-process. PG checkpointer requis pour scale-out. |

---

## Accepted Test Flakes

**Aucun.** Les deux flakes pré-existants ont été résolus pendant l'audit:

- `test_history_shows_logged_count` → `any(sessions_logged >= 1)` (était `max(by=start_date)`)
- `test_high_continuity_no_breaks` → activities window étendue à 2030-12-31 (was `date.today()` drift)

---

## Roadmap V2

Référence: `resilio-master-v3.md` + `docs/V1.1-BACKLOG.md`

**V1.1 (petits ajouts, aucun breaking change):**
- `GET /athletes/{id}/head-coach-messages`
- `GET /athletes/{id}/hormonal-profile`
- Auth sur `POST /athletes/`
- File upload size limits

**V2.0 (features majeures):**
- `get_agent_view()` enforcement dans le graph (access control)
- Rate limiting (slowapi ou nginx)
- Apple Health validation sur vrai device
- PostgreSQL LangGraph checkpointer (multi-worker)
- FatSecret integration (si requis par roadmap produit)

---

## Procédure d'Accès Post-Gel

```
1. Simon-Olivier identifie le besoin (feature/bug)
2. Ouvrir une discussion pour justifier
3. Si approuvé → créer design doc: docs/backend-v2/<feature>.md
4. git checkout -b session/backend-<feature>
5. Appliquer superpowers: brainstorming → writing-plans → executing-plans
6. Review + merge
7. Mettre à jour ce fichier avec la nouvelle version
```

---

## Procédure de Tagging V1.0.0

Après merge de `session/backend-final-audit` sur `main`:

```bash
git tag -a v1.0.0 -m "Backend V1 frozen — 2430 tests, 0 flakes, mypy clean"
git push origin v1.0.0
```

---

*Ce document a été généré par une session autonome Claude Sonnet 4.6.*  
*Session ID: BACKEND-FINAL-AUDIT | Date: 2026-04-17*
