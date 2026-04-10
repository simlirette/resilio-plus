from datetime import date
from app.agents.base import AgentContext, AgentRecommendation
from app.agents.nutrition_coach import NutritionCoach
from app.schemas.athlete import AthleteProfile, Sport


def _athlete():
    return AthleteProfile(
        name="Alex", age=30, sex="M", weight_kg=75, height_cm=178,
        sports=[Sport.RUNNING], primary_sport=Sport.RUNNING,
        goals=["marathon"], available_days=[0, 2, 4, 6], hours_per_week=10.0,
    )


def _context():
    return AgentContext(
        athlete=_athlete(),
        date_range=(date(2026, 4, 7), date(2026, 4, 13)),
        phase="general_prep", week_number=1, weeks_remaining=20,
        sport_budgets={"running": 10.0},
    )


def test_name_is_nutrition():
    assert NutritionCoach().name == "nutrition"


def test_analyze_returns_recommendation():
    result = NutritionCoach().analyze(_context())
    assert isinstance(result, AgentRecommendation)


def test_no_physical_sessions():
    result = NutritionCoach().analyze(_context())
    assert result.suggested_sessions == []


def test_weekly_load_is_zero():
    result = NutritionCoach().analyze(_context())
    assert result.weekly_load == 0.0


def test_readiness_modifier_is_one():
    result = NutritionCoach().analyze(_context())
    assert result.readiness_modifier == 1.0


def test_notes_contains_directives():
    result = NutritionCoach().analyze(_context())
    assert "carbs" in result.notes.lower() or "rest" in result.notes.lower()
