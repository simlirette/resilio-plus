# Database — Architecture, Conventions & Operations

**Engine:** PostgreSQL 16 (Docker Compose)
**ORM:** SQLAlchemy 2.x
**Migrations:** Alembic 1.13
**Current head:** `0005_energy_patterns`

---

## Schema Overview

13 tables across two model files:

### Core tables (`backend/app/db/models.py`)

| Table | Purpose |
|---|---|
| `users` | Auth credentials — email, hashed_password, athlete_id FK |
| `athletes` | Athlete profile — demographics, sports, goals, coaching mode |
| `training_plans` | Weekly training plans with JSON slot structure |
| `nutrition_plans` | Macro targets per athlete |
| `weekly_reviews` | Post-week summaries — actual hours, ACWR, HRV, notes |
| `connector_credentials` | OAuth tokens for Strava, Hevy, Terra |
| `session_logs` | Individual session results — RPE, duration, notes |

### V3 tables (`backend/app/models/schemas.py`)

| Table | Purpose |
|---|---|
| `energy_snapshots` | Daily Energy Coach output — allostatic score, veto, intensity cap |
| `hormonal_profiles` | Cycle tracking (1:1 with athletes) |
| `allostatic_entries` | 28-day rolling allostatic history |
| `external_plans` | Plans imported from file (tracking_only mode) |
| `external_sessions` | Individual sessions from external plans |
| `head_coach_messages` | Proactive coaching messages from pattern detection |

### FK relationships (simplified)

```
athletes ──< users (1:1)
athletes ──< training_plans
athletes ──< nutrition_plans
athletes ──< weekly_reviews ──> training_plans
athletes ──< connector_credentials (UC: athlete_id, provider)
athletes ──< session_logs ──> training_plans, external_sessions
athletes ──< energy_snapshots
athletes ──1 hormonal_profiles
athletes ──< allostatic_entries (UC: athlete_id, entry_date)
athletes ──< external_plans ──< external_sessions
athletes ──< head_coach_messages
```

---

## Migration History

| Revision | Description |
|---|---|
| `0001` | Initial schema — core 7 tables (users, athletes, training_plans, nutrition_plans, weekly_reviews, connector_credentials, session_logs) |
| `0002` | V3 AthleteState — energy_snapshots, hormonal_profiles, allostatic_entries for new V3 models |
| `0003` | Mode system + external plans — adds coaching_mode to athletes, training_plans.status, external_plans, external_sessions tables |
| `0004` | Energy scoring — adds objective_score and subjective_score columns to energy_snapshots |
| `0005` | Energy pattern detection — adds legs_feeling and stress_level to energy_snapshots; creates head_coach_messages table |

---

## Creating a New Migration

1. Modify a SQLAlchemy model in `backend/app/db/models.py` or `backend/app/models/schemas.py`

2. Generate the migration:
   ```bash
   alembic revision --autogenerate -m "describe_your_change"
   ```
   This creates `alembic/versions/XXXX_describe_your_change.py`

3. **Always review the generated file.** Autogenerate misses: renamed columns, custom constraints, partial indexes. Edit if needed.

4. Test upgrade:
   ```bash
   poetry run db-migrate
   ```

5. Test downgrade:
   ```bash
   alembic downgrade -1
   alembic upgrade head
   ```

6. Commit the migration file with the model change in the same commit.

---

## DB Commands

| Command | What it does |
|---|---|
| `poetry run db-migrate` | Apply pending migrations (`alembic upgrade head`) |
| `poetry run db-seed` | Insert dev personas (Alice + Marc) — idempotent |
| `poetry run db-seed-test` | Insert minimal test fixture against TEST_DATABASE_URL |
| `poetry run db-reset --confirm` | **DESTRUCTIVE** — drop schema + migrate + seed-dev |

---

## Docker Compose Quickstart (new machine)

```bash
# 1. Start PostgreSQL
docker compose up db -d

# 2. Apply migrations
poetry run db-migrate

# 3. Seed dev data
poetry run db-seed

# App is ready. Start backend:
docker compose up backend
```

For tests (separate DB on port 5433):
```bash
docker compose up db-test -d
TEST_DATABASE_URL=postgresql+psycopg2://resilio:resilio@localhost:5433/resilio_test \
  pytest tests/test_db/ -m db_integration -v
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg2://resilio:resilio@localhost:5432/resilio_db` | Dev/prod DB |
| `TEST_DATABASE_URL` | `postgresql+psycopg2://resilio:resilio@localhost:5433/resilio_test` | Test DB (port 5433) |

Both variables are read by `db_commands.py`. Alembic picks up `DATABASE_URL` at runtime.
