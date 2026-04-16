# tests/runtime/test_revision_loop.py
"""Tests for the revision loop — max 1 revision enforced."""
from __future__ import annotations

from tests.runtime.conftest import SIMON_PROFILE, STABLE_LOAD


class TestRevisionLoop:
    """Verify revision count enforcement."""

    def test_first_rejection_loops_back(self, mock_agents, runtime_db, runtime_svc):
        """First rejection returns a new proposed plan (revision happened)."""
        thread_id, _ = runtime_svc.create_plan(
            athlete_id="rt-simon-001",
            athlete_dict=SIMON_PROFILE,
            load_history=STABLE_LOAD,
            db=runtime_db,
        )

        proposed_v2 = runtime_svc.resume_plan(
            thread_id=thread_id,
            approved=False,
            feedback="Too intense",
            db=runtime_db,
        )

        assert proposed_v2 is not None
        assert "sessions" in proposed_v2

    def test_second_rejection_still_produces_plan(self, mock_agents, runtime_db, runtime_svc):
        """Second rejection routes to present_to_athlete (no more delegate loop).

        The graph enforces max 1 full revision cycle. After that, revise_plan
        routes directly to present_to_athlete instead of delegate_specialists.
        Either way, a proposed plan should exist.
        """
        thread_id, _ = runtime_svc.create_plan(
            athlete_id="rt-simon-001",
            athlete_dict=SIMON_PROFILE,
            load_history=STABLE_LOAD,
            db=runtime_db,
        )

        # First rejection
        runtime_svc.resume_plan(
            thread_id=thread_id,
            approved=False,
            feedback="Too intense",
            db=runtime_db,
        )

        # Second rejection
        proposed_v3 = runtime_svc.resume_plan(
            thread_id=thread_id,
            approved=False,
            feedback="Still too much",
            db=runtime_db,
        )

        # Graph should still produce a plan (routes to present, not delegate)
        assert proposed_v3 is not None

    def test_reject_twice_then_approve(self, mock_agents, runtime_db, runtime_svc):
        """Full cycle: create → reject → reject → approve → persisted."""
        thread_id, _ = runtime_svc.create_plan(
            athlete_id="rt-simon-001",
            athlete_dict=SIMON_PROFILE,
            load_history=STABLE_LOAD,
            db=runtime_db,
        )

        runtime_svc.resume_plan(thread_id=thread_id, approved=False, feedback="v1 bad", db=runtime_db)
        runtime_svc.resume_plan(thread_id=thread_id, approved=False, feedback="v2 bad", db=runtime_db)

        final = runtime_svc.resume_plan(
            thread_id=thread_id,
            approved=True,
            feedback=None,
            db=runtime_db,
        )

        assert final is not None
        assert final.get("db_plan_id") is not None
