# Resilio+ — Architecture Modulaire 2 Volets
**Date :** 2026-04-11  
**Statut :** Approuvé  
**Auteur :** Brainstorming session

---

## Contexte

Ce document définit l'architecture modulaire de Resilio+ autour de deux volets complémentaires et indépendants. Il remplace et consolide les décisions V3 partiellement documentées dans `docs/resilio-v3-master.md` et `v3-claude-md-additions.md`.

---

## 1. Vision — 2 Modes d'utilisation

Resilio+ supporte exactement **2 modes** :

| Mode | Volets actifs | Description |
|---|---|---|
| **Full Coaching** | Volet 1 + Volet 2 | Plan IA personnalisé + suivi Energy Cycle |
| **Tracking Only** | Volet 2 seul | Plan externe (coach humain) + suivi Energy Cycle |

**Le Energy Cycle (Volet 2) est toujours actif**, quel que soit le mode. Il n'existe pas de mode "Coaching Only".

---

## 2. Mode System

### Stockage

```python
# backend/app/db/models.py — AthleteModel
coaching_mode = Column(String, nullable=False, default="full")
# Valeurs : "full" | "tracking_only"
```

```python
# backend/app/schemas/athlete.py
coaching_mode: Literal["full", "tracking_only"] = "full"
```

### Onboarding

L'onboarding ajoute une **étape 0** (choix du mode) avant les étapes existantes :

```
Étape 0 : Choix du mode
  [A] J'ai besoin d'un plan personnalisé       → coaching_mode = "full"
  [B] J'ai déjà un coach / un plan             → coaching_mode = "tracking_only"

Mode "full"          → étapes 1-3 actuelles (profil complet)
Mode "tracking_only" → profil allégé (nom, sex, poids, sports, objectifs)
                        puis import/saisie plan externe
```

Champs **obligatoires en Tracking Only** : prénom, sex, poids, FFM estimé, sports actifs. Le FFM est requis pour le calcul EA du Energy Cycle.

### ModeGuard (FastAPI dependency)

```python
# backend/app/dependencies/mode_guard.py

def require_full_mode(athlete: AthleteModel = Depends(get_current_athlete)) -> AthleteModel:
    if athlete.coaching_mode != "full":
        raise HTTPException(403, "Nécessite le mode Full Coaching")
    return athlete

def require_tracking_mode(athlete: AthleteModel = Depends(get_current_athlete)) -> AthleteModel:
    if athlete.coaching_mode != "tracking_only":
        raise HTTPException(403, "Réservé au mode Tracking Only")
    return athlete
```

Routes coaching → `Depends(require_full_mode)`  
Routes plan externe → `Depends(require_tracking_mode)`  
Routes Energy Cycle → aucune restriction de mode

### Switch de mode

```
PATCH /athletes/{id}/mode
body: { "coaching_mode": "tracking_only" | "full" }
```

| Transition | Données préservées | Données désactivées (non supprimées) |
|---|---|---|
| Full → Tracking Only | Historique Energy Cycle, sessions loggées, plans passés | Plan actif archivé (`status = "archived"`) |
| Tracking Only → Full | Historique Energy Cycle, sessions loggées, plan externe | Plan externe reste en lecture |

**Règle absolue : on n'efface jamais.** Le switch change ce qui est actif, pas ce qui existe.

---

## 3. Volet 2 — Energy Cycle

### Base existante (réutilisée sans modification)

- `backend/app/agents/energy_coach/agent.py` — `EnergyCoach` avec 5 skills + `create_snapshot()`
- `backend/app/models/athlete_state.py` — `EnergySnapshot`, `HormonalProfile`, `AthleteStateV3`
- `backend/app/models/schemas.py` — tables `energy_snapshots`, `hormonal_profiles`, `allostatic_entries`
- `backend/app/core/allostatic.py`, `energy_availability.py`, `hormonal.py`
- `data/allostatic_weights.json`, `ea_thresholds.json`, `hormonal_adjustments.json`

