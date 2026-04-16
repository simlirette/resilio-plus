"""Streaming Apple Health export.xml parser.

Uses lxml.etree.iterparse for memory-efficient processing of large files (>100MB).
Only yields records for target HK types. Clears parsed elements to maintain O(1) memory.

WARNING: NOT VALIDATED ON REAL DEVICE — tested with synthetic fixtures only.
Validate against a real iPhone export before enabling APPLE_HEALTH_ENABLED=true in prod.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import BinaryIO, Generator

from lxml import etree

_DATE_FMT = "%Y-%m-%d %H:%M:%S %z"

TARGET_TYPES: frozenset[str] = frozenset({
    "HKQuantityTypeIdentifierHeartRateVariabilitySDNN",
    "HKCategoryTypeIdentifierSleepAnalysis",
    "HKQuantityTypeIdentifierRestingHeartRate",
    "HKQuantityTypeIdentifierBodyMass",
    "HKQuantityTypeIdentifierActiveEnergyBurned",
})


@dataclass
class AppleHealthRecord:
    """A single parsed Apple Health record."""

    record_type: str
    start_date: datetime   # timezone-aware, UTC
    end_date: datetime     # timezone-aware, UTC
    value: str             # Raw string. Quantity types: numeric. Category types: HKCategory* constant.
    unit: str
    source_name: str


def _parse_date(s: str) -> datetime:
    """Parse Apple Health date string to UTC-aware datetime.

    Format: "YYYY-MM-DD HH:MM:SS ±HHMM"
    """
    dt = datetime.strptime(s, _DATE_FMT)
    return dt.astimezone(timezone.utc)


def parse_records(
    file_obj: BinaryIO,
    target_types: frozenset[str] = TARGET_TYPES,
    since_date: date | None = None,
) -> Generator[AppleHealthRecord, None, None]:
    """Stream Apple Health XML, yielding records for target types only.

    Memory usage: O(1) per record. Clears each element after processing.
    Raises lxml.etree.XMLSyntaxError for malformed or truncated XML.

    Args:
        file_obj: Binary file-like object (UploadFile.file, open(..., "rb"), BytesIO)
        target_types: HK record type identifiers to include
        since_date: If given, skip records whose end_date.date() < since_date
    """
    context = etree.iterparse(
        file_obj,
        events=("end",),
        tag="Record",
        resolve_entities=False,
        huge_tree=True,
    )

    for _event, elem in context:
        record_type = elem.get("type", "")

        if record_type not in target_types:
            parent = elem.getparent()
            elem.clear()
            if parent is not None:
                while len(parent) and parent[0] is not elem:
                    del parent[0]
            continue

        start_str = elem.get("startDate")
        end_str = elem.get("endDate")
        value = elem.get("value", "")
        unit = elem.get("unit", "")
        source_name = elem.get("sourceName", "")

        parent = elem.getparent()
        elem.clear()
        if parent is not None:
            while len(parent) and parent[0] is not elem:
                del parent[0]

        if not start_str or not end_str:
            continue

        try:
            start_dt = _parse_date(start_str)
            end_dt = _parse_date(end_str)
        except ValueError:
            continue

        if since_date is not None and end_dt.date() < since_date:
            continue

        yield AppleHealthRecord(
            record_type=record_type,
            start_date=start_dt,
            end_date=end_dt,
            value=value,
            unit=unit,
            source_name=source_name,
        )
