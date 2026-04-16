# V3-U — Observability Stack Design

**Status:** Spec — awaiting implementation plan
**Date:** 2026-04-16
**Follows:** V3-S (background jobs), V3-T (LangGraph runtime — `resilio.graph` JSON logger)

---

## Goal

Minimal but complete observability V1 for the Resilio+ FastAPI backend, building on the JSON log format already in place for `resilio.graph` (V3-T). Uniformize structured logging across routes, services, integrations, and background jobs; add HTTP correlation IDs; expose in-memory runtime metrics behind an admin endpoint; wire optional Sentry error tracking. Zero PII leakage.

Out of scope:
- Prometheus exposition / external TSDB
- Distributed tracing (OpenTelemetry)
- APM vendor beyond Sentry
- Dashboards — consumers of `/admin/metrics` and logs are external
- Changes to `backend/app/deployment/` or `Dockerfile` (parallel session)

---

## Architecture

New module `backend/app/observability/`:

```
backend/app/observability/
├── __init__.py           — re-exports: configure_logging, init_sentry, metrics, track_agent_call, correlation_id_ctx
├── logging_config.py     — JSON formatter + root logger setup + filter attachment
├── pii_filter.py         — PIIFilter(logging.Filter) — field blocklist + regex scrubbers
├── correlation.py        — ContextVar + CorrelationIdMiddleware (FastAPI BaseHTTPMiddleware)
├── metrics.py            — Metrics singleton + LatencySummary + MetricsMiddleware + track_agent_call
└── sentry.py             — init_sentry() — no-op if SENTRY_DSN unset
```

Wire-up in `backend/app/main.py`:
1. `configure_logging()` at import time (runs before routers register)
2. `init_sentry()` (no-op if `SENTRY_DSN` unset)
3. Middleware stack order: CORS (outer) → CorrelationIdMiddleware → MetricsMiddleware → app
4. `/admin/metrics` added to existing `admin_router` (shares `_require_admin` dep with `/admin/jobs`)

Jobs: wrap `run_job()` internals (no API change) — set `correlation_id_ctx` to `job-<uuid4>`, emit `job_start`/`job_end` JSON events to `resilio.jobs` logger, increment `metrics.jobs_total` counter.

Agent calls: `track_agent_call(agent_name)` context manager wraps each of the 7 coaching agents' main entry points (`HeadCoach.build_week`, `RunningCoach.propose`, etc.).

Tests in `tests/backend/observability/` (new dir). Target ~39 new tests.

---

## Components

### Log format (unified JSON)

Every log line across every logger:

```json
{
  "ts": "2026-04-16T12:34:56.789Z",
  "level": "info",
  "logger": "app.routes.plans",
  "msg": "plan_created",
  "correlation_id": "a1b2c3d4-5678-...",
  "athlete_id": "e9f0g1h2-...",
  "path": "/plans",
  "status": 201,
  "duration_ms": 123
}
```

Field rules:
- `ts` — ISO 8601 UTC, always present
- `level` — `debug|info|warning|error|critical`
- `logger` — record's logger name
- `msg` — record's message string (short snake_case event name preferred, free text permitted)
- `correlation_id` — from `correlation_id_ctx` ContextVar; `"-"` if unset (never missing key)
- `athlete_id` — from `athlete_id_ctx` ContextVar; omitted if unset
- Extra fields from `extra={...}` merged into output after PII filter
- Exceptions: auto-serialized via `exc_info` → `error.type`, `error.message`, `error.stack` (stack truncated to 4096 chars)

Compatibility with `resilio.graph` (V3-T): existing `logger.info(json.dumps({...}))` calls continue to work — the JSON string becomes the `msg` field (nested string, harmless). No regression; cleanup of those call sites is optional future work.

### PII filter

`PIIFilter(logging.Filter)` mutates `record.args`, `record.msg`, and any dict-type values in `record.__dict__` (for `extra` fields) before formatter runs.

**Field-name blocklist** (case-insensitive, exact match):
```
password, passwd, token, access_token, refresh_token, authorization,
auth, api_key, apikey, secret, fernet_key, encryption_key,
smtp_password, jwt, bearer, client_secret, cookie
```
Matching values replaced with `"***"`. Applied recursively to dict values and list elements up to depth 5.

**Regex scrubbers** (applied to `msg` string and any string-type values):
| Name | Pattern | Purpose |
|---|---|---|
| JWT | `eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+` | JWT tokens |
| Bearer | `[Bb]earer\s+[A-Za-z0-9_.-]+` | `Authorization: Bearer ...` |
| Email | `[\w.+-]+@[\w-]+\.[\w.-]+` | Email addresses |
| Hex ≥32 | `[a-fA-F0-9]{32,}` | Fernet keys, long API keys |