### Daily check-in (5 questions, < 60 secondes)

Extension du `data/energy_coach_check_in_schema.json` — ajout de 2 questions subjectives :

```json
{
  "questions": [
    { "id": "work_intensity",  "options": ["light","normal","heavy","exhausting"] },
    { "id": "stress_level",    "options": ["none","mild","significant"] },
    { "id": "legs_feeling",    "options": ["fresh","normal","heavy","dead"] },
    { "id": "energy_global",   "options": ["great","ok","low","exhausted"] },
    { "id": "cycle_phase",     "options": ["menstrual","follicular","ovulation","luteal"],
      "required": false, "condition": "hormonal_profile.enabled == true" }
  ],
  "comment": { "optional": true, "max_chars": 140 },
  "estimated_duration_seconds": 45,
  "frequency": "daily",
  "optimal_timing": "morning"
}
```

**Calcul `subjective_score` (0–100, 100 = charge maximale) :**
```python
leg_scores    = {"fresh": 0, "normal": 25, "heavy": 60, "dead": 90}
energy_scores = {"great": 0, "ok": 20,    "low": 55,  "exhausted": 85}
subjective_score = (leg_scores[legs] + energy_scores[energy]) / 2
```

Une seule soumission par jour. Pas d'édition — correction via commentaire libre.

### API standalone (fonctionne sans Head Coach)

```
POST /athletes/{id}/checkin
     body: CheckInInput (5 questions + commentaire optionnel)
     → crée EnergySnapshot, stocke en DB
     → retourne ReadinessResponse

GET  /athletes/{id}/readiness
     → readiness du jour (ou dernier disponible si pas de check-in aujourd'hui)

GET  /athletes/{id}/energy/history?days=28
     → historique snapshots + tendances calculées

PATCH /athletes/{id}/hormonal-profile
      → mise à jour profil hormonal (déclaration jour 1, correction cycle)
```

### Algorithme de réconciliation objectif vs subjectif

```python
@dataclass
class ReadinessResponse:
    date:               date
    objective_score:    float   # 0–100 (HRV, ACWR, sommeil)
    subjective_score:   float   # 0–100 (jambes + énergie check-in)
    final_readiness:    float   # blend pondéré
    divergence:         float   # abs(objective - subjective)
    divergence_flag:    str     # "none" | "moderate" | "high"
    traffic_light:      str     # "green" | "yellow" | "red"
    allostatic_score:   float
    energy_availability: float
    intensity_cap:      float
    insights:           list[str]
```

**Calcul final_readiness :**
```python
divergence = abs(objective_score - subjective_score)
weight_subjective = 0.55 if divergence > 25 else 0.40
final_readiness = (
    objective_score * (1 - weight_subjective) +
    subjective_score * weight_subjective
)
```

**Seuils divergence :**
- `< 15 pts` → `"none"` — données cohérentes
- `15–30 pts` → `"moderate"` — signal à surveiller
- `> 30 pts` → `"high"` — divergence significative, insight affiché

**Insights — règles (factuels, jamais prescriptifs en Tracking Only) :**
- Divergence haute → *"HRV normale mais jambes à dead. Ton ressenti compte."*
- Jambes heavy ≥ 3 lundis → *"3e lundi consécutif avec jambes heavy. Tendance à surveiller."*
- ACWR ≥ 1.38 + check-in ≤ 4/10 → *"Si tu as un coach humain, c'est un bon moment pour l'informer."*
- RED-S signal → *"EA sous le seuil 3 jours consécutifs. Consulte un professionnel de santé."*

### EnergyCycleService

```python
# backend/app/services/energy_cycle_service.py

class EnergyCycleService:
    def submit_checkin(athlete_id: str, checkin: CheckInInput) -> ReadinessResponse: ...
    def get_today_snapshot(athlete_id: str) -> EnergySnapshot | None: ...
    def get_readiness(athlete_id: str) -> ReadinessResponse: ...
    def get_history(athlete_id: str, days: int = 28) -> list[EnergySnapshot]: ...
    def update_hormonal_profile(athlete_id: str, data: HormonalProfileUpdate) -> None: ...
```

