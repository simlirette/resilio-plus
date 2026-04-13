# DB Migrations & Seed Data — Design Spec

**Date:** 2026-04-13
**Status:** Approved
**Context:** Alembic already configured (5 migrations, PostgreSQL). Gap: no seed scripts, no dev commands, no test DB lifecycle, no documentation.

---

## Objective

Add deterministic seed data for dev and test environments, Poetry commands for all DB operations, Docker Compose database services, and comprehensive documentation. No new migration files — the 5 existing migrations already capture the full schema.

---

## Architecture

### Approach

Pydantic schemas → SQLAlchemy ORM inserts. Seed data defined as typed Python dicts validated against existing Pydantic models. No new dependencies. Consistent with how agents consume data.

### Database strategy

PostgreSQL-only for all environments (dev, test, CI, prod). `DATABASE_URL` env var drives everything — alembic.ini, database.py, and all scripts read it. No hardcoded URLs.

| Environment | Database | URL env var |
|---|---|---|
| Dev | `resilio_db` | `DATABASE_URL` |
| Test | `resilio_test` | `TEST_DATABASE_URL` |
| CI | `resilio_test` | `TEST_DATABASE_URL` |
| Prod | `resilio_db` (managed) | `DATABASE_URL` |

---

## File Map

| File | Action |
|---|---|
| `docker-compose.yml` | Create — `db` + `db-test` postgres:16-alpine services |
| `scripts/__init__.py` | Create — package marker |
| `scripts/db_commands.py` | Create — `migrate()`, `seed_dev()`, `seed_test()`, `reset()` |
| `scripts/seed_data/__init__.py` | Create — package marker |
| `scripts/seed_data/alice.py` | Create — Alice Dupont persona (recreational runner + lifting) |
| `scripts/seed_data/marc.py` | Create — Marc Leblanc persona (competitive triathlete) |
| `scripts/seed_data/test_fixture.py` | Create — minimal deterministic test fixture |
| `pyproject.toml` | Modify — add 4 Poetry scripts + `scripts` to packages |
| `alembic.ini` | Modify — replace hardcoded PostgreSQL URL with env var placeholder |
| `docs/backend/DATABASE.md` | Create — schema doc, migration guide, seed guide |
| `.gitignore` | Modify — add `*.db`, `resilio_dev.db` |
| `tests/conftest.py` | Modify — add `db_session` fixture with per-test rollback isolation |

---

## Poetry Scripts

```toml
[tool.poetry.scripts]
db-migrate   = "scripts.db_commands:migrate"
db-seed      = "scripts.db_commands:seed_dev"
db-seed-test = "scripts.db_commands:seed_test"
db-reset     = "scripts.db_commands:reset"
```

| Command | Description | Destructive |
|---|---|---|
| `poetry run db-migrate` | `alembic upgrade head` | No |
| `poetry run db-seed` | Insert Alice + Marc + 6 weeks history | No (idempotent via upsert) |
| `poetry run db-seed-test` | Insert minimal test fixture | No |
| `poetry run db-reset --confirm` | Drop schema + migrate + seed-dev | Yes — requires `--confirm` |

`db-reset` exits with a clear error if `--confirm` is absent. Never drops without explicit confirmation.

---

## Docker Compose

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: resilio
      POSTGRES_PASSWORD: resilio
      POSTGRES_DB: resilio_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  db-test:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: resilio
      POSTGRES_PASSWORD: resilio
      POSTGRES_DB: resilio_test
    ports:
      - "5433:5432"

volumes:
  postgres_data:
