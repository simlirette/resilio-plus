"""
Pure functions for computing analytics time-series.
Inputs: list of dicts (from SessionLogModel rows).
Outputs: list of dicts ready for JSON serialization.
"""
import json
from collections import defaultdict
from datetime import date, timedelta
from typing import Any


def _load_by_date(sessions: list[dict[str, Any]]) -> dict[str, float]:
    """Aggregate total_load per ISO date string."""
    by_date: dict[str, float] = defaultdict(float)
    for s in sessions:
        d = s.get("session_date")
        if d:
            by_date[str(d)] += float(s.get("total_load") or 0.0)
    return dict[str, Any](by_date)


def _date_range(start: date, end: date) -> list[date]:
    days = []
    current = start
    while current <= end:
        days.append(current)
        current += timedelta(days=1)
    return days


def compute_acwr_series(sessions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Compute ACWR (Acute:Chronic Workload Ratio) series using EWMA.
    Acute window: 7 days (λ = 2/8 = 0.25)
    Chronic window: 28 days (λ = 2/29 ≈ 0.069)
    Returns: list of {"date", "acwr", "acute", "chronic"} sorted ascending.
    """
    if not sessions:
        return []

    by_date = _load_by_date(sessions)
    dates = sorted(by_date.keys())
    start = date.fromisoformat(dates[0])
    end = date.fromisoformat(dates[-1])
    all_dates = _date_range(start, end)

    lambda_acute = 2 / (7 + 1)  # 0.25
    lambda_chronic = 2 / (28 + 1)  # ≈ 0.069

    # Warm-start both EWMAs at the first day's load so ACWR = 1.0 on day 1
    first_load = by_date.get(all_dates[0].isoformat(), 0.0)
    ewma_acute = first_load
    ewma_chronic = first_load
    result = []

    for d in all_dates:
        load = by_date.get(d.isoformat(), 0.0)
        ewma_acute = lambda_acute * load + (1 - lambda_acute) * ewma_acute
        ewma_chronic = lambda_chronic * load + (1 - lambda_chronic) * ewma_chronic
        acwr = (ewma_acute / ewma_chronic) if ewma_chronic > 0 else 1.0
        result.append(
            {
                "date": d.isoformat(),
                "acwr": round(acwr, 3),
                "acute": round(ewma_acute, 1),
                "chronic": round(ewma_chronic, 1),
            }
        )

    return result


def compute_ctl_atl_tsb(sessions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Compute CTL (Chronic Training Load), ATL (Acute Training Load), TSB (Training Stress Balance).
    CTL: 42-day EWMA (λ = 2/43)
    ATL: 7-day EWMA (λ = 2/8)
    TSB = CTL - ATL
    Returns: list of {"date", "ctl", "atl", "tsb"} sorted ascending.
    """
    if not sessions:
        return []

    by_date = _load_by_date(sessions)
    dates = sorted(by_date.keys())
    start = date.fromisoformat(dates[0])
    end = date.fromisoformat(dates[-1])
    all_dates = _date_range(start, end)

    lambda_ctl = 2 / (42 + 1)
    lambda_atl = 2 / (7 + 1)

    ctl = 0.0
    atl = 0.0
    result = []

    for d in all_dates:
        load = by_date.get(d.isoformat(), 0.0)
        ctl = lambda_ctl * load + (1 - lambda_ctl) * ctl
        atl = lambda_atl * load + (1 - lambda_atl) * atl
        tsb = ctl - atl
        result.append(
            {
                "date": d.isoformat(),
                "ctl": round(ctl, 1),
                "atl": round(atl, 1),
                "tsb": round(tsb, 1),
            }
        )

    return result


def compute_sport_breakdown(sessions: list[dict[str, Any]]) -> dict[str, int]:
    """
    Sum duration_minutes per sport.
    Returns: {"running": 180, "lifting": 90, ...}
    """
    totals: dict[str, int] = defaultdict(int)
    for s in sessions:
        sport = s.get("sport")
        mins = int(s.get("duration_minutes") or 0)
        if sport and mins:
            totals[sport] += mins
    return dict[str, Any](totals)


def compute_performance_trends(sessions: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """
    Extract VDOT (running) and e1RM (lifting) progression over time.
    Returns: {"vdot": [{"date", "value"}, ...], "e1rm": [{"date", "value"}, ...]}
    """
    vdot_series: list[dict[str, str | float]] = []
    e1rm_series: list[dict[str, str | float]] = []

    for s in sessions:
        sport = s.get("sport", "")
        d = s.get("session_date")
        raw_json = s.get("actual_data_json")
        if not (d and raw_json):
            continue
        try:
            data = json.loads(raw_json) if isinstance(raw_json, str) else raw_json
        except (json.JSONDecodeError, TypeError):
            continue

        if sport == "running" and "vdot" in data:
            vdot_series.append({"date": str(d), "value": float(data["vdot"])})
        elif sport == "lifting" and "e1rm_kg" in data:
            e1rm_series.append({"date": str(d), "value": float(data["e1rm_kg"])})

    vdot_series.sort(key=lambda x: str(x["date"]))
    e1rm_series.sort(key=lambda x: str(x["date"]))

    return {"vdot": vdot_series, "e1rm": e1rm_series}
