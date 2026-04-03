# Session 1 — Setup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Établir la fondation technique complète du repo Resilio+ — packaging Poetry, Dockerfile multi-stage, Alembic, corrections config, données d'exercices, CLAUDE.md à jour.

**Architecture:** Remplacement de `requirements.txt` par `pyproject.toml` (Poetry) comme source de vérité unique pour les dépendances et la config des outils (ruff, mypy, pytest). Docker multi-stage pour une image de prod légère. Alembic configuré en mode async pour PostgreSQL mais sans migration générée (première migration en S2).

**Tech Stack:** Python 3.12, Poetry, FastAPI, SQLAlchemy 2.0 async, PostgreSQL, Alembic, Ruff, Mypy, pytest-asyncio

---

## File Map

| Fichier | Action | Responsabilité |
|---|---|---|
| `pyproject.toml` | Créer | Dépendances prod/dev, config ruff/mypy/pytest |
| `requirements.txt` | Supprimer | Remplacé par pyproject.toml |
| `Dockerfile` | Créer | Build multi-stage prod |
| `.dockerignore` | Créer | Exclure fichiers inutiles du build |
| `alembic.ini` | Créer | Config Alembic (script_location, logging) |
| `alembic/env.py` | Créer | Connexion async PostgreSQL, import des modèles |
| `alembic/script.py.mako` | Créer | Template migrations |
| `alembic/versions/.gitkeep` | Créer | Dossier versions versionné |
| `core/config.py` | Modifier | Syntaxe Pydantic v2 + validator sécurité |
| `data/exercise_database.json` | Créer | ~30 exercices-clés avec structure validée |
| `CLAUDE.md` | Modifier | État d'avancement S1 et corrections |
| `tests/test_config.py` | Créer | Tests pour le validator de config |
| `tests/test_exercise_database.py` | Créer | Tests pour la structure JSON |

---

## Task 1 : `pyproject.toml` — Remplacement de `requirements.txt`

**Files:**
- Create: `pyproject.toml`
- Delete: `requirements.txt`

- [ ] **Step 1 : Créer `pyproject.toml`**

```toml
[tool.poetry]
name = "resilio-plus"
version = "0.1.0"
description = "Multi-agent hybrid athlete coaching platform"
authors = ["Simon"]
readme = "README.md"

[tool.poetry.dependencies]
python = "^3.12"
fastapi = "^0.115.6"
uvicorn = {extras = ["standard"], version = "^0.32.1"}
sqlalchemy = "^2.0.36"
asyncpg = "^0.30.0"
alembic = "^1.14.0"
pydantic = "^2.10.3"
pydantic-settings = "^2.7.0"
anthropic = "^0.40.0"
langgraph = "^0.2.60"
httpx = "^0.28.1"
python-multipart = "^0.0.20"
PyJWT = "^2.10.1"
passlib = {extras = ["bcrypt"], version = "^1.7.4"}
pandas = "^2.2.3"
numpy = "^2.2.0"
python-dateutil = "^2.9.0"

[tool.poetry.group.dev.dependencies]
pytest = "^8.3.4"
pytest-asyncio = "^0.24.0"
pytest-cov = "^6.0.0"
ruff = "^0.8.0"
mypy = "^1.13.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]
ignore = ["B008"]

[tool.mypy]
python_version = "3.12"
strict = true
ignore_missing_imports = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
pythonpath = ["."]
```

- [ ] **Step 2 : Supprimer `requirements.txt`**

```bash
rm /c/resilio-plus/requirements.txt
```

- [ ] **Step 3 : Installer les dépendances via Poetry**

```bash
cd /c/resilio-plus
poetry install
```

Résultat attendu : Poetry crée `.venv/`, installe toutes les dépendances, génère `poetry.lock`.

- [ ] **Step 4 : Vérifier que ruff et pytest sont disponibles**

```bash
poetry run ruff --version
poetry run pytest --version
```

Résultat attendu :
```
ruff 0.8.x
pytest 8.3.x
```

- [ ] **Step 5 : Commit**

```bash
git add pyproject.toml poetry.lock
git rm requirements.txt
git commit -m "build: replace requirements.txt with pyproject.toml (Poetry)

- Separate prod/dev dependencies
- Add ruff (linter/formatter) and mypy (type checking)
- Remove deprecated python-jose (replaced by PyJWT)
- Remove pytz (replaced by stdlib zoneinfo)
- Deduplicate httpx
- Add pytest asyncio_mode=auto and pythonpath config"
```

---

## Task 2 : `Dockerfile` + `.dockerignore`

**Files:**
- Create: `Dockerfile`
- Create: `.dockerignore`

- [ ] **Step 1 : Créer `Dockerfile` multi-stage**

