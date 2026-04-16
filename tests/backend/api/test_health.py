"""Tests for /health, /ready, /ready/deep — not authenticated, no athlete scope."""
from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest


def test_health_returns_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_ready_returns_ok_when_db_up(client):
    from app.routes import health as health_module
    from unittest.mock import MagicMock, patch

    mock_conn = MagicMock()
    mock_conn.__enter__ = lambda s: mock_conn
    mock_conn.__exit__ = MagicMock(return_value=False)

    with patch.object(health_module.engine, "connect", return_value=mock_conn):
        resp = client.get("/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ready"
    assert body["db"] == "ok"


def test_ready_returns_503_when_db_down(client):
    from app.routes import health as health_module

    with patch.object(
        health_module.engine, "connect", side_effect=RuntimeError("db offline")
    ):
        resp = client.get("/ready")
    assert resp.status_code == 503
    assert "db unreachable" in resp.json()["detail"]


def test_ready_deep_returns_503_when_no_api_key(client, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("CLAUDE_API_KEY", raising=False)
    resp = client.get("/ready/deep")
    assert resp.status_code == 503
    detail = resp.json()["detail"]
    assert detail["anthropic"] == "no_key"


def test_ready_deep_returns_200_when_all_green(client, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    from app.routes import health as health_module
    from unittest.mock import MagicMock, patch

    mock_conn = MagicMock()
    mock_conn.__enter__ = lambda s: mock_conn
    mock_conn.__exit__ = MagicMock(return_value=False)

    import respx
    from httpx import Response

    with patch.object(health_module.engine, "connect", return_value=mock_conn):
        with respx.mock(base_url="https://api.anthropic.com") as mock:
            mock.get("/v1/models").mock(return_value=Response(200))
            resp = client.get("/ready/deep")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ready"
    assert body["db"] == "ok"
    assert body["anthropic"] == "ok"
