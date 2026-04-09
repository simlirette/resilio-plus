# Phase 4 — Backend Frontend-Ready
**Date:** 2026-04-09
**Status:** Approved

---

## Objectif

Compléter le backend pour qu'il soit entièrement utilisable par le frontend (Phase 5). Quatre livrables : auth JWT, endpoint d'onboarding unifié, dérivation de `week_number`, boucle de suivi hebdomadaire.

Chat streaming et agents SwimmingCoach/BikeCoach/NutritionCoach reportés à Phase 5/6.

---

## 1. Auth JWT

### Nouveaux fichiers
- `backend/app/db/models.py` — ajouter `UserModel`
- `backend/app/schemas/auth.py` — `RegisterRequest`, `LoginRequest`, `TokenResponse`
- `backend/app/routes/auth.py` — router public `/auth`
- `backend/app/core/security.py` — utilitaires JWT + bcrypt

### Modèle UserModel
```python
class UserModel(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    athlete_id = Column(String, ForeignKey("athletes.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    athlete = relationship("AthleteModel", back_populates="user")
```

Ajouter `user = relationship("UserModel", back_populates="athlete", uselist=False)` dans `AthleteModel`.

### Endpoint
```
POST /auth/login      → { email, password } → TokenResponse
```

`/auth/register` est supprimé — l'inscription se fait uniquement via `/athletes/onboarding`.

`TokenResponse` : `{ access_token: str, token_type: "bearer", athlete_id: str }`

JWT signé HS256, expiration 24h. Secret dans variable d'environnement `JWT_SECRET` (défaut dev : `"resilio-dev-secret"`).

### Dépendance protégée
`backend/app/dependencies.py` — ajouter `get_current_athlete_id(token) -> str`.

Routes protégées : `/athletes/{id}/*`, `/athletes/{id}/plan`, `/athletes/{id}/connectors`.

Règle d'autorisation : l'`athlete_id` du token doit correspondre au `{id}` du path. Sinon HTTP 403.

### Librairies ajoutées
- `python-jose[cryptography]` — JWT
- `passlib[bcrypt]` — hashing

---

## 2. Onboarding API

### Endpoint
```
POST /athletes/onboarding   (public — pas de token requis)
```

**Body :** `OnboardingRequest` = `AthleteCreate` + `email: str` + `password: str` + `plan_start_date: date`

**Traitement :**
1. Vérifier email non dupliqué → HTTP 409 si conflit
2. Créer `AthleteModel`
3. Créer `UserModel` avec `hashed_password`
4. Générer le premier plan (même logique que `POST /athletes/{id}/plan`)
5. Générer le JWT

**Response :** `OnboardingResponse`
```python
class OnboardingResponse(BaseModel):
    athlete: AthleteResponse
    plan: TrainingPlanResponse
    access_token: str
    token_type: str = "bearer"
```

### Routing
`POST /athletes/onboarding` est monté dans un router dédié `routes/onboarding.py` avec `prefix="/athletes"`, enregistré **avant** le router athletes dans `main.py`. Cela évite que FastAPI matche `"onboarding"` comme un `{athlete_id}`.

### Fichiers touchés
- `backend/app/schemas/auth.py` — ajouter `OnboardingRequest`, `OnboardingResponse`
- `backend/app/routes/onboarding.py` — nouveau router dédié (pas dans `routes/auth.py`)
- `backend/app/routes/athletes.py` — extraire helper `_create_plan_for_athlete(athlete_id, start_date, db) -> TrainingPlanModel` pour éviter la duplication

---

## 3. Dérivation de week_number

### Problème
`week_number=1` hardcodé dans `backend/app/routes/plans.py`.

### Solution
Compter les plans existants pour cet athlète :
```python
week_number = db.query(TrainingPlanModel)\
    .filter(TrainingPlanModel.athlete_id == athlete_id)\
    .count() + 1
```

Appliqué dans `POST /athletes/{id}/plan` et dans le helper partagé `_create_plan_for_athlete`.

---

## 4. Boucle de suivi hebdomadaire

### WeeklyReviewModel — colonnes à ajouter
Ajouter à `WeeklyReviewModel` existant :
```python
week_number = Column(Integer, nullable=False)
planned_hours = Column(Float, nullable=False)
actual_hours = Column(Float, nullable=True)   # null si pas encore de données
acwr = Column(Float, nullable=True)
adjustment_applied = Column(Float, nullable=True)  # ex: 0.9 = volume réduit 10%
plan_id = Column(String, ForeignKey("training_plans.id"), nullable=True)
```

