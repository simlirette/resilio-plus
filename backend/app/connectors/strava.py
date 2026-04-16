import os
from datetime import date, datetime
from typing import Any
from urllib.parse import quote, urlencode

from ..connectors.base import BaseConnector, ConnectorAPIError
from ..schemas.connector import ConnectorCredential, StravaActivity, StravaLap

STRAVA_BASE = "https://www.strava.com/api/v3"
STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"
STRAVA_AUTH_URL = "https://www.strava.com/oauth/authorize"
STRAVA_SCOPE = "activity:read_all,profile:read_all"
PAGE_SIZE = 200


def _speed_to_pace_per_km(speed_mps: float | None) -> str | None:
    if not speed_mps or speed_mps <= 0:
        return None
    total_secs = 1000 / speed_mps
    mins = int(total_secs // 60)
    secs = int(total_secs % 60)
    return f"{mins}:{secs:02d}"


def _parse_activity(item: dict[str, Any]) -> StravaActivity:
    raw_date = item["start_date_local"][:10]  # "YYYY-MM-DD"
    return StravaActivity(
        id=f"strava_{item['id']}",
        name=item["name"],
        sport_type=item.get("sport_type") or item.get("type", "Unknown"),
        date=date.fromisoformat(raw_date),
        duration_seconds=item["elapsed_time"],
        distance_meters=item.get("distance"),
        elevation_gain_meters=item.get("total_elevation_gain"),
        average_hr=item.get("average_heartrate"),
        max_hr=item.get("max_heartrate"),
        perceived_exertion=item.get("perceived_exertion"),
    )


def _parse_lap(item: dict[str, Any]) -> StravaLap:
    return StravaLap(
        lap_index=item["lap_index"],
        elapsed_time_seconds=item["elapsed_time"],
        distance_meters=item["distance"],
        average_hr=item.get("average_heartrate"),
        pace_per_km=_speed_to_pace_per_km(item.get("average_speed")),
    )


class StravaConnector(BaseConnector):
    provider = "strava"

    def get_auth_url(self) -> str:
        redirect_uri = os.getenv(
            "STRAVA_REDIRECT_URI",
            "http://localhost:8000/auth/strava/callback",
        )
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "approval_prompt": "force",
            "scope": STRAVA_SCOPE,
        }
        return f"{STRAVA_AUTH_URL}?{urlencode(params, quote_via=quote, safe=':,')}"

    def exchange_code(self, code: str) -> ConnectorCredential:
        response = self._client.post(
            STRAVA_TOKEN_URL,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": code,
                "grant_type": "authorization_code",
            },
        )
        response.raise_for_status()
        data = response.json()
        return self.credential.model_copy(
            update={
                "access_token": data["access_token"],
                "refresh_token": data["refresh_token"],
                "expires_at": data["expires_at"],
            }
        )

    def _do_refresh_token(self) -> ConnectorCredential:
        response = self._client.post(
            STRAVA_TOKEN_URL,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self.credential.refresh_token,
                "grant_type": "refresh_token",
            },
        )
        response.raise_for_status()
        data = response.json()
        return self.credential.model_copy(
            update={
                "access_token": data["access_token"],
                "refresh_token": data["refresh_token"],
                "expires_at": data["expires_at"],
            }
        )

    def fetch_activities(self, since: datetime, until: datetime) -> list[StravaActivity]:
        token = self.get_valid_token()
        headers = {"Authorization": f"Bearer {token}"}
        activities: list[StravaActivity] = []
        page = 1
        while True:
            data = self._request(
                "GET",
                f"{STRAVA_BASE}/athlete/activities",
                headers=headers,
                params={
                    "after": int(since.timestamp()),
                    "before": int(until.timestamp()),
                    "per_page": PAGE_SIZE,
                    "page": page,
                },
            )
            if not data:
                break
            for item in data:
                activities.append(_parse_activity(item))
            if len(data) < PAGE_SIZE:
                break
            page += 1
        return activities

    def fetch_activity_laps(self, activity_id: str) -> list[StravaLap]:
        token = self.get_valid_token()
        try:
            data = self._request(
                "GET",
                f"{STRAVA_BASE}/activities/{activity_id}/laps",
                headers={"Authorization": f"Bearer {token}"},
            )
        except ConnectorAPIError as e:
            if e.status_code == 404:
                return []
            raise
        return [_parse_lap(lap) for lap in data]
