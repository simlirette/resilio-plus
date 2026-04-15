"""Tests for the log_node decorator."""
from __future__ import annotations

import json
import logging

from app.graphs.logging import log_node


def test_log_node_calls_function_and_returns_result():
    """log_node wrapper calls the original function and returns its result."""
    def my_node(state, config=None):
        return {"budgets": {"running": 5.0}}

    wrapped = log_node(my_node)
    result = wrapped({"athlete_id": "test-1"})
    assert result == {"budgets": {"running": 5.0}}


def test_log_node_emits_enter_and_exit(caplog):
    """log_node emits JSON logs with node_enter and node_exit events."""
    def my_node(state, config=None):
        return {"budgets": {}}

    wrapped = log_node(my_node)

    with caplog.at_level(logging.INFO, logger="resilio.graph"):
        wrapped({"athlete_id": "a1"})

    json_logs = [json.loads(r.message) for r in caplog.records if r.name == "resilio.graph"]
    events = [log["event"] for log in json_logs]
    assert "node_enter" in events
    assert "node_exit" in events

    exit_log = next(log for log in json_logs if log["event"] == "node_exit")
    assert exit_log["node"] == "my_node"
    assert exit_log["athlete_id"] == "a1"
    assert "duration_ms" in exit_log
    assert exit_log["keys_changed"] == ["budgets"]


def test_log_node_preserves_function_name():
    """log_node preserves __name__ for LangGraph node registration."""
    def analyze_profile(state, config=None):
        return {}

    wrapped = log_node(analyze_profile)
    assert wrapped.__name__ == "analyze_profile"
