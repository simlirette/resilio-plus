import time
from datetime import date

from ..connectors.base import BaseConnector
from ..schemas.connector import ConnectorCredential, FatSecretDay, FatSecretMeal

FATSECRET_API_URL = "https://platform.fatsecret.com/rest/server.api"
FATSECRET_TOKEN_URL = "https://oauth.fatsecret.com/connect/token"
_EPOCH = date(1970, 1, 1)


def _to_date_int(d: date) -> int:
    return (d - _EPOCH).days


def _parse_day(data: dict, query_date: date) -> FatSecretDay:
    entries_data = data.get("food_entries", {})
    raw_entries = entries_data.get("food_entry", [])
    # FatSecret returns a dict (not list) when there is only one entry
    if isinstance(raw_entries, dict):
        raw_entries = [raw_entries]

    meals: list[FatSecretMeal] = []
    total_cal = total_carbs = total_protein = total_fat = 0.0

    for entry in raw_entries:
        meal_name = entry.get("meal", "other").title()
        cal = float(entry.get("calories", 0))
        carbs = float(entry.get("carbohydrate", 0))
        protein = float(entry.get("protein", 0))
        fat = float(entry.get("fat", 0))
        meals.append(
            FatSecretMeal(
                name=meal_name,
                calories=cal,
                carbs_g=carbs,
                protein_g=protein,
                fat_g=fat,
            )
        )
        total_cal += cal
        total_carbs += carbs
        total_protein += protein
        total_fat += fat

    return FatSecretDay(
        date=query_date,
        calories_total=total_cal,
        carbs_g=total_carbs,
        protein_g=total_protein,
        fat_g=total_fat,
        meals=meals,
    )


class FatSecretConnector(BaseConnector):
    provider = "fatsecret"

    def _do_refresh_token(self) -> ConnectorCredential:
        response = self._client.post(
            FATSECRET_TOKEN_URL,
            data={"grant_type": "client_credentials", "scope": "basic"},
            auth=(self.client_id, self.client_secret),
        )
        response.raise_for_status()
        data = response.json()
        return self.credential.model_copy(
            update={
                "access_token": data["access_token"],
                "expires_at": int(time.time()) + data.get("expires_in", 86400),
            }
        )

    def fetch_food_entries(self, query_date: date) -> FatSecretDay:
        token = self.get_valid_token()
        data = self._request(
            "GET",
            FATSECRET_API_URL,
            headers={"Authorization": f"Bearer {token}"},
            params={
                "method": "food_entries.get",
                "date": _to_date_int(query_date),
                "format": "json",
            },
        )
        return _parse_day(data, query_date)
