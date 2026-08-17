"""D2 TDD — Recommendation schema with INTERPRETATION mode (DEP-C4-006 validators REC1+REC2)."""
from __future__ import annotations

import pytest
from pydantic import ValidationError


def _valid_planning(**overrides):
    """Valid PLANNING mode recommendation."""
    base = {
        "agent_name": "lifting",
        "trigger": "PLAN_GEN_DELEGATE_SPECIALISTS",
        "mode": "planning",
        "notes_for_head_coach": None,
        "flag_for_head_coach": None,
        # PLANNING-specific fields
        "sessions": [{"date": "2026-05-01", "session_type": "strength_lower", "duration_min": 60}],
        "block_theme": "hypertrophy",
        "generation_mode": "baseline",
        "weekly_volume_target": 3,
        "weekly_intensity_distribution": {"zone1": 0.7, "zone2": 0.3},
        "projected_strain_contribution": 45.0,
    }
    base.update(overrides)
    return base


def _valid_review(**overrides):
    base = {
        "agent_name": "lifting",
        "trigger": "CHAT_WEEKLY_REPORT",
        "mode": "review",
        "notes_for_head_coach": "All sessions completed at prescribed intensity.",
        "flag_for_head_coach": None,
        "block_analysis": "Week 3 of hypertrophy block, progression on track.",
        "proposed_trade_offs": None,
    }
    base.update(overrides)
    return base


def _valid_interpretation(**overrides):
    base = {
        "agent_name": "lifting",
        "trigger": "CHAT_SESSION_LOG_INTERPRETATION",
        "mode": "interpretation",
        "notes_for_head_coach": "RPE significantly above prescribed — form breakdown likely.",
        "flag_for_head_coach": None,
    }
    base.update(overrides)
    return base


class TestRecommendationModes:
    def test_planning_mode_valid(self):
        from app.schemas.recommendation import Recommendation
        r = Recommendation(**_valid_planning())
        assert r.mode.value == "planning"

    def test_review_mode_valid(self):
        from app.schemas.recommendation import Recommendation
        r = Recommendation(**_valid_review())
        assert r.mode.value == "review"

    def test_interpretation_mode_valid(self):
        from app.schemas.recommendation import Recommendation
        r = Recommendation(**_valid_interpretation())
        assert r.mode.value == "interpretation"

    def test_invalid_mode_raises(self):
        from app.schemas.recommendation import Recommendation
        with pytest.raises(ValidationError):
            Recommendation(**_valid_planning(mode="unknown"))


class TestValidatorREC2:
    """REC2: trigger must be admissible for the declared mode."""

    def test_plan_gen_delegate_requires_planning(self):
        from app.schemas.recommendation import Recommendation
        r = Recommendation(**_valid_planning(trigger="PLAN_GEN_DELEGATE_SPECIALISTS", mode="planning"))
        assert r.trigger == "PLAN_GEN_DELEGATE_SPECIALISTS"

    def test_chat_weekly_report_requires_review(self):
        from app.schemas.recommendation import Recommendation
        r = Recommendation(**_valid_review(trigger="CHAT_WEEKLY_REPORT", mode="review"))
        assert r.trigger == "CHAT_WEEKLY_REPORT"

    def test_session_log_interpretation_requires_interpretation(self):
        from app.schemas.recommendation import Recommendation
        r = Recommendation(**_valid_interpretation(trigger="CHAT_SESSION_LOG_INTERPRETATION", mode="interpretation"))
        assert r.trigger == "CHAT_SESSION_LOG_INTERPRETATION"

    def test_technical_question_lifting_requires_interpretation(self):
        from app.schemas.recommendation import Recommendation
        r = Recommendation(**_valid_interpretation(trigger="CHAT_TECHNICAL_QUESTION_LIFTING", mode="interpretation"))
        assert r.trigger == "CHAT_TECHNICAL_QUESTION_LIFTING"

    def test_wrong_mode_for_trigger_raises(self):
        from app.schemas.recommendation import Recommendation
        # planning trigger + review mode → REC2 violation
        with pytest.raises(ValidationError, match="REC2"):
            Recommendation(**_valid_planning(trigger="PLAN_GEN_DELEGATE_SPECIALISTS", mode="review"))

    def test_unknown_trigger_raises(self):
        from app.schemas.recommendation import Recommendation
        with pytest.raises(ValidationError, match="REC2"):
            Recommendation(**_valid_planning(trigger="UNKNOWN_TRIGGER"))


class TestValidatorREC1:
    """REC1: INTERPRETATION mode — notes_for_head_coach required, planning fields forbidden."""

    def test_interpretation_requires_notes_for_head_coach(self):
        from app.schemas.recommendation import Recommendation
        with pytest.raises(ValidationError, match="REC1"):
            Recommendation(**_valid_interpretation(notes_for_head_coach=None))

    def test_interpretation_forbids_sessions(self):
        from app.schemas.recommendation import Recommendation
        with pytest.raises(ValidationError, match="REC1"):
            Recommendation(
                **_valid_interpretation(
                    sessions=[{"date": "2026-05-01", "session_type": "strength", "duration_min": 60}]
                )
            )

    def test_interpretation_forbids_block_theme(self):
        from app.schemas.recommendation import Recommendation
        with pytest.raises(ValidationError, match="REC1"):
            Recommendation(**_valid_interpretation(block_theme="hypertrophy"))

    def test_interpretation_forbids_generation_mode(self):
        from app.schemas.recommendation import Recommendation
        with pytest.raises(ValidationError, match="REC1"):
            Recommendation(**_valid_interpretation(generation_mode="baseline"))

    def test_interpretation_allows_flag_for_head_coach(self):
        from app.schemas.recommendation import Recommendation
        r = Recommendation(**_valid_interpretation(flag_for_head_coach="elevated_rpe"))
        assert r.flag_for_head_coach == "elevated_rpe"

    def test_planning_does_not_require_notes(self):
        from app.schemas.recommendation import Recommendation
        r = Recommendation(**_valid_planning(notes_for_head_coach=None))
        assert r.notes_for_head_coach is None
