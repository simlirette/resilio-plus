# backend/app/core/energy_patterns.py
"""Energy pattern detection — pure functions + DB scanner.

Extracted from sync_scheduler.py. Detects 4 patterns from energy snapshots
and creates proactive Head Coach messages.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from ..db.models import EnergySnapshotModel, HeadCoachMessageModel


def _last_7_days(snapshots: list[EnergySnapshotModel]) -> list[EnergySnapshotModel]:
    """Filter snapshots to those within the last 7 days."""
    cutoff_aware = datetime.now(timezone.utc) - timedelta(days=7)
    cutoff_naive = cutoff_aware.replace(tzinfo=None)

    def _within_7d(snap: EnergySnapshotModel) -> bool:
        ts: datetime = snap.timestamp
        if ts.tzinfo is None:
            return bool(ts >= cutoff_naive)
        return bool(ts >= cutoff_aware)

    return [s for s in snapshots if _within_7d(s)]


def detect_heavy_legs(snapshots: list[EnergySnapshotModel]) -> bool:
    """Pattern 1: legs_feeling heavy/dead on >=3 of last 7 days."""
    recent = _last_7_days(snapshots)
    count = sum(1 for s in recent if s.legs_feeling in ("heavy", "dead"))
    return count >= 3


def detect_chronic_stress(snapshots: list[EnergySnapshotModel]) -> bool:
    """Pattern 2: stress_level == 'significant' on >=4 of last 7 days."""
    recent = _last_7_days(snapshots)
    count = sum(1 for s in recent if s.stress_level == "significant")
    return count >= 4


def detect_persistent_divergence(snapshots: list[EnergySnapshotModel]) -> bool:
    """Pattern 3: divergence >30 pts for >=3 consecutive days."""
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
            consecutive = 0
    return False


def detect_reds_signal(snapshots: list[EnergySnapshotModel]) -> bool:
    """Pattern 4: energy_availability < 30.0 on >=3 of last 7 days."""
    recent = _last_7_days(snapshots)
    count = sum(1 for s in recent if float(s.energy_availability) < 30.0)
    return count >= 3


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


def _has_recent_message(athlete_id: str, pattern_type: str, db: Session) -> bool:
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


def _maybe_create_message(athlete_id: str, pattern_type: str, db: Session) -> bool:
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


def detect_energy_patterns(db: Session) -> dict[str, Any]:
    """Scan all athletes' energy snapshots, detect 4 patterns, store messages.

    Returns: {"athletes_scanned": N, "messages_created": M}
    """
    from ..db.models import AthleteModel

    athletes = db.query(AthleteModel).all()
    athletes_scanned = 0
    messages_created = 0

    for athlete in athletes:
        athletes_scanned += 1
        snaps = (
            db.query(EnergySnapshotModel).filter(EnergySnapshotModel.athlete_id == athlete.id).all()
        )
        if not snaps:
            continue

        pattern_checks = [
            ("heavy_legs", detect_heavy_legs(snaps)),
            ("chronic_stress", detect_chronic_stress(snaps)),
            ("persistent_divergence", detect_persistent_divergence(snaps)),
            ("reds_signal", detect_reds_signal(snaps)),
        ]
        for pattern_type, triggered in pattern_checks:
            if triggered:
                created = _maybe_create_message(athlete.id, pattern_type, db)
                if created:
                    messages_created += 1

    db.commit()
    return {"athletes_scanned": athletes_scanned, "messages_created": messages_created}