Matched substrings replaced with `"***"`. Filter is idempotent and safe to chain.

Filter is attached to the root logger (so it applies to every logger in the app, including `resilio.graph`, `resilio.jobs`, and third-party libs like `uvicorn.access`).

### Correlation ID

`correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="-")`.

`CorrelationIdMiddleware(BaseHTTPMiddleware)` logic:
1. Read `X-Request-ID` header.
2. Validate — must match `^[A-Za-z0-9_-]{1,128}$`. If absent or invalid, generate `str(uuid.uuid4())`.
3. `token = correlation_id_ctx.set(cid)` — ContextVar set within request scope.
4. `try: response = await call_next(request)` — dispatch handler.
5. `response.headers["X-Request-ID"] = cid` — echo back.
6. `finally: correlation_id_ctx.reset(token)` — clean up.

For jobs: `run_job()` sets `correlation_id_ctx.set(f"job-{uuid4()}")` at entry, resets at exit. Worker thread captures ContextVar via `contextvars.copy_context().run(...)` so logs inside the worker carry the same ID.

`athlete_id_ctx` follows the same pattern — set by `get_current_athlete_id` dependency, reset at request end.

### Metrics

Module-level singleton `metrics` in `backend/app/observability/metrics.py`:

```python
class LatencySummary:
    def __init__(self, maxlen: int = 1000) -> None:
        self.count: int = 0
        self.sum_ms: float = 0.0
        self._samples: collections.deque[float] = collections.deque(maxlen=maxlen)
    
    def observe(self, ms: float) -> None: ...
    def mean(self) -> float: ...
    def percentile(self, p: float) -> float: ...  # p in [0, 100]
    def snapshot(self) -> dict: ...  # {count, mean, p50, p95, p99}


class Metrics:
    def __init__(self) -> None:
        self.started_at: datetime = datetime.now(timezone.utc)
        self.http_requests_total: dict[tuple[str, str, int], int] = defaultdict(int)
        self.http_latency_ms: dict[tuple[str, str], LatencySummary] = defaultdict(LatencySummary)
        self.agent_calls_total: dict[tuple[str, str], int] = defaultdict(int)
        self.agent_latency_ms: dict[str, LatencySummary] = defaultdict(LatencySummary)
        self.jobs_total: dict[tuple[str, str], int] = defaultdict(int)
        self._lock: threading.Lock = threading.Lock()
    
    def inc_http(self, method: str, path: str, status: int, duration_ms: float) -> None: ...
    def inc_agent(self, agent: str, status: str, duration_ms: float) -> None: ...
    def inc_job(self, job_type: str, status: str) -> None: ...
    def snapshot(self) -> dict: ...


metrics = Metrics()
```

Thread-safe via internal `_lock` — jobs run in worker threads; HTTP middleware runs in asyncio event loop thread.

**Path template capture:** MetricsMiddleware uses `request.scope["route"].path` (FastAPI populates after routing) to get parameterized path `/athletes/{id}/plans` — prevents cardinality explosion from raw IDs. Fallback to `request.url.path` if route absent (404s).

**Agent call helper:**
```python
@contextmanager
def track_agent_call(agent_name: str):
    t0 = time.perf_counter()
    status = "ok"
    try:
        yield
    except Exception:
        status = "error"
        raise
    finally:
        ms = (time.perf_counter() - t0) * 1000
        metrics.inc_agent(agent_name, status, ms)
```

Wrapped at each of the 7 agents' primary entry points. Agent names: `head_coach`, `running_coach`, `lifting_coach`, `swimming_coach`, `biking_coach`, `nutrition_coach`, `recovery_coach`.

### `/admin/metrics` endpoint

New route in `backend/app/routes/admin.py` (reuses `_require_admin` dep — same `ADMIN_ATHLETE_ID` gate as `/admin/jobs`):

```python
@router.get("/metrics")
def get_metrics(_: Annotated[str, Depends(_require_admin)]) -> dict:
    return metrics.snapshot()
```

