from datetime import date
import pytest
from app.agents.base import AgentContext, AgentRecommendation
from app.agents.biking_coach import BikingCoach
from app.schemas.athlete import AthleteProfile, Sport


def _athlete(ftp=200):
    return AthleteProfile(
        name="Caro", age=32, sex="F", weight_kg=62, height_cm=168,
        sports=[Sport.BIKING, Sport.RUNNING], primary_sport=Sport.BIKING,
        goals=["improve FTP"], available_days=[1, 3, 5],
        hours_per_week=8.0, ftp_watts=ftp,
    )


def _context(athlete=None):
    a = athlete or _athlete()
    return AgentContext(
        athlete=a,
        date_range=(date(2026, 4, 7), date(2026, 4, 13)),
        phase="general_prep",
        week_number=1,
        weeks_remaining=20,
        sport_budgets={"biking": 4.8, "running": 3.2},
    )


def test_name_is_biking():
    assert BikingCoach().name == "biking"


def test_analyze_returns_recommendation():
    result = BikingCoach().analyze(_context())
    assert isinstance(result, AgentRecommendation)


def test_analyze_sessions_are_biking_sport():
    result = BikingCoach().analyze(_context())
    for s in result.suggested_sessions:
        assert s.sport.value == "biking"


def test_analyze_zero_budget_returns_no_sessions():
    ctx = _context()
    ctx = AgentContext(**{**ctx.__dict__, "sport_budgets": {"biking": 0.0}})
    result = BikingCoach().analyze(ctx)
    assert result.suggested_sessions == []
    assert result.weekly_load == 0.0


def test_analyze_weekly_load_positive_with_sessions():
    result = BikingCoach().analyze(_context())
    if result.suggested_sessions:
        assert result.weekly_load > 0
