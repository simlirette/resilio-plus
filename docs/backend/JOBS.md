# Background Jobs

Resilio+ uses APScheduler 3.x for background job scheduling.

## Job Types

### Per-Athlete Jobs (dynamic)

Created when athlete connects a provider, removed on disconnect.

| Job | Frequency | What it does |
|---|---|---|
| `strava_sync_{id}` | Every 1h | Incremental Strava activity sync via `integrations.strava.sync_service.sync()` |
| `hevy_sync_{id}` | Every 6h | Hevy workout sync via `SyncService.sync_hevy()` |
| `terra_sync_{id}` | Every 6h | Terra HRV/sleep sync via `SyncService.sync_terra()` |

### Global Jobs

| Job | Schedule | What it does |
|---|---|---|
| `daily_snapshot` | 4:00 UTC daily | Compute readiness + strain for all athletes, store in `athlete_state_snapshots` |
| `energy_patterns` | Monday 6:00 UTC | Detect energy patterns, create proactive Head Coach messages |
| `cleanup_job_runs` | Sunday 3:00 UTC | Delete `job_runs` older than 30 days |

## How to Add a Job

1. Create your job function in `backend/app/jobs/` (e.g. `my_jobs.py`)
2. Wrap execution with `run_job()` from `jobs/runner.py` — this handles logging to `job_runs`
3. Register in `jobs/scheduler.py` (global) or `jobs/registry.py` (per-athlete)
4. Add tests in `tests/backend/jobs/`

## Monitoring

`GET /admin/jobs` — requires JWT + `ADMIN_ATHLETE_ID` env var match.

Returns all scheduled jobs with last run status, next run time, and 24h error count.

## Debugging

```sql
-- Recent failures
SELECT job_id, status, error_message, started_at
FROM job_runs WHERE status != 'ok'
ORDER BY started_at DESC LIMIT 20;

-- Job frequency
SELECT job_type, COUNT(*), AVG(duration_ms)
FROM job_runs WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY job_type;
```

## Architecture

- Module: `backend/app/jobs/`
- DB tables: `job_runs` (execution log), `athlete_state_snapshots` (daily snapshots)
- Scheduler starts in FastAPI lifespan (`main.py`)
- Per-athlete jobs registered on connect, unregistered on disconnect
- All jobs are idempotent — safe to rerun
- Timeout per job (60s for sync, 300s for compute)
- No retry — next scheduled interval is the natural retry
