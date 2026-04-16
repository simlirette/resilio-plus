"""In-memory metrics: counters + latency summaries."""
from __future__ import annotations

import collections
import math
import threading
import time
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any


class LatencySummary:
    """Bounded-memory latency collector. Stores up to maxlen samples for percentiles."""

    def __init__(self, maxlen: int = 1000) -> None:
        self.count: int = 0
        self.sum_ms: float = 0.0
        self._samples: collections.deque[float] = collections.deque(maxlen=maxlen)

    def observe(self, ms: float) -> None:
        self.count += 1
        self.sum_ms += ms
        self._samples.append(ms)

    def mean(self) -> float:
        if self.count == 0:
            return 0.0
        return self.sum_ms / self.count

    def percentile(self, p: float) -> float:
        if not self._samples:
            return 0.0
        sorted_samples = sorted(self._samples)
        # Nearest-rank method
        k = max(
            0, min(len(sorted_samples) - 1, int(math.ceil(p / 100.0 * len(sorted_samples))) - 1)
        )
        return sorted_samples[k]

    def snapshot(self) -> dict[str, Any]:
        return {
            "count": self.count,
            "mean": round(self.mean(), 3),
            "p50": round(self.percentile(50), 3),
            "p95": round(self.percentile(95), 3),
            "p99": round(self.percentile(99), 3),
        }


class Metrics:
    """Thread-safe in-memory counters + latency summaries."""

    def __init__(self) -> None:
        self.started_at: datetime = datetime.now(timezone.utc)
        self.http_requests_total: dict[tuple[str, str, int], int] = collections.defaultdict(int)
        self.http_latency_ms: dict[tuple[str, str], LatencySummary] = collections.defaultdict(
            LatencySummary
        )
        self.agent_calls_total: dict[tuple[str, str], int] = collections.defaultdict(int)
        self.agent_latency_ms: dict[str, LatencySummary] = collections.defaultdict(LatencySummary)
        self.jobs_total: dict[tuple[str, str], int] = collections.defaultdict(int)
        self._lock: threading.Lock = threading.Lock()

    def inc_http(self, method: str, path: str, status: int, duration_ms: float) -> None:
        with self._lock:
            self.http_requests_total[(method, path, status)] += 1
            self.http_latency_ms[(method, path)].observe(duration_ms)

    def inc_agent(self, agent: str, status: str, duration_ms: float) -> None:
        with self._lock:
            self.agent_calls_total[(agent, status)] += 1
            self.agent_latency_ms[agent].observe(duration_ms)

    def inc_job(self, job_type: str, status: str) -> None:
        with self._lock:
            self.jobs_total[(job_type, status)] += 1

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            uptime = (datetime.now(timezone.utc) - self.started_at).total_seconds()
            return {
                "started_at": self.started_at.isoformat().replace("+00:00", "Z"),
                "uptime_s": round(uptime, 1),
                "http": {
                    "requests_total": {
                        f"{m} {p}:{s}": n for (m, p, s), n in self.http_requests_total.items()
                    },
                    "latency_ms": {
                        f"{m} {p}": summary.snapshot()
                        for (m, p), summary in self.http_latency_ms.items()
                    },
                },
                "agents": {
                    "calls_total": {f"{a}:{s}": n for (a, s), n in self.agent_calls_total.items()},
                    "latency_ms": {
                        a: summary.snapshot() for a, summary in self.agent_latency_ms.items()
                    },
                },
                "jobs": {
                    "runs_total": {f"{jt}:{s}": n for (jt, s), n in self.jobs_total.items()},
                },
            }


# Module-level singleton
metrics = Metrics()


from starlette.middleware.base import BaseHTTPMiddleware  # noqa: E402
from starlette.requests import Request  # noqa: E402
from starlette.responses import Response  # noqa: E402


class MetricsMiddleware(BaseHTTPMiddleware):
    """Record HTTP request count + latency per (method, path_template, status)."""

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        t0 = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            resp: Response = response
            return resp
        finally:
            duration_ms = (time.perf_counter() - t0) * 1000
            # Prefer the parameterized route template; fall back to raw path
            route = request.scope.get("route")
            path = route.path if route is not None and hasattr(route, "path") else request.url.path
            metrics.inc_http(request.method, path, status, duration_ms)


@contextmanager
def track_agent_call(agent_name: str) -> Generator[None, None, None]:
    """Context manager: time an agent call, record ok/error status."""
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
