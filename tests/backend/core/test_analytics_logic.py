from datetime import date, timedelta
from backend.app.core.analytics_logic import (
    compute_acwr_series,
    compute_ctl_atl_tsb,
    compute_sport_breakdown,
    compute_performance_trends,
)


def make_day(offset: int, load: float, sport: str = "running") -> dict:
    return {
        "session_date": (date.today() - timedelta(days=offset)).isoformat(),
        "total_load": load,
        "sport": sport,
    }


def test_acwr_series_empty():
    result = compute_acwr_series([])
    assert result == []


def test_acwr_series_single_day():
    sessions = [make_day(0, 100.0)]
    result = compute_acwr_series(sessions)
    assert len(result) == 1
    entry = result[0]
    assert "date" in entry
    assert "acwr" in entry
    assert "acute" in entry
    assert "chronic" in entry
    # With a single day, chronic == acute
    assert entry["acwr"] == 1.0


def test_acwr_series_multiple_weeks():
    # 28 days of data at 100 load/day
    sessions = [make_day(i, 100.0) for i in range(27, -1, -1)]
    result = compute_acwr_series(sessions)
    assert len(result) == 28
    # Steady state: ACWR ≈ 1.0
    last = result[-1]
    assert 0.9 < last["acwr"] < 1.1


def test_acwr_series_spike():
    # 21 days at 100, then 7 days at 200
    sessions = [make_day(i, 100.0) for i in range(27, 6, -1)]
    sessions += [make_day(i, 200.0) for i in range(6, -1, -1)]
    result = compute_acwr_series(sessions)
    last = result[-1]
    # Acute load spiked, chronic still lower — ACWR > 1.0
    assert last["acwr"] > 1.0


def test_ctl_atl_tsb_empty():
    result = compute_ctl_atl_tsb([])
    assert result == []


def test_ctl_atl_tsb_values():
    sessions = [make_day(i, 100.0) for i in range(41, -1, -1)]
    result = compute_ctl_atl_tsb(sessions)
    assert len(result) == 42
    last = result[-1]
    assert "date" in last
    assert "ctl" in last
    assert "atl" in last
    assert "tsb" in last
    # TSB = CTL - ATL
    assert abs(last["tsb"] - (last["ctl"] - last["atl"])) < 0.01


def test_sport_breakdown_empty():
    result = compute_sport_breakdown([])
    assert result == {}


def test_sport_breakdown():
    sessions = [
        {"sport": "running", "duration_minutes": 60, "session_date": date.today().isoformat()},
        {"sport": "running", "duration_minutes": 30, "session_date": date.today().isoformat()},
        {"sport": "lifting", "duration_minutes": 45, "session_date": date.today().isoformat()},
    ]
    result = compute_sport_breakdown(sessions)
    assert result["running"] == 90
    assert result["lifting"] == 45


def test_performance_trends_empty():
    result = compute_performance_trends([])
    assert result["vdot"] == []
    assert result["e1rm"] == []


def test_performance_trends_vdot():
    sessions = [
        {"sport": "running", "session_date": "2026-01-01", "actual_data_json": '{"vdot": 45.0}'},
        {"sport": "running", "session_date": "2026-02-01", "actual_data_json": '{"vdot": 47.0}'},
    ]
    result = compute_performance_trends(sessions)
    assert len(result["vdot"]) == 2
    assert result["vdot"][0]["value"] == 45.0
    assert result["vdot"][1]["value"] == 47.0


def test_performance_trends_e1rm():
    sessions = [
        {"sport": "lifting", "session_date": "2026-01-01", "actual_data_json": '{"e1rm_kg": 100.0}'},
        {"sport": "lifting", "session_date": "2026-02-01", "actual_data_json": '{"e1rm_kg": 105.0}'},
    ]
    result = compute_performance_trends(sessions)
    assert len(result["e1rm"]) == 2
    assert result["e1rm"][0]["value"] == 100.0
