# Background Jobs System (V3-S) — Design Spec

## Goal

Replace the ad-hoc `sync_scheduler.py` with a structured background jobs system: per-athlete dynamic scheduling, persistent job execution logs, daily readiness/strain snapshots, and an admin monitoring endpoint.

## Architecture

APScheduler 3.x `BackgroundScheduler` (already in deps) with `SQLAlchemyJobStore` for persistence. New `backend/app/jobs/` module replaces `backend/app/core/sync_scheduler.py`.

### Module Layout

```
backend/app/jobs/
├── __init__.py
├── scheduler.py       — APScheduler setup, SQLAlchemyJobStore, lifespan integration
├── registry.py        — register/unregister per-athlete jobs (connect/disconnect hooks)
├── sync_jobs.py       — sync_strava_for_athlete(), sync_hevy_for_athlete(), sync_terra_for_athlete()
├── compute_jobs.py    — compute_daily_snapshot(), run_energy_patterns()
├── cleanup_jobs.py    — cleanup_old_job_runs() (30 days)
└── models.py          — JobRunModel, AthleteStateSnapshotModel
```

### Changes to Existing Code

- **Delete** `backend/app/core/sync_scheduler.py` — energy pattern detection logic (pure functions) moves to `backend/app/core/energy_patterns.py`. Job wrappers move to `jobs/compute_jobs.py`.
- **`main.py`**: replace `from .core.sync_scheduler import setup_scheduler` with `from .jobs.scheduler import setup_scheduler`.
- **`routes/strava.py`** `/connect`: after successful connect, call `registry.register_athlete_jobs(athlete_id, "strava")`.
- **`routes/connectors.py`** hevy/terra connect endpoints: call `registry.register_athlete_jobs(athlete_id, provider)`.
- **`routes/connectors.py`** delete endpoint: call `registry.unregister_athlete_jobs(athlete_id, provider)`.
- **New** `routes/admin.py` — admin jobs endpoint.
- **`main.py`**: add `admin_router`.

---

## Data Model

### `job_runs` table

| Column | Type | Notes |
|---|---|---|
| id | String PK | UUID |
| job_id | String, not null | APScheduler job ID (e.g. `strava_sync_{athlete_id}`) |
| athlete_id | String FK → athletes.id | nullable (global jobs have no athlete) |
| job_type | String, not null | `strava_sync`, `hevy_sync`, `terra_sync`, `daily_snapshot`, `energy_patterns`, `cleanup` |
| status | String, not null | `ok`, `error`, `timeout` |
| started_at | DateTime(tz), not null | |
| duration_ms | Integer, not null | |
| error_message | Text | nullable, truncated to 2000 chars |
| created_at | DateTime(tz) | server default utcnow |

Index on `(job_type, created_at)` for cleanup queries.

### `athlete_state_snapshots` table

| Column | Type | Notes |
|---|---|---|
| id | String PK | UUID |
| athlete_id | String FK → athletes.id, CASCADE | not null |
| snapshot_date | Date, not null | |
| readiness | Float, not null | range 0.5–1.5 |
| strain_json | Text, not null | JSON serialized MuscleStrainScore |
| created_at | DateTime(tz) | server default utcnow |

UniqueConstraint on `(athlete_id, snapshot_date)` — idempotent; daily job can rerun safely via upsert.

### Alembic migration 0009

Creates both tables. No changes to existing tables.

---

## Job Definitions

### Per-Athlete Jobs (dynamic)

Created when athlete connects a provider, removed on disconnect.

| Job | Trigger | ID pattern | Timeout |
|---|---|---|---|
| Strava sync | interval 1h | `strava_sync_{athlete_id}` | 60s |
| Hevy sync | interval 6h | `hevy_sync_{athlete_id}` | 60s |
| Terra sync | interval 6h | `terra_sync_{athlete_id}` | 60s |

Each job calls the existing sync function for that athlete:
- Strava: `integrations.strava.sync_service.sync(athlete_id, db)`
- Hevy: `services.sync_service.SyncService.sync_hevy(athlete_id, db)`
- Terra: `services.sync_service.SyncService.sync_terra(athlete_id, db)`

### Global Jobs (always running)

| Job | Trigger | ID | Timeout |
|---|---|---|---|
| Daily snapshot | cron 4:00 UTC | `daily_snapshot` | 300s |
| Energy patterns | cron Monday 6:00 UTC | `energy_patterns` | 300s |
| Job log cleanup | cron Sunday 3:00 UTC | `cleanup_job_runs` | 60s |

### Strava Token Refresh

No dedicated job. `oauth_service.get_valid_credential()` already auto-refreshes expired tokens at sync time. With hourly sync, tokens (6h expiry) are refreshed well before expiration.

---

## Job Execution Wrapper

Every job runs through `run_job(job_id, job_type, athlete_id, fn)`:

