from datetime import date
from app.agents.base import AgentContext, AgentRecommendation
from app.agents.recovery_coach import RecoveryCoach
from app.schemas.athlete import AthleteProfile, Sport


def _athlete():
    return AthleteProfile(
        name="Pat", age=35, sex="M", weight_kg=80, height_cm=182,
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


def test_name_is_recovery():
    assert RecoveryCoach().name == "recovery"


def test_analyze_returns_recommendation():
    result = RecoveryCoach().analyze(_context())
    assert isinstance(result, AgentRecommendation)


def test_weekly_load_is_zero():
    result = RecoveryCoach().analyze(_context())
    assert result.weekly_load == 0.0


def test_readiness_modifier_in_range():
    result = RecoveryCoach().analyze(_context())
    assert 0.5 <= result.readiness_modifier <= 1.5


def test_no_sessions_when_readiness_normal():
    result = RecoveryCoach().analyze(_context())
    # No terra data = readiness 1.0 = no forced recovery sessions
    assert result.suggested_sessions == []
