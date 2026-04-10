from datetime import date, timedelta
import pytest
from app.core.goal_analysis import analyze_goals
from app.schemas.athlete import AthleteProfile, Sport


def _athlete(goals, sports, primary, hours=10.0, race_date=None):
    return AthleteProfile(
        name="Test", age=28, sex="M", weight_kg=75, height_cm=180,
        sports=sports, primary_sport=primary,
        goals=goals, target_race_date=race_date,
        available_days=[0, 2, 4, 6], hours_per_week=hours,
    )


def test_single_sport_gets_all_hours():
    athlete = _athlete(["finish a 10K"], [Sport.RUNNING], Sport.RUNNING, hours=8.0)
    budgets = analyze_goals(athlete)
    assert abs(budgets[Sport.RUNNING] - 8.0) < 0.01


def test_sum_equals_hours_per_week():
    athlete = _athlete(
        ["marathon preparation"], [Sport.RUNNING, Sport.LIFTING], Sport.RUNNING, hours=10.0
    )
    budgets = analyze_goals(athlete)
    assert abs(sum(budgets.values()) - 10.0) < 0.01


def test_running_goal_boosts_running():
    athlete = _athlete(
        ["préparer un marathon"], [Sport.RUNNING, Sport.LIFTING], Sport.RUNNING, hours=10.0
    )
    budgets = analyze_goals(athlete)
    assert budgets[Sport.RUNNING] > budgets[Sport.LIFTING]


def test_biking_keyword_boosts_biking():
    athlete = _athlete(
        ["améliorer mon FTP vélo"], [Sport.RUNNING, Sport.BIKING], Sport.BIKING, hours=9.0
    )
    budgets = analyze_goals(athlete)
    assert budgets[Sport.BIKING] > budgets[Sport.RUNNING]


def test_all_sports_get_positive_budget():
    athlete = _athlete(
        ["triathlon sprint"], [Sport.RUNNING, Sport.BIKING, Sport.SWIMMING, Sport.LIFTING],
        Sport.RUNNING, hours=12.0,
    )
    budgets = analyze_goals(athlete)
    for sport in [Sport.RUNNING, Sport.BIKING, Sport.SWIMMING, Sport.LIFTING]:
        assert budgets[sport] >= 0.33  # floor: min 20min


def test_only_active_sports_in_output():
    athlete = _athlete(["trail running"], [Sport.RUNNING], Sport.RUNNING, hours=8.0)
    budgets = analyze_goals(athlete)
    assert set(budgets.keys()) == {Sport.RUNNING}


def test_near_race_boosts_detected_sport():
    near_race = date.today() + timedelta(weeks=6)
    athlete = _athlete(
        ["course 10K"],
        [Sport.RUNNING, Sport.LIFTING], Sport.RUNNING,
        hours=10.0, race_date=near_race,
    )
    far_athlete = _athlete(
        ["course 10K"],
        [Sport.RUNNING, Sport.LIFTING], Sport.RUNNING,
        hours=10.0, race_date=date.today() + timedelta(weeks=30),
    )
    near_budgets = analyze_goals(athlete)
    far_budgets = analyze_goals(far_athlete)
    assert near_budgets[Sport.RUNNING] >= far_budgets[Sport.RUNNING]
