"""Tests for Apple Health XML streaming parser."""
from __future__ import annotations

import io
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from lxml import etree

from backend.app.integrations.apple_health.xml_parser import (
    TARGET_TYPES,
    AppleHealthRecord,
    parse_records,
)

FIXTURE_DIR = Path(__file__).parents[3] / "tests" / "fixtures" / "apple_health"


def _parse(filename: str, **kwargs) -> list[AppleHealthRecord]:
    path = FIXTURE_DIR / filename
    with open(path, "rb") as f:
        return list(parse_records(f, **kwargs))


class TestMinimalValid:
    def test_yields_five_records(self):
        records = _parse("minimal_valid.xml")
        assert len(records) == 5

    def test_record_types_are_target_types(self):
        records = _parse("minimal_valid.xml")
        for r in records:
            assert r.record_type in TARGET_TYPES

    def test_dates_are_utc_aware(self):
        records = _parse("minimal_valid.xml")
        for r in records:
            assert r.start_date.tzinfo is not None
            assert r.end_date.tzinfo is not None
            assert r.start_date.tzinfo == timezone.utc

    def test_hrv_record_value_is_numeric_string(self):
        records = _parse("minimal_valid.xml")
        hrv = next(r for r in records if "HeartRateVariability" in r.record_type)
        assert float(hrv.value) == pytest.approx(45.3)

    def test_sleep_record_value_is_category_string(self):
        records = _parse("minimal_valid.xml")
        sleep = next(r for r in records if "SleepAnalysis" in r.record_type)
        assert sleep.value == "HKCategoryValueSleepAnalysisAsleep"

    def test_body_mass_unit_is_kg(self):
        records = _parse("minimal_valid.xml")
        mass = next(r for r in records if "BodyMass" in r.record_type)
        assert mass.unit == "kg"
        assert float(mass.value) == pytest.approx(72.5)


class TestSinceDate:
    def test_since_date_filters_older_records(self):
        """Records with end_date before since_date must be excluded."""
        records = _parse("minimal_valid.xml", since_date=date(2026, 4, 16))
        # All records in minimal_valid.xml end on 2026-04-15 → all filtered out
        assert len(records) == 0

    def test_since_date_includes_matching_records(self):
        records = _parse("minimal_valid.xml", since_date=date(2026, 4, 15))
        assert len(records) == 5


class TestSleepCategories:
    def test_ios15_sleep_record_included(self):
        records = _parse("sleep_ios15.xml")
        sleep_records = [r for r in records if "SleepAnalysis" in r.record_type]
        # Parser yields ALL sleep records; aggregator filters InBed
        assert len(sleep_records) == 2  # Asleep + InBed both yielded by parser

    def test_ios16_sleep_records_all_yielded(self):
        records = _parse("sleep_ios16.xml")
        sleep_records = [r for r in records if "SleepAnalysis" in r.record_type]
        assert len(sleep_records) == 4  # Core + Deep + REM + Awake all yielded by parser


class TestTruncatedXML:
    def test_raises_on_truncated_xml(self):
        with pytest.raises(etree.XMLSyntaxError):
            _parse("truncated.xml")


class TestEmptyTargetTypes:
    def test_no_records_yielded_for_non_target_types(self):
        records = _parse("empty_target_types.xml")
        assert len(records) == 0


class TestLargeRange:
    def test_90d_fixture_yields_expected_count(self):
        records = _parse("large_range_90d.xml")
        # 90 days × 4 records (HRV + sleep + RHR + energy) = 360
        assert len(records) == 360

    def test_no_memory_error(self):
        """Verify streaming works — no MemoryError on large fixture."""
        records = _parse("large_range_90d.xml")
        assert len(records) > 0


class TestBodyMassLbs:
    def test_yields_body_mass_record(self):
        records = _parse("body_mass_lbs.xml")
        assert len(records) == 1
        assert records[0].unit == "lb"
        # Parser yields raw value — unit conversion is aggregator's job
        assert float(records[0].value) == pytest.approx(159.83)
