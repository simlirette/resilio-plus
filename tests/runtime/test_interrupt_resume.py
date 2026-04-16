# tests/runtime/test_interrupt_resume.py
"""Tests for graph interrupt at present_to_athlete and resume via approve/reject."""
from __future__ import annotations

import pytest

from tests.runtime.conftest import SIMON_PROFILE, STABLE_LOAD


class TestInterruptResume:
    """Full create → interrupt → resume flow with mocked agents."""

    def test_create_plan_returns_proposed(self, mock_agents, runtime_db, runtime_svc):
        """create_plan stops at interrupt and returns proposed_plan_dict."""
        thread_id, proposed = runtime_svc.create_plan(
            athlete_id="rt-simon-001",
            athlete_dict=SIMON_PROFILE,
            load_history=STABLE_LOAD,
            db=runtime_db,
        )

        assert thread_id.startswith("rt-simon-001:")
        assert proposed is not None
        assert "sessions" in proposed
        assert len(proposed["sessions"]) > 0

    def test_approve_returns_final_with_db_plan_id(self, mock_agents, runtime_db, runtime_svc):
        """resume_plan(approved=True) returns final_plan_dict with db_plan_id."""
        thread_id, proposed = runtime_svc.create_plan(
            athlete_id="rt-simon-001",
            athlete_dict=SIMON_PROFILE,
            load_history=STABLE_LOAD,
            db=runtime_db,
        )

        final = runtime_svc.resume_plan(
            thread_id=thread_id,
            approved=True,
            feedback=None,
            db=runtime_db,
        )

        assert final is not None
        assert final.get("db_plan_id") is not None

    def test_reject_returns_new_proposed(self, mock_agents, runtime_db, runtime_svc):
        """resume_plan(approved=False) returns a new proposed_plan_dict."""
        thread_id, proposed_v1 = runtime_svc.create_plan(
            athlete_id="rt-simon-001",
            athlete_dict=SIMON_PROFILE,
            load_history=STABLE_LOAD,
            db=runtime_db,
        )

        proposed_v2 = runtime_svc.resume_plan(
            thread_id=thread_id,
            approved=False,
            feedback="Too much volume",
            db=runtime_db,
        )

        assert proposed_v2 is not None
        assert "sessions" in proposed_v2

    def test_reject_then_approve(self, mock_agents, runtime_db, runtime_svc):
        """Full cycle: create → reject → re-propose → approve → persisted."""
        thread_id, _ = runtime_svc.create_plan(
            athlete_id="rt-simon-001",
            athlete_dict=SIMON_PROFILE,
            load_history=STABLE_LOAD,
            db=runtime_db,
        )

        # Reject first proposal
        proposed_v2 = runtime_svc.resume_plan(
            thread_id=thread_id,
            approved=False,
            feedback="Less volume please",
            db=runtime_db,
        )
        assert proposed_v2 is not None

        # Approve second proposal
        final = runtime_svc.resume_plan(
            thread_id=thread_id,
            approved=True,
            feedback=None,
            db=runtime_db,
        )
        assert final is not None
        assert final.get("db_plan_id") is not None

    def test_graph_state_has_proposed_at_interrupt(self, mock_agents, runtime_db, runtime_svc):
        """After create_plan, graph state contains proposed_plan_dict."""
        thread_id, proposed = runtime_svc.create_plan(
            athlete_id="rt-simon-001",
            athlete_dict=SIMON_PROFILE,
            load_history=STABLE_LOAD,
            db=runtime_db,
        )

        config = {"configurable": {"thread_id": thread_id, "db": runtime_db}}
        snapshot = runtime_svc._graph.get_state(config)
        assert snapshot.values.get("proposed_plan_dict") is not None
        assert snapshot.values.get("human_approved") is False
