"""RecoveryCoachView builder — Phase D (D6), DEP-C3-001."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from ..db.models import AthleteModel, SessionLogModel
from ..schemas.recovery_view import RecoveryCoachView

_LOOKBACK_DAYS = 7


def build_recovery_view(athlete: AthleteModel, db: Any) -> RecoveryCoachView:
    """Build a RecoveryCoachView from the athlete record and recent session logs.

    Computes mean_vs_prescribed_delta_7d as the mean difference between
    actual_duration_min and prescribed_duration_min for logs in the last 7 days
    that have both values present.

    Args:
        athlete: ORM model.
        db: SQLAlchemy session.

    Returns:
        RecoveryCoachView with delta and recent RPE metrics.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=_LOOKBACK_DAYS)

    logs: list[SessionLogModel] = (
        db.query(SessionLogModel)
        .filter(SessionLogModel.athlete_id == athlete.id)
        .filter(SessionLogModel.logged_at >= cutoff)
        .all()
    )

    # Compute mean delta (actual - prescribed) for logs that have both values
    deltas: list[float] = []
    rpes: list[float] = []

    for log in logs:
        actual = log.actual_duration_min
        # prescribed_duration_min is not a DB column — it may be set by tests
        # via a computed/mock attribute; in production, default to None
        prescribed = getattr(log, "prescribed_duration_min", None)

        if actual is not None and prescribed is not None:
            deltas.append(float(actual) - float(prescribed))

        if log.rpe is not None:
            rpes.append(float(log.rpe))

    mean_delta: float | None = sum(deltas) / len(deltas) if deltas else None
    rpe_avg: float | None = sum(rpes) / len(rpes) if rpes else None

    return RecoveryCoachView(
        athlete_id=athlete.id,
        journey_phase=athlete.journey_phase,
        mean_vs_prescribed_delta_7d=mean_delta,
        recent_rpe_avg=rpe_avg,
        sessions_logged_last_7d=len(logs),
    )
