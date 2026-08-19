"""Push an approved week into the athlete's "Resilio Training" calendar.

Idempotent by construction: every workout slot maps to at most one Google
event, the event body is fingerprinted so an unchanged re-push writes nothing,
and a slot that disappeared from the week has its event deleted — but only
inside the pushed week's date range, so other weeks are never touched.
"""
from __future__ import annotations

import json
import logging
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...db.models import AthleteModel, CalendarEventModel, GoogleCalendarCredentialModel
from .client import GoogleCalendarClient, GoogleCalendarNotFoundError
from .event_builder import (
    CALENDAR_NAME,
    DEFAULT_TIMEZONE,
    InvalidSlotError,
    build_event,
    content_hash,
    slot_date,
)
from .oauth_service import GoogleCalendarNotConnectedError, token_provider

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SyncReport:
    created: int = 0
    updated: int = 0
    deleted: int = 0
    unchanged: int = 0
    skipped: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "created": self.created,
            "updated": self.updated,
            "deleted": self.deleted,
            "unchanged": self.unchanged,
            "skipped": self.skipped,
        }


class CalendarSyncService:
    """Reconcile one week of planned slots against Google Calendar."""

    def __init__(
        self,
        db: Session,
        *,
        client: GoogleCalendarClient | None = None,
    ) -> None:
        self._db = db
        self._client = client

    # ─── Calendar ────────────────────────────────────────────────────────────

    def ensure_calendar(self, athlete_id: str) -> str:
        """Return the id of the athlete's Resilio calendar, creating it if needed.

        Recreates the calendar when it was deleted upstream, so a stale id never
        blocks a push.
        """
        row = self._credential(athlete_id)
        client = self._client_for(athlete_id)

        if row.calendar_id:
            try:
                client.get_calendar(row.calendar_id)
                return row.calendar_id
            except GoogleCalendarNotFoundError:
                logger.info("gcal_calendar_missing_recreating")
                self._forget_events(athlete_id)

        athlete = self._db.get(AthleteModel, athlete_id)
        time_zone = getattr(athlete, "timezone", None) or DEFAULT_TIMEZONE
        created = client.create_calendar(CALENDAR_NAME, time_zone)
        calendar_id = str(created.get("id") or "")
        if not calendar_id:
            raise GoogleCalendarNotConnectedError(athlete_id)
        row.calendar_id = calendar_id
        self._db.commit()
        return calendar_id

    # ─── Push ────────────────────────────────────────────────────────────────

    def push_week(
        self,
        athlete_id: str,
        plan: Mapping[str, Any] | None,
    ) -> SyncReport:
        """Write the week's sessions, updating and pruning instead of duplicating."""
        sessions = _sessions_of(plan)
        athlete = self._db.get(AthleteModel, athlete_id)
        if athlete is None:
            raise ValueError(f"Athlete {athlete_id!r} not found")

        time_zone = getattr(athlete, "timezone", None) or DEFAULT_TIMEZONE
        preferences = _preferences_of(athlete)
        rationale = _rationale_of(plan)

        calendar_id = self.ensure_calendar(athlete_id)
        client = self._client_for(athlete_id)

        existing = {
            row.slot_id: row
            for row in self._db.scalars(
                select(CalendarEventModel).where(
                    CalendarEventModel.athlete_id == athlete_id
                )
            ).all()
        }

        created = updated = unchanged = skipped = 0
        seen: set[str] = set()
        dates: list[date] = []

        for session in sessions:
            slot_id = str(session.get("id") or "")
            if not slot_id:
                skipped += 1
                continue
            try:
                day = slot_date(session)
                body = build_event(
                    session,
                    timezone_name=time_zone,
                    preferences=preferences,
                    rationale=rationale,
                )
            except InvalidSlotError:
                logger.warning("gcal_slot_unplaceable", extra={"slot_id": slot_id})
                skipped += 1
                continue

            dates.append(day)
            seen.add(slot_id)
            digest = content_hash(body)
            row = existing.get(slot_id)

            if row is None:
                event = client.insert_event(calendar_id, body)
                self._db.add(
                    CalendarEventModel(
                        id=str(uuid.uuid4()),
                        athlete_id=athlete_id,
                        slot_id=slot_id,
                        slot_date=day,
                        gcal_event_id=str(event.get("id") or ""),
                        content_hash=digest,
                    )
                )
                created += 1
                continue

            if row.content_hash == digest:
                unchanged += 1
                continue

            try:
                client.patch_event(calendar_id, row.gcal_event_id, body)
            except GoogleCalendarNotFoundError:
                event = client.insert_event(calendar_id, body)
                row.gcal_event_id = str(event.get("id") or "")
            row.content_hash = digest
            row.slot_date = day
            row.updated_at = datetime.now(timezone.utc)
            updated += 1

        deleted = self._prune(
            athlete_id,
            calendar_id,
            client,
            existing,
            seen,
            dates,
        )

        self._touch_last_sync(athlete_id)
        self._db.commit()
        return SyncReport(
            created=created,
            updated=updated,
            deleted=deleted,
            unchanged=unchanged,
            skipped=skipped,
        )

    # ─── Internals ───────────────────────────────────────────────────────────

    def _prune(
        self,
        athlete_id: str,
        calendar_id: str,
        client: GoogleCalendarClient,
        existing: Mapping[str, CalendarEventModel],
        seen: set[str],
        dates: Sequence[date],
    ) -> int:
        """Delete events for slots dropped from *this* week, never other weeks."""
        if not dates:
            return 0
        first, last = _week_window(dates)
        deleted = 0
        for slot_id, row in existing.items():
            if slot_id in seen:
                continue
            if not (first <= row.slot_date <= last):
                continue
            client.delete_event(calendar_id, row.gcal_event_id)
            self._db.delete(row)
            deleted += 1
        return deleted

    def _credential(self, athlete_id: str) -> GoogleCalendarCredentialModel:
        row = self._db.get(GoogleCalendarCredentialModel, athlete_id)
        if row is None or row.refresh_token_enc is None:
            raise GoogleCalendarNotConnectedError(athlete_id)
        return row

    def _client_for(self, athlete_id: str) -> GoogleCalendarClient:
        if self._client is None:
            self._client = GoogleCalendarClient(token_provider(athlete_id, self._db))
        return self._client

    def _forget_events(self, athlete_id: str) -> None:
        for row in self._db.scalars(
            select(CalendarEventModel).where(
                CalendarEventModel.athlete_id == athlete_id
            )
        ).all():
            self._db.delete(row)
        self._db.commit()

    def _touch_last_sync(self, athlete_id: str) -> None:
        row = self._db.get(GoogleCalendarCredentialModel, athlete_id)
        if row is not None:
            row.last_sync_at = datetime.now(timezone.utc)


