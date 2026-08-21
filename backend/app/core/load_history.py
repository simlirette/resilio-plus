"""Daily training load history — the input ACWR needs and never received.

Every call site passed ``load_history=[]``, so :func:`app.core.acwr.compute_acwr`
had nothing to work with and reported 0.00 "undertrained" for every athlete
regardless of what they had actually done. This module reads what the
connectors already stored and turns it into the oldest-first daily series ACWR
expects.

The per-session formula is deliberately the same one
:mod:`app.core.strain` uses for cardio::

    load = duration_hours * (rpe / 10) ** 2 * 100

so strain and ACWR cannot drift into disagreeing about what a session cost.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

logger = logging.getLogger(__name__)

DEFAULT_RPE = 7.0
"""Used when a provider gives no perceived exertion — matches core.strain."""

DEFAULT_WINDOW_DAYS = 28
"""ACWR's chronic window; the acute 7-day EWMA is a subset of it."""


def session_load(duration_minutes: float, rpe: float | None) -> float:
    """Return one session's training load in arbitrary units.

    Intensity enters squared, so an hour at RPE 10 costs four times an hour at
    RPE 5 rather than twice.
    """
    if duration_minutes <= 0:
        return 0.0
    hours = duration_minutes / 60.0
    intensity = (DEFAULT_RPE if rpe is None else float(rpe)) / 10.0
    return hours * intensity**2 * 100.0


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _athlete_zone(athlete_id: str, db: Any) -> ZoneInfo | None:
    """The athlete's timezone, or None when it cannot be read."""
    try:
        from ..db.models import AthleteModel

        athlete = db.get(AthleteModel, athlete_id)
        name = getattr(athlete, "timezone", None) if athlete is not None else None
        if name:
            return ZoneInfo(str(name))
    except (ZoneInfoNotFoundError, ValueError, KeyError, AttributeError):
        logger.warning("athlete_timezone_unreadable", extra={"athlete_id": athlete_id})
    except Exception:
        logger.warning(
            "athlete_timezone_lookup_failed",
            extra={"athlete_id": athlete_id},
            exc_info=True,
        )
    return None


def _athlete_today(athlete_id: str, db: Any) -> date:
    """Today as the athlete experiences it.

    The window used to end on the UTC date, which for an athlete in Montreal is
    a different day for four hours of every evening. During that window the
    series gains a day that has not happened yet and every session shifts one
    bucket further into the past, so ACWR falls with no change in training.
    Observed live: 1.54 "danger" in the afternoon, 0.59 "undertrained" the same
    evening.

    Falls back to UTC when the athlete, or their timezone, cannot be read -- a
    slightly wrong window beats no plan.
    """
    now = _utcnow()
    zone = _athlete_zone(athlete_id, db)
    return now.astimezone(zone).date() if zone is not None else now.date()


def daily_training_loads(
    athlete_id: str,
    db: Any,
    *,
    days: int = DEFAULT_WINDOW_DAYS,
    reference_date: date | None = None,
) -> list[float]:
    """Return oldest-first daily loads for the window ending on ``reference_date``.

    Always returns exactly ``days`` values — a day with no training is 0.0, not
    a gap — because ACWR's EWMA needs an evenly spaced series.

    Degrades to all zeros if the database cannot be read: a missing history
    should make the coach cautious, not crash the weekly cycle.
    """
    end = reference_date or _athlete_today(athlete_id, db)
    start = end - timedelta(days=days - 1)
    buckets = [0.0] * days

    try:
        zone = _athlete_zone(athlete_id, db)
        _add_strava_activities(athlete_id, db, start, buckets)
        _add_session_logs(athlete_id, db, start, buckets, zone)
    except Exception:
        logger.warning(
            "load_history_unavailable", extra={"athlete_id": athlete_id}, exc_info=True
        )
        return [0.0] * days

    return buckets


def _index_for(
    moment: datetime | date,
    start: date,
    days: int,
    zone: ZoneInfo | None = None,
) -> int | None:
    """Bucket one session, by the athlete's calendar day.

    A run stored at 22:00 UTC is the next morning in Tokyo and the same evening
    in Montreal. Bucketing on the UTC date puts it on a day the athlete did not
    train, while the window end has already moved on -- so the session lands
    outside the acute window entirely.
    """
    if isinstance(moment, datetime):
        if zone is not None:
            aware = (
                moment
                if moment.tzinfo is not None
                else moment.replace(tzinfo=timezone.utc)
            )
            day = aware.astimezone(zone).date()
        else:
            day = moment.date()
    else:
        day = moment
    offset = (day - start).days
    return offset if 0 <= offset < days else None


def _add_strava_activities(
    athlete_id: str,
    db: Any,
    start: date,
    buckets: list[float],
) -> None:
    from ..db.models import StravaActivityModel

    rows = (
        db.query(StravaActivityModel)
        .filter(StravaActivityModel.athlete_id == athlete_id)
        .all()
    )
    for row in rows:
        # No zone conversion, deliberately. The connector reads Strava's
        # `start_date_local` as a bare date and activity_mapper stores it at
        # midnight UTC, so `started_at` is a local date wearing a datetime
        # costume. Converting it westwards moves every session back a day.
        index = _index_for(row.started_at, start, len(buckets))
        if index is None:
            continue
        buckets[index] += session_load(
            (row.duration_s or 0) / 60.0, row.perceived_exertion
        )


def _add_session_logs(
    athlete_id: str,
    db: Any,
    start: date,
    buckets: list[float],
    zone: ZoneInfo | None = None,
) -> None:
    from ..db.models import SessionLogModel

    rows = (
        db.query(SessionLogModel)
        .filter(SessionLogModel.athlete_id == athlete_id)
        .all()
    )
    for row in rows:
        if row.skipped:
            continue
        # `logged_at` *is* a real instant, so it does convert.
        index = _index_for(row.logged_at, start, len(buckets), zone)
        if index is None:
            continue
        buckets[index] += session_load(float(row.actual_duration_min or 0), row.rpe)