`EnergyCycleService` ne connaît pas l'existence du coaching graph. Interface unidirectionnelle.

---

## 4. Volet 1 — Coaching IA (LangGraph)

### Ce que LangGraph remplace

`HeadCoach.build_week()` → remplacé par `coaching_graph` (StateGraph).  
`routes/workflow.py` (create-plan, weekly-sync) → délèguent à `CoachingService`.  
Les agents spécialistes conservent leur interface `analyze(context)` — ils deviennent des nodes.

### AthleteCoachingState

```python
# backend/app/graphs/state.py
from typing import Annotated
from langgraph.graph import add_messages

class AthleteCoachingState(TypedDict):
    athlete_id:       str
    athlete:          AthleteModel
    context:          AgentContext
    load_history:     list[float]
    budgets:          dict
    recommendations:  list[AgentRecommendation]
    acwr:             ACWRResult | None
    conflicts:        list[Conflict]
    proposed_plan:    WeeklyPlan | None
    energy_snapshot:  EnergySnapshot | None      # injecté par apply_energy_snapshot
    human_approved:   bool
    human_feedback:   str | None
    final_plan:       WeeklyPlan | None
    messages:         Annotated[list, add_messages]
```

### Topologie du coaching graph (11 nodes)

```
START
  → analyze_profile          (analyze_goals → budgets sport)
  → compute_acwr             (ACWR + readiness, bloque si DANGER)
  → delegate_specialists     (fan-out parallèle vers agents actifs)
  → merge_recommendations    (agrège AgentRecommendation[])
  → detect_conflicts         (3 couches)
  ┌─ conflicts → resolve_conflicts (circuit breaker, max 2 itérations)
  └─ no conflicts ──────────────→
  → build_proposed_plan
  → [INTERRUPT] present_to_athlete    ← human-in-the-loop #1
  ┌─ rejected → revise_plan → back to delegate_specialists (max 1x)
  └─ approved →
  → apply_energy_snapshot    (lit EnergySnapshot via EnergyCycleService)
  ┌─ intensity_cap < 0.85 → [INTERRUPT] confirm_adjustment  ← human-in-the-loop #2 (optionnel)
  └─ cap ok →
  → finalize_plan            (persiste en DB)
END
```

**Les 11 nodes :**

| Node | Rôle | Interrupt |
|---|---|---|
| `analyze_profile` | `analyze_goals()` → sport budgets | Non |
| `compute_acwr` | ACWR + readiness pré-plan | Non |
| `delegate_specialists` | Fan-out parallèle agents actifs | Non |
| `merge_recommendations` | Agrège `AgentRecommendation[]` | Non |
| `detect_conflicts` | 3 couches scheduling/muscle/fatigue | Non |
| `resolve_conflicts` | Circuit breaker, menu résolutions | Non |
| `build_proposed_plan` | Construit `WeeklyPlan` draft | Non |
| `present_to_athlete` | Envoie le plan, attend approbation | **OUI** |
| `revise_plan` | Intègre feedback, repasse aux spécialistes | Non |
| `apply_energy_snapshot` | Lit snapshot du jour, ajuste intensity_cap | Non |
| `finalize_plan` | Persiste en DB, déclenche notifications | Non |

### Weekly review graph (5 nodes, distinct)

```
START → analyze_actual_vs_planned → compute_new_acwr →
update_athlete_state → [INTERRUPT] present_review → apply_adjustments → END
```

### CoachingService

```python
# backend/app/services/coaching_service.py

class CoachingService:
    def create_plan(athlete_id: str) -> str:           # retourne thread_id LangGraph
    def resume_plan(thread_id: str, approved: bool, feedback: str | None) -> WeeklyPlan: ...
    def weekly_review(athlete_id: str) -> str:         # retourne thread_id
    def resume_review(thread_id: str, approved: bool) -> None: ...
```

