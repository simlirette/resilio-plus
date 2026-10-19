"""
SP5 — push the lifting *program* (one routine per session) to Hevy.

Hevy tracks progress per routine, so routines must stay stable for a whole
mesocycle (~3-4 months). Push only when the program changes (new block, or an
exercise swap the athlete asked for), never once a week.

Hevy's API cannot delete routines, so Resilio owns one *slot* per session name
(``upper-a``, ``legs``, ``upper-b``, ``arms``…) inside a "Resilio" routine folder.
A push updates those routines in place. The weekday a session lands on does not
matter, and routines left out of a push are not touched. Routines outside the
Resilio folder are never touched.
"""

from __future__ import annotations

import re
from typing import Any, Optional

from pydantic import BaseModel, Field

from resilio.core.lifting.hevy_client import HevyAPIError
from resilio.core.lifting.store import LiftingStore
from resilio.schemas.lifting import ExercisePrescription

FOLDER_TITLE = "Resilio"


class PushAction(BaseModel):
    slot: str
    action: str  # create | update | recreate | skip
    title: str
    routine_id: Optional[str] = None
    payload: Optional[dict] = None
    note: Optional[str] = None


class PushReport(BaseModel):
    week_number: int
    dry_run: bool
    folder_id: Optional[int] = None
    folder_action: str = "existing"  # existing | created | would_create
    actions: list[PushAction] = Field(default_factory=list)


def _session_label(session) -> str:
    if session.title:
        return session.title
    stype = getattr(session.session_type, "value", session.session_type)
    return str(stype).replace("_", " ").title()


def _exercise_payload(e: ExercisePrescription) -> dict:
    note_bits = []
    if e.target_rir is not None:
        note_bits.append(f"RIR {e.target_rir}")
    if e.notes:
        note_bits.append(e.notes)
    sets: list[dict] = []
    for _ in range(e.warmup_sets):
        sets.append({"type": "warmup", "weight_kg": None,
                     "reps": e.rep_range[1] if e.rep_range else None,
                     "distance_meters": None, "duration_seconds": None, "custom_metric": None})
    for _ in range(e.sets):
        sets.append({
            "type": "normal",
            "weight_kg": e.load_kg,
            # reps = bottom of range as a fallback target if Hevy ignores rep_range
            "reps": e.rep_range[0] if e.rep_range else None,
            "distance_meters": None,
            "duration_seconds": e.duration_seconds,
            "custom_metric": None,
        })
        if e.rep_range:
            sets[-1]["rep_range"] = {"start": e.rep_range[0], "end": e.rep_range[1]}
    return {
        "exercise_template_id": e.exercise_template_id,
        "superset_id": e.superset_group,
        "rest_seconds": e.rest_seconds,
        "notes": " · ".join(note_bits) or None,
        "sets": sets,
    }


def slot_key(session) -> str:
    """Stable slot per session name: 'Upper A' -> 'upper-a', 'Arms (optional)' -> 'arms'."""
    label = re.sub(r"\(.*?\)", "", _session_label(session))
    return re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-") or "session"


def build_routine_payload(session, week_number: int) -> dict:
    # No weekday or week number in title/notes: the routine must read the same all block long.
    return {
        "title": f"Resilio · {_session_label(session)}",
        "notes": session.notes or None,
        "exercises": [_exercise_payload(e) for e in session.exercises],
    }


def _ensure_folder(client, mapping: dict, dry_run: bool) -> tuple[Optional[int], str]:
    if mapping.get("folder_id"):
        return int(mapping["folder_id"]), "existing"
    for f in client.iter_routine_folders():
        if str(f.get("title", "")).strip().lower() == FOLDER_TITLE.lower():
            return int(f["id"]), "existing"
    if dry_run:
        return None, "would_create"
    folder = client.create_routine_folder(FOLDER_TITLE)
    return int(folder["id"]), "created"


def push_week(client, store: LiftingStore, sessions: list, week_number: int, dry_run: bool = False) -> PushReport:
    mapping: dict[str, Any] = store.load_routine_map()
    slots: dict[str, str] = dict(mapping.get("slots") or {})
    folder_id, folder_action = _ensure_folder(client, mapping, dry_run)
    report = PushReport(week_number=week_number, dry_run=dry_run, folder_id=folder_id, folder_action=folder_action)
    if folder_id is not None and not dry_run:
        mapping["folder_id"] = folder_id
        store.save_routine_map({**mapping, "slots": slots})

    used: set[str] = set()
    for s in sorted(sessions, key=lambda x: (x.date, x.day_of_week)):
        slot, n = slot_key(s), 1
        while slot in used:
            n += 1
            slot = f"{slot_key(s)}-{n}"
        payload = build_routine_payload(s, week_number)
        if not s.exercises:
            report.actions.append(PushAction(slot=slot, action="skip", title=payload["title"],
                                             note="schedule-only session (no exercises)"))
            continue
        used.add(slot)
        rid = slots.get(slot)
        if dry_run:
            report.actions.append(PushAction(slot=slot, action="update" if rid else "create",
                                             title=payload["title"], routine_id=rid, payload=payload))
            continue
        action = "update"
        if rid:
            try:
                client.update_routine(rid, payload)
            except HevyAPIError as exc:
                if exc.status_code != 404:
                    raise
                rid, action = None, "recreate"
        if not rid:
            created = client.create_routine({**payload, "folder_id": folder_id})
            rid = str(created["id"])
            action = "create" if action != "recreate" else action
        slots[slot] = rid
        store.save_routine_map({**mapping, "slots": slots})
        report.actions.append(PushAction(slot=slot, action=action, title=payload["title"], routine_id=rid))
    return report
