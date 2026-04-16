"""Tests for Apple Health daily aggregator."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from backend.app.integrations.apple_health.aggregator import (
    AppleHealthDailySummary,
    aggregate,
)
from backend.app.integrations.apple_health.xml_parser import parse_records

FIXTURE_DIR = Path(__file__).parents[3] / "tests" / "fixtures" / "apple_health"


def _agg(filename: str, **parse_kwargs) -> dict[date, AppleHealthDailySummary]:
    path = FIXTURE_DIR / filename
    with open(path, "rb") as f:
        records = parse_records(f, **parse_kwargs)
        return aggregate(records)


class TestMinimalValid:
    def test_returns_one_day(self):
        result = _agg("minimal_valid.xml")
        assert len(result) == 1

    def test_hrv_sdnn_avg(self):
        result = _agg("minimal_valid.xml")
        day = result[date(2026, 4, 15)]
        assert day.hrv_sdnn_avg == pytest.approx(45.3)

    def test_sleep_hours(self):
        # startDate=2026-04-14 23:00 UTC, endDate=2026-04-15 07:00 UTC → 8h, attributed to 2026-04-15
        result = _agg("minimal_valid.xml")
        day = result[date(2026, 4, 15)]
        assert day.sleep_hours == pytest.approx(8.0)

    def test_rhr_bpm(self):
        result = _agg("minimal_valid.xml")
        day = result[date(2026, 4, 15)]
        assert day.rhr_bpm == pytest.approx(52.0)

    def test_body_mass_kg(self):
        result = _agg("minimal_valid.xml")
        day = result[date(2026, 4, 15)]
        assert day.body_mass_kg == pytest.approx(72.5)

    def test_active_energy_kcal(self):
        result = _agg("minimal_valid.xml")
        day = result[date(2026, 4, 15)]
        assert day.active_energy_kcal == pytest.approx(450.0)


class TestSleepIOS15:
    def test_inbed_excluded_asleep_included(self):
        # sleep_ios15.xml: Asleep 23:00→06:30 = 7.5h; InBed excluded
        result = _agg("sleep_ios15.xml")
        day = result[date(2026, 4, 15)]
        assert day.sleep_hours == pytest.approx(7.5)

    def test_inbed_only_sleep_hours_counted_correctly(self):
        # sleep_with_inbed.xml: InBed 9h excluded; Asleep 23:00→06:00 = 7h
        result = _agg("sleep_with_inbed.xml")
        day = result[date(2026, 4, 15)]
        assert day.sleep_hours == pytest.approx(7.0)


class TestSleepIOS16:
    def test_core_deep_rem_summed_awake_excluded(self):
        # Core 23:00→01:00 = 2h; Deep 01:00→02:30 = 1.5h; REM 02:30→04:30 = 2h; Awake excluded
        result = _agg("sleep_ios16.xml")
        day = result[date(2026, 4, 15)]
        assert day.sleep_hours == pytest.approx(5.5)


class TestSleepAttributedToEndDate:
    def test_sleep_spanning_midnight_attributed_to_wakeup_day(self):
        # Sleep record in minimal_valid.xml: start=2026-04-14, end=2026-04-15 → day=2026-04-15
        result = _agg("minimal_valid.xml")
        assert date(2026, 4, 15) in result
        assert date(2026, 4, 14) not in result


class TestBodyMassLbs:
    def test_lbs_converted_to_kg(self):
        result = _agg("body_mass_lbs.xml")
        day = result[date(2026, 4, 15)]
        # 159.83 lb × 0.453592 ≈ 72.498 kg
        assert day.body_mass_kg == pytest.approx(72.5, abs=0.05)


class TestMixedSources:
    def test_rhr_averaged_across_sources(self):
        # Apple Watch: 52, iPhone: 56 → mean=54.0
        result = _agg("mixed_sources.xml")
        day = result[date(2026, 4, 15)]
        assert day.rhr_bpm == pytest.approx(54.0)


class TestMultiDay7d:
    def test_returns_seven_days(self):
        result = _agg("multi_day_7d.xml")
        assert len(result) == 7

    def test_day_with_body_mass(self):
        result = _agg("multi_day_7d.xml")
        day = result[date(2026, 4, 12)]
        assert day.body_mass_kg == pytest.approx(73.0)

    def test_days_without_body_mass_are_none(self):
        result = _agg("multi_day_7d.xml")
        for d, summary in result.items():
            if d != date(2026, 4, 12):
                assert summary.body_mass_kg is None


class TestEmptyTargetTypes:
    def test_empty_result_for_no_target_records(self):
        result = _agg("empty_target_types.xml")
        assert len(result) == 0
