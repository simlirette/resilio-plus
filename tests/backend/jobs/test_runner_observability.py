"""Verify run_job() sets correlation ID, emits structured logs, increments metric."""
import logging
import pytest
from unittest.mock import MagicMock
from app.jobs.runner import run_job
from app.observability.metrics import metrics
from app.observability.correlation import correlation_id_ctx


def _reset_metrics():
    metrics.jobs_total.clear()


def test_run_job_sets_correlation_id():
    _reset_metrics()
    captured = {}

    def fn():
        captured["cid"] = correlation_id_ctx.get()

    mock_db = MagicMock()
    run_job(job_id="test_job", job_type="test", athlete_id=None, fn=fn, db=mock_db, timeout_s=5)
    assert captured["cid"].startswith("job-")


def test_run_job_increments_metric_on_success():
    _reset_metrics()
    mock_db = MagicMock()
    run_job(job_id="test_job", job_type="test_type", athlete_id=None, fn=lambda: None, db=mock_db, timeout_s=5)
    assert metrics.jobs_total[("test_type", "ok")] == 1


def test_run_job_increments_metric_on_error():
    _reset_metrics()

    def boom():
        raise ValueError("fail")

    mock_db = MagicMock()
    run_job(job_id="test_job", job_type="test_type", athlete_id=None, fn=boom, db=mock_db, timeout_s=5)
    assert metrics.jobs_total[("test_type", "error")] == 1


def test_run_job_logs_job_start_and_end(caplog):
    _reset_metrics()
    caplog.set_level(logging.INFO, logger="resilio.jobs")
    mock_db = MagicMock()
    run_job(job_id="jx", job_type="jt", athlete_id=None, fn=lambda: None, db=mock_db, timeout_s=5)
    messages = [r.getMessage() for r in caplog.records if r.name == "resilio.jobs"]
    assert any("job_start" in m for m in messages)
    assert any("job_end" in m for m in messages)
