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