1. Record `started_at` in `job_runs`
2. Execute `fn()` with timeout enforcement via `threading.Timer`
3. On success: log `status=ok`, `duration_ms`
4. On exception: log `status=error`, `error_message` (truncated 2000 chars)
5. On timeout: log `status=timeout`, kill the function

No retry for V1 — the next scheduled interval is the natural retry. All jobs are idempotent.

---

## Registry

`registry.py` manages the per-athlete job lifecycle:

- **`register_athlete_jobs(athlete_id, provider, scheduler)`** — adds the provider's interval job to APScheduler with `replace_existing=True`. Called after successful connect.
- **`unregister_athlete_jobs(athlete_id, provider, scheduler)`** — removes the job from APScheduler. Called on disconnect/delete.
- **`restore_all_jobs(scheduler, db)`** — called at startup. Queries `connector_credentials` table, registers jobs for all connected athletes. Ensures dynamic jobs exist after restart.

Job ID convention: `{provider}_sync_{athlete_id}` (e.g. `strava_sync_abc-123`).

---

## Scheduler Setup

`scheduler.py`:

```python
def setup_scheduler() -> BackgroundScheduler:
    jobstores = {"default": SQLAlchemyJobStore(url=DATABASE_URL)}
    scheduler = BackgroundScheduler(jobstores=jobstores)

    # Global jobs
    scheduler.add_job(run_daily_snapshot, trigger="cron", hour=4, id="daily_snapshot", ...)
    scheduler.add_job(run_energy_patterns, trigger="cron", day_of_week="mon", hour=6, id="energy_patterns", ...)
    scheduler.add_job(run_cleanup_job_runs, trigger="cron", day_of_week="sun", hour=3, id="cleanup_job_runs", ...)

    scheduler.start()

    # Restore per-athlete jobs from DB
    with SessionLocal() as db:
        restore_all_jobs(scheduler, db)

    return scheduler
```

Integrated in `main.py` lifespan (same pattern as current).

---

## Admin Endpoint

**Route:** `GET /admin/jobs`
**File:** `backend/app/routes/admin.py`
**Auth:** JWT + `ADMIN_ATHLETE_ID` env var. Returns 403 if `current_athlete_id != ADMIN_ATHLETE_ID`.

**Response:**
```json
{
  "jobs": [
    {
      "job_id": "strava_sync_abc-123",
      "job_type": "strava_sync",
      "athlete_id": "abc-123",
      "next_run": "2026-04-14T15:00:00Z",
      "last_run": {
        "status": "ok",
        "started_at": "2026-04-14T14:00:00Z",
        "duration_ms": 1230
      }
    }
  ],
  "summary": {
    "total_jobs": 12,
    "errors_24h": 2,
    "next_run": "2026-04-14T14:30:00Z"
  }
}
```

`summary.next_run` = earliest `next_run_time` across all scheduled jobs.
`summary.errors_24h` = count of `job_runs` with `status != 'ok'` in last 24h.

---

## Env Vars

- `ADMIN_ATHLETE_ID` — UUID of the admin athlete (you). Required for `/admin/jobs`.
- No new scheduler-specific env vars. APScheduler uses existing `DATABASE_URL` for job store.

---

## Error Handling

- Job wrapper catches **all** exceptions — scheduler never crashes.
- Error messages truncated to 2000 chars in `job_runs`.
- `ConnectorRateLimitError`: logged as `status=error` with `retry_after` value in error_message.
- Timeout: `threading.Timer` sets a flag; job wrapper checks and logs `status=timeout`.
- No retry for V1. Next scheduled execution is the natural retry.

---

## Testing Strategy

~19 tests total:

| Area | Tests | Approach |
|---|---|---|
| Job wrapper (`run_job`) | 3 | Mock job fn: success, error, timeout |
| Registry | 3 | Mock scheduler: register, unregister, restore_all |
| Sync jobs | 3 | Mock sync services, verify `run_job` called correctly |
| Daily snapshot | 3 | Real SQLite DB, `freezegun`, verify upsert idempotency |
| Cleanup job | 2 | Real SQLite DB, `freezegun`, verify old rows deleted |
| Energy patterns wrapper | 1 | Mock `detect_energy_patterns`, verify job wrapper |
| Admin endpoint | 3 | API client: 200 with jobs, 403 non-admin, empty state |
| **Total** | **~19** | |

Dependencies: `freezegun` (add to dev deps if not present).

---

## Out of Scope

- Distributed workers / Celery (future when >100 athletes)
- Per-athlete timezone-aware scheduling (V2 — all cron jobs run UTC for V1)
- Retry with backoff (V2 — natural interval retry sufficient for V1)
- Webhook-triggered sync (V2 — Strava supports push subscriptions)
- UI for job monitoring (V2 — admin endpoint + DB queries sufficient for V1)
