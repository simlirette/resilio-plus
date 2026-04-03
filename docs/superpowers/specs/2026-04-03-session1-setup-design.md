# Session 1 — Setup : Design Spec

**Date :** 2026-04-03
**Statut :** Approuvé
**Session suivante :** S2 — Schémas (AthleteState Pydantic + modèles DB)

---

## Contexte

Le repo `/c/resilio-plus/` est partiellement structuré. Les fondations de session 1 éliminent toute dette de configuration avant que le code métier commence en S2. Approche choisie : fondation optimale (pyproject.toml + toolchain complet + Docker + Alembic).

### État du repo en entrée de S1

| Élément | Statut |
|---|---|
| `agents/*/system_prompt.md` | Existants et complets |
| `agents/head_coach/graph.py` + edge cases | Existants |
| `models/database.py` | Existant — schéma SQLAlchemy complet |
| `models/db_session.py` | Existant |
| `data/` (7 fichiers JSON) | Existants — manque `exercise_database.json` |
| `resilio_docs/resilio_docs/` (9 JSON) | Existants et complets |
| `training_books/` (5 livres) | Existants |
| `tests/conftest.py` | Existant et complet |
| `core/config.py` | Existant — 2 corrections à apporter |
| `docker-compose.yml` | Existant et complet |
| `.env.example` / `.env` | Existants |
| `requirements.txt` | À remplacer par `pyproject.toml` |
| `Dockerfile` | Manquant |
| `alembic/` | Manquant |
| `data/exercise_database.json` | Manquant |

---

## Livrables S1

### 1. `pyproject.toml` — Remplacement de `requirements.txt`

Gestionnaire : **Poetry**. Source de vérité unique pour dépendances, config ruff, mypy, et pytest.

**Dépendances de production :**
- `fastapi`, `uvicorn[standard]`
- `sqlalchemy`, `asyncpg`, `alembic`
- `pydantic>=2.10`, `pydantic-settings>=2.7`
- `anthropic`, `langgraph`
- `httpx`, `python-multipart`
- `PyJWT`, `passlib[bcrypt]` — remplace `python-jose` (déprécié)
- `pandas`, `numpy`
- `python-dateutil`
- Note : `pytz` supprimé — remplacé par `zoneinfo` (stdlib Python 3.9+)
- Note : `httpx` dédupliqué (était listé deux fois dans `requirements.txt`)

**Dépendances de développement :**
- `pytest`, `pytest-asyncio`, `pytest-cov`
- `ruff` — linter + formatter (remplace black + flake8 + isort)
- `mypy` — vérification de types statique

**Config intégrée dans `pyproject.toml` :**
```toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]

[tool.mypy]
python_version = "3.12"
strict = true
ignore_missing_imports = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

`requirements.txt` est supprimé.

---

### 2. `Dockerfile` — Multi-stage

**Stage 1 — `builder` :**
- Image : `python:3.12-slim`
- Installe Poetry, exporte les dépendances de prod dans `/app/.venv`
- Aucune dépendance de dev dans l'image finale

**Stage 2 — `runtime` :**
- Image : `python:3.12-slim` vierge
- Copie uniquement `/app/.venv` + code source
- `ENV PATH="/app/.venv/bin:$PATH"`
- `CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]`
- `--reload` activé uniquement si `DEBUG=true` (géré via docker-compose override)

**`.dockerignore` créé :**
```
.git/
__pycache__/
*.pyc
*.pyo
.env
.venv/
node_modules/
frontend/.next/
*.db
```

`docker-compose.yml` non modifié — il est déjà correct.

---

### 3. Alembic — Migrations DB

**Structure créée :**
```
alembic.ini
alembic/
├── env.py
├── script.py.mako
└── versions/        ← vide en S1, première migration en S2
```

**`env.py` configuré :**
- Mode async (`run_async_migrations()` avec `asyncpg`)
- Importe `Base` depuis `models.database` — toutes les tables détectées automatiquement
- Lit `DATABASE_URL` depuis `core.config.settings` (pas de hardcoding)

**`alembic.ini` :**
- `script_location = alembic`
- `sqlalchemy.url` surchargé dans `env.py` via pydantic-settings

**En S1 :** Alembic configuré et prêt. Aucune migration générée (les modèles Pydantic n'existent pas encore). La première migration (`alembic revision --autogenerate -m "initial schema"`) sera faite en S2 après création de `models/athlete_state.py`.

---

### 4. `core/config.py` — Corrections Pydantic v2

Deux corrections, aucun nouveau champ :

**Correction 1 — Syntaxe Pydantic v2 :**
```python
# Avant (Pydantic v1)
class Config:
    env_file = ".env"

