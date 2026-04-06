"""
FIT connector — fichier binaire Garmin/Polar → RunActivity.
Utilise fitparse pour parser le format FIT binaire.
Chaque upload crée une nouvelle RunActivity (pas de déduplication).
"""

import io
import math
import uuid
from datetime import UTC, datetime

from fitparse import FitFile
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import RunActivity


class FitConnector:
    def parse_fit(self, content: bytes) -> dict:
        """
        Parse le fichier FIT et retourne les données d'activité.
        Utilise le message 'session' (Garmin summary) si disponible.
        """
        fitfile = FitFile(io.BytesIO(content))
        messages = list(fitfile.get_messages("session"))

        if not messages:
            raise ValueError("FIT file contains no 'session' message")

        msg = messages[0]

        def get(key: str):
            return msg.get_value(key)

        start_time_raw = get("start_time")
        if isinstance(start_time_raw, datetime):
            if start_time_raw.tzinfo is None:
                start_time_raw = start_time_raw.replace(tzinfo=UTC)
            activity_date = start_time_raw.date()
        else:
            activity_date = None

        total_distance = get("total_distance")  # metres
        distance_km = (total_distance / 1000) if total_distance is not None else None

        total_elapsed_time = get("total_elapsed_time")  # seconds
        duration_seconds = int(total_elapsed_time) if total_elapsed_time is not None else None

        avg_hr = get("avg_heart_rate")
        max_hr = get("max_heart_rate")
        elevation_gain_m = get("total_ascent")
        sport = get("sport") or "Run"

        avg_pace: float | None = None
        if distance_km and distance_km > 0 and duration_seconds:
            avg_pace = duration_seconds / distance_km

        return {
            "activity_date": activity_date,
            "activity_type": sport,
            "distance_km": distance_km,
            "duration_seconds": duration_seconds,
            "avg_pace_sec_per_km": avg_pace,
            "avg_hr": int(avg_hr) if avg_hr is not None else None,
            "max_hr": int(max_hr) if max_hr is not None else None,
            "elevation_gain_m": (
                float(elevation_gain_m) if elevation_gain_m is not None else None
            ),
        }

    async def ingest_fit(
        self,
        athlete_id: uuid.UUID,
        content: bytes,
        db: AsyncSession,
    ) -> RunActivity:
        """
        Parse le FIT et insère une RunActivity.
        Calcule le TRIMP HR-based si avg_hr et max_hr disponibles.
        """
        parsed = self.parse_fit(content)

        distance_km = parsed.get("distance_km") or 0.0
        duration_s = parsed.get("duration_seconds") or 0
        avg_hr = parsed.get("avg_hr")
        max_hr = parsed.get("max_hr")

        # TRIMP
        if avg_hr and max_hr:
            ratio = avg_hr / max_hr
            trimp = (duration_s / 60) * ratio * math.exp(1.92 * ratio)
        else:
            trimp = distance_km * 1.0

        run = RunActivity(
            athlete_id=athlete_id,
            activity_date=parsed.get("activity_date"),
            activity_type=parsed.get("activity_type", "Run"),
            distance_km=parsed.get("distance_km"),
            duration_seconds=parsed.get("duration_seconds"),
            avg_pace_sec_per_km=parsed.get("avg_pace_sec_per_km"),
            avg_hr=avg_hr,
            max_hr=max_hr,
            elevation_gain_m=parsed.get("elevation_gain_m"),
            trimp=trimp,
            strava_raw={"source": "fit"},
        )
        db.add(run)
        await db.flush()
        return run
