"""
Integration tests — Apple Health connector.

Tests both the JSON connector (AppleHealthConnector) and
the XML streaming parser (parse_apple_health_xml).
"""
from __future__ import annotations

import asyncio
import io
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.app.connectors.apple_health import (
    AppleHealthConnector,
    AppleHealthData,
    parse_apple_health_xml,
    _parse_apple_datetime,
    _HRV_SDNN,
    _RESTING_HR,
    _BODY_MASS,
    _SLEEP_ANALYSIS,
)


# ── Mock XML data ─────────────────────────────────────────────────────────────

APPLE_HEALTH_XML_SIMPLE = b"""\
<?xml version="1.0" encoding="UTF-8"?>
<HealthData locale="en_CA">
  <ExportDate value="2026-04-10 08:00:00 +0200"/>
  <Record type="HKQuantityTypeIdentifierHeartRateVariabilitySDNN"
          sourceName="Apple Watch Series 9"
          unit="ms"
          creationDate="2026-04-09 06:30:00 +0200"
          startDate="2026-04-09 06:30:00 +0200"
          endDate="2026-04-09 06:30:00 +0200"
          value="52.3"/>
  <Record type="HKQuantityTypeIdentifierHeartRateVariabilitySDNN"
          sourceName="Apple Watch Series 9"
          unit="ms"
          creationDate="2026-04-10 06:30:00 +0200"
          startDate="2026-04-10 06:30:00 +0200"
          endDate="2026-04-10 06:30:00 +0200"
          value="47.8"/>
  <Record type="HKQuantityTypeIdentifierRestingHeartRate"
          sourceName="Apple Watch Series 9"
          unit="count/min"
          creationDate="2026-04-10 07:00:00 +0200"
          startDate="2026-04-10 07:00:00 +0200"
          endDate="2026-04-10 07:00:00 +0200"
          value="52"/>
  <Record type="HKQuantityTypeIdentifierBodyMass"
          sourceName="Health"
          unit="kg"
          creationDate="2026-04-10 07:15:00 +0200"
          startDate="2026-04-10 07:15:00 +0200"
          endDate="2026-04-10 07:15:00 +0200"
          value="74.5"/>
  <Record type="HKCategoryTypeIdentifierSleepAnalysis"
          sourceName="Apple Watch Series 9"
          creationDate="2026-04-10 07:30:00 +0200"
          startDate="2026-04-09 22:45:00 +0200"
          endDate="2026-04-10 06:30:00 +0200"
          value="HKCategoryValueSleepAnalysisAsleepUnspecified"/>
</HealthData>
"""

APPLE_HEALTH_XML_LBS = b"""\
<?xml version="1.0" encoding="UTF-8"?>
<HealthData locale="en_US">
  <Record type="HKQuantityTypeIdentifierBodyMass"
          sourceName="Health"
          unit="lb"
          creationDate="2026-04-10 08:00:00 -0500"
          startDate="2026-04-10 08:00:00 -0500"
          endDate="2026-04-10 08:00:00 -0500"
          value="165"/>
</HealthData>
"""

APPLE_HEALTH_XML_EMPTY = b"""\
<?xml version="1.0" encoding="UTF-8"?>
<HealthData locale="en_CA">
  <ExportDate value="2026-04-10 08:00:00 +0200"/>
</HealthData>
"""

APPLE_HEALTH_XML_MULTIPLE_SLEEP_NIGHTS = b"""\
<?xml version="1.0" encoding="UTF-8"?>
<HealthData locale="en_CA">
  <Record type="HKCategoryTypeIdentifierSleepAnalysis"
          startDate="2026-04-08 23:00:00 +0200"
          endDate="2026-04-09 06:30:00 +0200"
          value="HKCategoryValueSleepAnalysisAsleepUnspecified"/>
  <Record type="HKCategoryTypeIdentifierSleepAnalysis"
          startDate="2026-04-09 23:15:00 +0200"
          endDate="2026-04-10 07:00:00 +0200"
          value="HKCategoryValueSleepAnalysisAsleepUnspecified"/>
</HealthData>
"""


def _make_upload(content: bytes):
    """Create a mock FastAPI UploadFile for testing."""
    buf = io.BytesIO(content)
    mock = MagicMock()
    mock.read = AsyncMock(side_effect=[content, b""])  # first call returns content, second returns EOF
    return mock


def _make_chunked_upload(content: bytes, chunk_size: int = 64):
    """Simulate chunked reading (streaming)."""
    chunks = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]
    chunks.append(b"")  # EOF
    mock = MagicMock()
    mock.read = AsyncMock(side_effect=chunks)
    return mock


# ── JSON connector (existing) tests ──────────────────────────────────────────

