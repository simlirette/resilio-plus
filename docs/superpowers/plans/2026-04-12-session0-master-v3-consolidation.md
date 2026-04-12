# SESSION 0 — Consolidation Master V3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Commit pending v3d artifacts, produce `resilio-master-v3.md` as the single architectural reference, archive v2, update `CLAUDE.md`, and deliver `SESSION_REPORT.md` with the ordered backend backlog for parallel sessions.

**Architecture:** Pure documentation session — no functional code touched. 5 tasks: commit pending files, create master v3 doc, archive v2 + update CLAUDE.md, create SESSION_REPORT.md, final commit.

**Tech Stack:** Git, Markdown.

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| Commit | `poetry.lock` | Pending artifact from LangGraph install |
| Commit | `docs/superpowers/plans/2026-04-11-v3d-langgraph-coaching-graph.md` | Pending v3d plan (all tasks checked ✅) |
| Create | `resilio-master-v3.md` | Single source of truth — V3 architecture |
| Move | `resilio-master-v2.md` → `docs/archive/resilio-master-v2_archived_2026-04-12.md` | Archive (do not delete) |
| Modify | `CLAUDE.md` | Update master reference, tech stack, phase status |
| Create | `SESSION_REPORT.md` | Session summary + ordered backend backlog |

---

### Task 1: Commit pending v3d artifacts

**Files:**
- Commit: `poetry.lock`
- Commit: `docs/superpowers/plans/2026-04-11-v3d-langgraph-coaching-graph.md`

- [ ] **Step 1: Verify pending files**

```bash
git status --short
```
Expected output:
```
 M poetry.lock
?? docs/superpowers/plans/2026-04-11-v3d-langgraph-coaching-graph.md
```

- [ ] **Step 2: Stage and commit**

```bash
git add poetry.lock docs/superpowers/plans/2026-04-11-v3d-langgraph-coaching-graph.md
git commit -m "chore: commit pending v3d artifacts before consolidation"
```
Expected: commit succeeds, `git status` shows clean for those 2 files.

---

### Task 2: Create resilio-master-v3.md

**Files:**
- Create: `resilio-master-v3.md` (repo root)

- [ ] **Step 1: Create the file with the following exact content**

Create `resilio-master-v3.md` at the repo root:

```markdown
# RESILIO HYBRID COACH — Document Maître V3

> **Ce document est la référence unique pour l'architecture V3 de Resilio+.**
> Il remplace `resilio-master-v2.md` (archivé dans `docs/archive/`).
> Il reflète l'état réel du code au 2026-04-12.
> Toute décision architecturale non documentée ici doit y être ajoutée.

---

## TABLE DES MATIÈRES

1. Vision & Architecture 2-Volets
2. Mode System
3. AthleteCoachingState (LangGraph)
4. get_agent_view() — Vues par Agent
5. LangGraph Coaching Graph — 11 Nodes
6. Volet 2 — EnergyCycleService
7. Collaboration Volet 1 ↔ Volet 2
8. Intégrations Actives (Phase 9)
9. Endpoints Existants — Table Complète
10. Infrastructure
11. État d'Implémentation (2026-04-12)
12. Travail Backend Restant — Sessions Parallèles

---

## 1. VISION & ARCHITECTURE 2-VOLETS

Resilio+ supporte exactement **2 modes** :

| Mode | Volets actifs | Description |
|---|---|---|
| **Full Coaching** | Volet 1 + Volet 2 | Plan IA personnalisé + suivi Energy Cycle |
| **Tracking Only** | Volet 2 seul | Plan externe (coach humain) + suivi Energy Cycle |

**Règle de modularité absolue :** Le Volet 2 (Energy Cycle) fonctionne sans le Volet 1.
Il n'existe pas de mode "Coaching Only" (sans Energy Cycle).
Tout nouveau code doit respecter cette invariante — le test de modularité est non-négociable.

**Principes :**
- Agents : expertise domaine
- Head Coach : intégration et résolution de conflits
- Tools/connectors : données quantitatives
- Human-in-the-loop : préservé partout où il existe

**Stack verrouillée :** LangGraph + FastAPI + Next.js + PostgreSQL + SQLAlchemy 2.0 (sync, psycopg2). Pas de Streamlit, pas de Celery, pas de substitution de stack.

---

## 2. MODE SYSTEM

### Stockage

```python
# backend/app/db/models.py — AthleteModel
coaching_mode = Column(String, nullable=False, default="full")
# Valeurs : "full" | "tracking_only"

