"""
Apple Health connector — JSON upload → parsed health data.
                        XML upload  → streamed parse of export.xml

Stores latest HRV/sleep/HR in ConnectorCredentialModel.extra_json.
Coexists with Terra: Recovery Coach reads from both, uses most recent.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import UploadFile


@dataclass
class AppleHealthData:
    snapshot_date: date
    hrv_rmssd: float | None
    sleep_hours: float | None
    hr_rest: int | None


class AppleHealthConnector:
    """Parses Apple Health export JSON and converts to storage format."""

    def parse(self, data: dict) -> AppleHealthData:
        """
        Parse Apple Health JSON payload.
        Required: snapshot_date (ISO string).
        Optional: hrv_rmssd (float), sleep_hours (float), hr_rest (int).
        """
        raw_date = data.get("snapshot_date")
        if raw_date is None:
            raise ValueError("snapshot_date is required in Apple Health payload")

        snapshot_date = date.fromisoformat(str(raw_date))

        hrv_rmssd = data.get("hrv_rmssd")
        sleep_hours = data.get("sleep_hours")
        hr_rest = data.get("hr_rest")

        return AppleHealthData(
            snapshot_date=snapshot_date,
            hrv_rmssd=float(hrv_rmssd) if hrv_rmssd is not None else None,
            sleep_hours=float(sleep_hours) if sleep_hours is not None else None,
            hr_rest=int(hr_rest) if hr_rest is not None else None,
        )

    def to_extra_dict(self, parsed: AppleHealthData) -> dict:
        """Convert parsed data to dict suitable for ConnectorCredentialModel.extra_json."""
        return {
            "last_snapshot_date": parsed.snapshot_date.isoformat(),
            "last_hrv_rmssd": parsed.hrv_rmssd,
            "last_sleep_hours": parsed.sleep_hours,
            "last_hr_rest": parsed.hr_rest,
            "last_upload": datetime.now(timezone.utc).isoformat(),
        }


# ── Apple Health XML streaming parser ────────────────────────────────────────

# Apple Health HKQuantityType identifiers we care about
_HRV_SDNN = "HKQuantityTypeIdentifierHeartRateVariabilitySDNN"
_RESTING_HR = "HKQuantityTypeIdentifierRestingHeartRate"
_BODY_MASS = "HKQuantityTypeIdentifierBodyMass"
_SLEEP_ANALYSIS = "HKCategoryTypeIdentifierSleepAnalysis"

# Sleep analysis values that count as actual sleep (not in-bed)
_SLEEP_VALUES = {"HKCategoryValueSleepAnalysisAsleepUnspecified", "HKCategoryValueSleepAnalysisAsleep"}

_CHUNK_SIZE = 64 * 1024  # 64 KB streaming chunks


def _parse_apple_datetime(s: str) -> datetime | None:
    """Parse Apple Health datetime: '2026-04-02 07:30:00 +0200'"""
    try:
        return datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return None


async def parse_apple_health_xml(upload: "UploadFile") -> dict:
    """
    Stream-parse an Apple Health export.xml file.

    Reads the file in chunks to handle exports up to 500 MB+.
    Returns a summary dict with latest HRV, sleep, HR, and weight values.
    """
    # Collect records by type — keep only most-recent per type
    records: dict[str, list[dict]] = {
        _HRV_SDNN: [],
        _RESTING_HR: [],
        _BODY_MASS: [],
        _SLEEP_ANALYSIS: [],
    }

    # We use iterparse in incremental mode. FastAPI UploadFile is async so we
    # read synchronously in a single pass (the XML parser needs the full stream)
    # but we keep memory low by clearing processed elements.
    parser = ET.XMLPullParser(["end"])

    while True:
        chunk = await upload.read(_CHUNK_SIZE)
        if not chunk:
            break
        parser.feed(chunk)
        for _event, elem in parser.read_events():
            if elem.tag != "Record":
                elem.clear()
                continue
            rec_type = elem.get("type", "")
            if rec_type not in records:
                elem.clear()
                continue
            records[rec_type].append({
                "value": elem.get("value"),
                "unit": elem.get("unit"),
                "startDate": elem.get("startDate"),
                "endDate": elem.get("endDate"),
            })
            elem.clear()

    # ── Aggregate results ──────────────────────────────────────────────────

    # HRV: average of all readings (Apple reports per-night measurement)
    hrv_values = []
    for r in records[_HRV_SDNN]:
        try:
            hrv_values.append(float(r["value"]))
        except (TypeError, ValueError):
            pass
    hrv_avg = round(sum(hrv_values) / len(hrv_values), 1) if hrv_values else None

    # Resting HR: latest reading
    resting_hr: int | None = None
    for r in sorted(records[_RESTING_HR], key=lambda x: x.get("startDate") or "", reverse=True):
        try:
            resting_hr = int(float(r["value"]))
            break
        except (TypeError, ValueError):
            pass

    # Body mass: latest reading, convert to kg if lbs
    weight_kg: float | None = None
    for r in sorted(records[_BODY_MASS], key=lambda x: x.get("startDate") or "", reverse=True):
        try:
            val = float(r["value"])
            if (r.get("unit") or "").lower() in ("lb", "lbs"):
                val = round(val * 0.453592, 1)
            weight_kg = round(val, 1)
            break
        except (TypeError, ValueError):
            pass

    # Sleep: sum durations of "asleep" category records for most recent night
    sleep_hours: float | None = None
    sleep_records = sorted(
        records[_SLEEP_ANALYSIS],
        key=lambda x: x.get("startDate") or "",
        reverse=True,
    )
    if sleep_records:
        # Group by calendar date of startDate, take most recent date
        from collections import defaultdict
        by_date: dict[str, float] = defaultdict(float)
        for r in sleep_records:
            val = r.get("value", "")
            if val not in _SLEEP_VALUES:
                continue
            start = _parse_apple_datetime(r.get("startDate") or "")
            end = _parse_apple_datetime(r.get("endDate") or "")
            if start and end:
                hours = max(0.0, (end - start).total_seconds() / 3600)
                day = start.strftime("%Y-%m-%d")
                by_date[day] += hours
        if by_date:
            latest_day = max(by_date)
            sleep_hours = round(by_date[latest_day], 2)

    snapshot_date = date.today().isoformat()

    return {
        "uploaded": True,
        "snapshot_date": snapshot_date,
        "hrv_sdnn_avg": hrv_avg,
        "hrv_readings": len(hrv_values),
        "resting_hr": resting_hr,
        "weight_kg": weight_kg,
        "sleep_hours": sleep_hours,
    }
