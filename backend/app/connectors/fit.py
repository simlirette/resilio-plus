"""
FIT connector — ANT FIT binary file → parsed activity data.
Uses fitparse library. Pure parser (no DB dependency).
"""

from __future__ import annotations

from datetime import date, datetime, timezone


class FitConnector:
    def parse(self, content: bytes) -> dict:
        """
        Parse FIT binary bytes.
        Returns: activity_date, distance_km, duration_seconds,
                 avg_pace_sec_per_km, elevation_gain_m.
        Raises ValueError if content is invalid or missing required data.
        """
        try:
            import fitparse
        except ImportError:
            raise RuntimeError("fitparse library not installed — run: pip install fitparse")

        fit = fitparse.FitFile(content)

        start_time: datetime | None = None
        total_elapsed_time: float | None = None
        total_distance_m: float | None = None
        total_ascent: float | None = None

        for record in fit.get_messages("session"):
            for field in record:
                if field.name == "start_time" and field.value:
                    raw = field.value
                    if isinstance(raw, datetime):
                        start_time = raw if raw.tzinfo else raw.replace(tzinfo=timezone.utc)
                    else:
                        start_time = datetime.fromisoformat(str(raw)).replace(tzinfo=timezone.utc)
                elif field.name == "total_elapsed_time" and field.value:
                    total_elapsed_time = float(field.value)
                elif field.name == "total_distance" and field.value:
                    total_distance_m = float(field.value)
                elif field.name == "total_ascent" and field.value:
                    total_ascent = float(field.value)

        if start_time is None:
            raise ValueError("FIT file missing start_time — cannot determine activity date")
        if total_elapsed_time is None:
            raise ValueError("FIT file missing total_elapsed_time")

        distance_km = (total_distance_m / 1000.0) if total_distance_m else None
        duration_seconds = int(total_elapsed_time)
        activity_date: date = start_time.date()

        avg_pace = (
            (duration_seconds / distance_km) if (distance_km and distance_km > 0) else None
        )

        return {
            "activity_date": activity_date,
            "distance_km": distance_km,
            "duration_seconds": duration_seconds,
            "avg_pace_sec_per_km": avg_pace,
            "elevation_gain_m": total_ascent,
        }