# backend/app/schemas/athlete.py
coaching_mode: Literal["full", "tracking_only"] = "full"
```

### ModeGuard (FastAPI dependency)

```python
# backend/app/dependencies/mode_guard.py  ← IMPLÉMENTÉ

def require_full_mode(athlete: AthleteModel = Depends(get_current_athlete)) -> AthleteModel:
    if athlete.coaching_mode != "full":
        raise HTTPException(403, "Nécessite le mode Full Coaching")
    return athlete

def require_tracking_mode(athlete: AthleteModel = Depends(get_current_athlete)) -> AthleteModel:
    if athlete.coaching_mode != "tracking_only":
        raise HTTPException(403, "Réservé au mode Tracking Only")
    return athlete
```

Routes Volet 1 (coaching) → `Depends(require_full_mode)`
Routes plan externe → `Depends(require_tracking_mode)`
Routes Energy Cycle → aucune restriction de mode

### Switch de mode

```
PATCH /athletes/{id}/mode
body: { "coaching_mode": "tracking_only" | "full" }
```

Implémenté dans `backend/app/routes/mode.py`.

| Transition | Données préservées | Données désactivées (non supprimées) |
|---|---|---|
| Full → Tracking Only | Historique Energy Cycle, sessions loggées, plans passés | Plan actif archivé (status = "archived") |
| Tracking Only → Full | Historique Energy Cycle, sessions loggées, plan externe | Plan externe reste en lecture seule |

**Règle absolue : on n'efface jamais. Le switch change ce qui est actif, pas ce qui existe.**

---

## 3. ATHLETECOACHINGSTATE (LANGGRAPH)

Le state LangGraph utilise exclusivement des types primitifs/dicts (JSON-serializable) pour la compatibilité avec `MemorySaver`. Les objets ORM ne sont **jamais** stockés dans le state — ils sont chargés en début de node via `config["configurable"]["db"]`.

```python
# backend/app/graphs/state.py  ← IMPLÉMENTÉ

class AthleteCoachingState(TypedDict):
    athlete_id: str
    # ↑ Clé primaire athlète. Les nodes chargent les données DB via
    #   config["configurable"]["db"] — la session n'est pas dans le state.

    athlete_dict: dict[str, Any]
    # ↑ AthleteProfile.model_dump(mode='json') — jamais l'objet ORM.

    load_history: list[float]
    # ↑ Charges journalières (oldest-first) pour calcul ACWR.

    budgets: dict[str, float]
    # ↑ Sport → heures/semaine, peuplé par analyze_profile.

    recommendations_dicts: list[dict[str, Any]]
    # ↑ AgentRecommendation[] sérialisés (un dict par agent actif).

    acwr_dict: dict[str, Any] | None
    # ↑ ACWRResult sérialisé ou None si pas encore calculé.

    conflicts_dicts: list[dict[str, Any]]
    # ↑ Conflict[] sérialisés depuis detect_conflicts.

    proposed_plan_dict: dict[str, Any] | None
    # ↑ WeeklyPlan draft avant approbation humaine.

    energy_snapshot_dict: dict[str, Any] | None
    # ↑ EnergySnapshot du jour (None si pas de check-in aujourd'hui).

    human_approved: bool
    # ↑ Passé à True par CoachingService.resume_plan(approved=True).

    human_feedback: str | None
    # ↑ Texte libre de l'athlète en cas de rejet du plan.

    final_plan_dict: dict[str, Any] | None
    # ↑ WeeklyPlan finalisé, persisté en DB par finalize_plan.

    messages: Annotated[list[BaseMessage], add_messages]
    # ↑ Accumulateur LangGraph — audit trail debug uniquement.
```

**Règle critique :** `config["configurable"]["db"]` transporte la session SQLAlchemy. Elle ne passe jamais par le state TypedDict.

---

## 4. GET_AGENT_VIEW() — VUES PAR AGENT

```python
# backend/app/models/athlete_state.py  ← IMPLÉMENTÉ

_AGENT_VIEWS: dict[str, list[str] | str] = {
    "head_coach":      "FULL",
    "energy_coach":    ["energy_snapshot", "hormonal_profile",
                        "allostatic_history", "sleep_data", "nutrition_summary"],
    "recovery_coach":  ["hrv_data", "sleep_data", "acwr",
                        "energy_snapshot", "hormonal_profile", "fatigue_snapshots"],
    "nutrition_coach": ["nutrition_profile", "training_today",
                        "energy_snapshot", "hormonal_profile", "body_composition"],
    "running_coach":   ["training_today", "acwr", "vdot", "fatigue_snapshots"],
    "lifting_coach":   ["training_today", "acwr", "fatigue_snapshots"],
    "swimming_coach":  ["training_today", "acwr"],
    "biking_coach":    ["training_today", "acwr"],
}

