"""Aggregate AppleHealthRecord stream into per-day summaries.

WARNING: NOT VALIDATED ON REAL DEVICE — tested with synthetic fixtures only.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable

from .xml_parser import AppleHealthRecord

# Sleep values that count as "asleep" time (InBed and Awake excluded)
_SLEEP_ASLEEP_VALUES: frozenset[str] = frozenset({
    "HKCategoryValueSleepAnalysisAsleep",       # iOS ≤ 15
    "HKCategoryValueSleepAnalysisAsleepCore",   # iOS 16+
    "HKCategoryValueSleepAnalysisAsleepDeep",   # iOS 16+
    "HKCategoryValueSleepAnalysisAsleepREM",    # iOS 16+
    # Excluded: HKCategoryValueSleepAnalysisInBed, HKCategoryValueSleepAnalysisAwake
})


@dataclass
class AppleHealthDailySummary:
    """Aggregated daily metrics from Apple Health records."""

    date: date
    hrv_sdnn_avg: float | None = None       # Mean SDNN (ms). NOTE: SDNN ≠ RMSSD; see INTEGRATIONS.md
    sleep_hours: float | None = None         # Sum of asleep durations; None if no asleep records
    rhr_bpm: float | None = None            # Mean resting heart rate (bpm)
    body_mass_kg: float | None = None       # Last body mass reading of the day (kg)
    active_energy_kcal: float | None = None  # Sum of active energy burned (kcal)


def aggregate(records: Iterable[AppleHealthRecord]) -> dict[date, AppleHealthDailySummary]:
    """Aggregate Apple Health records into per-day summaries.

    Returns a dict keyed by date. Dates with no target records are absent.

    Rules:
    - HRV SDNN: mean of all values for the day (by end_date)
    - Sleep: sum of asleep durations (InBed + Awake excluded); attributed to end_date (wake-up day)
    - RHR: mean of all readings for the day
    - Body mass: last reading of the day (latest end_date wins); lbs converted to kg
    - Active energy: sum of all readings for the day
    """
    _hrv: dict[date, list[float]] = defaultdict(list)
    _sleep: dict[date, float] = defaultdict(float)
    _sleep_seen: set[date] = set()  # tracks days with at least one asleep record
    _rhr: dict[date, list[float]] = defaultdict(list)
    _mass: dict[date, tuple[datetime, float]] = {}   # (end_datetime, value_kg)
    _energy: dict[date, float] = defaultdict(float)
    all_dates: set[date] = set()

    for r in records:
        rtype = r.record_type

        if rtype == "HKQuantityTypeIdentifierHeartRateVariabilitySDNN":
            try:
                d = r.end_date.date()
                all_dates.add(d)
                _hrv[d].append(float(r.value))
            except ValueError:
                pass

        elif rtype == "HKCategoryTypeIdentifierSleepAnalysis":
            d = r.end_date.date()  # attribute to wake-up day
            all_dates.add(d)
            if r.value in _SLEEP_ASLEEP_VALUES:
                duration_h = (r.end_date - r.start_date).total_seconds() / 3600
                _sleep[d] += duration_h
                _sleep_seen.add(d)

        elif rtype == "HKQuantityTypeIdentifierRestingHeartRate":
            try:
                d = r.end_date.date()
                all_dates.add(d)
                _rhr[d].append(float(r.value))
            except ValueError:
                pass

        elif rtype == "HKQuantityTypeIdentifierBodyMass":
            try:
                d = r.end_date.date()
                all_dates.add(d)
                raw = float(r.value)
                kg = raw * 0.453592 if r.unit in ("lb", "lbs") else raw
                existing = _mass.get(d)
                if existing is None or r.end_date > existing[0]:
                    _mass[d] = (r.end_date, kg)
            except ValueError:
                pass

        elif rtype == "HKQuantityTypeIdentifierActiveEnergyBurned":
            try:
                d = r.end_date.date()
                all_dates.add(d)
                _energy[d] += float(r.value)
            except ValueError:
                pass

    result: dict[date, AppleHealthDailySummary] = {}
    for d in all_dates:
        hrv_vals = _hrv.get(d, [])
        rhr_vals = _rhr.get(d, [])
        mass_entry = _mass.get(d)
        result[d] = AppleHealthDailySummary(
            date=d,
            hrv_sdnn_avg=sum(hrv_vals) / len(hrv_vals) if hrv_vals else None,
            sleep_hours=_sleep[d] if d in _sleep_seen else None,
            rhr_bpm=sum(rhr_vals) / len(rhr_vals) if rhr_vals else None,
            body_mass_kg=mass_entry[1] if mass_entry else None,
            active_energy_kcal=_energy[d] if d in _energy else None,
        )
    return result
