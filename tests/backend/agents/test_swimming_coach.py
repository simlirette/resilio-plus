from datetime import date
from app.agents.base import AgentContext, AgentRecommendation
from app.agents.swimming_coach import SwimmingCoach
from app.schemas.athlete import AthleteProfile, Sport


def _athlete():
    return AthleteProfile(
        name="Marie", age=26, sex="F", weight_kg=60, height_cm=165,
        sports=[Sport.SWIMMING, Sport.RUNNING], primary_sport=Sport.SWIMMING,
        goals=["triathlon"], available_days=[1, 3, 6],
        hours_per_week=8.0, css_per_100m=100.0,
    )


def _context():
    return AgentContext(
        athlete=_athlete(),
        date_range=(date(2026, 4, 7), date(2026, 4, 13)),
        phase="general_prep", week_number=1, weeks_remaining=20,
        sport_budgets={"swimming": 4.0, "running": 4.0},
    )


def test_name_is_swimming():
    assert SwimmingCoach().name == "swimming"


def test_analyze_returns_recommendation():
    result = SwimmingCoach().analyze(_context())
    assert isinstance(result, AgentRecommendation)


def test_sessions_are_swimming_sport():
    result = SwimmingCoach().analyze(_context())
    for s in result.suggested_sessions:
        assert s.sport.value == "swimming"
