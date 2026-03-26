from datetime import date

from app.connectors.base import BaseConnector
from app.schemas.connector import ConnectorCredential, TerraHealthData

TERRA_BASE = "https://api.tryterra.co/v2"


def _parse_daily(data: dict, query_date: date) -> TerraHealthData:
    items = data.get("data", [])
    if not items:
        return TerraHealthData(
            date=query_date,
            hrv_rmssd=None,
            sleep_duration_hours=None,
            sleep_score=None,
            steps=None,
            active_energy_kcal=None,
        )
    item = items[0]

    # HRV RMSSD — deeply nested; absent at any level → None
    hrv_rmssd = None
    hr_data = item.get("heart_rate_data", {})
    hrv_data = hr_data.get("summary", {}).get("hrv_rmssd_data", [])
    if hrv_data:
        hrv_rmssd = hrv_data[0].get("hrv_rmssd")

    # Sleep
    sleep_secs = item.get("sleep_durations_data", {}).get("total_sleep_time")
    sleep_hours = round(sleep_secs / 3600, 2) if sleep_secs else None

    # Movement
    movement = item.get("daily_movement", {})
    steps = movement.get("steps")
    active_kcal = movement.get("active_energy_burned_cal")

    sleep_score = item.get("sleep_score")

    return TerraHealthData(
        date=query_date,
        hrv_rmssd=hrv_rmssd,
        sleep_duration_hours=sleep_hours,
        sleep_score=sleep_score,
        steps=steps,
        active_energy_kcal=active_kcal,
    )


class TerraConnector(BaseConnector):
    provider = "terra"

    def _do_refresh_token(self) -> ConnectorCredential:
        return self.credential  # API Key never expires

    def _headers(self) -> dict:
        return {
            "x-api-key": self.client_id,    # TERRA_API_KEY
            "dev-id": self.client_secret,    # TERRA_DEV_ID
        }

    def fetch_daily(self, query_date: date) -> TerraHealthData:
        terra_user_id = self.credential.extra.get("terra_user_id", "")
        data = self._request(
            "GET",
            f"{TERRA_BASE}/daily",
            headers=self._headers(),
            params={
                "user_id": terra_user_id,
                "start_date": query_date.isoformat(),
                "end_date": query_date.isoformat(),
                "to_webhook": "false",
            },
        )
        return _parse_daily(data, query_date)