# Après (Pydantic v2)
model_config = SettingsConfigDict(
    env_file=".env",
    env_file_encoding="utf-8",
    case_sensitive=True,
)
```

**Correction 2 — Validation de sécurité :**
```python
@model_validator(mode="after")
def check_secret_key(self) -> "Settings":
    if not self.DEBUG and self.SECRET_KEY == "change-me-in-production":
        raise ValueError("SECRET_KEY must be set in production (DEBUG=False)")
    return self
```

---

### 5. `tests/conftest.py` — Aucune modification

Le fichier est complet et bien conçu :
- Fixtures DB async avec rollback par test
- Simon : dict brut, athlete DB, state DB, fatigue VERT (ACWR 1.05), fatigue ROUGE (ACWR 1.61)
- Vues filtrées Running Coach et Lifting Coach

Seul ajout : `asyncio_mode = "auto"` dans `pyproject.toml` (évite `@pytest.mark.asyncio` sur chaque test).

---

### 6. `data/exercise_database.json` — Exercices-clés (partiel)

Fichier créé avec les ~25-30 exercices utilisés dans les exemples du master doc (Upper A, Lower, Upper B). Structure par exercice :

```json
{
  "exercise_id": "D04AC939",
  "name": "Barbell Bench Press",
  "tier": 3,
  "muscle_primary": "chest",
  "muscle_secondary": ["shoulders", "triceps"],
  "equipment": ["barbell"],
  "movement_pattern": "horizontal_push",
  "sfr_score": 6,
  "form_cues_fr": ["Omoplates serrées", "Descends à 2-3cm du torse"],
  "hevy_exercise_id": "D04AC939"
}
```

Les 400+ exercices sont ajoutés en S7 (Lifting Coach). En S1 on pose la structure avec les exercices-clés pour que S7 parte d'une base réelle.

---

### 7. `CLAUDE.md` — Mise à jour état d'avancement

Modifications :
- Corriger `ANTHROPIC_MODEL` : `claude-sonnet-4-20250514` → `claude-sonnet-4-6`
- Ajouter section **"ÉTAT D'AVANCEMENT DES SESSIONS"** mise à jour après chaque session
- Marquer dans "STRUCTURE DU REPO" les fichiers qui existent déjà vs à créer
- Ajouter commande de démarrage local :
  ```bash
  docker compose up db -d
  poetry run uvicorn api.main:app --reload
  ```
- Règle ajoutée : CLAUDE.md ne documente que l'état actuel — jamais l'état futur

---

## Ce que S1 ne fait PAS

- Pas de `models/athlete_state.py` Pydantic → S2
- Pas de `connectors/` → S3-S4
- Pas de `api/main.py` → S11
- Pas de `frontend/` → S12-S13
- Pas de migration Alembic → S2 (après modèles Pydantic)
- Pas d'exercices database complet (400+) → S7
- Pas de tests métier → chaque session crée ses propres tests

---

## Commandes de vérification post-S1

```bash
# Vérifier l'installation
poetry install

# Linter
poetry run ruff check .

# Types
poetry run mypy .

# Tests (nécessite PostgreSQL via Docker)
docker compose up db -d
poetry run pytest tests/ -v

# Démarrage local
poetry run uvicorn api.main:app --reload
```

---

## Décisions prises

| Décision | Choix | Raison |
|---|---|---|
| Gestionnaire de paquets | Poetry | Séparation dev/prod, lock file reproductible |
| Linter/formatter | ruff | Remplace black + flake8 + isort en un outil |
| Auth | JWT (PyJWT + passlib) | Multi-user dès le départ, `python-jose` déprécié |
| Timezone | `zoneinfo` (stdlib) | `pytz` redondant en Python 3.9+ |
| Dockerfile | Multi-stage | Image prod légère (~200MB vs ~800MB) |
| Alembic | Configuré mais sans migration | Première migration en S2 avec modèles Pydantic |
| `exercise_database.json` | Partiel (25-30 exercices) | YAGNI — 400+ exercices en S7 |
