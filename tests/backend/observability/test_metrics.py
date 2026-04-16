from app.observability.metrics import LatencySummary


def test_latency_observe_increments_count_and_sum():
    s = LatencySummary()
    s.observe(10.0)
    s.observe(20.0)
    assert s.count == 2
    assert s.sum_ms == 30.0


def test_latency_mean():
    s = LatencySummary()
    s.observe(10.0)
    s.observe(20.0)
    s.observe(30.0)
    assert s.mean() == 20.0


def test_latency_mean_zero_samples():
    s = LatencySummary()
    assert s.mean() == 0.0


def test_latency_percentiles():
    s = LatencySummary()
    for v in range(1, 101):
        s.observe(float(v))
    assert s.percentile(50) == 50.0
    assert s.percentile(95) == 95.0
    assert s.percentile(99) == 99.0


def test_latency_percentile_empty():
    s = LatencySummary()
    assert s.percentile(50) == 0.0


def test_latency_deque_maxlen_enforced():
    s = LatencySummary(maxlen=5)
    for v in range(10):
        s.observe(float(v))
    assert s.count == 10              # counter not bounded
    assert len(s._samples) == 5       # deque bounded


def test_latency_snapshot_shape():
    s = LatencySummary()
    s.observe(5.0)
    snap = s.snapshot()
    assert set(snap.keys()) == {"count", "mean", "p50", "p95", "p99"}
    assert snap["count"] == 1


import pytest
from app.observability.metrics import Metrics


def test_metrics_inc_http():
    m = Metrics()
    m.inc_http("GET", "/athletes/{id}", 200, 12.5)
    m.inc_http("GET", "/athletes/{id}", 200, 18.0)
    assert m.http_requests_total[("GET", "/athletes/{id}", 200)] == 2
    assert m.http_latency_ms[("GET", "/athletes/{id}")].count == 2


def test_metrics_inc_agent():
    m = Metrics()
    m.inc_agent("running_coach", "ok", 320.0)
    m.inc_agent("running_coach", "error", 15.0)
    assert m.agent_calls_total[("running_coach", "ok")] == 1
    assert m.agent_calls_total[("running_coach", "error")] == 1
    assert m.agent_latency_ms["running_coach"].count == 2


def test_metrics_inc_job():
    m = Metrics()
    m.inc_job("strava_sync", "ok")
    m.inc_job("strava_sync", "ok")
    m.inc_job("strava_sync", "timeout")
    assert m.jobs_total[("strava_sync", "ok")] == 2
    assert m.jobs_total[("strava_sync", "timeout")] == 1


def test_metrics_snapshot_shape():
    m = Metrics()
    m.inc_http("GET", "/foo", 200, 10.0)
    m.inc_agent("head_coach", "ok", 100.0)
    m.inc_job("daily_snapshot", "ok")
    snap = m.snapshot()
    assert "started_at" in snap
    assert snap["uptime_s"] >= 0
    assert snap["http"]["requests_total"]["GET /foo:200"] == 1
    assert "GET /foo" in snap["http"]["latency_ms"]
    assert snap["agents"]["calls_total"]["head_coach:ok"] == 1
    assert snap["jobs"]["runs_total"]["daily_snapshot:ok"] == 1


def test_metrics_thread_safety():
    import threading
    m = Metrics()

    def worker():
        for _ in range(1000):
            m.inc_http("GET", "/x", 200, 1.0)

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert m.http_requests_total[("GET", "/x", 200)] == 4000
