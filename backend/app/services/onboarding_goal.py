"""What the profile still lacks, and whether it is enough to plan from.

Onboarding used to be six fixed instructions. Block 4 said "collecte
l'historique sportif", block 5 said "fréquence souhaitée par discipline", so
the coach asked for running volume in blocks 3, 4 *and* 5 -- after Phase A had
given it the whole conversation and it visibly read it ("Tu cours 3x par
semaine depuis mai"). It was not forgetting. It was obeying.

A gap list replaces the script. The model is told what is still missing and
chooses what to ask; the phrasing is its job, the destination is not.

Completion stays deterministic. Letting the model decide when onboarding is
over invites both failure modes -- stopping with a profile no plan can be built
from, or interviewing indefinitely. Gaps decide readiness; the model only
decides wording.
"""
from __future__ import annotations

import json
from typing import Any

#: Without these a generated week is guesswork.
#:
#: Body measurements are deliberately absent. `age`, `sex`, `weight_kg`,
#: `height_cm` and `hours_per_week` are NOT NULL on `athletes` and are set when
#: the row is created, so they can never be a gap -- treating them as one would
#: make the coach ask for data it already holds, which is the failure this
#: whole change exists to end.
#:
#: `sessions_per_week` is here because its absence produced a 1h30 week
#: containing no lifting for an athlete who lifts four times a week.
REQUIRED_FIELDS: tuple[str, ...] = (
    "sports",
    "goals",
    "sessions_per_week",
)

#: Worth asking for, never worth blocking on. A plan is better with a race date
#: and a recent time; it is still a plan without them.
WANTED_FIELDS: tuple[str, ...] = (
    "target_race_date",
    "recent race result",
    "available_days",
    "resting_hr",
)

#: An athlete who has answered this many times deserves a plan even if one
#: field never landed. Without a ceiling a stubborn extraction failure becomes
#: an interrogation with no exit.
MAX_TURNS = 10

_LABELS: dict[str, str] = {
    "sports": "les sports qu'il pratique",
    "goals": "son objectif principal",
    "sessions_per_week": "combien de séances par semaine, par sport",
    "target_race_date": "la date de sa course cible",
    "recent race result": "un chrono récent sur une distance connue",
    "available_days": "ses jours disponibles",
    "resting_hr": "sa fréquence cardiaque au repos",
}


def _has_list(raw: Any) -> bool:
    """True when a JSON list column holds at least one entry."""
    if not raw:
        return False
    try:
        value = json.loads(raw)
    except (TypeError, ValueError):
        return False
    return bool(value) if isinstance(value, (list, dict)) else False


def profile_gaps(athlete: Any) -> list[str]:
    """Required fields the athlete has not supplied, in a stable order."""
    gaps: list[str] = []
    if not _has_list(getattr(athlete, "sports_json", None)):
        gaps.append("sports")
    if not _has_list(getattr(athlete, "goals_json", None)):
        gaps.append("goals")
    if not _covers_every_sport(athlete):
        gaps.append("sessions_per_week")
    return gaps


def _covers_every_sport(athlete: Any) -> bool:
    """Session counts must name every sport the athlete practises.

    A partial answer used to close this gap and end onboarding early. On a live
    replay the extractor read "dek hockey 1x/semaine" as `{"biking": 1}`; that
    alone satisfied the requirement, the profile looked complete after two
    answers, and the athlete reached a plan without ever stating how often they
    run or lift -- the exact hole this field exists to close.
    """
    sports = _as_list(getattr(athlete, "sports_json", None))
    counts = _as_dict(getattr(athlete, "sessions_per_week_json", None))
    if not sports or not counts:
        return False
    return all(sport in counts for sport in sports)


def _as_list(raw: Any) -> list[str]:
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except (TypeError, ValueError):
        return []
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []


def _as_dict(raw: Any) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except (TypeError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def optional_gaps(athlete: Any) -> list[str]:
    """Nice-to-have fields still missing. Never blocks completion."""
    gaps: list[str] = []
    if getattr(athlete, "target_race_date", None) is None:
        gaps.append("target_race_date")
    if getattr(athlete, "vdot", None) is None:
        gaps.append("recent race result")
    if not _has_list(getattr(athlete, "available_days_json", None)):
        gaps.append("available_days")
    if getattr(athlete, "resting_hr", None) is None:
        gaps.append("resting_hr")
    return gaps


def describe_gaps(gaps: list[str]) -> str:
    """Render a gap list for the model.

    Never returns an empty string: an empty instruction leaves the model to
    invent a purpose for the turn, which is how it started re-asking.
    """
    if not gaps:
        return "Aucune information requise ne manque."
    return "Il manque encore : " + ", ".join(_LABELS.get(gap, gap) for gap in gaps)


def describe_optional(gaps: list[str]) -> str:
    """Nice-to-have fields, phrased so the coach knows they are not blocking."""
    if not gaps:
        return ""
    listed = ", ".join(_LABELS.get(gap, gap) for gap in gaps)
    return (
        f"Si l'occasion se présente naturellement, tu peux aussi récupérer : "
        f"{listed}. Ne bloque pas dessus."
    )


def ready_to_confirm(athlete: Any, turns_taken: int) -> bool:
    """Whether the coach should stop collecting and summarise.

    The turn ceiling is not a nicety. A field the extractor keeps failing to
    read would otherwise loop forever, and the athlete would never reach a
    plan.
    """
    if turns_taken >= MAX_TURNS:
        return True
    return not profile_gaps(athlete)
