"""Upsert Apple Health daily summaries to DB.

Side effects:
- Creates/updates apple_health_daily rows (upsert by athlete_id + record_date)
- Updates AthleteModel.weight_kg when body_mass_kg is present and < 7 days old
- Creates/updates ConnectorCredentialModel for provider="apple_health" with latest snapshot

WARNING: NOT VALIDATED ON REAL DEVICE — tested with synthetic fixtures only.
"""
from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from ...db.models import AppleHealthDailyModel, AthleteModel, ConnectorCredentialModel
from .aggregator import AppleHealthDailySummary


def import_daily_summaries(
    athlete_id: str,
    summaries: dict[date, AppleHealthDailySummary],
    db: Session,
) -> dict[str, object]:
    """Upsert daily Apple Health summaries into apple_health_daily.

    Returns:
        dict with keys: days_imported, weight_updated, date_range
    """
    now = datetime.now(timezone.utc)
    cutoff_for_weight = (now - timedelta(days=7)).date()

    days_imported = 0
    weight_updated = False
    latest_date: date | None = None
    latest_summary: AppleHealthDailySummary | None = None

    for d, summary in sorted(summaries.items()):
        row = (
            db.query(AppleHealthDailyModel)
            .filter_by(athlete_id=athlete_id, record_date=d)
            .first()
        )
        if row is None:
            row = AppleHealthDailyModel(
                id=str(uuid.uuid4()),
                athlete_id=athlete_id,
                record_date=d,
            )
            db.add(row)

        row.hrv_sdnn_avg = summary.hrv_sdnn_avg
        row.sleep_hours = summary.sleep_hours
        row.rhr_bpm = summary.rhr_bpm
        row.body_mass_kg = summary.body_mass_kg
        row.active_energy_kcal = summary.active_energy_kcal
        row.imported_at = now
        days_imported += 1

        # Track latest for ConnectorCredential
        if latest_date is None or d > latest_date:
            latest_date = d
            latest_summary = summary

        # Update weight if measurement is recent (< 7 days old)
        if summary.body_mass_kg is not None and d >= cutoff_for_weight:
            athlete = db.get(AthleteModel, athlete_id)
            if athlete is not None:
                athlete.weight_kg = summary.body_mass_kg
                weight_updated = True

    # Update ConnectorCredential snapshot (backward compat with JSON upload endpoint)
    if latest_summary is not None and latest_date is not None:
        _update_connector_credential(athlete_id, latest_date, latest_summary, now, db)

    db.commit()

    dates = list(summaries.keys())
    return {
        "days_imported": days_imported,
        "weight_updated": weight_updated,
        "date_range": {
            "from": min(dates).isoformat() if dates else None,
            "to": max(dates).isoformat() if dates else None,
        },
    }


def _update_connector_credential(
    athlete_id: str,
    latest_date: date,
    latest: AppleHealthDailySummary,
    now: datetime,
    db: Session,
) -> None:
    extra = {
        "last_snapshot_date": latest_date.isoformat(),
        "last_hrv_sdnn": latest.hrv_sdnn_avg,
        "last_sleep_hours": latest.sleep_hours,
        "last_hr_rest": int(latest.rhr_bpm) if latest.rhr_bpm is not None else None,
        "last_upload": now.isoformat(),
    }
    row = (
        db.query(ConnectorCredentialModel)
        .filter_by(athlete_id=athlete_id, provider="apple_health")
        .first()
    )
    if row is not None:
        existing = json.loads(row.extra_json or "{}")
        existing.update(extra)
        row.extra_json = json.dumps(existing)
    else:
        db.add(
            ConnectorCredentialModel(
                id=str(uuid.uuid4()),
                athlete_id=athlete_id,
                provider="apple_health",
                extra_json=json.dumps(extra),
            )
        )