def get_agent_view(state: AthleteStateV3, agent: str) -> list[str] | str:
    """head_coach → "FULL" | agents connus → liste de clés | inconnu → []"""
    return _AGENT_VIEWS.get(agent, [])
```

---

## 5. LANGGRAPH COACHING GRAPH — 11 NODES

### Fichiers

| Fichier | Rôle | Statut |
|---|---|---|
| `backend/app/graphs/state.py` | `AthleteCoachingState` TypedDict | ✅ |
| `backend/app/graphs/nodes.py` | 11 fonctions node | ✅ |
| `backend/app/graphs/coaching_graph.py` | `build_coaching_graph(interrupt)` factory | ✅ |
| `backend/app/services/coaching_service.py` | `CoachingService` wrapping le graph | ✅ |

### Topologie

```
START
  → analyze_profile          (analyze_goals → sport budgets)
  → compute_acwr             (ACWR + readiness — bloque si DANGER)
  → delegate_specialists     (fan-out parallèle vers agents actifs)
  → merge_recommendations    (agrège AgentRecommendation[])
  → detect_conflicts         (3 couches : scheduling / muscle / fatigue)
  ┌─ conflicts → resolve_conflicts (circuit breaker, max 2 itérations)
  └─ no conflicts ──────────────────────────────────────────────────→
  → build_proposed_plan
  → [INTERRUPT #1] present_to_athlete     ← human-in-the-loop
  ┌─ rejected → revise_plan → back to delegate_specialists (max 1x)
  └─ approved ────────────────────────────────────────────────────→
  → apply_energy_snapshot    (lit EnergySnapshot via EnergyCycleService)
  ┌─ intensity_cap < 0.85 → [INTERRUPT #2] confirm_adjustment (optionnel)
  └─ cap ok ──────────────────────────────────────────────────────→
  → finalize_plan            (persiste en DB)
END
```

### Les 11 Nodes

| Node | Rôle | Interrupt |
|---|---|---|
| `analyze_profile` | `analyze_goals()` → sport budgets | Non |
| `compute_acwr` | ACWR + readiness pré-plan | Non |
| `delegate_specialists` | Fan-out parallèle agents actifs | Non |
| `merge_recommendations` | Agrège `AgentRecommendation[]` | Non |
| `detect_conflicts` | 3 couches scheduling/muscle/fatigue | Non |
| `resolve_conflicts` | Circuit breaker, menu résolutions | Non |
| `build_proposed_plan` | Construit `WeeklyPlan` draft | Non |
| `present_to_athlete` | Envoie plan, attend approbation | **OUI** |
| `revise_plan` | Intègre feedback, repasse aux spécialistes | Non |
| `apply_energy_snapshot` | Lit snapshot du jour, ajuste intensity_cap | Non |
| `finalize_plan` | Persiste en DB | Non |

### CoachingService

```python
# backend/app/services/coaching_service.py  ← IMPLÉMENTÉ

class CoachingService:
    def create_plan(athlete_id: str, db: Session) -> str:
        # Lance le graph, s'arrête à INTERRUPT #1 (present_to_athlete).
        # Retourne thread_id LangGraph.

    def resume_plan(thread_id: str, approved: bool, feedback: str | None, db: Session) -> dict:
        # Reprend après INTERRUPT #1.
        # approved=True → finalize_plan → retourne final_plan_dict
        # approved=False + feedback → revise_plan → retourne proposed_plan_dict révisé

    # weekly_review() et resume_review() : NON IMPLÉMENTÉS (scope V3-future)
```

### Endpoints workflow (v3d)

```
POST /athletes/{id}/plan/create   → { thread_id, proposed_plan }   [require_full_mode]
POST /athletes/{id}/plan/approve  → { final_plan }                  [require_full_mode]
POST /athletes/{id}/plan/revise   → { proposed_plan_revised }       [require_full_mode]
```

---

## 6. VOLET 2 — ENERGYCYCLESERVICE

```python
# backend/app/services/energy_cycle_service.py  ← IMPLÉMENTÉ

class EnergyCycleService:
    @staticmethod
    def submit_checkin(athlete_id: str, checkin: CheckInInput, db: Session) -> ReadinessResponse: ...

    @staticmethod
    def get_today_snapshot(athlete_id: str, db: Session) -> EnergySnapshot | None: ...

    @staticmethod
    def get_readiness(athlete_id: str, db: Session) -> ReadinessResponse: ...

    @staticmethod
    def get_history(athlete_id: str, days: int, db: Session) -> list[EnergySnapshot]: ...

    @staticmethod
    def update_hormonal_profile(athlete_id: str, data: HormonalProfileUpdate, db: Session) -> None: ...
```

**`EnergyCycleService` ne connaît pas l'existence du coaching graph.** Interface unidirectionnelle.

### ReadinessResponse

```python
@dataclass
class ReadinessResponse:
    date:                 date
    objective_score:      float   # 0–100 (HRV, ACWR, sommeil)
    subjective_score:     float   # 0–100 (jambes + énergie check-in)
    final_readiness:      float   # blend pondéré
    divergence:           float   # abs(objective - subjective)
    divergence_flag:      str     # "none" | "moderate" | "high"
    traffic_light:        str     # "green" | "yellow" | "red"
    allostatic_score:     float
    energy_availability:  float
    intensity_cap:        float   # 0.0–1.0 (1.0 = aucun cap)
    insights:             list[str]
```

**Calcul final_readiness :**
```python
divergence = abs(objective_score - subjective_score)
weight_subjective = 0.55 if divergence > 25 else 0.40
final_readiness = objective_score * (1 - weight_subjective) + subjective_score * weight_subjective
```

**Seuils divergence :**
- `< 15 pts` → `"none"` — données cohérentes
- `15–30 pts` → `"moderate"` — signal à surveiller
- `> 30 pts` → `"high"` — divergence significative, insight affiché

### Endpoints Energy Cycle

```
POST   /athletes/{id}/checkin
GET    /athletes/{id}/readiness
GET    /athletes/{id}/energy/history?days=28
PATCH  /athletes/{id}/hormonal-profile
```

---

## 7. COLLABORATION VOLET 1 ↔ VOLET 2

**Règle d'or : flux unidirectionnel.**
```
EnergyCycleService → (lecture seule) → coaching graph
coaching graph     → (jamais)        → EnergyCycleService
```

Le node `apply_energy_snapshot` lit le snapshot du jour via `EnergyCycleService.get_today_snapshot()`.
Si aucun check-in n'a été soumis aujourd'hui, le plan s'applique sans ajustement énergie — **pas de blocage**.

### apply_energy_snapshot — logique

```python
def apply_energy_snapshot(state, config):
    db = config["configurable"]["db"]
    snapshot = EnergyCycleService.get_today_snapshot(state["athlete_id"], db)

    if snapshot is None:
        # Pas de check-in → plan inchangé, message informatif
        return state

    state["energy_snapshot_dict"] = snapshot.model_dump(mode="json")

    # Override subjectif si divergence haute
    if snapshot.subjective_score is not None:
        divergence = abs(snapshot.objective_score - snapshot.subjective_score)
        if snapshot.subjective_score < 40 and divergence > 30:
            # Cap agressif si l'athlète se sent mal malgré des métriques correctes
            effective_cap = min(snapshot.recommended_intensity_cap, 0.80)
        else:
            effective_cap = snapshot.recommended_intensity_cap

    if effective_cap < 1.0:
        state["proposed_plan_dict"] = _apply_intensity_cap(
            state["proposed_plan_dict"], effective_cap
        )

    return state
```

---

## 8. INTÉGRATIONS ACTIVES (PHASE 9)

### SyncService

```python
# backend/app/services/sync_service.py  ← IMPLÉMENTÉ

class SyncService:
    @staticmethod
    def sync_strava(athlete_id: str, db: Session) -> dict:
        # Fetch activités Strava depuis last_sync_at → crée SessionLog entries

    @staticmethod
    def sync_hevy(athlete_id: str, db: Session) -> dict:
        # Fetch workouts Hevy → crée SessionLog entries (type="strength")

    @staticmethod
    def sync_terra(athlete_id: str, db: Session) -> dict:
        # Fetch HRV + sleep depuis Terra API
        # → stocke hrv_rmssd + sleep_hours dans ConnectorCredential.extra_json
        # → ces données sont lues par EnergyCoach lors du calcul objective_score
```

### Terra → Energy Cycle (pipeline)

```
Terra API → SyncService.sync_terra() → ConnectorCredential.extra_json
                                            ↓
                              EnergyCoach lit hrv_rmssd + sleep_hours
                                            ↓
                              EnergySnapshot.objective_score
```

### APScheduler (auto-sync — toutes les 6h)

```python
# backend/app/core/sync_scheduler.py  ← IMPLÉMENTÉ

scheduler.add_job(sync_all_strava, trigger="interval", hours=6)
scheduler.add_job(sync_all_hevy,   trigger="interval", hours=6)
scheduler.add_job(sync_all_terra,  trigger="interval", hours=6)
# detect_energy_patterns() : NON IMPLÉMENTÉ (V3-F)
```

### Endpoints connector

```
POST   /athletes/{id}/connectors/strava          → OAuth2 connect
POST   /athletes/{id}/connectors/strava/sync     → sync manuel
POST   /athletes/{id}/connectors/hevy            → API key connect
POST   /athletes/{id}/connectors/hevy/sync       → sync manuel
POST   /athletes/{id}/connectors/terra           → terra_user_id connect
POST   /athletes/{id}/connectors/terra/sync      → sync manuel HRV/sleep
DELETE /athletes/{id}/connectors/{provider}      → disconnect
GET    /athletes/{id}/connectors                 → liste statuts + last_sync_at
```

---

## 9. ENDPOINTS EXISTANTS — TABLE COMPLÈTE

| Domaine | Méthode | Route | Mode requis |
|---|---|---|---|
| **Auth** | POST | `/auth/register` | — |
| **Auth** | POST | `/auth/login` | — |
| **Athlete** | GET | `/athletes/{id}` | — |
| **Athlete** | PATCH | `/athletes/{id}` | — |
| **Athlete** | PATCH | `/athletes/{id}/mode` | — |
| **Onboarding** | POST | `/athletes/{id}/onboarding` | — |
| **Plan (v3d)** | POST | `/athletes/{id}/plan/create` | full |
| **Plan (v3d)** | POST | `/athletes/{id}/plan/approve` | full |
| **Plan (v3d)** | POST | `/athletes/{id}/plan/revise` | full |
| **Plans** | GET | `/athletes/{id}/plans` | — |
| **Plans** | GET | `/athletes/{id}/plans/{plan_id}` | — |
| **Sessions** | GET | `/athletes/{id}/sessions` | — |
| **Sessions** | POST | `/athletes/{id}/sessions` | — |
| **Sessions** | GET | `/athletes/{id}/sessions/{session_id}` | — |
| **Sessions** | PATCH | `/athletes/{id}/sessions/{session_id}` | — |
| **Reviews** | POST | `/athletes/{id}/reviews` | — |
| **Check-in** | POST | `/athletes/{id}/checkin` | — |
| **Check-in** | GET | `/athletes/{id}/readiness` | — |
| **Check-in** | GET | `/athletes/{id}/energy/history` | — |
| **Check-in** | PATCH | `/athletes/{id}/hormonal-profile` | — |
| **Recovery** | GET | `/athletes/{id}/recovery` | — |
| **Nutrition** | GET | `/athletes/{id}/nutrition` | — |
| **Analytics** | GET | `/athletes/{id}/analytics` | — |
| **Connector** | POST | `/athletes/{id}/connectors/strava` | — |
| **Connector** | POST | `/athletes/{id}/connectors/strava/sync` | — |
| **Connector** | POST | `/athletes/{id}/connectors/hevy` | — |
| **Connector** | POST | `/athletes/{id}/connectors/hevy/sync` | — |
| **Connector** | POST | `/athletes/{id}/connectors/terra` | — |
| **Connector** | POST | `/athletes/{id}/connectors/terra/sync` | — |
| **Connector** | DELETE | `/athletes/{id}/connectors/{provider}` | — |
| **Connector** | GET | `/athletes/{id}/connectors` | — |

---

## 10. INFRASTRUCTURE

### Base de données

- **Engine :** PostgreSQL + `psycopg2-binary` (sync — asyncpg non encore migré)
- **ORM :** SQLAlchemy 2.0 (sync)
- **Migrations Alembic (4 actives) :**
  - `0001_initial_schema.py` — 7 tables V2 (athletes, plans, sessions, session_logs, reviews, connector_credentials, food_logs)
  - `0002_v3_athlete_state.py` — energy_snapshots, hormonal_profiles, allostatic_entries
  - `0003_mode_and_external_plans.py` — coaching_mode sur AthleteModel + external_plans, external_sessions
  - `0004_energy_snapshot_scores.py` — objective_score, subjective_score sur EnergySnapshot

### Dépendances clés (pyproject.toml)

```toml
langgraph = ">=0.2,<1.0"
langchain-core = ">=0.2,<1.0"
psycopg2-binary = ">=2.9"
apscheduler = ">=3.10"
```

### Fichiers cœur

```
backend/app/
  graphs/
    state.py              — AthleteCoachingState TypedDict
    nodes.py              — 11 node functions
    coaching_graph.py     — build_coaching_graph() factory
  services/
    coaching_service.py   — CoachingService (LangGraph wrapper)
    energy_cycle_service.py — EnergyCycleService (Volet 2)
    sync_service.py       — SyncService (Strava/Hevy/Terra)
  dependencies/
    mode_guard.py         — require_full_mode / require_tracking_mode
  routes/
    workflow.py           — /plan/create, /plan/approve, /plan/revise
    checkin.py            — /checkin, /readiness, /energy/history
    mode.py               — PATCH /mode
    connectors.py         — tous les endpoints connecteurs
  core/
    sync_scheduler.py     — APScheduler jobs (6h interval)
  models/
    athlete_state.py      — AthleteStateV3, get_agent_view()
  agents/                 — 7 agents (head_coach, running, lifting, swimming, biking, nutrition, recovery)
```

---

## 11. ÉTAT D'IMPLÉMENTATION (2026-04-12)

### IMPLÉMENTÉ ✅

| Composant | Fichiers clés | Phase |
|---|---|---|
| PostgreSQL + Alembic (4 migrations) | `db/database.py`, `alembic/versions/` | V3-A |
| ModeGuard + PATCH /mode | `dependencies/mode_guard.py`, `routes/mode.py` | V3-B |
| AthleteModel.coaching_mode | `db/models.py`, `schemas/athlete.py` | V3-B |
| EnergyCycleService | `services/energy_cycle_service.py` | V3-C |
| Routes check-in / readiness / history | `routes/checkin.py` | V3-C |
| AthleteCoachingState TypedDict | `graphs/state.py` | V3-D |
| 11 nodes coaching graph | `graphs/nodes.py` | V3-D |
| build_coaching_graph() | `graphs/coaching_graph.py` | V3-D |
| CoachingService | `services/coaching_service.py` | V3-D |
| Endpoints /plan/create + /approve + /revise | `routes/workflow.py` | V3-D |
| SyncService (Strava / Hevy / Terra) | `services/sync_service.py` | Phase 9 |
| Terra health pipeline → Energy Coach | `connectors/terra.py`, `routes/connectors.py` | Phase 9 |
| APScheduler auto-sync (6h) | `core/sync_scheduler.py` | Phase 9 |
| Frontend settings — connect forms | `frontend/src/app/settings/` | Phase 9 |
| get_agent_view() — 8 agents | `models/athlete_state.py` | V3 |

### NON IMPLÉMENTÉ ❌

| Composant | Scope | Session cible |
|---|---|---|
| ExternalPlan CRUD (saisie manuelle) | `services/external_plan_service.py`, `routes/external_plan.py` | S-1 |
| Import fichier plan externe (Claude Haiku) | `routes/external_plan.py` (POST /import) | S-2 |
| Weekly review graph (5 nodes) | `graphs/weekly_review_graph.py` | S-3 |
| CoachingService.weekly_review() | `services/coaching_service.py` (ajout) | S-3 |
| detect_energy_patterns() APScheduler | `core/sync_scheduler.py` (ajout) | S-4 |
| Challenges proactifs (messages Head Coach) | `services/energy_cycle_service.py` (ajout) | S-4 |
| Frontend check-in page | `frontend/src/app/checkin/` | S-5 |
| Frontend energy card dashboard | `frontend/src/app/dashboard/` (ajout card) | S-5 |
| Frontend tracking page (Tracking Only) | `frontend/src/app/tracking/` | S-6 |
| Frontend import fichier | `frontend/src/app/tracking/import/` | S-6 |
| E2E tests 2-volet | `tests/e2e/` (nouveaux scénarios) | S-7 |

---

## 12. TRAVAIL BACKEND RESTANT — SESSIONS PARALLÈLES

Ordre recommandé pour 7 sessions parallèles. Les sessions S-1, S-3, S-4, S-5 n'ont pas de dépendances mutuelles et peuvent démarrer simultanément.

| Session | Scope | Dépend de | Fichiers clés |
|---|---|---|---|
| **S-1** | ExternalPlan backend — tables + CRUD saisie manuelle | aucune | `services/external_plan_service.py`, `routes/external_plan.py`, `db/models.py` |
| **S-2** | Import fichier plan externe (Claude Haiku parse + confirm) | S-1 | `routes/external_plan.py` (POST /import, POST /import/confirm) |
| **S-3** | Weekly review graph (5 nodes) + CoachingService.weekly_review() | aucune | `graphs/weekly_review_graph.py`, `services/coaching_service.py` |
| **S-4** | detect_energy_patterns() + challenges proactifs | aucune | `core/sync_scheduler.py`, `services/energy_cycle_service.py` |
| **S-5** | Frontend check-in + energy card dashboard | aucune | `frontend/src/app/checkin/page.tsx`, `frontend/src/app/dashboard/page.tsx` |
| **S-6** | Frontend tracking page + import UI | S-1 (API ExternalPlan) | `frontend/src/app/tracking/page.tsx`, `frontend/src/app/tracking/import/page.tsx` |
| **S-7** | E2E tests 2-volet + CLAUDE.md final | S-1 → S-4 terminées | `tests/e2e/` (scénarios Full + Tracking Only) |

### Décisions architecturales non-négociables (rappel pour sessions parallèles)

1. **Modularité** : Volet 2 fonctionne sans Volet 1. Tester chaque session indépendamment.
2. **ModeGuard** : routes Volet 1 → `require_full_mode`. Routes plan externe → `require_tracking_mode`. Routes Volet 2 → pas de restriction.
3. **Jamais effacer** : toujours archiver (`status = "archived"`), jamais `DELETE`.
4. **State LangGraph** : uniquement types primitifs/dicts. Session DB via `config["configurable"]["db"]`.
5. **Flux V1 → V2** : unidirectionnel. `apply_energy_snapshot` lit, ne pousse jamais.
6. **Human-in-the-loop** : préservé aux 2 INTERRUPT existants. Ne pas bypasser.
7. **TDD obligatoire** : red → green → refactor. Invariant pytest ≥ 1243 tests passing.
```

- [ ] **Step 2: Verify the file was created**

```bash
head -5 resilio-master-v3.md && wc -l resilio-master-v3.md
```
Expected: starts with `# RESILIO HYBRID COACH — Document Maître V3`, file is 300+ lines.

---

### Task 3: Archive v2 and update CLAUDE.md

**Files:**
- Move: `resilio-master-v2.md` → `docs/archive/resilio-master-v2_archived_2026-04-12.md`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Create archive directory and move v2**

```bash
mkdir -p docs/archive
cp resilio-master-v2.md docs/archive/resilio-master-v2_archived_2026-04-12.md
git rm resilio-master-v2.md
```
Expected: `resilio-master-v2.md` removed from root, copy in `docs/archive/`.

- [ ] **Step 2: Update CLAUDE.md — Quick Start section**

In `CLAUDE.md`, replace the Quick Start block:

```markdown
**Tech Stack**: Python 3.13 (FastAPI backend), Next.js (frontend), SQLite (persistence), Poetry (dependency management).
```

With:

```markdown
**Tech Stack**: Python 3.13 (FastAPI backend), Next.js (frontend), PostgreSQL + psycopg2 (persistence), Poetry (dependency management), LangGraph (coaching orchestration).

**Master Architecture Doc**: `resilio-master-v3.md` (racine du repo) — référence unique V3.
```

- [ ] **Step 3: Update CLAUDE.md — Phase Status table**

In `CLAUDE.md`, replace the Phase Status table with:

```markdown
| Phase | Scope | Status |
|---|---|---|
| 0–6 | Setup, schemas, agents v1, connectors, frontend, Docker, E2E | ✅ Complete — tagged v1.0.0 |
| 7 | Biking + Swimming + Nutrition + Recovery agents + core logic + endpoints | ✅ Complete |
| 8 | Session detail, logging, history (backend + frontend) | ✅ Complete |
| 9 | Connector sync (Hevy→SessionLog, Terra→Recovery, Strava improved) + Settings UI | ✅ Complete |
| V3-A | PostgreSQL + Alembic (4 migrations) | ✅ Complete |
| V3-B | ModeGuard + coaching_mode + PATCH /mode | ✅ Complete |
| V3-C | EnergyCycleService + check-in routes | ✅ Complete |
| V3-D | LangGraph coaching graph (11 nodes) + CoachingService + approve/revise | ✅ Complete |
| V3-E | ExternalPlan CRUD + import fichier (Claude Haiku) | ❌ Not started |
| V3-F | detect_energy_patterns() + challenges proactifs | ❌ Not started |
| V3-G | Frontend check-in + energy card + tracking page | ❌ Not started |
| V3-H | E2E tests 2-volet + CLAUDE.md final | ❌ Not started |
```

- [ ] **Step 4: Update CLAUDE.md — Key References section**

In `CLAUDE.md`, update (or add) the Key References section to read:

```markdown
## Key References

- **Master Architecture V3**: `resilio-master-v3.md` ← RÉFÉRENCE PRINCIPALE
- **Roadmap Phases 9–11**: `docs/superpowers/specs/2026-04-09-phases7-11-roadmap.md`
- **Architecture Modulaire 2-Volets**: `docs/superpowers/specs/2026-04-11-modular-architecture-design.md`
- **Phase 8 Design**: `docs/superpowers/specs/2026-04-10-phase8-design.md`
- **Coaching Methodology**: `docs/coaching/methodology.md`
- **Master V2 (archivé)**: `docs/archive/resilio-master-v2_archived_2026-04-12.md`
```

- [ ] **Step 5: Verify CLAUDE.md looks correct**

```bash
grep -n "resilio-master-v3\|PostgreSQL\|V3-D\|V3-E" CLAUDE.md
```
Expected: finds references to `resilio-master-v3.md`, `PostgreSQL`, and V3 phases.

---

### Task 4: Create SESSION_REPORT.md

**Files:**
- Create: `SESSION_REPORT.md` (repo root)

- [ ] **Step 1: Create the file**

Create `SESSION_REPORT.md` at the repo root:

```markdown
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
- Dépend : `anthropic>=0.25` (déjà dans pyproject.toml ?)

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

## Invariants à respecter dans chaque session

1. `pytest tests/` doit passer (≥ 1243 tests)
2. `npx tsc --noEmit` doit passer (frontend)
3. `poetry install` doit réussir
4. Chaque session produit des commits atomiques fréquents
5. Volet 2 doit fonctionner sans Volet 1 (tester en isolation)
6. `resilio-master-v3.md` fait autorité — toute décision qui s'en écarte doit être documentée
```

- [ ] **Step 2: Verify the file was created**

```bash
head -5 SESSION_REPORT.md
```
Expected: starts with `# SESSION 0 — Rapport de Consolidation V3`.

---

### Task 5: Final commit

**Files:**
- Commit: `resilio-master-v3.md` (new)
- Commit: `docs/archive/resilio-master-v2_archived_2026-04-12.md` (moved)
- Commit: `CLAUDE.md` (modified)
- Commit: `SESSION_REPORT.md` (new)
- Commit: `docs/superpowers/plans/2026-04-12-session0-master-v3-consolidation.md` (this plan)

- [ ] **Step 1: Verify all files ready**

```bash
git status --short
```
Expected: `A resilio-master-v3.md`, `A docs/archive/resilio-master-v2_archived_2026-04-12.md`, `D resilio-master-v2.md`, `M CLAUDE.md`, `A SESSION_REPORT.md`, `A docs/superpowers/plans/2026-04-12-session0-master-v3-consolidation.md`.

- [ ] **Step 2: Stage and commit**

```bash
git add resilio-master-v3.md \
        docs/archive/resilio-master-v2_archived_2026-04-12.md \
        CLAUDE.md \
        SESSION_REPORT.md \
        docs/superpowers/plans/2026-04-12-session0-master-v3-consolidation.md
git commit -m "docs(session0): consolidate resilio-master-v3 + archive v2 + update CLAUDE.md"
```
Expected: clean git status, 1 commit with all files.

- [ ] **Step 3: Verify final state**

```bash
git log --oneline -3
ls resilio-master-v3.md SESSION_REPORT.md docs/archive/resilio-master-v2_archived_2026-04-12.md
git status --short
```
Expected: 3 recent commits, all 3 files exist, working tree clean.

---

## Self-Review

**Spec coverage check:**
- ✅ Commit pending artifacts (Task 1)
- ✅ resilio-master-v3.md avec les 12 sections demandées (Task 2)
- ✅ Archive resilio-master-v2.md (Task 3)
- ✅ CLAUDE.md mis à jour : master reference + tech stack + phase status (Task 3)
- ✅ SESSION_REPORT.md avec backlog ordonné 7 sessions (Task 4)
- ✅ Final commit propre (Task 5)

**Placeholder scan:** Aucun TBD, TODO, ou section incomplète. Tous les paths de fichiers sont exacts.

**Type consistency:** Pas de code fonctionnel — N/A.

**Scope check:** Session purement documentaire, pas de code fonctionnel touché.