Response schema:
```json
{
  "started_at": "2026-04-16T00:00:00Z",
  "uptime_s": 3600,
  "http": {
    "requests_total": {"GET /athletes/{id}:200": 45, "POST /plans:201": 3, "GET /athletes:500": 1},
    "latency_ms": {
      "GET /athletes/{id}": {"count": 45, "mean": 12.3, "p50": 9.0, "p95": 28.0, "p99": 55.0}
    }
  },
  "agents": {
    "calls_total": {"head_coach:ok": 12, "running_coach:error": 1},
    "latency_ms": {
      "head_coach": {"count": 12, "mean": 450.0, "p50": 410.0, "p95": 820.0, "p99": 1100.0}
    }
  },
  "jobs": {
    "runs_total": {"strava_sync:ok": 24, "hevy_sync:timeout": 1}
  }
}
```

Counter keys use `"<label>:<label>"` string format (JSON-safe) flattened from tuple keys.

### Sentry

`backend/app/observability/sentry.py`:

```python
def init_sentry() -> None:
    dsn = os.getenv("SENTRY_DSN", "").strip()
    if not dsn:
        logger.info("sentry_disabled_no_dsn")
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
    except ImportError:
        logger.warning("sentry_sdk_not_installed")
        return
    
    sentry_sdk.init(
        dsn=dsn,
        environment=os.getenv("SENTRY_ENVIRONMENT", "development"),
        release=os.getenv("SENTRY_RELEASE") or None,
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.0")),
        send_default_pii=False,
        before_send=_sentry_pii_scrubber,
        integrations=[
            FastApiIntegration(),
            StarletteIntegration(),
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
        ],
    )
    logger.info("sentry_initialized")
```

`_sentry_pii_scrubber(event, hint) -> event | None`: reuses `PIIFilter` logic on `event["extra"]`, `event["contexts"]`, `event["request"]`, `event["user"]` sub-dicts. Attaches `correlation_id` from ContextVar as a Sentry tag.

`sentry-sdk` added to `pyproject.toml` (runtime dep). Import is guarded in case of future removal; ImportError → no-op with warning log.

---

## Data flow

### HTTP request flow
```
Request arrives
  → CORSMiddleware (outer)
  → CorrelationIdMiddleware: read X-Request-ID or gen UUID → set correlation_id_ctx
  → MetricsMiddleware: t0 = perf_counter()
  → routing → get_current_athlete_id dep → sets athlete_id_ctx
  → handler executes (logger calls inside automatically tagged with correlation_id + athlete_id)
  → response returned
  → MetricsMiddleware: metrics.inc_http(method, path_template, status, perf_counter() - t0)
  → CorrelationIdMiddleware: response.headers["X-Request-ID"] = cid; reset ContextVars
  → CORSMiddleware: adds CORS headers
  → response sent
```

### Job run flow
```
Scheduler triggers run_job()
  → correlation_id_ctx.set(f"job-{uuid4()}")
  → logger.info("job_start", extra={"job_id":..., "job_type":..., "athlete_id":...})
  → worker thread dispatched with copy_context().run(...) — inherits ContextVar
  → fn() executes (logger calls inside carry correlation_id)
  → worker completes or times out
  → logger.info("job_end", extra={"status":..., "duration_ms":..., "error":...})
  → metrics.inc_job(job_type, status)
  → if status == "error": sentry_sdk.capture_exception(exc) (if Sentry enabled)
  → DB job_runs row written (existing behavior, unchanged)
  → correlation_id_ctx.reset(token)
```

### Error flow (request)
```
handler raises Exception
  → FastApiIntegration captures + sends to Sentry (if enabled, via before_send PII scrubber)
  → outer middleware catches → logs {"level":"error","msg":"request_failed","exc_info":true}
  → MetricsMiddleware increments http_requests_total{status=500}
  → FastAPI default 500 response
```

---

## Environment variables

`.env.example` additions:
```
# Observability — Sentry (optional; leave empty to disable)
SENTRY_DSN=
SENTRY_ENVIRONMENT=development
SENTRY_RELEASE=
SENTRY_TRACES_SAMPLE_RATE=0.0
```

No other env vars required. `ADMIN_ATHLETE_ID` (existing, from V3-S) gates `/admin/metrics`.

---

## Testing

New dir `tests/backend/observability/` with:

| File | Tests | Coverage |
|---|---|---|
| `test_pii_filter.py` | ~12 | each blocklisted field scrubbed, each regex pattern, nested recursion, exc_info args, idempotency, legitimate data preserved |
| `test_logging_config.py` | ~5 | JSON shape, extra merged, correlation_id/athlete_id from ContextVar, `resilio.graph` compat |
| `test_correlation.py` | ~6 | uuid gen on missing header, echo on valid header, invalid header regenerated, ContextVar set/reset, response header present |
| `test_metrics.py` | ~8 | http counter + latency, path template used (not raw ID), agent tracker ok/error, jobs counter, deque maxlen, percentile on small sample |
| `test_admin_metrics.py` | ~4 | 403 no auth, 403 wrong athlete, 200 admin match, response schema |
| `test_sentry.py` | ~4 | no-op on unset DSN, no-op on ImportError, before_send scrubs email in message, before_send scrubs token in extra |

