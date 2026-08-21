"""Turn free-text onboarding answers into typed athlete fields.

The onboarding graph asks six blocks of questions and used to keep the answers
only in `state.collected_data`, a process-local dict. The handoff persisted
`journey_phase` and nothing else, so an athlete could complete the whole
conversation and leave their row exactly as it was.

Two rules shape everything here, because a coach acting on a bad number does
more harm than one acting on none:

  - **Refuse, do not clamp.** A weight of 400 kg is not a 250 kg athlete, it
    is a failed extraction. Clamping would launder a parsing error into a
    plausible-looking value that nothing downstream could question.
  - **Never overwrite something with nothing.** An answer that does not
    mention weight must leave the known weight alone.

VDOT is derived, never asked. The model reports which race and what time; the
Daniels table turns that into a number. Letting a language model emit a VDOT
directly would let it set every prescribed pace for the whole training block.
"""
from __future__ import annotations

import importlib
import json
import logging
import os
import re
from datetime import date
from typing import Any

import anthropic

from ..db.models import AthleteModel
from .conversation import Turn

logger = logging.getLogger(__name__)

_MODEL = "claude-haiku-4-5-20251001"
_MAX_TOKENS = 1024
_TIMEOUT_SECONDS = 20.0

# Physiologically possible, deliberately wide. This is a nonsense filter, not a
# clinical range -- a real outlier athlete must not be rejected.
_NUMERIC_BOUNDS: dict[str, tuple[type, float, float]] = {
    "age": (int, 10, 100),
    "weight_kg": (float, 30.0, 250.0),
    "height_cm": (float, 100.0, 250.0),
    "max_hr": (int, 120, 230),
    "resting_hr": (int, 30, 100),
    "hours_per_week": (float, 1.0, 40.0),
    "ftp_watts": (int, 50, 600),
    "css_per_100m": (float, 60.0, 180.0),
}

_SPORT_ORDER: tuple[str, ...] = ("running", "lifting", "swimming", "biking")
_KNOWN_SPORTS: frozenset[str] = frozenset(_SPORT_ORDER)

# RaceDistance values accepted by resilio.core.vdot.calculator
_RACE_DISTANCES: dict[str, str] = {
    "mile": "mile",
    "5k": "5k",
    "10k": "10k",
    "15k": "15k",
    "half_marathon": "half_marathon",
    "half": "half_marathon",
    "semi": "half_marathon",
    "marathon": "marathon",
}

# Below these, the time is not a real performance for the distance -- it is a
# parsing error (a lap time read as a race time, or seconds read as minutes).
_MIN_PLAUSIBLE_SECONDS: dict[str, int] = {
    "mile": 3 * 60,
    "5k": 12 * 60,
    "10k": 25 * 60,
    "15k": 40 * 60,
    "half_marathon": 55 * 60,
    "marathon": 115 * 60,
}
_MAX_PLAUSIBLE_SECONDS: dict[str, int] = {
    "mile": 20 * 60,
    "5k": 60 * 60,
    "10k": 2 * 3600,
    "15k": 3 * 3600,
    "half_marathon": 5 * 3600,
    "marathon": 9 * 3600,
}

_BLOCK_TARGETS: dict[int, str] = {
    1: "nothing -- this block is an introduction",
    2: "age, sex (M or F), weight_kg, height_cm, max_hr, resting_hr",
    3: "goals (list of short strings), target_race_date (YYYY-MM-DD)",
    4: (
        "race_distance (one of mile, 5k, 10k, 15k, half_marathon, marathon) and "
        "race_time_seconds for the most recent race the athlete mentions; "
        "ftp_watts, css_per_100m, hours_per_week"
    ),
    5: "hours_per_week, available_days (list of weekday numbers, Monday=0)",
    6: "sports (any of running, lifting, swimming, biking), primary_sport",
}

