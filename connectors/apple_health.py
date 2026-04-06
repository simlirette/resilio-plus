"""
Apple Health connector — JSON structuré → FatigueSnapshot.
Upsert sur (athlete_id, snapshot_date) — un seul snapshot par athlète par jour.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import FatigueSnapshot

# Champs scalaires Apple Health → FatigueSnapshot
_FIELD_MAP: dict[str, type] = {
    "hrv_rmssd": float,
    "hr_rest": int,
    "sleep_hours": float,
    "sleep_quality_subjective": int,
}


class AppleHealthConnector:
    async def ingest_snapshot(
        self,
        athlete_id: uuid.UUID,
        data: dict,
        db: AsyncSession,
    ) -> FatigueSnapshot:
        """
        Parse les données Apple Health et upsert un FatigueSnapshot.
        Seuls les champs présents et non-None dans `data` sont mis à jour.
        """
        snapshot_date_raw = data.get("snapshot_date")
        if snapshot_date_raw is None:
            raise ValueError("snapshot_date is required")

        if isinstance(snapshot_date_raw, str):
            snapshot_date = date.fromisoformat(snapshot_date_raw)
        elif isinstance(snapshot_date_raw, datetime):
            snapshot_date = snapshot_date_raw.date()
        else:
            snapshot_date = snapshot_date_raw  # assume date object

        # Base values required for INSERT (fatigue_by_muscle is NOT NULL in DB)
        insert_values: dict = {
            "athlete_id": athlete_id,
            "snapshot_date": snapshot_date,
            "fatigue_by_muscle": {},
        }

        # Add only provided non-None Apple Health fields
        for field, cast in _FIELD_MAP.items():
            if field in data and data[field] is not None:
                insert_values[field] = cast(data[field])

        # On conflict: update only the Apple Health fields (not athlete_id,
        # snapshot_date, or fatigue_by_muscle — preserve ACWR calculations)
        update_set = {
            k: v for k, v in insert_values.items()
            if k not in ("athlete_id", "snapshot_date", "fatigue_by_muscle")
        }

        stmt = (
            pg_insert(FatigueSnapshot)
            .values(**insert_values)
            .on_conflict_do_update(
                index_elements=["athlete_id", "snapshot_date"],
                set_=update_set,
            )
        )
        await db.execute(stmt)
        await db.flush()

        result = await db.execute(
            select(FatigueSnapshot).where(
                FatigueSnapshot.athlete_id == athlete_id,
                FatigueSnapshot.snapshot_date == snapshot_date,
            )
        )
        return result.scalar_one()