```dockerfile
# ══════════════════════════════════════════════
# Stage 1 — builder : installe les dépendances
# ══════════════════════════════════════════════
FROM python:3.12-slim AS builder

WORKDIR /app

# Installer Poetry
RUN pip install --no-cache-dir poetry==1.8.4

# Copier uniquement les fichiers de dépendances
COPY pyproject.toml poetry.lock* ./

# Créer le venv dans /app/.venv et installer les dépendances prod uniquement
RUN poetry config virtualenvs.in-project true && \
    poetry install --only=main --no-root --no-interaction

# ══════════════════════════════════════════════
# Stage 2 — runtime : image légère sans Poetry
# ══════════════════════════════════════════════
FROM python:3.12-slim AS runtime

WORKDIR /app

# Copier le venv compilé depuis le builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copier le code source
COPY . .

EXPOSE 8000

# En prod : uvicorn sans --reload
# En dev : docker-compose override avec --reload
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2 : Créer `.dockerignore`**

```
.git/
.venv/
__pycache__/
*.pyc
*.pyo
*.pyd
.pytest_cache/
.mypy_cache/
.ruff_cache/
.env
node_modules/
frontend/.next/
frontend/node_modules/
*.db
*.sqlite
data/resilio.db
alembic/versions/*.pyc
```

- [ ] **Step 3 : Vérifier le build Docker (DB uniquement pour l'instant)**

```bash
cd /c/resilio-plus
docker compose up db -d
```

Résultat attendu : conteneur `resilio_db` démarre, healthcheck passe.

```bash
docker compose ps
```

Résultat attendu :
```
NAME         STATUS
resilio_db   Up (healthy)
```

- [ ] **Step 4 : Commit**

```bash
git add Dockerfile .dockerignore
git commit -m "build: add multi-stage Dockerfile and .dockerignore

- Stage 1 (builder): installs Poetry + prod deps into .venv
- Stage 2 (runtime): python:3.12-slim + .venv only (~200MB)
- .dockerignore excludes .env, __pycache__, .venv, test artifacts"
```

---

## Task 3 : `core/config.py` — Corrections Pydantic v2 (TDD)

**Files:**
- Create: `tests/test_config.py`
- Modify: `core/config.py`

- [ ] **Step 1 : Écrire les tests qui échouent**

Créer `tests/test_config.py` :

```python
"""Tests pour core/config.py — Settings Pydantic v2."""

import pytest
from pydantic import ValidationError


def test_settings_load_with_defaults():
    """Settings se chargent avec les valeurs par défaut."""
    from core.config import Settings

    s = Settings(_env_file=None)
    assert s.APP_NAME == "Resilio+"
    assert s.DEBUG is False
    assert s.TESTING is False
    assert s.ANTHROPIC_MAX_TOKENS == 4096


def test_settings_reject_default_secret_key_in_production():
    """SECRET_KEY 'change-me-in-production' est rejeté quand DEBUG=False."""
    from core.config import Settings

    with pytest.raises(ValidationError, match="SECRET_KEY must be set in production"):
        Settings(
            DEBUG=False,
            SECRET_KEY="change-me-in-production",
            _env_file=None,
        )


def test_settings_allow_default_secret_key_in_debug_mode():
    """SECRET_KEY peut rester par défaut quand DEBUG=True."""
    from core.config import Settings

    s = Settings(DEBUG=True, SECRET_KEY="change-me-in-production", _env_file=None)
    assert s.SECRET_KEY == "change-me-in-production"


def test_settings_accept_valid_secret_key_in_production():
    """Une vraie SECRET_KEY est acceptée en production."""
    from core.config import Settings

    s = Settings(
        DEBUG=False,
        SECRET_KEY="a-real-secret-key-that-is-not-the-default",
        _env_file=None,
    )
    assert s.DEBUG is False
```

- [ ] **Step 2 : Vérifier que les tests échouent**

```bash
cd /c/resilio-plus
poetry run pytest tests/test_config.py -v
```

Résultat attendu : les tests `test_settings_reject_*` et `test_settings_load_*` échouent car `class Config` (syntaxe v1) ne lève pas la bonne erreur.

- [ ] **Step 3 : Corriger `core/config.py`**

Remplacer le contenu complet du fichier :

```python
"""
CONFIGURATION — Resilio+
Variables d'environnement via Pydantic Settings v2.
Copier .env.example → .env et remplir les valeurs.
"""

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # ── Application ──────────────────────────────────
    APP_NAME: str = "Resilio+"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    TESTING: bool = False

    # ── Base de données ──────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://resilio:resilio@localhost:5432/resilio_db"
    DB_ECHO: bool = False

    # ── Strava OAuth ─────────────────────────────────
    STRAVA_CLIENT_ID: str = ""
    STRAVA_CLIENT_SECRET: str = ""
    STRAVA_REDIRECT_URI: str = "http://localhost:8000/api/v1/connectors/strava/callback"

    # ── USDA FoodData Central ────────────────────────
    USDA_API_KEY: str = ""

    # ── Anthropic (agents) ───────────────────────────
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-6"
    ANTHROPIC_MAX_TOKENS: int = 4096

    # ── Sécurité API ─────────────────────────────────
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24h

    @model_validator(mode="after")
    def check_secret_key(self) -> "Settings":
        if not self.DEBUG and self.SECRET_KEY == "change-me-in-production":
            raise ValueError(
                "SECRET_KEY must be set in production (DEBUG=False). "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        return self


settings = Settings()
```

- [ ] **Step 4 : Vérifier que les tests passent**

```bash
poetry run pytest tests/test_config.py -v
```

Résultat attendu :
```
tests/test_config.py::test_settings_load_with_defaults PASSED
tests/test_config.py::test_settings_reject_default_secret_key_in_production PASSED
tests/test_config.py::test_settings_allow_default_secret_key_in_debug_mode PASSED
tests/test_config.py::test_settings_accept_valid_secret_key_in_production PASSED
4 passed in 0.xx s
```

- [ ] **Step 5 : Vérifier que ruff ne signale rien**

```bash
poetry run ruff check core/config.py tests/test_config.py
```

Résultat attendu : aucune sortie (aucune erreur).

- [ ] **Step 6 : Commit**

```bash
git add core/config.py tests/test_config.py
git commit -m "fix: migrate core/config.py to Pydantic v2 SettingsConfigDict

- Replace class Config (Pydantic v1) with model_config = SettingsConfigDict(...)
- Add @model_validator to reject default SECRET_KEY in production
- Update ANTHROPIC_MODEL to claude-sonnet-4-6
- Add tests for all validator branches"
```

---

## Task 4 : Alembic — Configuration migrations async

**Files:**
- Create: `alembic.ini`
- Create: `alembic/env.py`
- Create: `alembic/script.py.mako`
- Create: `alembic/versions/.gitkeep`

- [ ] **Step 1 : Initialiser Alembic**

```bash
cd /c/resilio-plus
poetry run alembic init alembic
```

Résultat attendu : Alembic crée `alembic.ini`, `alembic/env.py`, `alembic/script.py.mako`, `alembic/versions/`.

- [ ] **Step 2 : Remplacer `alembic/env.py` par la version async**

```python
"""
Alembic env.py — Configuration async pour PostgreSQL (asyncpg).
Les migrations sont générées avec : alembic revision --autogenerate -m "message"
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

# Importer Base pour que autogenerate détecte toutes les tables
from models.database import Base
from core.config import settings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Génère le SQL sans connexion DB (pour review avant exécution)."""
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Exécute les migrations sur la DB async."""
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

- [ ] **Step 3 : Mettre à jour `alembic.ini` pour lire la DB depuis l'env**

Dans `alembic.ini`, commenter la ligne `sqlalchemy.url` (sera fournie par `env.py` via pydantic-settings) :

Trouver la ligne :
```ini
sqlalchemy.url = driver://user:pass@localhost/dbname
```

La remplacer par :
```ini
# sqlalchemy.url est fournie par alembic/env.py via core.config.settings
# Ne pas définir ici pour éviter de hardcoder les credentials
```

- [ ] **Step 4 : Créer `alembic/versions/.gitkeep`**

```bash
touch /c/resilio-plus/alembic/versions/.gitkeep
```

- [ ] **Step 5 : Vérifier qu'Alembic démarre sans erreur**

PostgreSQL doit tourner (`docker compose up db -d`) pour ce test.

```bash
cd /c/resilio-plus
poetry run alembic current
```

Résultat attendu :
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
(no current revision)
```

Si l'erreur est `"change-me-in-production"`, mettre `DEBUG=true` dans `.env` temporairement pour ce test.

- [ ] **Step 6 : Commit**

```bash
git add alembic.ini alembic/
git commit -m "build: configure Alembic for async PostgreSQL migrations

- env.py uses create_async_engine with asyncpg
- Reads DATABASE_URL from core.config.settings (not hardcoded)
- Imports Base from models.database for autogenerate
- versions/ dir tracked via .gitkeep (first migration in S2)"
```

---

## Task 5 : `data/exercise_database.json` — Exercices-clés (TDD)

**Files:**
- Create: `data/exercise_database.json`
- Create: `tests/test_exercise_database.py`

- [ ] **Step 1 : Écrire le test de structure qui échoue**

Créer `tests/test_exercise_database.py` :

```python
"""Tests de structure pour data/exercise_database.json."""

import json
from pathlib import Path

EXERCISE_DB_PATH = Path(__file__).parent.parent / "data" / "exercise_database.json"
REQUIRED_FIELDS = {
    "exercise_id", "name", "tier", "muscle_primary",
    "muscle_secondary", "equipment", "movement_pattern",
    "sfr_score", "form_cues_fr", "hevy_exercise_id",
}
VALID_TIERS = {1, 2, 3}
VALID_MOVEMENT_PATTERNS = {
    "horizontal_push", "horizontal_pull", "vertical_push", "vertical_pull",
    "squat", "hinge", "lunge", "isolation_push", "isolation_pull",
    "isolation_fly", "isolation_curl", "isolation_extension",
    "isolation_raise", "core", "prevention",
}


def load_db() -> list[dict]:
    with open(EXERCISE_DB_PATH, encoding="utf-8") as f:
        return json.load(f)


def test_exercise_database_exists():
    assert EXERCISE_DB_PATH.exists(), "data/exercise_database.json is missing"


def test_exercise_database_has_exercises():
    db = load_db()
    assert len(db) >= 20, f"Expected at least 20 exercises, got {len(db)}"


def test_all_exercises_have_required_fields():
    db = load_db()
    for ex in db:
        missing = REQUIRED_FIELDS - set(ex.keys())
        assert not missing, f"Exercise '{ex.get('name')}' missing fields: {missing}"


def test_all_exercise_ids_are_unique():
    db = load_db()
    ids = [ex["exercise_id"] for ex in db]
    assert len(ids) == len(set(ids)), "Duplicate exercise_ids found"


def test_all_tiers_are_valid():
    db = load_db()
    for ex in db:
        assert ex["tier"] in VALID_TIERS, (
            f"Exercise '{ex['name']}' has invalid tier: {ex['tier']}"
        )


def test_all_movement_patterns_are_valid():
    db = load_db()
    for ex in db:
        assert ex["movement_pattern"] in VALID_MOVEMENT_PATTERNS, (
            f"Exercise '{ex['name']}' has unknown pattern: {ex['movement_pattern']}"
        )


def test_sfr_score_in_range():
    db = load_db()
    for ex in db:
        assert 1 <= ex["sfr_score"] <= 10, (
            f"Exercise '{ex['name']}' sfr_score {ex['sfr_score']} out of range [1, 10]"
        )


def test_master_doc_exercises_present():
    """Les 6 exercices avec Hevy IDs connus (master doc §6.3) sont présents."""
    db = load_db()
    known_ids = {
        "D04AC939",  # Barbell Bench Press
        "85ADE148",  # Barbell Row
        "3A72B1D0",  # Incline Dumbbell Press
        "F198B2A3",  # Cable Row Seated
        "B5C12E87",  # Cable Lateral Raise
        "A1D3F456",  # Overhead Cable Tricep Extension
    }
    present_ids = {ex["exercise_id"] for ex in db}
    missing = known_ids - present_ids
    assert not missing, f"Master doc exercises missing from DB: {missing}"
```

- [ ] **Step 2 : Vérifier que les tests échouent**

```bash
poetry run pytest tests/test_exercise_database.py -v
```

Résultat attendu : `test_exercise_database_exists` FAIL (fichier manquant).

- [ ] **Step 3 : Créer `data/exercise_database.json`**

```json
[
  {
    "exercise_id": "D04AC939",
    "name": "Barbell Bench Press",
    "tier": 3,
    "muscle_primary": "chest",
    "muscle_secondary": ["shoulders", "triceps"],
    "equipment": ["barbell", "bench"],
    "movement_pattern": "horizontal_push",
    "sfr_score": 6,
    "form_cues_fr": [
      "Omoplates serrées et rétractées",
      "Arche lombaire naturelle",
      "Descends à 2-3cm du torse",
      "Poussée explosive, descente contrôlée 2s"
    ],
    "hevy_exercise_id": "D04AC939"
  },
  {
    "exercise_id": "85ADE148",
    "name": "Barbell Row",
    "tier": 2,
    "muscle_primary": "back",
    "muscle_secondary": ["biceps", "forearms"],
    "equipment": ["barbell"],
    "movement_pattern": "horizontal_pull",
    "sfr_score": 6,
    "form_cues_fr": [
      "Buste à 45°, dos plat",
      "Tire vers le nombril",
      "Pas d'élan avec les hanches",
      "Pause 1s en position haute"
    ],
    "hevy_exercise_id": "85ADE148"
  },
  {
    "exercise_id": "3A72B1D0",
    "name": "Incline Dumbbell Press",
    "tier": 2,
    "muscle_primary": "chest",
    "muscle_secondary": ["shoulders", "triceps"],
    "equipment": ["dumbbells", "bench"],
    "movement_pattern": "horizontal_push",
    "sfr_score": 8,
    "form_cues_fr": [
      "Banc à 30° (pas plus — protège les épaules)",
      "Descends jusqu'à l'étirement complet du pec",
      "Coudes légèrement vers l'intérieur"
    ],
    "hevy_exercise_id": "3A72B1D0"
  },
  {
    "exercise_id": "F198B2A3",
    "name": "Cable Row (Seated)",
    "tier": 1,
    "muscle_primary": "back",
    "muscle_secondary": ["biceps"],
    "equipment": ["cables"],
    "movement_pattern": "horizontal_pull",
    "sfr_score": 9,
    "form_cues_fr": [
      "Prise neutre (poignée en V)",
      "Tire vers le bas du sternum",
      "Pause 1s en contraction",
      "Étirement complet en avant"
    ],
    "hevy_exercise_id": "F198B2A3"
  },
  {
    "exercise_id": "B5C12E87",
    "name": "Cable Lateral Raise",
    "tier": 1,
    "muscle_primary": "shoulders",
    "muscle_secondary": [],
    "equipment": ["cables"],
    "movement_pattern": "isolation_raise",
    "sfr_score": 9,
    "form_cues_fr": [
      "Légère flexion du coude (15-20°)",
      "Monte jusqu'à parallèle au sol",
      "Contrôle la descente 2-3s",
      "Pas de rotation du torse"
    ],
    "hevy_exercise_id": "B5C12E87"
  },
  {
    "exercise_id": "A1D3F456",
    "name": "Overhead Cable Tricep Extension",
    "tier": 1,
    "muscle_primary": "triceps",
    "muscle_secondary": [],
    "equipment": ["cables"],
    "movement_pattern": "isolation_extension",
    "sfr_score": 9,
    "form_cues_fr": [
      "Coudes fixes au-dessus de la tête",
      "Étirement complet en bas (long chef)",
      "Extension complète sans verrouiller"
    ],
    "hevy_exercise_id": "A1D3F456"
  },
  {
    "exercise_id": "LEG-PRESS-001",
    "name": "Leg Press",
    "tier": 1,
    "muscle_primary": "quadriceps",
    "muscle_secondary": ["glutes", "hamstrings"],
    "equipment": ["machines"],
    "movement_pattern": "squat",
    "sfr_score": 9,
    "form_cues_fr": [
      "Pieds écartés à largeur des épaules",
      "Descends jusqu'à 90° de flexion du genou",
      "Ne verrouille pas les genoux en haut",
      "Préféré au squat barbell pour les hybrides (moins de CNS)"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "RDL-DB-001",
    "name": "Romanian Deadlift (Dumbbell)",
    "tier": 2,
    "muscle_primary": "hamstrings",
    "muscle_secondary": ["glutes", "lower_back"],
    "equipment": ["dumbbells"],
    "movement_pattern": "hinge",
    "sfr_score": 7,
    "form_cues_fr": [
      "Hanches en arrière, dos plat",
      "Haltères près du corps tout au long",
      "Descends jusqu'à étirement des ischio-jambiers",
      "Extension complète des hanches en haut"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "SEATED-LEG-CURL-001",
    "name": "Seated Leg Curl",
    "tier": 1,
    "muscle_primary": "hamstrings",
    "muscle_secondary": [],
    "equipment": ["machines"],
    "movement_pattern": "isolation_curl",
    "sfr_score": 9,
    "form_cues_fr": [
      "Étirement complet en position haute",
      "Contraction maximale en bas",
      "Contrôle la montée 2s"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "CALF-RAISE-STAND-001",
    "name": "Standing Calf Raise",
    "tier": 2,
    "muscle_primary": "calves",
    "muscle_secondary": [],
    "equipment": ["machines"],
    "movement_pattern": "isolation_raise",
    "sfr_score": 7,
    "form_cues_fr": [
      "Étirement complet en bas (talon sous la plateforme)",
      "Contraction et pause 1s en haut",
      "Range of motion complète — éviter les demi-répétitions"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "AB-WHEEL-001",
    "name": "Ab Wheel Rollout",
    "tier": 1,
    "muscle_primary": "core",
    "muscle_secondary": ["shoulders", "lats"],
    "equipment": ["ab_wheel"],
    "movement_pattern": "core",
    "sfr_score": 8,
    "form_cues_fr": [
      "Dos plat tout au long du mouvement",
      "Ne laisse pas les hanches tomber",
      "Reviens en contractant le core, pas le bas du dos"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "LAT-PULLDOWN-001",
    "name": "Lat Pulldown",
    "tier": 1,
    "muscle_primary": "back",
    "muscle_secondary": ["biceps"],
    "equipment": ["cables"],
    "movement_pattern": "vertical_pull",
    "sfr_score": 9,
    "form_cues_fr": [
      "Prise légèrement plus large que les épaules",
      "Tire vers la clavicule (pas le menton)",
      "Étirement complet des lats en haut"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "CABLE-FLY-001",
    "name": "Cable Fly",
    "tier": 1,
    "muscle_primary": "chest",
    "muscle_secondary": [],
    "equipment": ["cables"],
    "movement_pattern": "isolation_fly",
    "sfr_score": 9,
    "form_cues_fr": [
      "Légère flexion des coudes fixe",
      "Étirement maximal en position ouverte",
      "Contraction au centre — imagine serrer une boîte"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "FACE-PULL-001",
    "name": "Face Pull",
    "tier": 1,
    "muscle_primary": "shoulders",
    "muscle_secondary": ["rear_delts", "rotator_cuff"],
    "equipment": ["cables"],
    "movement_pattern": "horizontal_pull",
    "sfr_score": 9,
    "form_cues_fr": [
      "Corde à hauteur des yeux",
      "Tire vers le visage en écartant les mains",
      "Rotation externe des épaules en fin de mouvement"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "INCLINE-DB-CURL-001",
    "name": "Incline Dumbbell Curl",
    "tier": 1,
    "muscle_primary": "biceps",
    "muscle_secondary": [],
    "equipment": ["dumbbells", "bench"],
    "movement_pattern": "isolation_curl",
    "sfr_score": 9,
    "form_cues_fr": [
      "Banc à 45-60°",
      "Étirement complet des biceps en bas",
      "Pas de balancement des épaules"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "CABLE-PUSHDOWN-001",
    "name": "Cable Tricep Pushdown",
    "tier": 1,
    "muscle_primary": "triceps",
    "muscle_secondary": [],
    "equipment": ["cables"],
    "movement_pattern": "isolation_extension",
    "sfr_score": 9,
    "form_cues_fr": [
      "Coudes fixes au corps",
      "Extension complète en bas",
      "Prise en pronation ou neutre selon confort"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "HIP-EXT-ROTATION-001",
    "name": "Hip External Rotation (Band)",
    "tier": 1,
    "muscle_primary": "glutes",
    "muscle_secondary": ["rotator_cuff_hip"],
    "equipment": ["resistance_band"],
    "movement_pattern": "prevention",
    "sfr_score": 8,
    "form_cues_fr": [
      "Élastique autour des genoux",
      "Pousse les genoux vers l'extérieur",
      "Prévention du valgus du genou (essentiel pour les coureurs)"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "HACK-SQUAT-001",
    "name": "Hack Squat",
    "tier": 1,
    "muscle_primary": "quadriceps",
    "muscle_secondary": ["glutes"],
    "equipment": ["machines"],
    "movement_pattern": "squat",
    "sfr_score": 8,
    "form_cues_fr": [
      "Pieds hauts sur la plateforme = plus de fessiers",
      "Pieds bas = plus de quadriceps",
      "Descends jusqu'à 90° minimum"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "PULL-UP-001",
    "name": "Pull-up",
    "tier": 2,
    "muscle_primary": "back",
    "muscle_secondary": ["biceps"],
    "equipment": ["pull_up_bar"],
    "movement_pattern": "vertical_pull",
    "sfr_score": 7,
    "form_cues_fr": [
      "Prise pronation, légèrement plus large que les épaules",
      "Descends jusqu'à extension complète des bras",
      "Pas d'élan — mouvement contrôlé"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "DIP-001",
    "name": "Dip",
    "tier": 2,
    "muscle_primary": "triceps",
    "muscle_secondary": ["chest", "shoulders"],
    "equipment": ["dip_bar"],
    "movement_pattern": "vertical_push",
    "sfr_score": 6,
    "form_cues_fr": [
      "Corps vertical = plus de triceps",
      "Incliné vers l'avant = plus de poitrine",
      "Descends jusqu'à 90° des coudes"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "BULGARIAN-SS-001",
    "name": "Bulgarian Split Squat",
    "tier": 2,
    "muscle_primary": "quadriceps",
    "muscle_secondary": ["glutes", "hamstrings"],
    "equipment": ["dumbbells", "bench"],
    "movement_pattern": "lunge",
    "sfr_score": 7,
    "form_cues_fr": [
      "Pied arrière sur banc à hauteur de genou",
      "Descends verticalement — genou avant ne dépasse pas le pied",
      "Attention aux DOMS — introduire progressivement"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "BACK-SQUAT-001",
    "name": "Barbell Back Squat",
    "tier": 3,
    "muscle_primary": "quadriceps",
    "muscle_secondary": ["glutes", "hamstrings", "core"],
    "equipment": ["barbell"],
    "movement_pattern": "squat",
    "sfr_score": 4,
    "form_cues_fr": [
      "Barre sur les trapèzes (low bar) ou les épaules (high bar)",
      "Descends jusqu'à profondeur parallèle minimum",
      "RÉSERVÉ phase base uniquement — interdit phase peak (volume course élevé)"
    ],
    "hevy_exercise_id": ""
  },
  {
    "exercise_id": "DEADLIFT-001",
    "name": "Conventional Deadlift",
    "tier": 3,
    "muscle_primary": "back",
    "muscle_secondary": ["hamstrings", "glutes", "quadriceps"],
    "equipment": ["barbell"],
    "movement_pattern": "hinge",
    "sfr_score": 3,
    "form_cues_fr": [
      "Barre au-dessus du milieu du pied",
      "Dos plat — ne jamais arrondir la colonne",
      "Fatigue CNS maximale — utiliser avec parcimonie chez les hybrides"
    ],
    "hevy_exercise_id": ""
  }
]
```

- [ ] **Step 4 : Vérifier que les tests passent**

```bash
poetry run pytest tests/test_exercise_database.py -v
```

Résultat attendu :
```
tests/test_exercise_database.py::test_exercise_database_exists PASSED
tests/test_exercise_database.py::test_exercise_database_has_exercises PASSED
tests/test_exercise_database.py::test_all_exercises_have_required_fields PASSED
tests/test_exercise_database.py::test_all_exercise_ids_are_unique PASSED
tests/test_exercise_database.py::test_all_tiers_are_valid PASSED
tests/test_exercise_database.py::test_all_movement_patterns_are_valid PASSED
tests/test_exercise_database.py::test_sfr_score_in_range PASSED
tests/test_exercise_database.py::test_master_doc_exercises_present PASSED
8 passed in 0.xx s
```

- [ ] **Step 5 : Commit**

```bash
git add data/exercise_database.json tests/test_exercise_database.py
git commit -m "feat: add exercise_database.json with 23 key exercises

- Structure: exercise_id, name, tier (1-3), muscle groups, equipment,
  movement_pattern, sfr_score, form_cues_fr, hevy_exercise_id
- 6 exercises with known Hevy IDs from master doc §6.3
- 17 exercises with empty hevy_exercise_id (to be filled in S7)
- Tests validate structure, uniqueness, tier validity, sfr range"
```

---

## Task 6 : Mise à jour `CLAUDE.md`

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1 : Mettre à jour `CLAUDE.md`**

Remplacer le contenu complet du fichier :

```markdown
# RESILIO+ — CLAUDE.md

> Ce fichier est lu par Claude Code au démarrage de chaque session.
> Il contient tout le contexte nécessaire pour travailler sur ce projet.
> Ne jamais modifier sans validation explicite.
> RÈGLE : Ce fichier documente uniquement l'état ACTUEL. L'état futur est dans le plan d'exécution.

---

## PROJET EN UNE LIGNE

Resilio+ est un orchestrateur multi-agents de performance sportive pour athlètes hybrides. Il génère des plans d'entraînement prescriptifs exacts (charges, allures, RPE) via un Head Coach IA qui coordonne des agents spécialistes, en gérant l'interférence métabolique (mTOR/AMPK), l'ACWR et la fatigue neuromusculaire.

---

## DÉCISIONS D'ARCHITECTURE — GRAVÉES DANS LE MARBRE

Ces décisions ne sont pas négociables. Ne jamais les remettre en question ni les contourner.

| Décision | Choix | Raison |
|----------|-------|--------|
| Orchestration agents | **LangGraph** (lite V1) | StateGraph, nodes, edges conditionnels uniquement |
| Backend | **FastAPI** (Python) | RESTful, OpenAPI/Swagger auto-généré, indépendant du frontend |
| Frontend | **Next.js** (React) | Consommateur de l'API uniquement |
| Prototype intermédiaire | **AUCUN** | Pas de Streamlit, pas de CLI-only — frontend dès le départ |
| Unité de poids | **kg uniquement** | Conversion lbs→kg à l'ingestion |
| Langue du code | **Anglais** | Variables, fonctions, commentaires en anglais |
| Langue des prompts agents | **Français** | Les agents parlent à l'utilisateur en français |
| AthleteState — écriture | **Head Coach uniquement** | Les autres agents lisent via `get_agent_view()` |
| AthleteState — lecture | **Vues filtrées** | Chaque agent reçoit uniquement sa sous-section |
| Gestion des edge cases | **Human-in-the-loop** | Le Head Coach recommande, l'utilisateur décide toujours |
| Ton des agents | **Clinique, zéro emoji, zéro encouragement** | Voir system_prompt.md par agent |
| Gestionnaire de paquets | **Poetry** | `pyproject.toml` — source de vérité unique dépendances + outils |
| Linter/formatter | **ruff** | Remplace black + flake8 + isort en un outil |
| Auth | **JWT (PyJWT + passlib)** | Multi-user dès le départ |

---

## DÉMARRAGE LOCAL

```bash
# 1. Démarrer PostgreSQL
docker compose up db -d

# 2. Vérifier que la DB est healthy
docker compose ps

# 3. Lancer le backend en mode dev
poetry run uvicorn api.main:app --reload

# 4. Lancer les tests
poetry run pytest tests/ -v

# 5. Linter
poetry run ruff check .
```

---

## ÉTAT D'AVANCEMENT — 15 SESSIONS

| Session | Module | Livrable | Statut |
|---------|--------|---------|--------|
| **S1** | Setup | pyproject.toml, Dockerfile, Alembic, config, exercise_database.json | ✅ FAIT |
| **S2** | Schémas | AthleteState Pydantic complet, modèles DB, migration initiale | ⬜ À FAIRE |
| **S3** | Connecteurs | Strava OAuth + Hevy (API ou CSV fallback) | ⬜ À FAIRE |
| **S4** | Connecteurs | USDA/Open Food Facts + Apple Health + fallbacks GPX/FIT | ⬜ À FAIRE |
| **S5** | Agents base | Agent base class + Head Coach + `get_agent_view()` + edge cases | ⬜ À FAIRE |
| **S6** | Running Coach | VDOT + zones + output format Runna/Garmin | ⬜ À FAIRE |
| **S7** | Lifting Coach | Exercise DB complet (400+) + Volume Landmarks + output format Hevy | ⬜ À FAIRE |
| **S8** | Recovery Coach | Readiness score + gate keeper + HRV pipeline | ⬜ À FAIRE |
| **S9** | Workflow | Onboarding 7 blocs + création de plan + audit conflits | ⬜ À FAIRE |
| **S10** | Workflow | Boucle hebdomadaire + matrice vivante + suivi | ⬜ À FAIRE |
| **S11** | Backend | FastAPI endpoints + OpenAPI docs + auth | ⬜ À FAIRE |
| **S12** | Frontend | Next.js — Dashboard + calendrier + chat | ⬜ À FAIRE |
| **S13** | Frontend | Next.js — Suivi hebdo + pages détail | ⬜ À FAIRE |
| **S14** | Intégration | Docker + tests E2E + polish | ⬜ À FAIRE |
| **S15** | Nutrition Coach | USDA/OFF/FCÉN + NLP meal input + macros + race-week | ⬜ À FAIRE |

---

## STRUCTURE DU REPO — ÉTAT ACTUEL

```
resilio-plus/
│
├── CLAUDE.md                          ← CE FICHIER
├── README.md
├── pyproject.toml                     ← ✅ S1 — Dépendances + config ruff/mypy/pytest
├── poetry.lock                        ← ✅ S1 — Lock file généré
├── Dockerfile                         ← ✅ S1 — Multi-stage prod
├── .dockerignore                      ← ✅ S1
├── docker-compose.yml                 ← ✅ Existant — PostgreSQL + API
├── alembic.ini                        ← ✅ S1 — Config migrations
├── alembic/
│   ├── env.py                         ← ✅ S1 — Async PostgreSQL
│   ├── script.py.mako
│   └── versions/                      ← ⬜ Première migration en S2
│
├── resilio-master-v2.md               ← Document maître (lire en second)
├── resilio-nutrition-coach-section.md ← Section 6B Nutrition Coach
│
├── agents/
│   ├── head_coach/
│   │   ├── system_prompt.md           ← ✅ Existant
│   │   ├── graph.py                   ← ✅ Existant (LangGraph stub)
│   │   └── edge_cases/                ← ✅ Existant (3 scénarios)
│   ├── lifting_coach/
│   │   └── system_prompt.md           ← ✅ Existant
│   ├── running_coach/
│   │   └── system_prompt.md           ← ✅ Existant
│   ├── nutrition_coach/
│   │   └── system_prompt.md           ← ✅ Existant
│   └── recovery_coach/
│       └── system_prompt.md           ← ✅ Existant
│
├── api/
│   └── endpoints_design.md            ← ✅ Existant (design doc)
│   (api/main.py → S11)
│
├── core/
│   └── config.py                      ← ✅ S1 — Pydantic v2, validator sécurité
│
├── models/
│   ├── database.py                    ← ✅ Existant — Schéma SQLAlchemy complet
│   ├── db_session.py                  ← ✅ Existant — Engine async + session factory
│   (athlete_state.py → S2)
│
├── connectors/                        ← ⬜ S3-S4
│
├── data/
│   ├── agent_view_map.json            ← ✅ Existant
│   ├── exercise_database.json         ← ✅ S1 — 23 exercices-clés (400+ en S7)
│   ├── food_database_cache.json       ← ✅ Existant
│   ├── muscle_overlap.json            ← ✅ Existant
│   ├── nutrition_targets.json         ← ✅ Existant
│   ├── running_zones.json             ← ✅ Existant
│   ├── vdot_paces.json                ← ✅ Existant
│   └── volume_landmarks.json          ← ✅ Existant
│
├── resilio_docs/resilio_docs/         ← ✅ Existant — 9 JSON connaissances scientifiques
├── training_books/                    ← ✅ Existant — 5 livres résumés
│
├── tests/
│   ├── conftest.py                    ← ✅ Existant — Simon complet (DB + vues agents)
│   ├── test_config.py                 ← ✅ S1
│   └── test_exercise_database.py      ← ✅ S1
│
├── docs/
│   └── superpowers/
│       ├── specs/
│       │   └── 2026-04-03-session1-setup-design.md
│       └── plans/
│           └── 2026-04-03-session1-setup.md
│
└── frontend/                          ← ⬜ S12-S13
```

---

## INTÉGRATIONS API — STATUT

| Service | Méthode primaire | Fallback | Statut |
|---------|-----------------|---------|--------|
| Hevy | API REST (si dispo) | CSV export → parser | ⬜ S3 |
| Strava | API OAuth | GPX / FIT file import | ⬜ S3 |
| Apple Health | HealthKit / Terra API | Input manuel JSON | ⬜ S4 |
| USDA FoodData | API REST gratuite | Cache local JSON | ⬜ S15 |
| Open Food Facts | API REST gratuite | Cache local JSON | ⬜ S15 |
| FCÉN Santé Canada | CSV téléchargeable | Cache local JSON | ⬜ S15 |

---

## ATHLÈTE DE TEST — "SIMON"

Fixtures complètes dans `tests/conftest.py` :
- `simon_dict` — dict brut (sans DB)
- `simon_athlete` — Athlete persisté en DB de test
- `simon_state` — AthleteState en phase base_building, semaine 3
- `simon_fatigue_normal` — ACWR 1.05, readiness VERT
- `simon_fatigue_red` — ACWR 1.61, readiness ROUGE
- `simon_agent_view_running` — Vue filtrée Running Coach
- `simon_agent_view_lifting` — Vue filtrée Lifting Coach

Données de référence Simon : VDOT 38.2, 5k en 28:30, poids 78.5kg, objectif sub-25 5k en 16 semaines.

---

## ORDRE DE LECTURE AU DÉMARRAGE DE CHAQUE SESSION

1. `CLAUDE.md` (ce fichier)
2. `resilio-master-v2.md` — architecture, AthleteState, connaissances agents
3. `resilio-nutrition-coach-section.md` — section 6B Nutrition Coach
4. Le(s) `system_prompt.md` des agents concernés par la session
5. Les fichiers existants du dossier de travail

Ne jamais commencer à coder avant d'avoir lu les documents 1 à 3.

---

## RÈGLES ABSOLUES POUR CLAUDE CODE

1. **Lire avant de coder** — toujours lire CLAUDE.md + master doc avant de toucher un fichier
2. **Pas de Streamlit** — jamais, pour aucune raison
3. **Poids en kg** — toute donnée entrante en lbs est convertie immédiatement à l'ingestion
4. **get_agent_view() est la seule porte d'entrée** vers l'AthleteState pour les agents
5. **Human-in-the-loop sur les edge cases** — le système propose, l'humain décide toujours
6. **Mettre à jour CLAUDE.md à la fin de chaque session** — uniquement l'état actuel
7. **Ne jamais casser les tests existants** — si un test échoue après un changement, corriger avant de continuer
8. **Format de sortie respecté** — séances de course en JSON Runna-compatible, séances lifting en JSON Hevy-compatible
9. **TDD** — écrire le test qui échoue avant d'écrire le code
10. **Commits atomiques** — un commit par tâche logique
```

- [ ] **Step 2 : Vérifier que tous les tests passent toujours**

```bash
poetry run pytest tests/ -v
```

Résultat attendu : tous les tests passent (aucune régression introduite par la mise à jour CLAUDE.md).

- [ ] **Step 3 : Commit final S1**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md with S1 completion state

- Add session progress tracker (S1 done, S2-S15 pending)
- Update repo structure to reflect actual current state
- Add local startup commands
- Add rule: CLAUDE.md documents current state only
- Fix ANTHROPIC_MODEL reference"
```

---

## Vérification finale S1

- [ ] **Run complet des tests**

```bash
poetry run pytest tests/ -v --tb=short
```

Résultat attendu :
```
tests/test_config.py::test_settings_load_with_defaults PASSED
tests/test_config.py::test_settings_reject_default_secret_key_in_production PASSED
tests/test_config.py::test_settings_allow_default_secret_key_in_debug_mode PASSED
tests/test_config.py::test_settings_accept_valid_secret_key_in_production PASSED
tests/test_exercise_database.py::test_exercise_database_exists PASSED
tests/test_exercise_database.py::test_exercise_database_has_exercises PASSED
tests/test_exercise_database.py::test_all_exercises_have_required_fields PASSED
tests/test_exercise_database.py::test_all_exercise_ids_are_unique PASSED
tests/test_exercise_database.py::test_all_tiers_are_valid PASSED
tests/test_exercise_database.py::test_all_movement_patterns_are_valid PASSED
tests/test_exercise_database.py::test_sfr_score_in_range PASSED
tests/test_exercise_database.py::test_master_doc_exercises_present PASSED
12 passed in 0.xx s
```

- [ ] **Ruff sur tout le repo**

```bash
poetry run ruff check .
```

Résultat attendu : aucune sortie.

- [ ] **Docker healthcheck**

```bash
docker compose ps
```

Résultat attendu : `resilio_db` est `Up (healthy)`.

- [ ] **Alembic connecté**

```bash
poetry run alembic current
```

Résultat attendu :
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
(no current revision)
```
