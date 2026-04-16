"""Liveness / readiness probes — not authenticated, not athlete-scoped."""
from __future__ import annotations

import os
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from ..db.database import engine

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness — returns 200 as long as the process is up. No external calls."""
    return {"status": "ok"}


@router.get("/ready")
def ready() -> dict[str, Any]:
    """Readiness — verifies DB reachable. Used by orchestrator probes."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"db unreachable: {type(exc).__name__}")
    return {"status": "ready", "db": "ok"}


@router.get("/ready/deep")
def ready_deep() -> dict[str, Any]:
    """Deep readiness — DB + Anthropic reachability. Manual diagnostic only."""
    result: dict[str, Any] = {"status": "ready", "db": "unknown", "anthropic": "unknown"}

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        result["db"] = "ok"
    except Exception as exc:
        result["db"] = f"fail: {type(exc).__name__}"
        result["status"] = "degraded"

    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY", "")
    if not api_key:
        result["anthropic"] = "no_key"
        result["status"] = "degraded"
    else:
        try:
            with httpx.Client(timeout=3.0) as client:
                resp = client.get(
                    "https://api.anthropic.com/v1/models",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                    },
                )
            result["anthropic"] = "ok" if resp.status_code < 500 else f"http_{resp.status_code}"
            if resp.status_code >= 500:
                result["status"] = "degraded"
        except Exception as exc:
            result["anthropic"] = f"fail: {type(exc).__name__}"
            result["status"] = "degraded"

    if result["status"] != "ready":
        raise HTTPException(status_code=503, detail=result)
    return result
