# tests/runtime/test_state_transitions.py
"""Tests for state transitions — each node produces expected keys."""
from __future__ import annotations

from tests.runtime.conftest import SIMON_PROFILE, STABLE_LOAD


class TestStateTransitions:
    """Verify state keys after each graph phase."""

    def test_proposed_plan_has_required_keys(self, mock_agents, runtime_db, runtime_svc):
        """proposed_plan_dict contains sessions, phase, readiness_level, acwr, conflicts."""
        _, proposed = runtime_svc.create_plan(
            athlete_id="rt-simon-001",
            athlete_dict=SIMON_PROFILE,
            load_history=STABLE_LOAD,
            db=runtime_db,
        )

        assert proposed is not None
        required = {"sessions", "phase", "readiness_level", "acwr", "conflicts"}
        actual = set(proposed.keys())
        missing = required - actual
        assert not missing, f"proposed_plan_dict missing keys: {missing}"

    def test_acwr_dict_populated_after_create(self, mock_agents, runtime_db, runtime_svc):
        """Graph state has acwr_dict after running through compute_acwr node."""
        thread_id, _ = runtime_svc.create_plan(
            athlete_id="rt-simon-001",
            athlete_dict=SIMON_PROFILE,
            load_history=STABLE_LOAD,
            db=runtime_db,
        )

        snapshot = runtime_svc.get_graph_state(thread_id)
        acwr = snapshot.values.get("acwr_dict")
        assert acwr is not None
        assert "ratio" in acwr
        assert "status" in acwr

    def test_budgets_populated(self, mock_agents, runtime_db, runtime_svc):
        """Graph state has non-empty budgets after analyze_profile."""
        thread_id, _ = runtime_svc.create_plan(
            athlete_id="rt-simon-001",
            athlete_dict=SIMON_PROFILE,
            load_history=STABLE_LOAD,
            db=runtime_db,
        )

        snapshot = runtime_svc.get_graph_state(thread_id)
        budgets = snapshot.values.get("budgets")
        assert budgets is not None
        assert len(budgets) > 0

    def test_recommendations_populated(self, mock_agents, runtime_db, runtime_svc):
        """Graph state has recommendations_dicts from delegate_specialists."""
        thread_id, _ = runtime_svc.create_plan(
            athlete_id="rt-simon-001",
            athlete_dict=SIMON_PROFILE,
            load_history=STABLE_LOAD,
            db=runtime_db,
        )

        snapshot = runtime_svc.get_graph_state(thread_id)
        recs = snapshot.values.get("recommendations_dicts")
        assert recs is not None
        assert len(recs) > 0

    def test_final_plan_has_db_plan_id(self, mock_agents, runtime_db, runtime_svc):
        """final_plan_dict includes db_plan_id after finalize_plan."""
        thread_id, _ = runtime_svc.create_plan(
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
        assert final["db_plan_id"] is not None
        assert isinstance(final["db_plan_id"], str)

    def test_no_session_has_zero_duration(self, mock_agents, runtime_db, runtime_svc):
        """All sessions in proposed plan have duration_min >= 1."""
        _, proposed = runtime_svc.create_plan(
            athlete_id="rt-simon-001",
            athlete_dict=SIMON_PROFILE,
            load_history=STABLE_LOAD,
            db=runtime_db,
        )

        for s in proposed.get("sessions", []):
            assert s["duration_min"] >= 1, f"Session has zero/negative duration: {s}"
