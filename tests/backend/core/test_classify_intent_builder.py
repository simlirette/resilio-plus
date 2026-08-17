"""D3 TDD — classify_intent_builder (build_classify_intent_request)."""
from __future__ import annotations

import json

import pytest

from app.db.models import AthleteModel
from app.schemas.intent import IntentClassificationRequest


def _make_athlete(**overrides) -> AthleteModel:
    defaults = dict(
        id="athlete-1",
        name="Test",
        age=30,
        sex="M",
        weight_kg=70.0,
        height_cm=175.0,
        primary_sport="running",
        hours_per_week=8.0,
        sports_json='["running", "lifting"]',
        goals_json='["fitness"]',
        available_days_json="[0,2,4]",
        equipment_json="[]",
        coaching_mode="full",
        journey_phase="steady_state",
    )
    defaults.update(overrides)
    return AthleteModel(**defaults)


class TestBuildClassifyIntentRequest:
    def test_basic_request_shape(self):
        from app.core.classify_intent_builder import build_classify_intent_request

        athlete = _make_athlete()
        req = build_classify_intent_request(
            athlete=athlete,
            user_message="Combien de créatine je devrais prendre ?",
            last_3_intents=[],
        )
        assert isinstance(req, IntentClassificationRequest)
        assert req.user_message == "Combien de créatine je devrais prendre ?"

    def test_athlete_id_propagated(self):
        from app.core.classify_intent_builder import build_classify_intent_request

        athlete = _make_athlete(id="abc-123")
        req = build_classify_intent_request(athlete=athlete, user_message="test", last_3_intents=[])
        assert req.user_profile_minimal.athlete_id == "abc-123"

    def test_journey_phase_propagated(self):
        from app.core.classify_intent_builder import build_classify_intent_request

        athlete = _make_athlete(journey_phase="baseline_active")
        req = build_classify_intent_request(athlete=athlete, user_message="test", last_3_intents=[])
        assert req.user_profile_minimal.journey_phase == "baseline_active"

    def test_sports_parsed_from_json(self):
        from app.core.classify_intent_builder import build_classify_intent_request

        athlete = _make_athlete(sports_json='["running", "swimming", "lifting"]')
        req = build_classify_intent_request(athlete=athlete, user_message="test", last_3_intents=[])
        assert set(req.user_profile_minimal.sports) == {"running", "swimming", "lifting"}

    def test_last_3_intents_propagated(self):
        from app.core.classify_intent_builder import build_classify_intent_request

        athlete = _make_athlete()
        intents = ["HEAD_COACH_DIRECT", "SPECIALIST_TECHNICAL", "HEAD_COACH_DIRECT"]
        req = build_classify_intent_request(athlete=athlete, user_message="test", last_3_intents=intents)
        assert req.conversation_context_minimal.last_3_intents == intents

    def test_last_3_intents_truncated_to_3(self):
        from app.core.classify_intent_builder import build_classify_intent_request

        athlete = _make_athlete()
        intents = ["A", "B", "C", "D", "E"]
        req = build_classify_intent_request(athlete=athlete, user_message="test", last_3_intents=intents)
        assert len(req.conversation_context_minimal.last_3_intents) == 3

    def test_clinical_flag_none_by_default(self):
        from app.core.classify_intent_builder import build_classify_intent_request

        athlete = _make_athlete()
        req = build_classify_intent_request(athlete=athlete, user_message="test", last_3_intents=[])
        assert req.user_profile_minimal.clinical_context_flag is None

    def test_empty_sports_json(self):
        from app.core.classify_intent_builder import build_classify_intent_request

        athlete = _make_athlete(sports_json="[]")
        req = build_classify_intent_request(athlete=athlete, user_message="test", last_3_intents=[])
        assert req.user_profile_minimal.sports == []
