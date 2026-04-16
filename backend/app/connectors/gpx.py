"""
GPX connector — GPS XML file → parsed activity data.
Pure parser (no DB dependency) — route layer handles persistence.
"""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from datetime import date, datetime
from typing import Any

_GPX_NS = "http://www.topografix.com/GPX/1/1"


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.asin(math.sqrt(a))


class GpxConnector:
    def parse(self, content: bytes) -> dict[str, Any]:
        """
        Parse GPX XML bytes.
        Returns: activity_date, distance_km, duration_seconds,
                 avg_pace_sec_per_km, elevation_gain_m.
        Raises ValueError if content is invalid.
        """
        root = ET.fromstring(content)
        ns = {"g": _GPX_NS}

        trackpoints = root.findall(".//g:trkpt", ns)
        if not trackpoints:
            raise ValueError("GPX file contains no trackpoints")

        lats = [float(tp.get("lat", 0)) for tp in trackpoints]
        lons = [float(tp.get("lon", 0)) for tp in trackpoints]

        eles: list[float | None] = []
        for tp in trackpoints:
            ele_el = tp.find("g:ele", ns)
            eles.append(float(ele_el.text) if ele_el is not None and ele_el.text is not None else None)

        times: list[datetime] = []
        for tp in trackpoints:
            time_el = tp.find("g:time", ns)
            if time_el is not None:
                if time_el.text is not None:
                    times.append(datetime.fromisoformat(time_el.text.replace("Z", "+00:00")))

        if len(times) < 2:
            raise ValueError(
                "GPX file contains no trackpoint timestamps — cannot determine duration"
            )

        activity_date: date = times[0].date()
        duration_seconds = int((times[-1] - times[0]).total_seconds())

        distance_km = sum(
            _haversine_km(lats[i], lons[i], lats[i + 1], lons[i + 1]) for i in range(len(lats) - 1)
        )

        avg_pace = (duration_seconds / distance_km) if distance_km > 0 else None

        valid_eles = [e for e in eles if e is not None]
        elevation_gain_m: float | None = None
        if len(valid_eles) >= 2:
            elevation_gain_m = sum(
                max(0.0, valid_eles[i + 1] - valid_eles[i]) for i in range(len(valid_eles) - 1)
            )

        return {
            "activity_date": activity_date,
            "distance_km": distance_km if distance_km > 0 else None,
            "duration_seconds": duration_seconds,
            "avg_pace_sec_per_km": avg_pace,
            "elevation_gain_m": elevation_gain_m,
        }