```

Dev DB on port 5432. Test DB on port 5433 (separate instance, no volume — ephemeral).

---

## Seed Data — Dev (`seed_dev.py`)

### Athlete A — Alice Dupont

| Field | Value |
|---|---|
| Age | 28 |
| Sex | F |
| Weight | 60 kg |
| Sports | Run + Lifting |
| Goal | marathon_sub4 |
| Hours/week | 8 |
| Coaching mode | active |
| Hormonal tracking | enabled (follicular phase) |

**History (6 weeks):**
- 4 runs/week (E/T zones alternating) + 2 lifting sessions/week
- Week 4: recovery dip — sleep drops to 5.5h, HRV drops to 42ms, veto triggered once
- Allostatic entries: 28 days, trend declining in week 4 → recovering in week 5
- Energy snapshots: daily for 14 days
- 2 weekly reviews (weeks 5 and 6)
- Muscle strain: quads + posterior_chain elevated in week 5 (squat-heavy block)
- 1 head_coach_message flagging the recovery dip

### Athlete B — Marc Leblanc

| Field | Value |
|---|---|
| Age | 34 |
| Sex | M |
| Weight | 75 kg |
| Sports | Run + Bike + Swim |
| Goal | ironman_70_3 |
| Hours/week | 12 |
| Coaching mode | active |
| Hormonal tracking | disabled |

**History (6 weeks):**
- 3 runs + 3 bikes + 2 swims/week
- ACWR spike in week 3 (1.4 — caution zone), normalizes by week 5
- HRV baseline 65–75ms, high allostatic resilience
- Allostatic entries: 28 days, trend stable
- 1 connector credential: fake Strava token (structurally valid, non-functional)
- 2 weekly reviews (weeks 5 and 6)

**Both athletes use separate user accounts** — tests multi-tenant isolation.

### Idempotency

`seed_dev()` uses `INSERT ... ON CONFLICT DO NOTHING` (or SQLAlchemy equivalent) keyed on email for users. Running twice is safe.

---

## Seed Data — Test (`seed_test.py`)

Minimal deterministic fixture. Applied once per test session, not per test.

| Table | Rows | Notes |
|---|---|---|
| users | 1 | `test@resilio.dev` / `testpass` (bcrypt) |
| athletes | 1 | Alice minimal (no history) |
| training_plans | 1 | Current week, 3 slots |
| session_logs | 3 | 1 completed, 1 skipped, 1 pending |
| energy_snapshots | 1 | No veto |
| allostatic_entries | 1 | Green baseline |

---

## Test DB Lifecycle

`tests/conftest.py` adds a `db_session` fixture:

1. Connects to `TEST_DATABASE_URL` (port 5433)
2. Runs `alembic upgrade head` once per test session
3. Calls `seed_test()` once per test session
4. Wraps each test in a savepoint (nested transaction) — rolls back after each test
5. Drops schema after full test session completes

Tests are fully isolated: no test can pollute the next. The rollback strategy uses SQLAlchemy `SAVEPOINT` (compatible with PostgreSQL).

---

## alembic.ini Fix

Current `alembic.ini` has hardcoded PostgreSQL URL. Replace with:

```ini
sqlalchemy.url = %(DATABASE_URL)s
```

And update `alembic/env.py` to inject `DATABASE_URL` from environment:

```python
db_url = os.environ.get("DATABASE_URL")
if not db_url:
    raise RuntimeError("DATABASE_URL environment variable is not set")
config.set_main_option("sqlalchemy.url", db_url)
```

---

## Documentation (`docs/backend/DATABASE.md`)

Four sections:

1. **Schema overview** — 13 tables, one-line purpose each, FK relationships, current head (0005)
2. **Creating a new migration** — step-by-step: modify model → autogenerate → review → test up/down → commit
3. **Seed commands** — when to use each, example invocations
4. **Docker Compose quickstart** — three commands to go from zero to seeded dev DB

---

## .gitignore additions

```
# Local databases
*.db
resilio_dev.db
data/*.db
```

---

## Invariants

- `poetry install` must pass after changes to `pyproject.toml`
- `pytest tests/` must pass (≥2021 existing + any new tests)
- `poetry run db-reset --confirm` must complete without errors on a clean Postgres
- `poetry run db-seed` is idempotent (safe to run twice)
- No migration files are created or modified — 0001→0005 chain is untouched
- `.backup` before modifying `alembic.ini`, `pyproject.toml`, `tests/conftest.py`
