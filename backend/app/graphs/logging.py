"""Structured JSON logging decorator for LangGraph node functions.

Usage:
    from .logging import log_node
    builder.add_node("analyze_profile", log_node(analyze_profile))

Emits two JSON log lines per node invocation:
    {"event": "node_enter", "node": "<name>", "athlete_id": "<id>"}
    {"event": "node_exit",  "node": "<name>", "athlete_id": "<id>", "duration_ms": N, "keys_changed": [...]}
"""
from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from functools import wraps
from typing import Any

logger = logging.getLogger("resilio.graph")

_NodeFunc = Callable[..., dict[str, Any]]


def log_node(func: _NodeFunc) -> _NodeFunc:
    """Decorator that logs entry/exit for a LangGraph node function."""

    @wraps(func)
    def wrapper(state: dict[str, Any], config: object = None) -> dict[str, Any]:
        node = func.__name__
        athlete = state.get("athlete_id", "?")
        logger.info(
            json.dumps(
                {
                    "event": "node_enter",
                    "node": node,
                    "athlete_id": athlete,
                }
            )
        )
        t0 = time.perf_counter()
        result: dict[str, Any] = func(state, config) if config is not None else func(state)
        ms = round((time.perf_counter() - t0) * 1000)
        changed = list(result.keys()) if isinstance(result, dict) else []
        logger.info(
            json.dumps(
                {
                    "event": "node_exit",
                    "node": node,
                    "athlete_id": athlete,
                    "duration_ms": ms,
                    "keys_changed": changed,
                }
            )
        )
        return result

    return wrapper
