"""Map StravaActivity schema objects to StravaActivityModel DB rows."""
import json
from datetime import datetime, timezone

from ...db.models import StravaActivityModel
from ...schemas.connector import StravaActivity

SPORT_MAP: dict[str, str] = {
    "Run": "running",
    "TrailRun": "running",
    "VirtualRun": "running",
    "Ride": "biking",
    "VirtualRide": "biking",
    "EBikeRide": "biking",
    "Swim": "swimming",
}


def to_model(activity: StravaActivity, athlete_id: str) -> StravaActivityModel:
    """Convert a StravaActivity (connector schema) to a StravaActivityModel (DB row).

    `activity.id` has format "strava_{int}" — strava_id is the integer part.
    sport_type is mapped via SPORT_MAP; unrecognized types are lowercased.
    """
    sport = SPORT_MAP.get(activity.sport_type, activity.sport_type.lower())
    strava_id = int(activity.id.replace("strava_", ""))

    # Convert date → datetime at midnight UTC for started_at
    started_at = datetime(
        activity.date.year,
        activity.date.month,
        activity.date.day,
        tzinfo=timezone.utc,
    )

    raw = {
        "id": strava_id,
        "name": activity.name,
        "sport_type": activity.sport_type,
        "date": activity.date.isoformat(),
        "duration_seconds": activity.duration_seconds,
        "distance_meters": activity.distance_meters,
        "elevation_gain_meters": activity.elevation_gain_meters,
        "average_hr": activity.average_hr,
        "max_hr": activity.max_hr,
        "avg_watts": activity.avg_watts,
        "perceived_exertion": activity.perceived_exertion,
    }

    return StravaActivityModel(
        id=activity.id,
        athlete_id=athlete_id,
        strava_id=strava_id,
        sport_type=sport,
        name=activity.name,
        started_at=started_at,
        duration_s=activity.duration_seconds,
        distance_m=activity.distance_meters,
        elevation_m=activity.elevation_gain_meters,
        avg_hr=int(activity.average_hr) if activity.average_hr is not None else None,
        max_hr=int(activity.max_hr) if activity.max_hr is not None else None,
        avg_watts=activity.avg_watts,
        perceived_exertion=float(activity.perceived_exertion)
        if activity.perceived_exertion is not None
        else None,
        raw_json=json.dumps(raw),
    )