_SYSTEM_PROMPT = """You extract structured facts from an athlete answer
during coaching onboarding.

Return ONLY a JSON object. No prose, no explanation, no code fence.

Rules:
- Include a key ONLY if the athlete stated it explicitly or it follows directly.
- Never guess, never infer from context, never fill a plausible default.
- Omit anything not stated. An empty object is a valid and common answer.
- Never output a `vdot` key. Report the race and its time instead.
- Times go in seconds. Dates go in YYYY-MM-DD.
- The athlete may answer in French or English."""


_PROFILE_PROMPT = """You read a coaching conversation and extract the athlete's profile.

Return ONLY a JSON object. No prose, no explanation, no code fence.

Rules:
- Include a key ONLY if the athlete stated it. Never guess, never infer, never
  fill a plausible default. An empty object is valid.
- Never output a `vdot` key.
- `race_distance` and `race_time_seconds` describe a race the athlete has
  ALREADY RUN. If they state any finished time -- "5km: 26min47s", "10 km en
  1h04" -- ALWAYS report it; that is the single most useful fact in the whole
  conversation. If several are mentioned, report the longest distance.
  A goal or a target time is NOT a result: "objectif sub-2h au semi" is a goal
  and must never be reported here. When the only time mentioned is a goal,
  omit both keys.
- `race_distance` must be one of: mile, 5k, 10k, 15k, half_marathon, marathon.
  Never a number, never metres.
- `sports` and `sports_removed` must use exactly: running, lifting, swimming,
  biking. Weight training, musculation, gym, strength training are all
  `lifting`. A sport that is none of these -- hockey, football, climbing,
  tennis -- is simply NOT REPORTED. Never map it to the nearest value: dek
  hockey is not biking, and a wrong sport puts sessions in the wrong plan.
- `sports` is every sport the athlete practises. Naming one as a priority is
  not a reason to omit the others.
- `sports_removed` is only for sports they explicitly said they have stopped.
- `sessions_per_week` is {sport: count} — how many SESSIONS, not hours.
- `hours_per_week` only if they gave a duration, never a session count.
- Dates as YYYY-MM-DD. Resolve relative dates against the date given at the top
  of the transcript; never assume the current year.
- The athlete may write in French or English.

Keys: age, sex (M/F), weight_kg, height_cm, max_hr, resting_hr, sports,
sports_removed, primary_sport, sessions_per_week, hours_per_week, goals,
target_race_date, race_distance, race_time_seconds, ftp_watts, css_per_100m,
available_days (weekday numbers, Monday=0)."""


def build_profile_transcript(turns: list[Turn], today: date) -> str:
    """Render a conversation for the extractor, anchored to a date.

    Without the date the extractor resolved "19 septembre" to 2024 for a race
    in 2026 -- it has no clock, so it used its training prior.
    """
    lines = [f"Today's date: {today.isoformat()}", ""]
    lines += [
        f"{'ATHLETE' if turn.role == 'user' else 'COACH'}: {turn.content}"
        for turn in turns
    ]
    return "\n\n".join(lines)


def _call_profile_extractor(transcript: str) -> str:
    """One Haiku call over the whole conversation. Split out for tests."""
    message = _client().messages.create(
        model=_MODEL,
        max_tokens=_MAX_TOKENS,
        system=_PROFILE_PROMPT,
        messages=[{"role": "user", "content": transcript}],
    )
    return str(getattr(message.content[0], "text", ""))


def extract_profile(turns: list[Turn]) -> dict[str, Any]:
    """Extract the athlete's profile from an entire conversation.

    Per-block extraction lost whatever the athlete happened to say in the
    "wrong" block -- most damagingly two race times given while being asked for
    body measurements, which is why VDOT stayed NULL after an onboarding whose
    whole purpose was to establish it. Reading the transcript removes that
    failure by construction.
    """
    if not turns:
        return {}

    transcript = build_profile_transcript(turns, date.today())

    try:
        raw = _call_profile_extractor(transcript)
    except Exception:
        logger.warning("profile_extraction_failed", exc_info=True)
        return {}

    parsed = _first_json_object(raw)
    if parsed is None:
        logger.info("profile_extraction_unparseable")
        return {}

    return {key: value for key, value in parsed.items() if value is not None}



