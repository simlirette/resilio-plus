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
scheduler.add_job(run_energy_patterns_weekly, trigger="cron", day_of_week="mon", hour=6)
# → détecte 4 patterns (jambes lourdes, stress chronique, divergence, RED-S)
# → stocke messages dans head_coach_messages table (déduplication 7j)
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
| detect_energy_patterns() APScheduler (4 patterns) | `core/sync_scheduler.py` | S-4 ✅ |
| HeadCoachMessageModel + head_coach_messages table | `models/schemas.py`, migration 0005 | S-4 ✅ |

### NON IMPLÉMENTÉ ❌

| Composant | Scope | Session cible |
|---|---|---|
| ExternalPlan CRUD (saisie manuelle) | `services/external_plan_service.py`, `routes/external_plan.py` | S-1 |
| Import fichier plan externe (Claude Haiku) | `routes/external_plan.py` (POST /import) | S-2 |
| Weekly review graph (5 nodes) | `graphs/weekly_review_graph.py` | S-3 |
| CoachingService.weekly_review() | `services/coaching_service.py` (ajout) | S-3 |
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
| **S-7** | E2E tests 2-volet + CLAUDE.md final | S-1 → S-4 terminées | `tests/e2e/` (nouveaux scénarios) |

### Décisions architecturales non-négociables (rappel pour sessions parallèles)

1. **Modularité** : Volet 2 fonctionne sans Volet 1. Tester chaque session indépendamment.
2. **ModeGuard** : routes Volet 1 → `require_full_mode`. Routes plan externe → `require_tracking_mode`. Routes Volet 2 → pas de restriction.
3. **Jamais effacer** : toujours archiver (`status = "archived"`), jamais `DELETE`.
4. **State LangGraph** : uniquement types primitifs/dicts. Session DB via `config["configurable"]["db"]`.
5. **Flux V1 → V2** : unidirectionnel. `apply_energy_snapshot` lit, ne pousse jamais.
6. **Human-in-the-loop** : préservé aux 2 INTERRUPT existants. Ne pas bypasser.
7. **TDD obligatoire** : red → green → refactor. Invariant pytest ≥ 1243 tests passing.
