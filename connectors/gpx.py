"""
GPX connector — fichier XML GPS → RunActivity.
Chaque upload crée une nouvelle RunActivity (pas de déduplication).
"""

import math
import uuid
import xml.etree.ElementTree as ET
from datetime import date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from models.database import RunActivity

_GPX_NS = "http://www.topografix.com/GPX/1/1"


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance en km entre deux points GPS via formule haversine."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.asin(math.sqrt(a))


class GpxConnector:
    def parse_gpx(self, content: bytes) -> dict:
        """
        Parse le XML GPX et retourne les données d'activité.
        Retourne : activity_date, distance_km, duration_seconds,
                   avg_pace_sec_per_km, elevation_gain_m.
        """
        root = ET.fromstring(content)
        ns = {"g": _GPX_NS}

        trackpoints = root.findall(".//g:trkpt", ns)
        if not trackpoints:
            raise ValueError("GPX file contains no trackpoints")

        lats = [float(tp.get("lat", 0)) for tp in trackpoints]
        lons = [float(tp.get("lon", 0)) for tp in trackpoints]
        eles = []
        for tp in trackpoints:
            ele_el = tp.find("g:ele", ns)
            eles.append(float(ele_el.text) if ele_el is not None else None)

        times = []
        for tp in trackpoints:
            time_el = tp.find("g:time", ns)
            if time_el is not None:
                times.append(
                    datetime.fromisoformat(time_el.text.replace("Z", "+00:00"))
                )

        # Distance via haversine
        distance_km = sum(
            _haversine_km(lats[i], lons[i], lats[i + 1], lons[i + 1])
            for i in range(len(lats) - 1)
        )

        # Duration
        duration_seconds: int | None = None
        activity_date: date | None = None
        if len(times) >= 2:
            duration_seconds = int((times[-1] - times[0]).total_seconds())
            activity_date = times[0].date()

        if activity_date is None:
            raise ValueError(
                "GPX file contains no trackpoint timestamps — "
                "cannot determine activity date"
            )

        # Avg pace
        avg_pace = (
            (duration_seconds / distance_km)
            if (distance_km > 0 and duration_seconds)
            else None
        )

        # Elevation gain (sum of positive increments)
        elevation_gain_m: float | None = None
        valid_eles = [e for e in eles if e is not None]
        if len(valid_eles) >= 2:
            elevation_gain_m = sum(
                max(0.0, valid_eles[i + 1] - valid_eles[i])
                for i in range(len(valid_eles) - 1)
            )

        return {
            "activity_date": activity_date,
            "distance_km": distance_km if distance_km > 0 else None,
            "duration_seconds": duration_seconds,
            "avg_pace_sec_per_km": avg_pace,
            "elevation_gain_m": elevation_gain_m,
        }

    async def ingest_gpx(
        self,
        athlete_id: uuid.UUID,
        content: bytes,
        db: AsyncSession,
    ) -> RunActivity:
        """
        Parse le GPX et insère une RunActivity.
        Pas d'upsert — chaque upload GPX crée une nouvelle activité.
        """
        parsed = self.parse_gpx(content)

        distance_km = parsed.get("distance_km") or 0.0

        # TRIMP fallback (pas de HR dans GPX)
        trimp = distance_km * 1.0

        run = RunActivity(
            athlete_id=athlete_id,
            activity_date=parsed["activity_date"],
            activity_type="Run",
            distance_km=parsed.get("distance_km"),
            duration_seconds=parsed.get("duration_seconds"),
            avg_pace_sec_per_km=parsed.get("avg_pace_sec_per_km"),
            elevation_gain_m=parsed.get("elevation_gain_m"),
            trimp=trimp,
            strava_raw={"source": "gpx"},
        )
        db.add(run)
        await db.flush()
        return run
