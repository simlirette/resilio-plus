"""
SP5 — push a plan week's strength sessions to Hevy as routines.

Hevy's API cannot delete routines, so Resilio owns a fixed set of *slots* (one routine
per weekday, ``mon``…``sun``, plus ``mon-2`` for a second session on the same day)
inside a "Resilio" routine folder. Each push updates the slot routines in place; slots
not used this week are renamed "(not scheduled)" with their exercises left intact.
Routines outside the Resilio folder are never touched.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from resilio.core.lifting.hevy_client import HevyAPIError
from resilio.core.lifting.store import LiftingStore
from resilio.schemas.lifting import ExercisePrescription

FOLDER_TITLE = "Resilio"
DAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
_SET_FIELDS = ("type", "weight_kg", "reps", "distance_meters", "duration_seconds", "custom_metric", "rep_range")
_EXERCISE_FIELDS = ("exercise_template_id", "superset_id", "rest_seconds", "notes")


class PushAction(BaseModel):
    slot: str
    action: str  # create | update | recreate | rename_unused | skip
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


def build_routine_payload(session, week_number: int) -> dict:
    day = DAY_LABELS[session.day_of_week]
    notes = [f"Resilio — Week {week_number} — {session.date.isoformat()}"]
    if session.notes:
        notes.append(session.notes)
    return {
        "title": f"Resilio · {day} · {_session_label(session)}",
        "notes": "\n".join(notes),
        "exercises": [_exercise_payload(e) for e in session.exercises],
    }


def _put_set(s: dict) -> dict:
    # Hevy PUT rejects "rep_range": null ("Expected object, received null"); POST tolerates it.
    out = {k: s.get(k) for k in _SET_FIELDS}
    if out.get("rep_range") is None:
        out.pop("rep_range")
    return out


def _to_put_payload(routine: dict, title: str) -> dict:
    exercises = []
    for e in routine.get("exercises") or []:
        ex = {k: e.get(k) for k in _EXERCISE_FIELDS}
        ex["sets"] = [_put_set(s) for s in e.get("sets") or []]
        exercises.append(ex)
    return {"title": title, "notes": routine.get("notes"), "exercises": exercises}


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
    per_day: dict[int, int] = {}
    for s in sorted(sessions, key=lambda x: (x.date, x.day_of_week)):
        per_day[s.day_of_week] = per_day.get(s.day_of_week, 0) + 1
        n = per_day[s.day_of_week]
        slot = DAY_KEYS[s.day_of_week] + ("" if n == 1 else f"-{n}")
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

    for slot, rid in sorted(slots.items()):
        if slot in used:
            continue
        day_label = DAY_LABELS[DAY_KEYS.index(slot.split("-")[0])]
        title = f"Resilio · {day_label} · (not scheduled)"
        if dry_run:
            report.actions.append(PushAction(slot=slot, action="rename_unused", title=title, routine_id=rid))
            continue
        try:
            current = client.get_routine(rid)
            client.update_routine(rid, _to_put_payload(current, title))
            report.actions.append(PushAction(slot=slot, action="rename_unused", title=title, routine_id=rid))
        except HevyAPIError as exc:
            if exc.status_code != 404:
                raise
            slots.pop(slot)
            store.save_routine_map({**mapping, "slots": slots})
            report.actions.append(PushAction(slot=slot, action="skip", title=title, routine_id=rid,
                                             note="routine deleted in Hevy; slot forgotten"))
    return report
