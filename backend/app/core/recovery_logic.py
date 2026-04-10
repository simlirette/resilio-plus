from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from ..core.readiness import compute_readiness
from ..schemas.connector import TerraHealthData

_SLEEP_BANKING_WEEKS = 2  # activate sleep banking if race within this many weeks


@dataclass
class RecoveryStatus:
    readiness_modifier: float       # [0.5, 1.5]
    hrv_trend: str                  # "improving" | "stable" | "declining"
    sleep_avg_hours: float | None   # average sleep over last 7 days
    sleep_banking_active: bool      # True if race within _SLEEP_BANKING_WEEKS
    recommendation: str             # human-readable coaching note


def compute_recovery_status(
    terra_data: list[TerraHealthData],
    target_race_date: date | None,
    week_start: date,
) -> RecoveryStatus:
    """Compute recovery status from Terra health data.

    Delegates readiness_modifier to existing compute_readiness().
    Adds HRV trend (3-point slope) and sleep banking flag.
    """
    readiness_modifier = compute_readiness(terra_data)

    # HRV trend: compare first 3 vs last 3 entries (oldest-first after sort)
    hrv_values = [
        e.hrv_rmssd
        for e in sorted(terra_data, key=lambda e: e.date)
        if e.hrv_rmssd is not None
    ]
    hrv_trend = _compute_hrv_trend(hrv_values)

    # Sleep average
    sleep_values = [e.sleep_duration_hours for e in terra_data if e.sleep_duration_hours]
    sleep_avg = round(sum(sleep_values) / len(sleep_values), 1) if sleep_values else None

    # Sleep banking
    sleep_banking_active = False
    if target_race_date:
        weeks_to_race = (target_race_date - week_start).days // 7
        sleep_banking_active = 0 < weeks_to_race <= _SLEEP_BANKING_WEEKS

    # Recommendation
    recommendation = _build_recommendation(
        readiness_modifier, hrv_trend, sleep_avg, sleep_banking_active
    )

    return RecoveryStatus(
        readiness_modifier=readiness_modifier,
        hrv_trend=hrv_trend,
        sleep_avg_hours=sleep_avg,
        sleep_banking_active=sleep_banking_active,
        recommendation=recommendation,
    )


def _compute_hrv_trend(hrv_values: list[float]) -> str:
    """Return 'improving', 'stable', or 'declining' based on 3-point comparison."""
    if len(hrv_values) < 4:
        return "stable"
    early_mean = sum(hrv_values[:3]) / 3
    late_mean = sum(hrv_values[-3:]) / 3
    delta_pct = (late_mean - early_mean) / early_mean if early_mean > 0 else 0
    if delta_pct > 0.05:
        return "improving"
    if delta_pct < -0.05:
        return "declining"
    return "stable"


def _build_recommendation(
    modifier: float,
    trend: str,
    sleep_avg: float | None,
    banking: bool,
) -> str:
    parts = []
    if modifier < 0.7:
        parts.append("Readiness low — reduce intensity, prioritize sleep and recovery.")
    elif modifier < 0.9:
        parts.append("Readiness moderate — avoid maximal efforts.")
    else:
        parts.append("Readiness good — proceed as planned.")

    if trend == "declining":
        parts.append("HRV declining — monitor for overtraining.")
    elif trend == "improving":
        parts.append("HRV improving — recovery on track.")

    if banking:
        parts.append("Sleep banking active — target 8.5-10h/night this week.")
    elif sleep_avg is not None and sleep_avg < 7.0:
        parts.append(f"Sleep averaging {sleep_avg}h — aim for 7.5-8h minimum.")

    return " ".join(parts)
