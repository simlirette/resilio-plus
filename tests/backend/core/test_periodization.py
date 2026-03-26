from datetime import date, timedelta
from app.core.periodization import get_current_phase, MacroPhase, TIDStrategy


def _race_in(weeks: int) -> date:
    return date.today() + timedelta(weeks=weeks)


def test_no_race_date_defaults_to_general_prep():
    result = get_current_phase(None, date.today())
    assert result.phase == MacroPhase.GENERAL_PREP
    assert result.tid_recommendation == TIDStrategy.PYRAMIDAL
    assert result.volume_modifier == 1.0


def test_more_than_22_weeks_is_general_prep():
    result = get_current_phase(_race_in(30), date.today())
    assert result.phase == MacroPhase.GENERAL_PREP
    assert result.tid_recommendation == TIDStrategy.PYRAMIDAL
    assert result.volume_modifier == 1.0


def test_exactly_22_weeks_is_specific_prep():
    result = get_current_phase(_race_in(22), date.today())
    assert result.phase == MacroPhase.SPECIFIC_PREP


def test_14_to_22_weeks_is_specific_prep():
    result = get_current_phase(_race_in(18), date.today())
    assert result.phase == MacroPhase.SPECIFIC_PREP
    assert result.tid_recommendation == TIDStrategy.MIXED
    assert result.volume_modifier == 0.9


def test_7_to_13_weeks_is_pre_competition():
    result = get_current_phase(_race_in(10), date.today())
    assert result.phase == MacroPhase.PRE_COMPETITION
    assert result.tid_recommendation == TIDStrategy.POLARIZED
    assert result.volume_modifier == 0.8


def test_1_to_6_weeks_is_competition():
    result = get_current_phase(_race_in(3), date.today())
    assert result.phase == MacroPhase.COMPETITION
    assert result.tid_recommendation == TIDStrategy.POLARIZED
    assert result.volume_modifier == 0.5


def test_post_race_is_transition():
    past_race = date.today() - timedelta(weeks=1)
    result = get_current_phase(past_race, date.today())
    assert result.phase == MacroPhase.TRANSITION
    assert result.tid_recommendation == TIDStrategy.MIXED
    assert result.volume_modifier == 0.6


def test_weeks_remaining_computed_correctly():
    race = date.today() + timedelta(days=35)  # exactly 5 weeks
    result = get_current_phase(race, date.today())
    assert result.weeks_remaining == 5