---

## 5. Collaboration Volet 1 ↔ Volet 2 (mode Full)

### Règle d'or : unidirectionnel

```
EnergyCycleService → (lecture seule) → coaching graph
coaching graph     → (jamais)        → EnergyCycleService
```

### apply_energy_snapshot — logique complète

```python
def apply_energy_snapshot(state: AthleteCoachingState) -> AthleteCoachingState:
    snapshot = EnergyCycleService.get_today_snapshot(state["athlete_id"])

    if snapshot is None:
        state["messages"].append(
            AIMessage("Check-in non complété. Plan appliqué sans ajustement énergie.")
        )
        return state

    state["energy_snapshot"] = snapshot

    # Override subjectif si divergence haute
    if snapshot.subjective_score is not None:
        divergence = abs(snapshot.objective_score - snapshot.subjective_score)
        if snapshot.subjective_score < 40 and divergence > 30:
            snapshot = snapshot.model_copy(
                update={"recommended_intensity_cap": min(snapshot.recommended_intensity_cap, 0.80)}
            )

    if snapshot.recommended_intensity_cap < 1.0:
        state["proposed_plan"] = _apply_intensity_cap(
            state["proposed_plan"], snapshot.recommended_intensity_cap
        )

    if snapshot.veto_triggered:
        state["proposed_plan"] = _apply_veto(state["proposed_plan"])

    return state
```

### Challenges proactifs (background job hebdomadaire)

APScheduler (existant dans `core/sync_scheduler.py`) — job `detect_energy_patterns()` :