def push_week_for_athlete(
    athlete_id: str,
    plan: Mapping[str, Any],
    db: Session,
) -> Mapping[str, int]:
    """Calendar seam used by the approval flow — returns the sync counts."""
    report = CalendarSyncService(db).push_week(athlete_id, plan)
    return report.as_dict()


def _week_window(dates: Sequence[date]) -> tuple[date, date]:
    """Full calendar weeks covered by the pushed plan.

    Pruning against the surviving slots' own min/max would let a dropped
    Saturday session survive whenever the shrunken week ends on Wednesday, so
    the window is widened to the Monday-Sunday weeks the plan sits in.
    """
    first, last = min(dates), max(dates)
    week_start = first - timedelta(days=first.weekday())
    week_end = last + timedelta(days=6 - last.weekday())
    return week_start, week_end


def _sessions_of(plan: Mapping[str, Any] | None) -> list[Mapping[str, Any]]:
    if not isinstance(plan, Mapping):
        return []
    sessions = plan.get("sessions")
    if not isinstance(sessions, Sequence):
        return []
    return [s for s in sessions if isinstance(s, Mapping)]


def _preferences_of(athlete: AthleteModel) -> Mapping[str, Any]:
    raw = getattr(athlete, "preferred_session_hour_json", None)
    try:
        value = json.loads(raw or "{}")
    except (TypeError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _rationale_of(plan: Mapping[str, Any] | None) -> str:
    if not isinstance(plan, Mapping):
        return ""
    notes = plan.get("notes")
    if isinstance(notes, str):
        return notes
    if isinstance(notes, Sequence):
        return " ".join(str(n) for n in notes if str(n).strip())
    return ""