Total: ~39 new tests. Target: 2310 → 2349 passing (2 pre-existing unrelated failures remain).

**Test infrastructure:**
- `caplog` for log capture (pytest built-in)
- FastAPI `TestClient` for middleware + admin endpoint
- `unittest.mock.patch` for `sentry_sdk.init` assertion + `os.environ` for Sentry toggles
- No new fixtures needed

---

## Documentation

**New file:** `docs/backend/OBSERVABILITY.md` — format matching `docs/backend/JOBS.md`:
- Overview + scope
- Log format spec + example lines
- Correlation ID flow (HTTP + jobs)
- Metrics endpoint schema + curl example
- PII filter rules + how to add a new field/pattern
- Sentry env vars + conditional behavior
- Cheat sheet: "how to add a metric", "how to log a new event", "how to trace a request"

**Updates:**
- `CLAUDE.md`: V3-U phase table row + references entry (via `/revise-claude-md` at end)
- `.env.example`: Sentry vars

---

## Implementation order (high-level for plan phase)

1. PII filter + unit tests (leaf dep, no FastAPI needed)
2. Logging config (JSON formatter, root logger setup, `configure_logging()`)
3. Correlation ID ContextVars + middleware
4. Metrics (LatencySummary, Metrics singleton, MetricsMiddleware, `track_agent_call`)
5. Sentry (conditional init + before_send scrubber)
6. `/admin/metrics` endpoint
7. Wire into `main.py`
8. Instrument `run_job()` (correlation_id + structured logs + metrics)
9. Instrument 7 coaching agents with `track_agent_call`
10. `docs/backend/OBSERVABILITY.md`
11. `.env.example` update
12. `pyproject.toml` add `sentry-sdk`
13. `poetry install` + full test run verification

Each step gets a task in the implementation plan with TDD red→green→refactor cycle + atomic commit.

---

## Invariants post-implementation

- `poetry install` succeeds
- `pytest tests/` shows ≥2349 passing (2 pre-existing unrelated failures unchanged)
- `curl http://localhost:8000/health` (or any endpoint) returns `X-Request-ID` header
- `grep -r 'password\|token\|refresh_token\|Bearer\|eyJ' logs/` on a smoke-test log dump returns zero matches (PII filter working)
- `GET /admin/metrics` with admin JWT returns schema-valid JSON; without, returns 403
- Sentry unset → no Sentry network calls (verified via `respx` in test)
- `logger.info("hello")` anywhere in backend emits JSON line matching format above

---

## Risks + mitigations

| Risk | Mitigation |
|---|---|
| Root logger JSON config conflicts with uvicorn access log formatter | Use `dictConfig` with explicit uvicorn handler passthrough; test manually with `uvicorn --log-config ...` |
| ContextVar leak across async tasks | Use `contextvars.copy_context()` on thread spawn; test inheritance in `test_correlation.py` |
| High-cardinality path labels (e.g., `/athletes/abc-123`) blow up metrics dict | Use `request.scope["route"].path` (parameterized); test explicit path template extraction |
| PII regex false positives scrubbing legitimate content (e.g., `@` in user comments) | Keep scope to known formats; test `test_pii_filter.py` has "preserves legitimate" case; document in OBSERVABILITY.md |
| Sentry PII leak via before_send bypassed | Test `before_send` explicitly; `send_default_pii=False` as defense in depth |
| Metrics singleton growing unbounded over long uptime | `LatencySummary` uses bounded `deque(maxlen=1000)`; counter dicts naturally bounded by endpoint/agent count |
| Thread safety on metrics increments | Explicit `threading.Lock()` in Metrics; test with `concurrent.futures` |

---

## References

- `docs/backend/LANGGRAPH-FLOW.md` — V3-T source of `resilio.graph` JSON logger pattern
- `docs/backend/JOBS.md` — V3-S `run_job()` wrapper (target for instrumentation) + `/admin/jobs` template
- `backend/app/routes/admin.py` — `_require_admin` dep (reuse for `/admin/metrics`)
- `backend/app/graphs/logging.py` — `log_node` decorator (reference implementation of structured JSON logs)
- Sentry Python SDK: https://docs.sentry.io/platforms/python/integrations/fastapi/ (doc fetch during implementation via context7)
