"""Every fact, with where it came from.

On 2026-08-21 the coach opened with "Tu m'as indiqué 8 heures par semaine". The
athlete had never said it: `hours_per_week` came from `scripts/bootstrap_v4.py`.
He noticed immediately, and asked when he had supposedly said it — a question
the coach then ignored twice.

The view handed the model a number with no history, and the model did the
natural thing with a fact about an athlete: it attributed it to them. Nothing
in the context made "what he told me" distinguishable from "what the row
happens to contain".

Three provenances:

    déclaré  — the athlete said it
    mesuré   — a connector measured it, or it was derived from measurement
    supposé  — a default nobody confirmed

Only `déclaré` may be quoted back to the athlete as theirs. That rule is stated
in the text handed to the model, because a label it cannot see protects nobody.
"""
from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

DECLARED = "déclaré"
MEASURED = "mesuré"
ASSUMED = "supposé"

#: Bootstrap writes these when the row is created. Until the athlete confirms
#: one, it is an assumption wearing a value.
_BOOTSTRAP_DEFAULTS = ("hours_per_week",)

_PROVENANCE_RULE = (
    "Provenance : « déclaré » = l'athlète te l'a dit ; « mesuré » = vient d'un "
    "capteur ou en est dérivé ; « supposé » = valeur par défaut que personne "
    "n'a confirmée. Ne présente jamais un fait « supposé » comme quelque chose "
    "que l'athlète t'a dit. Si tu as besoin d'un « supposé », demande-le."
)

# Observed 2026-08-21: with the tools available but unused, the model wrote its
# own weekly table -- inventing paces like "5:41/km" that no engine produced.
# A coach whose numbers come from nowhere is the thing this project exists to
# not be.
_ENGINE_RULE = (
    "Tu ne rédiges JAMAIS une séance toi-même. Les allures, durées, zones et "
    "types de séance viennent exclusivement de l'outil generate_plan, qui "
    "appelle les agents spécialistes et les règles de charge. Si l'athlète veut "
    "un plan, appelle generate_plan et rapporte ce qu'il renvoie. Tu peux "
    "expliquer, nuancer, proposer un choix — jamais inventer un chiffre "
    "d'entraînement."
)

_RULE = _PROVENANCE_RULE + "\n\n" + _ENGINE_RULE


def _declared_fields(db: Any, athlete_id: str) -> set[str]:
    """Fields the athlete has confirmed, read from what they actually wrote.

    A field is `déclaré` once it has been touched by `update_profile` during a
    conversation. Until then it is whatever created the row.
    """
    try:
        from ..db.models import ChatMessageModel

        rows = (
            db.query(ChatMessageModel)
            .filter(
                ChatMessageModel.athlete_id == athlete_id,
                ChatMessageModel.role == "assistant",
            )
            .all()
        )
    except Exception:
        logger.warning("provenance_unreadable", extra={"athlete_id": athlete_id})
        return set()

    declared: set[str] = set()
    for row in rows:
        raw = getattr(row, "specialists_consulted", None)
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except (TypeError, ValueError):
            continue
        if isinstance(payload, dict):
            declared.update(str(name) for name in payload.get("declared", []))
    return declared


def _provenance(field: str, declared: set[str]) -> str:
    if field in declared:
        return DECLARED
    if field in _BOOTSTRAP_DEFAULTS:
        return ASSUMED
    return MEASURED


def describe_profile(view: Any, db: Any, athlete_id: str) -> str:
    """The facts the coach may reason from, each labelled with its origin."""
    declared = _declared_fields(db, athlete_id)
    lines: list[str] = [_RULE, ""]

    def add(label: str, value: Any, provenance: str) -> None:
        if value is None or value == [] or value == {}:
            return
        lines.append(f"- {label} : {value} ({provenance})")

    add("aujourd'hui", view.today, MEASURED)
    add("âge", view.age, _provenance("age", declared))
    add("sexe", view.sex, _provenance("sex", declared))
    add("poids (kg)", view.weight_kg, _provenance("weight_kg", declared))
    add("taille (cm)", view.height_cm, _provenance("height_cm", declared))
    add(
        "heures dispo par semaine",
        view.hours_per_week,
        _provenance("hours_per_week", declared),
    )
    add("sports", view.sports, _provenance("sports", declared))
    add("objectifs", view.goals, _provenance("goals", declared))
    add("date de course", view.target_race_date, _provenance("target_race_date", declared))
    if view.days_to_race is not None:
        add("jours avant la course", view.days_to_race, MEASURED)

    if view.vdot is not None:
        source = DECLARED if view.vdot_source == "declared" else MEASURED
        add("VDOT", view.vdot, source)

    add("ACWR", view.acwr_ratio, MEASURED)
    if view.acwr_status:
        add("statut de charge", view.acwr_status, MEASURED)
    add("readiness", view.readiness, MEASURED)
    if view.muscle_strain:
        top = dict(sorted(view.muscle_strain.items(), key=lambda kv: -kv[1])[:4])
        add("fatigue musculaire", top, MEASURED)
    add("plan actif", view.active_plan_summary, MEASURED)
    if view.recent_sessions:
        add("séances récentes", len(view.recent_sessions), MEASURED)

    missing = _missing(view)
    if missing:
        lines.append("")
        lines.append(f"Pas encore connu : {', '.join(missing)}.")

    if view.goal_feasibility:
        lines.append("")
        lines.append(view.goal_feasibility)

    return "\n".join(lines)


def _missing(view: Any) -> list[str]:
    """What the profile lacks. Stated as a fact, never as an instruction.

    The previous version said "demande à l'athlète ce qui manque", and the
    model obeyed that every turn instead of listening. Naming the gap and
    saying nothing about what to do with it is the whole difference.
    """
    gaps: list[str] = []
    if not view.sports:
        gaps.append("les sports pratiqués")
    if not view.goals:
        gaps.append("l'objectif")
    if view.vdot is None:
        gaps.append("un chrono de référence")
    if view.target_race_date is None:
        gaps.append("la date de course")
    return gaps