def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic(
        api_key=os.getenv("ANTHROPIC_API_KEY", ""), timeout=_TIMEOUT_SECONDS
    )


def _call_extractor(block: int, answer: str) -> str:
    """One Haiku call. Split out so tests can replace it."""
    targets = _BLOCK_TARGETS.get(block, "any field the athlete states")
    message = _client().messages.create(
        model=_MODEL,
        max_tokens=_MAX_TOKENS,
        system=_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Fields to look for in this block: {targets}\n\n"
                    f"Athlete's answer:\n{answer}"
                ),
            }
        ],
    )
    return str(getattr(message.content[0], "text", ""))


def _first_json_object(raw: str) -> dict[str, Any] | None:
    """Pull the first JSON object out of whatever the model returned."""
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match is None:
            return None
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None

    return parsed if isinstance(parsed, dict) else None


def extract_block(block: int, answer: str) -> dict[str, Any]:
    """Return the facts stated in one block answer.

    Always returns a dict. An unusable model response, or no response at all,
    yields ``{}`` -- losing an extraction costs precision; raising here would
    end the athlete's onboarding conversation.
    """
    if not (answer or "").strip():
        return {}

    try:
        raw = _call_extractor(block, answer)
    except Exception:
        logger.warning("onboarding_extraction_failed", extra={"block": block}, exc_info=True)
        return {}

    parsed = _first_json_object(raw)
    if parsed is None:
        logger.info("onboarding_extraction_unparseable", extra={"block": block})
        return {}

    return {key: value for key, value in parsed.items() if value is not None}


# ─── Applying an extraction ───────────────────────────────────────────────────


def _clean_numeric(field: str, value: Any) -> float | int | None:
    kind, low, high = _NUMERIC_BOUNDS[field]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not low <= float(value) <= high:
        return None
    return int(value) if kind is int else float(value)


def _clean_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        return None


def _clean_sports(value: Any) -> list[str] | None:
    if not isinstance(value, list):
        return None
    kept = [
        item.strip().lower()
        for item in value
        if isinstance(item, str) and item.strip().lower() in _KNOWN_SPORTS
    ]
    return kept or None


def _derive_vdot(data: dict[str, Any]) -> float | None:
    """Turn a stated race result into a VDOT, or nothing."""
    raw_distance = data.get("race_distance")
    seconds = data.get("race_time_seconds")
    if not isinstance(raw_distance, str) or isinstance(seconds, bool):
        return None
    if not isinstance(seconds, (int, float)):
        return None

    distance = _RACE_DISTANCES.get(raw_distance.strip().lower())
    if distance is None:
        return None
    if not (
        _MIN_PLAUSIBLE_SECONDS[distance] <= seconds <= _MAX_PLAUSIBLE_SECONDS[distance]
    ):
        return None

    try:
        # Imported dynamically on purpose. `resilio/` is the read-only legacy
        # CLI: it predates the strict typing rules, so a static import would
        # pull it into mypy's graph and fail the gate on code we may not edit.
        # Daniels' race-time table lives there and nowhere else -- duplicating
        # it in backend/ would be a second source of truth for every pace the
        # coach prescribes.
        calculator = importlib.import_module("resilio.core.vdot.calculator")

        result = calculator.calculate_vdot(
            calculator.RaceDistance(distance), int(seconds)
        )
        return float(result.vdot)
    except Exception:
        logger.warning("vdot_derivation_failed", exc_info=True)
        return None


#: A sport is not dropped for being unmentioned, and never below one.
MIN_SESSIONS = 1
MAX_SESSIONS = 14


def _json_list(raw: str | None) -> list[str]:
    """Read a JSON list column, tolerating anything that is not one."""
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except (TypeError, ValueError):
        return []
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []


def _merge_sports(athlete: AthleteModel, data: dict[str, Any]) -> bool:
    """Add what the athlete named; remove only what they explicitly dropped.

    A list of sports is a *mention*, not a complete declaration. "Prioriser la
    course" made the model answer `["running"]`, the old code overwrote the
    column, and `build_agents` then never instantiated the LiftingCoach -- so a
    week arrived with zero lifting for an athlete who lifts four times a week.

    Removal stays possible through `sports_removed`, and never empties the
    list: an athlete with no sports cannot be coached, so that is a bad
    extraction rather than an instruction.
    """
    current = set(_json_list(getattr(athlete, "sports_json", None)))
    updated = set(current)

    mentioned = _clean_sports(data.get("sports")) if "sports" in data else None
    if mentioned:
        updated |= set(mentioned)

    removed = _clean_sports(data.get("sports_removed")) if "sports_removed" in data else None
    if removed:
        remaining = updated - set(removed)
        if remaining:
            updated = remaining

    if updated == current or not updated:
        return False

    ordered = [sport for sport in _SPORT_ORDER if sport in updated]
    athlete.sports_json = json.dumps(ordered, ensure_ascii=False)
    return True


def _apply_sessions_per_week(athlete: AthleteModel, value: Any) -> bool:
    """Store {sport: sessions}. Never touches `hours_per_week`.

    The two were one column, so "je vise 3 sorties" was written as three
    *hours* and capped the generated week at 1h30.
    """
    if not isinstance(value, dict):
        return False

    counts: dict[str, int] = {}
    for sport, count in value.items():
        if not isinstance(sport, str) or sport.strip().lower() not in _KNOWN_SPORTS:
            continue
        if isinstance(count, bool) or not isinstance(count, (int, float)):
            continue
        if not MIN_SESSIONS <= int(count) <= MAX_SESSIONS:
            continue
        counts[sport.strip().lower()] = int(count)

    if not counts:
        return False

    athlete.sessions_per_week_json = json.dumps(counts, ensure_ascii=False)
    return True


def apply_extraction(
    athlete: AthleteModel,
    data: dict[str, Any],
    db: Any,
) -> list[str]:
    """Write the valid parts of an extraction to the athlete row.

    Returns the field names that actually changed. Anything unrecognised,
    out of range, or of the wrong type is dropped silently -- the athlete gets
    asked again rather than coached off a bad number.
    """
    changed: list[str] = []

    for field in _NUMERIC_BOUNDS:
        if field not in data:
            continue
        cleaned = _clean_numeric(field, data[field])
        if cleaned is not None and getattr(athlete, field, None) != cleaned:
            setattr(athlete, field, cleaned)
            changed.append(field)

    sex = data.get("sex")
    if isinstance(sex, str) and sex.strip().upper() in {"M", "F"}:
        value = sex.strip().upper()
        if athlete.sex != value:
            athlete.sex = value
            changed.append("sex")

    race_date = _clean_date(data.get("target_race_date")) if "target_race_date" in data else None
    if race_date is not None and athlete.target_race_date != race_date:
        athlete.target_race_date = race_date
        changed.append("target_race_date")

    goals = data.get("goals")
    if isinstance(goals, list):
        kept = [g.strip() for g in goals if isinstance(g, str) and g.strip()]
        if kept:
            athlete.goals_json = json.dumps(kept, ensure_ascii=False)
            changed.append("goals")

    if _merge_sports(athlete, data):
        changed.append("sports")

    if _apply_sessions_per_week(athlete, data.get("sessions_per_week")):
        changed.append("sessions_per_week")

    primary = data.get("primary_sport")
    if isinstance(primary, str) and primary.strip().lower() in _KNOWN_SPORTS:
        value = primary.strip().lower()
        if athlete.primary_sport != value:
            athlete.primary_sport = value
            changed.append("primary_sport")

    days = data.get("available_days")
    if isinstance(days, list):
        kept_days = sorted(
            {d for d in days if isinstance(d, int) and not isinstance(d, bool) and 0 <= d <= 6}
        )
        if kept_days:
            athlete.available_days_json = json.dumps(kept_days)
            changed.append("available_days")

    # Derived last: a race result in this same answer wins over nothing, and
    # a `vdot` key from the model is ignored entirely.
    vdot = _derive_vdot(data)
    if vdot is not None and athlete.vdot != vdot:
        athlete.vdot = vdot
        changed.append("vdot")

    if changed:
        db.commit()

    return changed
