from datetime import date
from app.agents.base import AgentContext
from app.schemas.athlete import AthleteProfile, Sport


def _athlete():
    return AthleteProfile(
        name="A", age=30, sex="M", weight_kg=70, height_cm=175,
        sports=[Sport.RUNNING], primary_sport=Sport.RUNNING,
        goals=[], available_days=[0, 2, 4], hours_per_week=8.0,
    )


def test_agent_context_has_week_number_default():
    ctx = AgentContext(
        athlete=_athlete(),
        date_range=(date(2026, 4, 7), date(2026, 4, 13)),
        phase="general_prep",
    )
    assert ctx.week_number == 1


def test_agent_context_has_weeks_remaining_default():
    ctx = AgentContext(
        athlete=_athlete(),
        date_range=(date(2026, 4, 7), date(2026, 4, 13)),
        phase="general_prep",
    )
    assert ctx.weeks_remaining == 0


def test_agent_context_week_number_settable():
    ctx = AgentContext(
        athlete=_athlete(),
        date_range=(date(2026, 4, 7), date(2026, 4, 13)),
        phase="general_prep",
        week_number=5,
        weeks_remaining=12,
    )
    assert ctx.week_number == 5
    assert ctx.weeks_remaining == 12
