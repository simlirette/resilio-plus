"""Unit tests for WeeklyAnalyzer and WeeklyAdjuster."""
import pytest

from models.weekly_review import ActualWorkout

# ── helpers ──────────────────────────────────────────────────────────────────

def _run(date="2026-04-07", completed=True, duration_min=60, workout_type="easy", avg_hr=None):
    actual_data: dict = {"duration_min": duration_min, "type": workout_type}
    if avg_hr is not None:
        actual_data["avg_hr"] = avg_hr
    return ActualWorkout(sport="running", date=date, completed=completed, actual_data=actual_data)


def _lift(date="2026-04-08", completed=True, duration_min=60, session_type="hypertrophy"):
    return ActualWorkout(
        sport="lifting",
        date=date,
        completed=completed,
        actual_data={"duration_min": duration_min, "session_type": session_type},
    )


# ── WeeklyAnalyzer ────────────────────────────────────────────────────────────

def test_analyzer_all_completed():
    """All sessions completed → completion_rate=1.0."""
    from core.weekly_review import WeeklyAnalyzer

    workouts = [_run("2026-04-07"), _lift("2026-04-08")]
    planned = [{"id": 1}, {"id": 2}]
    result = WeeklyAnalyzer().analyze(planned, workouts)
    assert result["completion_rate"] == 1.0
    assert result["sessions_completed"] == 2
    assert result["sessions_planned"] == 2


def test_analyzer_partial_completion():
    """3 of 5 sessions completed → completion_rate=0.6."""
    from core.weekly_review import WeeklyAnalyzer

    workouts = [
        _run("2026-04-07", completed=True),
        _run("2026-04-08", completed=False),
        _lift("2026-04-09", completed=True),
        _lift("2026-04-10", completed=False),
        _run("2026-04-11", completed=True),
    ]
    planned = [{"id": i} for i in range(5)]
    result = WeeklyAnalyzer().analyze(planned, workouts)
    assert result["completion_rate"] == pytest.approx(0.6)
    assert result["sessions_completed"] == 3
    assert result["sessions_planned"] == 5


def test_analyzer_trimp_running_easy():
    """Easy run 60 min → TRIMP=60 (factor 1.0). 2026-04-06 is a Monday → week_loads[0]=60."""
    from core.weekly_review import WeeklyAnalyzer

    workout = _run("2026-04-06", duration_min=60, workout_type="easy")
    result = WeeklyAnalyzer().analyze([], [workout])
    assert result["trimp_total"] == pytest.approx(60.0)
    assert result["trimp_by_sport"]["running"] == pytest.approx(60.0)
    assert result["week_loads"][0] == pytest.approx(60.0)  # Monday = index 0
    assert len(result["week_loads"]) == 7


# ── WeeklyAdjuster ────────────────────────────────────────────────────────────

def test_adjuster_low_completion_suggests_reduction():
    """completion_rate=0.5, no history → adjustments has volume_reduction."""
    from core.weekly_review import WeeklyAdjuster

    analysis = {"completion_rate": 0.5, "week_loads": [0.0] * 7}
    adjustments, acwr_new = WeeklyAdjuster().adjust(analysis, [], None)
    assert acwr_new is None  # no history → no ACWR
    types = [a["type"] for a in adjustments]
    assert "volume_reduction" in types
    vol = next(a for a in adjustments if a["type"] == "volume_reduction")
    assert vol["reason"] == "low_completion"
    assert vol["pct"] == 10


def test_adjuster_acwr_danger_suggests_rest():
    """21 days×10 + 7 days×40 → ACWR>1.5 → rest_week adjustment."""
    from core.weekly_review import WeeklyAdjuster

    daily_loads_28d = [10.0] * 21
    week_loads = [40.0] * 7
    analysis = {"completion_rate": 0.9, "week_loads": week_loads}
    adjustments, acwr_new = WeeklyAdjuster().adjust(analysis, daily_loads_28d, None)
    assert acwr_new is not None
    assert acwr_new > 1.5
    types = [a["type"] for a in adjustments]
    assert "rest_week" in types
    assert "intensity_reduction" not in types  # rule 2 fires, rule 3 skipped


def test_adjuster_healthy_load_no_adjustments():
    """completion_rate=0.9, ACWR≈1.02 → adjustments=[]."""
    from core.weekly_review import WeeklyAdjuster

    daily_loads_28d = [50.0] * 21
    week_loads = [52.0] * 7
    analysis = {"completion_rate": 0.9, "week_loads": week_loads}
    adjustments, acwr_new = WeeklyAdjuster().adjust(analysis, daily_loads_28d, None)
    assert acwr_new is not None
    assert 0.8 <= acwr_new <= 1.3
    assert adjustments == []
