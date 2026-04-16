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


from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.observability.metrics import (
    MetricsMiddleware,
    track_agent_call,
    metrics,
)


def _reset_metrics():
    metrics.http_requests_total.clear()
    metrics.http_latency_ms.clear()
    metrics.agent_calls_total.clear()
    metrics.agent_latency_ms.clear()
    metrics.jobs_total.clear()


def test_middleware_increments_http_counter():
    _reset_metrics()
    app = FastAPI()
    app.add_middleware(MetricsMiddleware)

    @app.get("/foo")
    def foo():
        return {"ok": True}

    client = TestClient(app)
    client.get("/foo")
    client.get("/foo")
    assert metrics.http_requests_total[("GET", "/foo", 200)] == 2


def test_middleware_uses_path_template_not_raw():
    _reset_metrics()
    app = FastAPI()
    app.add_middleware(MetricsMiddleware)

    @app.get("/athletes/{athlete_id}")
    def get_athlete(athlete_id: str):
        return {"id": athlete_id}

    client = TestClient(app)
    client.get("/athletes/abc-123")
    client.get("/athletes/def-456")
    # Both hits should collapse to the template
    assert metrics.http_requests_total[("GET", "/athletes/{athlete_id}", 200)] == 2


def test_middleware_captures_status_code():
    _reset_metrics()
    app = FastAPI()
    app.add_middleware(MetricsMiddleware)

    @app.get("/bad")
    def bad():
        from fastapi import HTTPException
        raise HTTPException(status_code=404)

    client = TestClient(app)
    client.get("/bad")
    assert metrics.http_requests_total[("GET", "/bad", 404)] == 1


def test_track_agent_call_ok():
    _reset_metrics()
    with track_agent_call("running_coach"):
        pass
    assert metrics.agent_calls_total[("running_coach", "ok")] == 1
    assert metrics.agent_latency_ms["running_coach"].count == 1


def test_track_agent_call_error_reraises_and_records_error():
    _reset_metrics()
    with pytest.raises(ValueError):
        with track_agent_call("lifting_coach"):
            raise ValueError("boom")
    assert metrics.agent_calls_total[("lifting_coach", "error")] == 1
    assert metrics.agent_latency_ms["lifting_coach"].count == 1
