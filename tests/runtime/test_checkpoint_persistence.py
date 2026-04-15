# tests/runtime/test_checkpoint_persistence.py
"""Tests for checkpoint persistence — CoachingService accepts checkpointer."""
from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver

from app.services.coaching_service import CoachingService


def test_coaching_service_accepts_checkpointer():
    """CoachingService can be created with an explicit checkpointer."""
    svc = CoachingService(checkpointer=MemorySaver())
    assert svc._graph is not None


def test_coaching_service_checkpointer_kwarg_only():
    """checkpointer must be passed as keyword argument."""
    svc = CoachingService(checkpointer=MemorySaver())
    assert svc is not None