Note : `plan_id` existe déjà dans le modèle actuel.

### Endpoint GET /athletes/{id}/week-status
Retourne l'état de la semaine en cours :
- Plan actif (le plus récent, basé sur `created_at`)
- Calcul `actual_hours` : somme des durées des activités Strava + Hevy dont la date tombe entre `plan.start_date` et `today` (inclus)
- Écart `planned_hours - actual_hours`

ACWR calculé sur les 28 derniers jours d'activités Strava (durée en heures par jour).

**Response :** `WeekStatusResponse`
```python
class WeekStatusResponse(BaseModel):
    week_number: int
    plan: TrainingPlanResponse
    planned_hours: float
    actual_hours: float
    completion_pct: float
    acwr: float | None
```

### Endpoint POST /athletes/{id}/review
Déclenche la boucle de fin de semaine :
1. Pull données connecteurs via `fetch_connector_data`
2. Calcule `actual_hours` (somme des activités Strava + Hevy de la semaine)
3. Calcule ACWR avec `backend/app/core/acwr.py`
4. Si ACWR > 1.3 → `adjustment = 0.9` (réduction 10% semaine suivante)
5. Si ACWR < 0.8 → `adjustment = 1.1` (hausse 10%)
6. Sinon → `adjustment = 1.0`
7. Sauvegarde `WeeklyReviewModel`
8. Retourne le résumé + suggestion pour la semaine suivante

**Body :** `WeeklyReviewRequest`
```python
class WeeklyReviewRequest(BaseModel):
    week_end_date: date
    readiness_score: float | None = None   # 1-10
    hrv_rmssd: float | None = None
    sleep_hours_avg: float | None = None
    comment: str = ""
```

**Response :** `WeeklyReviewResponse`
```python
class WeeklyReviewResponse(BaseModel):
    review_id: str
    week_number: int
    planned_hours: float
    actual_hours: float
    acwr: float
    adjustment_applied: float
    next_week_suggestion: str   # message lisible ex: "Volume réduit de 10% (ACWR élevé)"
```

### Fichiers touchés
- `backend/app/schemas/review.py` — nouveaux schémas
- `backend/app/routes/reviews.py` — nouveau router, monté dans `main.py`

---

## Architecture globale après Phase 4

```
POST /auth/login
POST /athletes/onboarding               ← nouveau (public, router dédié)

GET  /athletes/{id}                     ← protégé
PUT  /athletes/{id}                     ← protégé
DELETE /athletes/{id}                   ← protégé
POST /athletes/{id}/plan                ← protégé
GET  /athletes/{id}/plan                ← protégé
GET  /athletes/{id}/week-status         ← nouveau (protégé)
POST /athletes/{id}/review              ← nouveau (protégé)
POST /athletes/{id}/connectors/strava/authorize
GET  /athletes/{id}/connectors/strava/callback
POST /athletes/{id}/connectors/hevy
GET  /athletes/{id}/connectors
DELETE /athletes/{id}/connectors/{provider}
```

---

## Gestion d'erreurs

| Cas | HTTP |
|---|---|
| Email déjà utilisé | 409 |
| Credentials invalides (login) | 401 |
| Token manquant ou invalide | 401 |
| Token valide mais mauvais athlete_id | 403 |
| Athlète inexistant | 404 |
| Pas de plan pour la semaine courante | 404 |

---

## Tests (TDD obligatoire)

Chaque module = fichier de test dédié :
- `tests/backend/test_auth.py` — register, login, token invalide, email dupliqué
- `tests/backend/test_onboarding.py` — flux complet, email dupliqué, dates invalides
- `tests/backend/test_week_number.py` — dérivation correcte au 1er, 2e, 3e plan
- `tests/backend/test_weekly_review.py` — GET week-status, POST review, ajustements ACWR

---

## Livrables

- `backend/app/core/security.py`
- `backend/app/schemas/auth.py`
- `backend/app/schemas/review.py`
- `backend/app/routes/auth.py`
- `backend/app/routes/reviews.py`
- Modifications : `db/models.py`, `routes/athletes.py`, `routes/plans.py`, `dependencies.py`, `main.py`
- Branche : `feat/phase4-backend-ready`
