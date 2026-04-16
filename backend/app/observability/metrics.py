"""In-memory metrics: counters + latency summaries."""
from __future__ import annotations

import collections
import math
import threading
import time
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
        k = max(0, min(len(sorted_samples) - 1, int(math.ceil(p / 100.0 * len(sorted_samples))) - 1))
        return sorted_samples[k]

    def snapshot(self) -> dict[str, Any]:
        return {
            "count": self.count,
            "mean": round(self.mean(), 3),
            "p50": round(self.percentile(50), 3),
            "p95": round(self.percentile(95), 3),
            "p99": round(self.percentile(99), 3),
        }
