"""Is the athlete's stated goal reachable, and what is the honest alternative?

The first live plan accepted "sub-2h au semi" without comment and generated a
1h30 week for an athlete whose 10 km projects 2h20. That silence is the
substance of "ce n'est pas un vrai coach" -- not the tone. A coach says what
the numbers say.

Operator decision (2026-08-21): when the goal is ambitious, present **both**
weeks -- the one built for the stated target and what would change for a
realistic one -- and let the athlete choose. The coach never revises the target
on its own, and it says the risk **once** rather than repeating it every week.

Everything here is derived from Daniels' table, never from a model. Checked:
VDOT 30 projects 2h24 on a half, 35 projects 2h00, 40 projects 1h42 -- so
sub-2h needs VDOT 35, not the 36-37 an interpolation suggested.
"""
from __future__ import annotations

import enum
import importlib
import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class Verdict(enum.Enum):
    ON_TRACK = "on_track"
    AMBITIOUS = "ambitious"
    OUT_OF_REACH = "out_of_reach"
    #: No measured fitness or no stated time. Guessing would be worse than
    #: silence: a fabricated verdict shapes a whole training block.
    UNKNOWN = "unknown"


#: How much faster than the current projection still counts as reachable
#: inside a normal training block, rather than as a different athlete.
_AMBITIOUS_MARGIN = 0.12
_OUT_OF_REACH_MARGIN = 0.25

_FIELD_BY_DISTANCE = {
    "mile": "mile_seconds",
    "5k": "five_k_seconds",
    "10k": "ten_k_seconds",
    "half_marathon": "half_marathon_seconds",
    "marathon": "marathon_seconds",
}

#: "2h", "2h05", "1h45", "2:00", "sub-2h", "sous 2h". Deliberately not a
#: general time parser: "19 septembre 2026" must not read as a target.
_HOURS_MINUTES = re.compile(r"\b(\d)\s*[h:]\s*(\d{2})?\b", re.IGNORECASE)


@dataclass(frozen=True)
class GoalAssessment:
    verdict: Verdict
    current_vdot: float | None = None
    goal_seconds: int | None = None
    projected_seconds: int | None = None
    required_vdot: int | None = None
    #: What to offer alongside the athlete's target. None when on track.
    realistic_seconds: int | None = None


def parse_goal_time(text: str) -> int | None:
    """Seconds from a stated goal, or None when the goal has no time in it.

    "Compléter le semi" is a real goal. Inventing a time for it would put a
    number the athlete never gave at the centre of every pace prescription.
    """
    if not text:
        return None
    if re.search(r"\b(19|20)\d{2}\b", text):
        # A year: "semi le 19 septembre 2026" is a date, not a target time.
        text = re.sub(r"\b(19|20)\d{2}\b", " ", text)

    match = _HOURS_MINUTES.search(text)
    if match is None:
        return None
    hours = int(match.group(1))
    minutes = int(match.group(2) or 0)
    if hours > 9 or minutes > 59:
        return None
    return hours * 3600 + minutes * 60


def _table_seconds(vdot: int, distance: str) -> int | None:
    field = _FIELD_BY_DISTANCE.get(distance)
    if field is None:
        return None
    try:
        tables = importlib.import_module("resilio.core.vdot.tables")
        entry = tables.get_vdot_entry(vdot)
    except Exception:
        logger.warning("vdot_table_unavailable", exc_info=True)
        return None
    value = getattr(entry, field, None) if entry is not None else None
    return int(value) if isinstance(value, (int, float)) else None


def _nearest_projection(vdot: float, distance: str) -> tuple[int, int] | None:
    """(vdot used, projected seconds) from the nearest table row at or below."""
    for candidate in range(int(vdot), 19, -1):
        seconds = _table_seconds(candidate, distance)
        if seconds is not None:
            return candidate, seconds
    return None


def _vdot_required(goal_seconds: int, distance: str) -> int | None:
    """The lowest VDOT whose table time meets the goal."""
    for candidate in range(20, 86):
        seconds = _table_seconds(candidate, distance)
        if seconds is not None and seconds <= goal_seconds:
            return candidate
    return None


def assess_goal(
    vdot: float | None,
    distance: str,
    goal_seconds: int | None,
) -> GoalAssessment:
    """Compare a stated goal against what the athlete's fitness projects."""
    if vdot is None or goal_seconds is None:
        return GoalAssessment(verdict=Verdict.UNKNOWN)

    projection = _nearest_projection(vdot, distance)
    if projection is None:
        return GoalAssessment(verdict=Verdict.UNKNOWN, current_vdot=vdot)

    _, projected = projection
    required = _vdot_required(goal_seconds, distance)
    gap = (projected - goal_seconds) / projected

    if gap <= 0:
        verdict = Verdict.ON_TRACK
    elif gap <= _AMBITIOUS_MARGIN:
        verdict = Verdict.AMBITIOUS
    elif gap <= _OUT_OF_REACH_MARGIN:
        verdict = Verdict.AMBITIOUS
    else:
        verdict = Verdict.OUT_OF_REACH

    realistic = None
    if verdict is not Verdict.ON_TRACK:
        # Halfway between where they are and where they want to be: a target
        # the block can plausibly deliver, offered *alongside* theirs.
        realistic = int(goal_seconds + (projected - goal_seconds) * 0.5)

    return GoalAssessment(
        verdict=verdict,
        current_vdot=vdot,
        goal_seconds=goal_seconds,
        projected_seconds=projected,
        required_vdot=required,
        realistic_seconds=realistic,
    )


def _hm(seconds: int) -> str:
    return f"{seconds // 3600}h{(seconds % 3600) // 60:02d}"


def describe_assessment(assessment: GoalAssessment) -> str:
    """What to tell the Head Coach. Empty when there is nothing honest to say."""
    if assessment.verdict is Verdict.UNKNOWN:
        return ""

    if assessment.verdict is Verdict.ON_TRACK:
        return (
            f"L'objectif de l'athlète ({_hm(assessment.goal_seconds or 0)}) est "
            f"cohérent avec sa forme actuelle "
            f"(projection {_hm(assessment.projected_seconds or 0)}). "
            "Confirme-le sans réserve et construis la semaine dessus."
        )

    lines = [
        f"Faisabilité : sa forme actuelle projette "
        f"{_hm(assessment.projected_seconds or 0)}, son objectif est "
        f"{_hm(assessment.goal_seconds or 0)}.",
    ]
    if assessment.required_vdot is not None:
        lines.append(f"Cet objectif demande un VDOT de {assessment.required_vdot}.")
    if assessment.realistic_seconds is not None:
        lines.append(
            f"Présente DEUX semaines dans la même réponse : celle construite "
            f"pour son objectif, et ce qui changerait pour "
            f"{_hm(assessment.realistic_seconds)}. Laisse-le choisir — ne "
            f"révise jamais sa cible toi-même."
        )
    lines.append(
        "Dis-le une seule fois, clairement, puis exécute ce qu'il demande. "
        "Ne reviens pas dessus à chaque message."
    )
    return " ".join(lines)