| Pattern | Condition | Message Head Coach |
|---|---|---|
| Jambes lourdes récurrentes | `legs ∈ {heavy,dead}` ≥ 3/7 derniers jours | *"Tes jambes sont lourdes 3 lundis de suite. Volume trop élevé ?"* |
| Stress chronique | `stress == "significant"` ≥ 4/7 jours | *"Semaine chargée côté stress. On allège cette semaine ?"* |
| Divergence persistante | `divergence_flag == "high"` ≥ 3 jours consécutifs | *"Ton ressenti et tes données divergent depuis 3 jours. On en parle ?"* |
| RED-S signal | `EA < seuil` ≥ 3 jours consécutifs | Alert RED-S (règle absolue #13) |

Messages dans la conversation Head Coach du dashboard — pas de notifications push. L'athlète peut répondre, ignorer, ou demander un ajustement.

### Philosophie Head Coach (préservée)

- ❌ N'annule jamais une séance sans confirmation humaine
- ❌ Ne pénalise pas l'athlète qui ignore un check-in
- ✅ Recommande toujours, décide jamais seul
- ✅ L'athlète peut override : *"Je me sens bien, on y va"*

---

## 6. Plan externe (Mode Tracking Only)

### Data model

```python
# Nouvelles tables

class ExternalPlanModel(Base):
    __tablename__ = "external_plans"
    id           = Column(String, primary_key=True)
    athlete_id   = Column(String, ForeignKey("athletes.id"), nullable=False)
    title        = Column(String, nullable=False)
    source       = Column(String, nullable=False)   # "manual" | "file_import"
    status       = Column(String, nullable=False, default="active")  # "active" | "archived"
    start_date   = Column(Date, nullable=True)
    end_date     = Column(Date, nullable=True)
    created_at   = Column(DateTime(timezone=True), nullable=False)
    athlete      = relationship("AthleteModel", back_populates="external_plans")
    sessions     = relationship("ExternalSessionModel", back_populates="plan",
                                cascade="all, delete-orphan")

class ExternalSessionModel(Base):
    __tablename__ = "external_sessions"
    id           = Column(String, primary_key=True)
    plan_id      = Column(String, ForeignKey("external_plans.id"), nullable=False)
    athlete_id   = Column(String, ForeignKey("athletes.id"), nullable=False)
    session_date = Column(Date, nullable=False)
    sport        = Column(String, nullable=False)
    title        = Column(String, nullable=False)
    description  = Column(Text, nullable=True)
    duration_min = Column(Integer, nullable=True)
    status       = Column(String, default="planned")  # "planned" | "completed" | "skipped"
    plan         = relationship("ExternalPlanModel", back_populates="sessions")
    log          = relationship("SessionLogModel", back_populates="external_session",
                                uselist=False)
```

Le logging réutilise `SessionLogModel` existant (Phase 8) — même endpoint, même formulaire.

**Règle : un seul plan actif.** `ExternalPlanModel` et `TrainingPlanModel` ne peuvent pas être simultanément `status = "active"`.

### API

```
# Saisie manuelle
POST   /athletes/{id}/external-plan                          → crée plan + titre
POST   /athletes/{id}/external-plan/sessions                 → ajoute une session
PATCH  /athletes/{id}/external-plan/sessions/{session_id}    → modifie
DELETE /athletes/{id}/external-plan/sessions/{session_id}    → supprime

# Import fichier
POST   /athletes/{id}/external-plan/import
       body: multipart/form-data { file (PDF/TXT/CSV/ICS), title, start_date }
       → Claude Haiku parse le fichier
       → retourne ExternalPlanDraft (non sauvegardé)

POST   /athletes/{id}/external-plan/import/confirm
       body: ExternalPlanDraft (édité ou tel quel)
       → sauvegarde définitive
```

### ExternalPlanDraft (format intermédiaire)

```json
{
  "title": "Plan marathon 16 semaines",
  "sessions_parsed": 48,
  "sessions": [
    {
      "session_date": "2026-04-14",
      "sport": "running",
      "title": "Long run",
      "description": "22km allure facile Z2",
      "duration_min": 130
    }
  ],
  "parse_warnings": ["Semaine 3 : date ambiguë, assignée au 2026-04-28"]
}
```

L'athlète voit le draft, peut éditer/supprimer, puis confirme.

---

## 7. Infrastructure

### Base de données — PostgreSQL + Alembic

Migration unique `0001_postgresql_and_2volet.py` contenant :
- Toutes les tables V2 existantes (7 tables)
- Tables V3 déjà créées (energy_snapshots, hormonal_profiles, allostatic_entries)
- Nouvelles tables : external_plans, external_sessions
- Nouveau champ : `athletes.coaching_mode`

`backend/app/db/database.py` : `create_async_engine` PostgreSQL via `asyncpg`.  
`docker-compose.yml` : service `db` PostgreSQL 16 alpine avec healthcheck.

### Background jobs — APScheduler (préservé)

`core/sync_scheduler.py` — ajout du job hebdomadaire `detect_energy_patterns()`.  
Pas de Celery/Redis — over-ingénierie à ce stade.

### Nouvelles dépendances Python

```toml
langgraph = ">=0.2"
asyncpg = ">=0.29"
psycopg2-binary = ">=2.9"
anthropic = ">=0.25"   # Claude Haiku pour import fichier
```

---

## 8. Nouveaux fichiers

```
backend/app/
  services/
    energy_cycle_service.py
    coaching_service.py
    external_plan_service.py
  graphs/
    coaching_graph.py          — StateGraph 11 nodes
    weekly_review_graph.py     — StateGraph 5 nodes
    state.py                   — AthleteCoachingState TypedDict
  routes/
    checkin.py
    external_plan.py
    mode.py
  dependencies/
    mode_guard.py

alembic/versions/
  0001_postgresql_and_2volet.py

frontend/src/app/
  onboarding/mode/page.tsx
  checkin/page.tsx
  energy/                      — composants dashboard énergie (intégré dashboard principal)
  tracking/page.tsx
  tracking/import/page.tsx
```

---

## 9. Fichiers modifiés

| Fichier | Modification |
|---|---|
| `backend/app/db/models.py` | `coaching_mode` sur `AthleteModel` + relations `external_plans` |
| `backend/app/db/database.py` | SQLite sync → PostgreSQL async |
| `backend/app/routes/workflow.py` | Délègue à `CoachingService` (LangGraph) |
| `backend/app/routes/onboarding.py` | Capture `coaching_mode` étape 0 |
| `backend/app/routes/athletes.py` | Expose `coaching_mode` |
| `backend/app/schemas/athlete.py` | Ajoute `coaching_mode` |
| `backend/app/core/sync_scheduler.py` | Ajoute `detect_energy_patterns()` |
| `backend/app/main.py` | Monte nouveaux routers |
| `docker-compose.yml` | Service PostgreSQL |
| `pyproject.toml` | Nouvelles dépendances |
| `data/energy_coach_check_in_schema.json` | Ajout questions legs_feeling + energy_global |
| `frontend/src/app/onboarding/page.tsx` | Redirect vers étape 0 |
| `frontend/src/app/dashboard/page.tsx` | Card Energy Cycle + CTAs selon mode |
| `frontend/src/lib/api.ts` | Nouveaux appels API |
| `frontend/src/components/TopNav.tsx` | Lien "Énergie" + "Mon plan" |

## 10. Fichiers NON modifiés

```
backend/app/agents/energy_coach/      — intact
backend/app/agents/head_coach.py      — préservé (utilisé par les nodes du graph)
backend/app/models/athlete_state.py   — intact
backend/app/models/schemas.py         — intact
backend/app/core/allostatic.py        — intact
backend/app/core/energy_availability.py — intact
backend/app/core/hormonal.py          — intact
tous les agents spécialistes          — interfaces analyze() préservées
data/*.json (sauf check_in_schema)    — intacts
```

---

## 11. Décisions architecturales non-négociables

12. **Energy Coach** : 7e agent. Produit `EnergySnapshot`. Ne prescrit jamais de workouts. Fichier : `agents/energy_coach/`
13. **Charge allostatique** : variable d'entraînement de premier ordre. `core/allostatic.py`. Seuils dans `data/allostatic_weights.json`.
14. **Energy Availability (EA)** : métrique de santé prioritaire. Seuil critique → veto indépendant du HRV. `data/ea_thresholds.json`.
15. **Cycle hormonal féminin** : intégration transversale dans tous les agents. `data/hormonal_adjustments.json`.
16. **Recovery Coach veto V3** : 5 composantes — HRV + ACWR + EA + Allostatic Score + Phase cycle.
17. **LangGraph** : coaching workflow uniquement (11 nodes). Energy Cycle = service Python natif.
18. **2 modes** : `"full"` (Volet 1 + Volet 2) et `"tracking_only"` (Volet 2 seul). Pas de mode coaching sans Energy Cycle.
19. **Switch de mode** : non destructif. On archive, jamais on efface.
20. **Import fichier** : Claude Haiku parse le fichier. L'athlète confirme le draft avant sauvegarde.
21. **PostgreSQL** : migration unique incluant toutes les tables V2 + V3 + 2-volet.

---

## 12. Workflow d'exécution recommandé

| Phase | Scope | Dépendances |
|---|---|---|
| **V3-A** | PostgreSQL + Alembic + migration complète (tables V2+V3+2volet) | Aucune |
| **V3-B** | ModeGuard + mode onboarding + PATCH /mode | V3-A |
| **V3-C** | EnergyCycleService + routes check-in/readiness/history | V3-A |
| **V3-D** | LangGraph coaching graph (remplace build_week) | V3-B, V3-C |
| **V3-E** | Plan externe (CRUD manuel + import fichier Haiku) | V3-B |
| **V3-F** | Background jobs + challenges proactifs | V3-C, V3-D |
| **V3-G** | Frontend : check-in + energy card dashboard + tracking plan | V3-C, V3-E |
| **V3-H** | Tests E2E 2-volet + revise-claude-md | Toutes |
