# Observability

Resilio+ emits structured JSON logs, per-request correlation IDs, in-memory runtime metrics, and optional Sentry error events.

## Log Format

Every log line is a single-line JSON object:

```json
{
  "ts": "2026-04-16T12:34:56.789Z",
  "level": "info",
  "logger": "app.routes.plans",
  "msg": "plan_created",
  "correlation_id": "a1b2c3d4-...",
  "athlete_id": "uuid-...",
  "path": "/plans",
  "status": 201,
  "duration_ms": 123
}
```

Fields:

| Field | When present | Source |
|---|---|---|
| `ts` | always | ISO 8601 UTC |
| `level` | always | `info` / `warning` / `error` / etc. |
| `logger` | always | Python logger name |
| `msg` | always | short snake_case event name preferred |
| `correlation_id` | always (`"-"` if unset) | `correlation_id_ctx` ContextVar |
| `athlete_id` | when request authenticated | `athlete_id_ctx` ContextVar |
| `error.type`, `error.message`, `error.stack` | on exceptions | `exc_info` |
| custom extra fields | when logger called with `extra={...}` | merged verbatim (after PII filter) |

## Correlation IDs

- HTTP requests: `CorrelationIdMiddleware` reads `X-Request-ID` header or generates a UUID4. The value is set on `correlation_id_ctx` for the request duration and echoed back in the response `X-Request-ID` header.
- Background jobs: `run_job()` sets `job-<uuid4>` as the correlation ID; the worker thread inherits it via `contextvars.copy_context()`.

To trace a request end-to-end in logs:

```bash
curl -H "X-Request-ID: my-trace-id" http://localhost:8000/plans
# then search logs for "my-trace-id"
```

## Metrics (`GET /admin/metrics`)

Protected by `ADMIN_ATHLETE_ID` (same gate as `/admin/jobs`). Returns:

```json
{
  "started_at": "2026-04-16T00:00:00Z",
  "uptime_s": 3600,
  "http": {
    "requests_total": {"GET /athletes/{id}:200": 45, "POST /plans:201": 3},
    "latency_ms": {
      "GET /athletes/{id}": {"count": 45, "mean": 12.3, "p50": 9.0, "p95": 28.0, "p99": 55.0}
    }
  },
  "agents": {
    "calls_total": {"head_coach:ok": 12, "running_coach:error": 1},
    "latency_ms": {"head_coach": {"count": 12, "mean": 450.0, "p50": 410.0, "p95": 820.0, "p99": 1100.0}}
  },
  "jobs": {
    "runs_total": {"strava_sync:ok": 24, "hevy_sync:timeout": 1}
  }
}
```

Counters reset on app restart. Latency summaries store the last 1000 samples per key (bounded memory).

Example:

```bash
curl -H "Authorization: Bearer $JWT" http://localhost:8000/admin/metrics | jq
```

## PII Filter

Attached to root logger + Sentry `before_send`. Scrubs automatically:

**Field-name blocklist (case-insensitive):**
`password, passwd, token, access_token, refresh_token, authorization, auth, api_key, apikey, secret, fernet_key, encryption_key, smtp_password, jwt, bearer, client_secret, cookie`

**Regex patterns (scrubbed in `msg` strings and string values):**
- JWT: `eyJ[...].[...].[...]`
- Bearer tokens: `Bearer <token>`
- Email addresses
- Long hex strings (≥32 chars, e.g., Fernet keys, API keys)

To add a new blocklisted field, edit `_BLOCKLIST_FIELDS` in `backend/app/observability/pii_filter.py` and add a regression test in `tests/backend/observability/test_pii_filter.py`.

## Sentry (optional)

Disabled by default. To enable, set `SENTRY_DSN` in `.env`. All Sentry events run through the same PII scrubber as logs. `send_default_pii=False` as defense in depth.

Env vars:

| Var | Default | Purpose |
|---|---|---|
| `SENTRY_DSN` | empty | Sentry project DSN; empty = disabled |
| `SENTRY_ENVIRONMENT` | `development` | e.g., `production`, `staging` |
| `SENTRY_RELEASE` | unset | version/git SHA for release tracking |
| `SENTRY_TRACES_SAMPLE_RATE` | `0.0` | performance traces sampling rate (0.0–1.0) |

## Cheat Sheet

**Add a metric counter for a new code path:**
```python
from app.observability.metrics import metrics
metrics.inc_agent("my_new_agent", "ok", duration_ms)
```

**Log a structured event:**
```python
import logging
logger = logging.getLogger(__name__)
logger.info("thing_happened", extra={"thing_id": "123", "count": 5})
```

**Trace a request:**
1. Frontend/client sets `X-Request-ID: <your-id>` header.
2. Backend echoes it back on the response.
3. Search logs for `"correlation_id": "<your-id>"`.

## Architecture

- Module: `backend/app/observability/`
- Middleware stack (outer → inner): `CORSMiddleware` → `CorrelationIdMiddleware` → `MetricsMiddleware` → handler
- `configure_logging()` called at the top of `backend/app/main.py` before any router imports
- `init_sentry()` called after `configure_logging()`; no-op if `SENTRY_DSN` unset or `sentry-sdk` not installed
