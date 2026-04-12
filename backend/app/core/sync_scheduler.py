"""
Sync scheduler — APScheduler BackgroundScheduler.
Runs sync_all_strava, sync_all_hevy, sync_all_terra every 6 hours for all connected athletes.
Each function creates its own DB session (thread-safe, independent of request sessions).
Delegates all sync logic to SyncService.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler

from ..db.database import SessionLocal
from ..db.models import ConnectorCredentialModel
from ..models.schemas import EnergySnapshotModel, HeadCoachMessageModel
from ..services.sync_service import ConnectorNotFoundError, SyncService

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pattern detector helpers (pure functions — testable without DB)
# ---------------------------------------------------------------------------

def _last_7_days(snapshots: list) -> list:
    """Filter snapshots to those within the last 7 days.
    Handles both timezone-aware (PostgreSQL) and naive (SQLite) timestamps.
    """
    cutoff_aware = datetime.now(timezone.utc) - timedelta(days=7)
    cutoff_naive = cutoff_aware.replace(tzinfo=None)

    def _within_7d(snap) -> bool:
        ts = snap.timestamp
        if ts.tzinfo is None:
            return ts >= cutoff_naive
        return ts >= cutoff_aware

    return [s for s in snapshots if _within_7d(s)]


def _detect_heavy_legs(snapshots: list) -> bool:
    """Pattern 1: legs_feeling heavy/dead on >=3 of last 7 days."""
    recent = _last_7_days(snapshots)
    count = sum(1 for s in recent if s.legs_feeling in ("heavy", "dead"))
    return count >= 3


def _detect_chronic_stress(snapshots: list) -> bool:
    """Pattern 2: stress_level == 'significant' on >=4 of last 7 days."""
    recent = _last_7_days(snapshots)
    count = sum(1 for s in recent if s.stress_level == "significant")
    return count >= 4


def _detect_persistent_divergence(snapshots: list) -> bool:
    """Pattern 3: divergence >30 pts for >=3 consecutive days (most recent first)."""
    recent = sorted(_last_7_days(snapshots), key=lambda s: s.timestamp, reverse=True)
    consecutive = 0
    for snap in recent:
        obj = float(snap.objective_score) if snap.objective_score is not None else 50.0
        subj = float(snap.subjective_score) if snap.subjective_score is not None else 50.0
        if abs(obj - subj) > 30.0:
            consecutive += 1
            if consecutive >= 3:
                return True
        else:
            consecutive = 0  # streak broken
    return False


def _detect_reds_signal(snapshots: list) -> bool:
    """Pattern 4: energy_availability < 30.0 on >=3 of last 7 days (RED-S risk)."""
    recent = _last_7_days(snapshots)
    count = sum(1 for s in recent if float(s.energy_availability) < 30.0)
    return count >= 3


# ---------------------------------------------------------------------------
# detect_energy_patterns() — DB scanning + proactive message creation
# ---------------------------------------------------------------------------

_PATTERN_MESSAGES: dict[str, str] = {
    "heavy_legs": (
        "Tes jambes sont lourdes depuis 3 jours ou plus. "
        "Ton Head Coach recommande une seance de recuperation active ou un jour de repos complet."
    ),
    "chronic_stress": (
        "Ton niveau de stress est eleve depuis 4 jours ou plus. "
        "Ton Head Coach recommande de reduire l'intensite et de prioriser le sommeil."
    ),
    "persistent_divergence": (
        "Tes donnees objectives et subjectives divergent fortement depuis 3 jours consecutifs. "
        "Ton ressenti compte — ton Head Coach ajuste l'intensite a la baisse."
    ),
    "reds_signal": (
        "Ta disponibilite energetique est basse depuis 3 jours ou plus. "
        "Ton Head Coach recommande d'augmenter les apports caloriques et de reduire le volume."
    ),
}


def _has_recent_message(athlete_id: str, pattern_type: str, db) -> bool:
    """Return True if a message of this pattern_type was created in the last 7 days."""
    cutoff_aware = datetime.now(timezone.utc) - timedelta(days=7)
    cutoff_naive = cutoff_aware.replace(tzinfo=None)
    existing = (
        db.query(HeadCoachMessageModel)
        .filter(
            HeadCoachMessageModel.athlete_id == athlete_id,
            HeadCoachMessageModel.pattern_type == pattern_type,
        )
        .order_by(HeadCoachMessageModel.created_at.desc())
        .first()
    )
    if existing is None:
        return False
    ts = existing.created_at
    if ts.tzinfo is None:
        return ts >= cutoff_naive
    return ts >= cutoff_aware


def _maybe_create_message(athlete_id: str, pattern_type: str, db) -> bool:
    """Create a Head Coach message if no duplicate exists in last 7 days. Returns True if created."""
    if _has_recent_message(athlete_id, pattern_type, db):
        return False
    msg = HeadCoachMessageModel(
        id=str(uuid.uuid4()),
        athlete_id=athlete_id,
        pattern_type=pattern_type,
        message=_PATTERN_MESSAGES[pattern_type],
        created_at=datetime.now(timezone.utc),
        is_read=False,
    )
    db.add(msg)
    return True


def detect_energy_patterns(db) -> dict:
    """
    Scan all athletes' energy snapshots for the last 7 days.
    Detect 4 patterns and store proactive Head Coach messages.
    Called by the weekly APScheduler job (Mondays at 06:00).
    Returns summary dict: {"athletes_scanned": N, "messages_created": M}.
    """
    from ..db.models import AthleteModel

    athletes = db.query(AthleteModel).all()
    athletes_scanned = 0
    messages_created = 0

    for athlete in athletes:
        athletes_scanned += 1
        snaps = (
            db.query(EnergySnapshotModel)
            .filter(EnergySnapshotModel.athlete_id == athlete.id)
            .all()
        )
        if not snaps:
            continue

        pattern_checks = [
            ("heavy_legs", _detect_heavy_legs(snaps)),
            ("chronic_stress", _detect_chronic_stress(snaps)),
            ("persistent_divergence", _detect_persistent_divergence(snaps)),
            ("reds_signal", _detect_reds_signal(snaps)),
        ]
        for pattern_type, triggered in pattern_checks:
            if triggered:
                created = _maybe_create_message(athlete.id, pattern_type, db)
                if created:
                    messages_created += 1

    db.commit()
    return {"athletes_scanned": athletes_scanned, "messages_created": messages_created}


# ---------------------------------------------------------------------------
# Weekly job wrapper
# ---------------------------------------------------------------------------

def run_energy_patterns_weekly() -> None:
    """Weekly job: detect energy patterns for all athletes and store proactive messages."""
    with SessionLocal() as db:
        try:
            result = detect_energy_patterns(db)
            logger.info(
                "Energy patterns scan: athletes=%d messages_created=%d",
                result["athletes_scanned"], result["messages_created"],
            )
        except Exception:
            logger.warning("Energy patterns scan failed", exc_info=True)


# ---------------------------------------------------------------------------
# Existing sync jobs
# ---------------------------------------------------------------------------

def sync_all_strava() -> None:
    """Auto-sync Strava for all athletes with active Strava credentials."""
    with SessionLocal() as db:
        creds = db.query(ConnectorCredentialModel).filter_by(provider="strava").all()
        for cred_model in creds:
            try:
                result = SyncService.sync_strava(cred_model.athlete_id, db)
                logger.info(
                    "Strava sync OK: athlete=%s synced=%d skipped=%d",
                    cred_model.athlete_id, result["synced"], result.get("skipped", 0),
                )
            except ConnectorNotFoundError:
                pass
            except Exception:
                logger.warning(
                    "Strava sync failed: athlete=%s", cred_model.athlete_id, exc_info=True
                )


def sync_all_hevy() -> None:
    """Auto-sync Hevy for all athletes with active Hevy API key."""
    with SessionLocal() as db:
        creds = db.query(ConnectorCredentialModel).filter_by(provider="hevy").all()
        for cred_model in creds:
            try:
                result = SyncService.sync_hevy(cred_model.athlete_id, db)
                logger.info(
                    "Hevy sync OK: athlete=%s synced=%d skipped=%d",
                    cred_model.athlete_id, result["synced"], result.get("skipped", 0),
                )
            except ConnectorNotFoundError:
                pass
            except Exception:
                logger.warning(
                    "Hevy sync failed: athlete=%s", cred_model.athlete_id, exc_info=True
                )


def sync_all_terra() -> None:
    """Auto-sync Terra HRV/sleep for all athletes with active Terra credentials."""
    with SessionLocal() as db:
        creds = db.query(ConnectorCredentialModel).filter_by(provider="terra").all()
        for cred_model in creds:
            try:
                result = SyncService.sync_terra(cred_model.athlete_id, db)
                logger.info(
                    "Terra sync OK: athlete=%s hrv=%s sleep=%s",
                    cred_model.athlete_id, result["hrv_rmssd"], result["sleep_hours"],
                )
            except ConnectorNotFoundError:
                pass
            except Exception:
                logger.warning(
                    "Terra sync failed: athlete=%s", cred_model.athlete_id, exc_info=True
                )


def setup_scheduler() -> BackgroundScheduler:
    """Create, configure, and start the BackgroundScheduler."""
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        sync_all_strava, trigger="interval", hours=6,
        id="strava_sync", replace_existing=True, misfire_grace_time=300,
    )
    scheduler.add_job(
        sync_all_hevy, trigger="interval", hours=6,
        id="hevy_sync", replace_existing=True, misfire_grace_time=300,
    )
    scheduler.add_job(
        sync_all_terra, trigger="interval", hours=6,
        id="terra_sync", replace_existing=True, misfire_grace_time=300,
    )
    scheduler.add_job(
        run_energy_patterns_weekly,
        trigger="cron",
        day_of_week="mon",
        hour=6,
        minute=0,
        id="energy_patterns_weekly",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.start()
    return scheduler