class TestAppleHealthJsonConnector:
    def test_parse_valid_json(self):
        connector = AppleHealthConnector()
        result = connector.parse({
            "snapshot_date": "2026-04-10",
            "hrv_rmssd": 48.5,
            "sleep_hours": 7.2,
            "hr_rest": 52,
        })
        assert isinstance(result, AppleHealthData)
        assert result.snapshot_date == date(2026, 4, 10)
        assert result.hrv_rmssd == 48.5
        assert result.sleep_hours == 7.2
        assert result.hr_rest == 52

    def test_parse_optional_fields_none(self):
        connector = AppleHealthConnector()
        result = connector.parse({"snapshot_date": "2026-04-10"})
        assert result.hrv_rmssd is None
        assert result.sleep_hours is None
        assert result.hr_rest is None

    def test_parse_missing_snapshot_date_raises(self):
        connector = AppleHealthConnector()
        with pytest.raises(ValueError, match="snapshot_date"):
            connector.parse({"hrv_rmssd": 45.0})

    def test_to_extra_dict_keys(self):
        connector = AppleHealthConnector()
        parsed = AppleHealthData(
            snapshot_date=date(2026, 4, 10),
            hrv_rmssd=48.5,
            sleep_hours=7.2,
            hr_rest=52,
        )
        extra = connector.to_extra_dict(parsed)
        assert "last_snapshot_date" in extra
        assert "last_hrv_rmssd" in extra
        assert "last_sleep_hours" in extra
        assert "last_hr_rest" in extra
        assert "last_upload" in extra
        assert extra["last_hrv_rmssd"] == 48.5


# ── XML parser ────────────────────────────────────────────────────────────────

class TestAppleHealthXmlParser:
    def test_hrv_average(self):
        upload = _make_upload(APPLE_HEALTH_XML_SIMPLE)
        result = asyncio.run(parse_apple_health_xml(upload))
        # (52.3 + 47.8) / 2 = 50.05
        assert result["hrv_sdnn_avg"] is not None
        assert abs(result["hrv_sdnn_avg"] - 50.05) < 0.1
        assert result["hrv_readings"] == 2

    def test_resting_hr(self):
        upload = _make_upload(APPLE_HEALTH_XML_SIMPLE)
        result = asyncio.run(parse_apple_health_xml(upload))
        assert result["resting_hr"] == 52

    def test_weight_kg(self):
        upload = _make_upload(APPLE_HEALTH_XML_SIMPLE)
        result = asyncio.run(parse_apple_health_xml(upload))
        assert result["weight_kg"] == 74.5

    def test_weight_lbs_converted(self):
        upload = _make_upload(APPLE_HEALTH_XML_LBS)
        result = asyncio.run(parse_apple_health_xml(upload))
        # 165 lbs ≈ 74.8 kg
        assert result["weight_kg"] is not None
        assert abs(result["weight_kg"] - 74.8) < 0.2

    def test_sleep_hours(self):
        upload = _make_upload(APPLE_HEALTH_XML_SIMPLE)
        result = asyncio.run(parse_apple_health_xml(upload))
        # 22:45 → 06:30 = 7h45m = 7.75h
        assert result["sleep_hours"] is not None
        assert abs(result["sleep_hours"] - 7.75) < 0.05

    def test_empty_xml_returns_nulls(self):
        upload = _make_upload(APPLE_HEALTH_XML_EMPTY)
        result = asyncio.run(parse_apple_health_xml(upload))
        assert result["uploaded"] is True
        assert result["hrv_sdnn_avg"] is None
        assert result["resting_hr"] is None
        assert result["weight_kg"] is None
        assert result["sleep_hours"] is None

    def test_multiple_sleep_nights_takes_latest(self):
        upload = _make_upload(APPLE_HEALTH_XML_MULTIPLE_SLEEP_NIGHTS)
        result = asyncio.run(parse_apple_health_xml(upload))
        # Latest night: 23:15 → 07:00 = 7h45m = 7.75h
        assert result["sleep_hours"] is not None
        assert abs(result["sleep_hours"] - 7.75) < 0.05

    def test_returns_uploaded_true(self):
        upload = _make_upload(APPLE_HEALTH_XML_SIMPLE)
        result = asyncio.run(parse_apple_health_xml(upload))
        assert result["uploaded"] is True

    def test_snapshot_date_present(self):
        upload = _make_upload(APPLE_HEALTH_XML_SIMPLE)
        result = asyncio.run(parse_apple_health_xml(upload))
        assert "snapshot_date" in result
        # snapshot_date is today's date (ISO format)
        assert len(result["snapshot_date"]) == 10


# ── Datetime parsing ──────────────────────────────────────────────────────────

class TestParseAppleDatetime:
    def test_standard_format(self):
        dt = _parse_apple_datetime("2026-04-10 07:30:00 +0200")
        assert dt is not None
        assert dt.year == 2026
        assert dt.month == 4
        assert dt.day == 10
        assert dt.hour == 7
        assert dt.minute == 30

    def test_us_format(self):
        dt = _parse_apple_datetime("2026-04-10 07:30:00 -0500")
        assert dt is not None
        assert dt.day == 10

    def test_invalid_returns_none(self):
        assert _parse_apple_datetime(None) is None
        assert _parse_apple_datetime("") is None
        assert _parse_apple_datetime("not a date") is None
