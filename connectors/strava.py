"""
Strava connector — OAuth2 flow + activity ingestion.
Classes de service pures — aucune dépendance FastAPI.
"""

import math
import uuid
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from models.database import ConnectorCredential, RunActivity


class StravaConnector:
    BASE_URL = "https://www.strava.com/api/v3"
    AUTH_URL = "https://www.strava.com/oauth/authorize"
    TOKEN_URL = "https://www.strava.com/oauth/token"

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.client_id = settings.STRAVA_CLIENT_ID
        self.client_secret = settings.STRAVA_CLIENT_SECRET
        self.redirect_uri = settings.STRAVA_REDIRECT_URI
        self._transport = transport

    def _client(self) -> httpx.AsyncClient:
        """Crée un AsyncClient — transport injectable pour les tests."""
        return httpx.AsyncClient(transport=self._transport)

    def get_authorization_url(self) -> str:
        """Génère l'URL OAuth Strava pour rediriger l'athlète."""
        params = (
            f"client_id={self.client_id}"
            f"&redirect_uri={self.redirect_uri}"
            f"&response_type=code"
            f"&approval_prompt=auto"
            f"&scope=activity:read_all"
        )
        return f"{self.AUTH_URL}?{params}"

    async def exchange_code(
        self, code: str, athlete_id: uuid.UUID, db: AsyncSession
    ) -> ConnectorCredential:
        """Échange le code d'autorisation contre des tokens. Stocke en DB via upsert."""
        async with self._client() as client:
            resp = await client.post(
                self.TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        return await self._upsert_strava_credential(
            athlete_id=athlete_id,
            db=db,
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            token_expires_at=datetime.fromtimestamp(data["expires_at"], tz=UTC),
            external_athlete_id=str(data["athlete"]["id"]),
        )

    async def _upsert_strava_credential(
        self,
        athlete_id: uuid.UUID,
        db: AsyncSession,
        access_token: str,
        refresh_token: str,
        token_expires_at: datetime,
        external_athlete_id: str,
    ) -> ConnectorCredential:
        """Insère ou met à jour le ConnectorCredential Strava."""
        update_set = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_expires_at": token_expires_at,
            "external_athlete_id": external_athlete_id,
        }
        stmt = (
            pg_insert(ConnectorCredential)
            .values(
                athlete_id=athlete_id,
                provider="strava",
                **update_set,
            )
            .on_conflict_do_update(
                index_elements=["athlete_id", "provider"],
                set_=update_set,
            )
        )
        await db.execute(stmt)
        await db.flush()
        result = await db.execute(
            select(ConnectorCredential).where(
                ConnectorCredential.athlete_id == athlete_id,
                ConnectorCredential.provider == "strava",
            )
        )
        return result.scalar_one()

    async def refresh_token_if_expired(
        self, cred: ConnectorCredential, db: AsyncSession
    ) -> ConnectorCredential:
        """Refresh si le token expire dans moins de 5 minutes."""
        if cred.token_expires_at is None:
            return cred
        threshold = datetime.now(tz=UTC) + timedelta(minutes=5)
        if cred.token_expires_at > threshold:
            return cred

        async with self._client() as client:
            resp = await client.post(
                self.TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": cred.refresh_token,
                    "grant_type": "refresh_token",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        cred.access_token = data["access_token"]
        cred.refresh_token = data["refresh_token"]
        cred.token_expires_at = datetime.fromtimestamp(data["expires_at"], tz=UTC)
        await db.flush()
        return cred

    async def fetch_activities(
        self, cred: ConnectorCredential, since: datetime, limit: int = 50
    ) -> list[dict]:
        """GET /athlete/activities depuis `since`. Retourne la liste brute."""
        async with self._client() as client:
            resp = await client.get(
                f"{self.BASE_URL}/athlete/activities",
                headers={"Authorization": f"Bearer {cred.access_token}"},
                params={"after": int(since.timestamp()), "per_page": limit},
            )
            resp.raise_for_status()
            return list(resp.json())

    async def ingest_activities(
        self, athlete_id: uuid.UUID, activities: list[dict], db: AsyncSession
    ) -> int:
        """Convertit et upsert les activités dans run_activities. Retourne le count ingéré."""
        count = 0
        for act in activities:
            if act.get("type") not in ("Run", "Ride", "Swim"):
                continue

            raw_distance = act.get("distance")
            # for TRIMP calc
            distance_km = (raw_distance / 1000) if raw_distance is not None else 0.0
            duration_s = act.get("elapsed_time") or 0  # for TRIMP calc
            avg_hr = act.get("average_heartrate")
            max_hr_val = act.get("max_heartrate")

            # TRIMP : HR-based si disponible, sinon distance-based
            if avg_hr and max_hr_val:
                ratio = avg_hr / max_hr_val
                trimp = (duration_s / 60) * ratio * math.exp(1.92 * ratio)
            else:
                trimp = distance_km * 1.0

            avg_speed = act.get("average_speed")  # m/s
            avg_pace = (1000 / avg_speed) if avg_speed else None  # sec/km

            start_date_str = act.get("start_date", "")
            activity_date = (
                datetime.fromisoformat(start_date_str.replace("Z", "+00:00")).date()
                if start_date_str
                else None
            )

            values: dict = {
                "athlete_id": athlete_id,
                "strava_activity_id": str(act["id"]),
                "activity_date": activity_date,
                "activity_type": act.get("type", "Run").lower(),
                "distance_km": (raw_distance / 1000) if raw_distance is not None else None,
                "duration_seconds": act.get("elapsed_time"),
                "avg_pace_sec_per_km": avg_pace,
                "avg_hr": int(avg_hr) if avg_hr else None,
                "max_hr": int(max_hr_val) if max_hr_val else None,
                "elevation_gain_m": act.get("total_elevation_gain"),
                "trimp": trimp,
                "strava_raw": act,
            }
            update_set = {
                k: v for k, v in values.items()
                if k not in ("strava_activity_id", "athlete_id")
            }
            stmt = (
                pg_insert(RunActivity)
                .values(**values)
                .on_conflict_do_update(
                    index_elements=["strava_activity_id"],
                    set_=update_set,
                )
            )
            await db.execute(stmt)
            count += 1

        await db.flush()
        return count
