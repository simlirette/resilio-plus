"""
Hevy connector — validation de clé API + ingestion workouts.
Classes de service pures — aucune dépendance FastAPI.
"""

import uuid
from datetime import UTC, datetime

import httpx
from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import LiftingSession, LiftingSet, SetType


class HevyConnector:
    BASE_URL = "https://api.hevyapp.com"

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._transport = transport

    def _client(self) -> httpx.AsyncClient:
        """Crée un AsyncClient — transport injectable pour les tests."""
        return httpx.AsyncClient(transport=self._transport)

    async def validate_api_key(self, api_key: str) -> bool:
        """GET /v1/workouts?page=1&pageSize=1 — 200 = valide, sinon invalide."""
        async with self._client() as client:
            resp = await client.get(
                f"{self.BASE_URL}/v1/workouts",
                headers={"api-key": api_key},
                params={"page": 1, "pageSize": 1},
            )
            return resp.status_code == 200

    async def fetch_workouts(
        self, api_key: str, page: int = 1, page_size: int = 10
    ) -> list[dict]:
        """GET /v1/workouts — retourne les workouts paginés."""
        async with self._client() as client:
            resp = await client.get(
                f"{self.BASE_URL}/v1/workouts",
                headers={"api-key": api_key},
                params={"page": page, "pageSize": page_size},
            )
            resp.raise_for_status()
            return list(resp.json().get("workouts", []))

    async def fetch_all_since(self, api_key: str, since: datetime) -> list[dict]:
        """Pagine jusqu'à ce que updated_at < since ou page vide."""
        since_utc = since if since.tzinfo is not None else since.replace(tzinfo=UTC)
        all_workouts: list[dict] = []
        page = 1
        while True:
            workouts = await self.fetch_workouts(api_key=api_key, page=page, page_size=10)
            if not workouts:
                break
            done = False
            for w in workouts:
                updated_at_str = w.get("updated_at", "")
                if updated_at_str:
                    updated_at = datetime.fromisoformat(
                        updated_at_str.replace("Z", "+00:00")
                    )
                    if updated_at < since_utc:
                        done = True
                        break
                all_workouts.append(w)
            if done:
                break
            page += 1
        return all_workouts

    async def ingest_workouts(
        self, athlete_id: uuid.UUID, workouts: list[dict], db: AsyncSession
    ) -> int:
        """Convertit et upsert les workouts dans lifting_sessions + lifting_sets."""
        count = 0
        for w in workouts:
            start_dt = (
                datetime.fromisoformat(w["start_time"].replace("Z", "+00:00"))
                if w.get("start_time")
                else None
            )
            end_dt = (
                datetime.fromisoformat(w["end_time"].replace("Z", "+00:00"))
                if w.get("end_time")
                else None
            )

            duration_minutes = None
            if start_dt and end_dt:
                duration_minutes = int((end_dt - start_dt).total_seconds() / 60)

            exercises = w.get("exercises", [])
            all_sets = [s for ex in exercises for s in ex.get("sets", [])]

            total_sets = len(all_sets)
            total_volume_kg = sum(
                (
                    s.get("weight_kg")
                    if s.get("weight_kg") is not None
                    else (s.get("weight_lbs", 0) * 0.453592)
                )
                * (s.get("reps") or 0)
                for s in all_sets
            )

            session_values: dict = {
                "athlete_id": athlete_id,
                "hevy_workout_id": str(w["id"]),
                "hevy_title": w.get("title", ""),
                "session_date": start_dt.date() if start_dt else None,
                "start_time": start_dt,
                "end_time": end_dt,
                "duration_minutes": duration_minutes,
                "source": "hevy_api",
                "total_volume_kg": total_volume_kg,
                "total_sets": total_sets,
            }
            update_set = {
                k: v for k, v in session_values.items()
                if k not in ("hevy_workout_id", "athlete_id")
            }

            # Upsert LiftingSession sur hevy_workout_id
            stmt = (
                pg_insert(LiftingSession)
                .values(**session_values)
                .on_conflict_do_update(
                    index_elements=["hevy_workout_id"],
                    set_=update_set,
                )
                .returning(LiftingSession.id)
            )
            result = await db.execute(stmt)
            session_id = result.scalar_one()

            # Supprime et recrée les sets (garantit la cohérence après upsert)
            await db.execute(
                delete(LiftingSet).where(LiftingSet.session_id == session_id)
            )

            for ex in exercises:
                for i, s in enumerate(ex.get("sets", [])):
                    weight_kg = s.get("weight_kg")
                    if weight_kg is None and s.get("weight_lbs") is not None:
                        weight_kg = s["weight_lbs"] * 0.453592

                    set_type_str = s.get("type", "normal")
                    try:
                        set_type = SetType(set_type_str)
                    except ValueError:
                        set_type = SetType.normal

                    db.add(
                        LiftingSet(
                            session_id=session_id,
                            exercise_title=ex.get("title", ""),
                            set_index=i,
                            set_type=set_type,
                            weight_kg=weight_kg,
                            reps=s.get("reps"),
                            rpe=s.get("rpe"),
                        )
                    )

            count += 1

        await db.flush()
        return count
