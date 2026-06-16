"""
Google Calendar sync — plan → events mapping and upsert/diff orchestration.

Does NOT import Google libs directly; receives GoogleCalendarClient as dep.
Reads MasterPlan via api.plan.get_plan_weeks and pushes to a dedicated
"Resilio Training" Google Calendar.

Idempotence strategy:
- Every managed event carries extendedProperties.private.resilio_uid with a
  deterministic key: resilio-{date_iso}-{session_type}-w{week_number}
- On each sync: list remote managed events in window, compute desired events
  from plan, then insert/patch/delete to converge.
- Past events (before today) are never touched.

Event mapping (runs):
  easy / fartlek / strides  → 🏃 {type} {distance}km + pace
  tempo / intervals         → 🏃 {structured summary}
  long_run                  → 🏃 Long run {distance}km
  race                      → 🏁 Race {distance}km
  rest                      → 🛌 Rest  (all-day)

Event mapping (strength):
  legs / upper / chest_back / arms → 🏋️ {label}   "Voir Hevy pour le détail"
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from resilio.schemas.config import GoogleCalendarSettings
from resilio.schemas.plan import (
    StrengthSession,
    StrengthType,
    WeekPlan,
    WorkoutPrescription,
    WorkoutType,
)

logger = logging.getLogger(__name__)

# ============================================================
# CONSTANTS
# ============================================================

MANAGED_MARKER = "1"

STRENGTH_LABELS: dict[str, str] = {
    StrengthType.LEGS.value: "Leg day",
    StrengthType.UPPER.value: "Upper day",
    StrengthType.CHEST_BACK.value: "Chest/Back day",
    StrengthType.ARMS.value: "Arms day",
    StrengthType.CORE.value: "Core/Mobility",
    StrengthType.OTHER.value: "Gym",
}

WORKOUT_EMOJIS: dict[str, str] = {
    WorkoutType.EASY.value: "🏃",
    WorkoutType.LONG_RUN.value: "🏃",
    WorkoutType.TEMPO.value: "🏃",
    WorkoutType.INTERVALS.value: "🏃",
    WorkoutType.FARTLEK.value: "🏃",
    WorkoutType.STRIDES.value: "🏃",
    WorkoutType.RACE.value: "🏁",
    WorkoutType.REST.value: "🛌",
}

# ============================================================
# RESULT TYPES
# ============================================================


@dataclass
class SyncReport:
    inserted: int = 0
    patched: int = 0
    deleted: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"insert={self.inserted} patch={self.patched} "
            f"delete={self.deleted} skip={self.skipped} errors={len(self.errors)}"
        )


# ============================================================
# UID HELPERS
# ============================================================


def _resilio_uid(event_date: date, session_type: str, week_number: int) -> str:
    """Deterministic key stored in extendedProperties.private.resilio_uid."""
    return f"resilio-{event_date.isoformat()}-{session_type}-w{week_number}"


# ============================================================
# EVENT BUILDERS
# ============================================================


def _rfc3339(d: date, time_str: str, tz_offset: str = "-04:00") -> str:
    """Build RFC3339 datetime string from date + HH:MM + UTC offset."""
    h, m = time_str.split(":")
    return f"{d.isoformat()}T{int(h):02d}:{int(m):02d}:00{tz_offset}"


def _reminder_override(minutes: int) -> list[dict]:
    if minutes <= 0:
        return []
    return [{"method": "popup", "minutes": minutes}]


def _run_title(workout: WorkoutPrescription) -> str:
    wtype = getattr(workout.workout_type, "value", workout.workout_type)
    emoji = WORKOUT_EMOJIS.get(wtype, "🏃")

    if wtype == WorkoutType.REST.value:
        return "🛌 Rest"
    if wtype == WorkoutType.LONG_RUN.value:
        return f"🏃 Long run {workout.distance_km:.0f}km"
    if wtype == WorkoutType.RACE.value:
        return f"🏁 Race {workout.distance_km:.0f}km"

    # Quality: build summary from intervals if present
    if wtype in (WorkoutType.INTERVALS.value, WorkoutType.TEMPO.value):
        if workout.intervals:
            first = workout.intervals[0]
            reps = first.get("reps", "")
            dist = first.get("distance", "")
            if reps and dist:
                return f"{emoji} {reps}×{dist} {wtype}"
        return f"{emoji} {wtype.replace('_', ' ').title()} {workout.distance_km:.0f}km"

    return f"{emoji} {wtype.replace('_', ' ').title()} {workout.distance_km:.0f}km"


def _run_description(workout: WorkoutPrescription) -> str:
    parts: list[str] = []

    wtype = getattr(workout.workout_type, "value", workout.workout_type)
    if wtype == WorkoutType.REST.value:
        if workout.notes:
            parts.append(workout.notes)
        return "\n".join(parts)

    if workout.warmup_km and workout.warmup_km > 0:
        parts.append(f"WU: {workout.warmup_km:.1f}km easy")

    if workout.intervals:
        for iv in workout.intervals:
            reps = iv.get("reps", "")
            dist = iv.get("distance", "")
            pace = iv.get("pace", "")
            rec = iv.get("recovery", "")
            line = "  •"
            if reps and dist:
                line += f" {reps}×{dist}"
            elif dist:
                line += f" {dist}"
            if pace:
                line += f" @ {pace}"
            if rec:
                line += f" — rec {rec}"
            parts.append(line)
    elif workout.pace_range:
        parts.append(f"Pace: {workout.pace_range}/km")

    if workout.cooldown_km and workout.cooldown_km > 0:
        parts.append(f"CD: {workout.cooldown_km:.1f}km easy")

    parts.append(f"RPE: {workout.target_rpe}/10")

    if workout.notes:
        parts.append("")
        parts.append(workout.notes)

    return "\n".join(parts)


def _strength_title(sess: StrengthSession) -> str:
    stype = getattr(sess.session_type, "value", sess.session_type)
    label = STRENGTH_LABELS.get(stype, "Gym")
    return f"🏋️ {label}"


def _run_day_time(day_of_week: int, settings: GoogleCalendarSettings) -> str:
    """Return run start time for the given weekday (0=Mon)."""
    return settings.run_day_times.get(str(day_of_week), "09:00")


def _strength_day_time(day_of_week: int, settings: GoogleCalendarSettings) -> str:
    """Return strength start time for the given weekday (0=Mon)."""
    return settings.strength_day_times.get(str(day_of_week), "15:00")


def _allday_event(summary: str, description: str, event_date: date, uid: str) -> dict:
    return {
        "summary": summary,
        "description": description,
        "start": {"date": event_date.isoformat()},
        "end": {"date": (event_date + timedelta(days=1)).isoformat()},
        "reminders": {"useDefault": False, "overrides": []},
        "extendedProperties": {
            "private": {"resilio_managed": MANAGED_MARKER, "resilio_uid": uid}
        },
    }


def _timed_event(
    summary: str,
    description: str,
    event_date: date,
    start_time: str,
    duration_min: int,
    reminder_min: int,
    uid: str,
    timezone: str,
    tz_offset: str,
) -> dict:
    end_dt = datetime.strptime(start_time, "%H:%M") + timedelta(minutes=duration_min)
    end_time = end_dt.strftime("%H:%M")
    return {
        "summary": summary,
        "description": description,
        "start": {"dateTime": _rfc3339(event_date, start_time, tz_offset), "timeZone": timezone},
        "end": {"dateTime": _rfc3339(event_date, end_time, tz_offset), "timeZone": timezone},
        "reminders": {"useDefault": False, "overrides": _reminder_override(reminder_min)},
        "extendedProperties": {
            "private": {"resilio_managed": MANAGED_MARKER, "resilio_uid": uid}
        },
    }


def build_run_event(
    workout: WorkoutPrescription,
    week: WeekPlan,
    settings: GoogleCalendarSettings,
    tz_offset: str = "-04:00",
) -> dict:
    """Build Google Calendar event dict for a run workout."""
    wtype = getattr(workout.workout_type, "value", workout.workout_type)
    uid = _resilio_uid(workout.date, wtype, workout.week_number)
    summary = _run_title(workout)
    description = _run_description(workout)

    if wtype == WorkoutType.REST.value:
        return _allday_event(summary, description, workout.date, uid)

    start_time = _run_day_time(workout.day_of_week, settings)

    reminder_key = "long_run" if wtype == WorkoutType.LONG_RUN.value else wtype
    reminder_min = settings.reminders.get(reminder_key, settings.reminders.get("easy", 30))
    duration_min = workout.duration_minutes or 45

    return _timed_event(summary, description, workout.date, start_time,
                        duration_min, reminder_min, uid, settings.timezone, tz_offset)


def build_strength_event(
    sess: StrengthSession,
    settings: GoogleCalendarSettings,
    tz_offset: str = "-04:00",
) -> dict:
    """Build Google Calendar event dict for a strength session."""
    stype = getattr(sess.session_type, "value", sess.session_type)
    uid = _resilio_uid(sess.date, stype, sess.week_number)
    summary = _strength_title(sess)
    description = "Voir Hevy pour le détail"

    start_time = _strength_day_time(sess.day_of_week, settings)
    reminder_min = settings.reminders.get("strength", 30)
    return _timed_event(summary, description, sess.date, start_time,
                        sess.duration_minutes, reminder_min, uid, settings.timezone, tz_offset)


def _event_fingerprint(event: dict) -> str:
    """Stable hash of the fields we care about to detect changes."""
    return json.dumps(
        {
            "summary": event.get("summary"),
            "description": event.get("description"),
            "start": event.get("start"),
            "end": event.get("end"),
            "reminders": event.get("reminders"),
        },
        sort_keys=True,
    )


# ============================================================
# SYNC ORCHESTRATOR
# ============================================================


class PlanToCalendarSync:
    """
    Sync a set of WeekPlan weeks to Google Calendar.

    Usage:
        client = GoogleCalendarClient(...)
        client.authenticate()
        syncer = PlanToCalendarSync(client, settings, state_path)
        report = syncer.sync(weeks, dry_run=False)
    """

    def __init__(
        self,
        client: object,  # GoogleCalendarClient (typed loosely to avoid circular import)
        settings: GoogleCalendarSettings,
        state_path: Path,
    ) -> None:
        self._client = client
        self._settings = settings
        self._state_path = state_path
        self._calendar_id: Optional[str] = None

    def _load_state(self) -> dict:
        if self._state_path.exists():
            return json.loads(self._state_path.read_text())
        return {}

    def _save_state(self, state: dict) -> None:
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        self._state_path.write_text(json.dumps(state, indent=2))

    def _get_calendar_id(self) -> str:
        if self._calendar_id:
            return self._calendar_id
        state = self._load_state()
        if "calendar_id" in state:
            self._calendar_id = state["calendar_id"]
            return self._calendar_id
        # First run: create calendar
        cal_id = self._client.ensure_calendar(self._settings.calendar_name)  # type: ignore[attr-defined]
        state["calendar_id"] = cal_id
        self._save_state(state)
        self._calendar_id = cal_id
        return cal_id

    def sync(
        self,
        weeks: list[WeekPlan],
        dry_run: bool = False,
        force: bool = False,
    ) -> SyncReport:
        """
        Sync weeks to Google Calendar.

        Args:
            weeks: WeekPlan objects to sync (today-forward only).
            dry_run: Print planned changes without calling API.
            force: Ignore local state fingerprints, re-evaluate everything.

        Returns:
            SyncReport with counts.
        """
        report = SyncReport()
        today = date.today()

        # Build desired events (only today-forward)
        desired: dict[str, dict] = {}  # uid → event_body
        tz_offset = "-04:00"  # America/Toronto EDT; fine for plan horizon

        for week in weeks:
            for workout in week.workouts:
                if workout.date < today:
                    continue
                ev = build_run_event(workout, week, self._settings, tz_offset)
                uid = ev["extendedProperties"]["private"]["resilio_uid"]
                desired[uid] = ev

            for sess in week.strength_sessions:
                if sess.date < today:
                    continue
                ev = build_strength_event(sess, self._settings, tz_offset)
                uid = ev["extendedProperties"]["private"]["resilio_uid"]
                desired[uid] = ev

        if dry_run:
            print(f"[dry-run] Desired events: {len(desired)}")
            for uid, ev in desired.items():
                print(f"  {uid}: {ev['summary']} {ev.get('start', {})}")
            return report

        cal_id = self._get_calendar_id()

        # Fetch remote managed events in window
        if weeks:
            all_dates = [
                d
                for week in weeks
                for d in [week.start_date, week.end_date]
            ]
            window_start = min(all_dates)
            window_end = max(all_dates) + timedelta(days=1)
        else:
            return report

        # Ensure dates are date objects
        if isinstance(window_start, str):
            window_start = date.fromisoformat(window_start)
        if isinstance(window_end, str):
            window_end = date.fromisoformat(window_end)

        time_min = f"{max(window_start, today).isoformat()}T00:00:00Z"
        time_max = f"{window_end.isoformat()}T00:00:00Z"

        remote_events = self._client.list_managed_events(cal_id, time_min, time_max)  # type: ignore[attr-defined]
        remote_by_uid: dict[str, dict] = {}
        for ev in remote_events:
            uid = ev.get("extendedProperties", {}).get("private", {}).get("resilio_uid")
            if uid:
                remote_by_uid[uid] = ev

        # Insert / patch (delete+insert when allday↔timed format changes)
        for uid, desired_ev in desired.items():
            if uid not in remote_by_uid:
                try:
                    self._client.create_event(cal_id, desired_ev)  # type: ignore[attr-defined]
                    report.inserted += 1
                    logger.info("Inserted: %s", uid)
                except Exception as exc:
                    report.errors.append(f"insert {uid}: {exc}")
            else:
                remote_ev = remote_by_uid[uid]
                if _event_fingerprint(desired_ev) != _event_fingerprint(remote_ev):
                    # Google rejects patch when allday↔timed format changes → delete+insert
                    remote_is_allday = "date" in remote_ev.get("start", {}) and "dateTime" not in remote_ev.get("start", {})
                    desired_is_allday = "date" in desired_ev.get("start", {}) and "dateTime" not in desired_ev.get("start", {})
                    format_changed = remote_is_allday != desired_is_allday
                    try:
                        if format_changed:
                            self._client.delete_event(cal_id, remote_ev["id"])  # type: ignore[attr-defined]
                            self._client.create_event(cal_id, desired_ev)  # type: ignore[attr-defined]
                            logger.info("Replaced (format change): %s", uid)
                        else:
                            self._client.patch_event(cal_id, remote_ev["id"], desired_ev)  # type: ignore[attr-defined]
                            logger.info("Patched: %s", uid)
                        report.patched += 1
                    except Exception as exc:
                        report.errors.append(f"patch {uid}: {exc}")
                else:
                    report.skipped += 1

        # Delete remote events no longer in plan
        for uid, remote_ev in remote_by_uid.items():
            if uid not in desired:
                try:
                    self._client.delete_event(cal_id, remote_ev["id"])  # type: ignore[attr-defined]
                    report.deleted += 1
                    logger.info("Deleted: %s", uid)
                except Exception as exc:
                    report.errors.append(f"delete {uid}: {exc}")

        return report
