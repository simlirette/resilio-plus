import pytest
from app.agents.base import AgentRecommendation, AgentContext
from app.schemas.athlete import AthleteProfile, Sport
from datetime import date
from tests.backend.agents.conftest import make_recommendation, MockAgent, make_fatigue


def test_agent_recommendation_default_readiness_modifier():
    rec = make_recommendation()
    assert rec.readiness_modifier == 1.0


def test_agent_recommendation_readiness_modifier_valid_range():
    # min and max valid values
    rec_low = make_recommendation(readiness_modifier=0.5)
    rec_high = make_recommendation(readiness_modifier=1.5)
    assert rec_low.readiness_modifier == 0.5
    assert rec_high.readiness_modifier == 1.5


def test_agent_recommendation_readiness_modifier_below_range_raises():
    with pytest.raises(ValueError):
        make_recommendation(readiness_modifier=0.4)


def test_agent_recommendation_readiness_modifier_above_range_raises():
    with pytest.raises(ValueError):
        make_recommendation(readiness_modifier=1.6)


def test_mock_agent_name_property():
    rec = make_recommendation("lifting")
    agent = MockAgent("lifting", rec)
    assert agent.name == "lifting"


def test_mock_agent_analyze_returns_recommendation(sample_context):
    rec = make_recommendation("running")
    agent = MockAgent("running", rec)
    result = agent.analyze(sample_context)
    assert result.agent_name == "running"
    assert result.weekly_load == 100.0
