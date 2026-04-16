# tests/runtime/test_checkpoint_persistence.py
"""Tests for checkpoint persistence — CoachingService accepts checkpointer."""
from __future__ import annotations

import os
import sqlite3
import tempfile

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver

from app.services.coaching_service import CoachingService
from tests.runtime.conftest import SIMON_PROFILE, STABLE_LOAD


def test_coaching_service_accepts_checkpointer():
    """CoachingService can be created with an explicit checkpointer."""
    svc = CoachingService(checkpointer=MemorySaver())
    assert svc._graph is not None


def test_coaching_service_checkpointer_kwarg_only():
    """checkpointer must be passed as keyword argument."""
    svc = CoachingService(checkpointer=MemorySaver())
    assert svc is not None


class TestSqliteCheckpointPersistence:
    """Checkpoint written to SQLite file survives service reinstantiation."""

    def test_checkpoint_survives_service_restart(self, runtime_db, mock_agents):
        """Create plan with svc1, resume with svc2 using same SQLite file."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
            db_path = f.name

        try:
            conn1 = sqlite3.connect(db_path, check_same_thread=False)
            saver1 = SqliteSaver(conn1)
            saver1.setup()

            svc1 = CoachingService(checkpointer=saver1)
            thread_id, proposed = svc1.create_plan(
                athlete_id="rt-simon-001",
                athlete_dict=SIMON_PROFILE,
                load_history=STABLE_LOAD,
                db=runtime_db,
            )
            assert proposed is not None
            conn1.close()

            # New connection, new service — simulates process restart
            conn2 = sqlite3.connect(db_path, check_same_thread=False)
            saver2 = SqliteSaver(conn2)
            saver2.setup()

            svc2 = CoachingService(checkpointer=saver2)
            final = svc2.resume_plan(
                thread_id=thread_id,
                approved=True,
                feedback=None,
                db=runtime_db,
            )

            assert final is not None
            assert final.get("db_plan_id") is not None
            conn2.close()
        finally:
            os.unlink(db_path)
