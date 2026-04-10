"""
Apple Health connector — JSON upload → parsed health data.
Stores latest HRV/sleep/HR in ConnectorCredentialModel.extra_json.
Coexists with Terra: Recovery Coach reads from both, uses most recent.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone


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
