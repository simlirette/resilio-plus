"""The capabilities the coach can call, and nothing else.

The graph used to decide everything — which question, when to extract, when to
finish — and the model only wrote the sentence. That is a narrator. It is why a
direct question went unanswered three times: the model was under orders to
collect, not to converse.

Here the model decides *what the turn is*. These four tools cover exactly what
the athlete asked the coach to do:

    update_profile   — construire son profil
    assess_goal      — analyser ses objectifs
    generate_plan    — créer un plan d'entraînement
    review_training  — faire le suivi

Each wraps machinery that already exists and is already tested. The model never
computes a pace, a zone or a VDOT: no tool accepts one as input. It decides
*when* to ask for one, and how to say the answer.

Every tool returns a result, including on failure. A tool that raised would end
the athlete's turn mid-sentence; one that reports "je n'ai pas pu" lets the
coach say so and carry on.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

logger = logging.getLogger(__name__)

MAX_REVIEW_DAYS = 28


@dataclass(frozen=True)
class ToolContext:
    athlete_id: str
    db: Any


@dataclass(frozen=True)
class ToolResult:
    ok: bool
    content: str


TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "update_profile",
        "description": (
            "Enregistre ce que l'athlète vient de te dire sur lui. N'appelle "
            "cet outil que pour des faits qu'il a énoncés, jamais pour une "
            "supposition. Les valeurs hors bornes physiologiques sont refusées "
            "et te sont signalées."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "age": {"type": "integer"},
                "sex": {"type": "string", "enum": ["M", "F"]},
                "weight_kg": {"type": "number"},
                "height_cm": {"type": "number"},
                "resting_hr": {"type": "integer"},
                "max_hr": {"type": "integer"},
                "sports": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["running", "lifting", "swimming", "biking"],
                    },
                },
                "sports_removed": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "sessions_per_week": {
                    "type": "object",
                    "description": "Nombre de SÉANCES par sport, pas des heures.",
                },
                "hours_per_week": {"type": "number"},
                "goals": {"type": "array", "items": {"type": "string"}},
                "target_race_date": {
                    "type": "string",
                    "description": "AAAA-MM-JJ",
                },
                "race_distance": {
                    "type": "string",
                    "enum": ["mile", "5k", "10k", "15k", "half_marathon", "marathon"],
                    "description": "Une course DÉJÀ COURUE, jamais un objectif.",
                },
                "race_time_seconds": {
                    "type": "integer",
                    "description": "Le chrono de cette course, en secondes.",
                },
                "available_days": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Jours disponibles, lundi = 0.",
                },
                "preferred_session_hour": {
                    "type": "object",
                    "description": (
                        "Heure de la journée par sport, 0-23. Ex : "
                        '{"running": 7, "lifting": 18}.'
                    ),
                },
                "schedule_flexibility": {
                    "type": "string",
                    "enum": ["fixed", "flexible"],
                    "description": (
                        "« fixed » si les créneaux ne bougent pas, « flexible » "
                        "si tu peux déplacer une séance dans la semaine."
                    ),
                },
            },
        },
    },
    {
        "name": "assess_goal",
        "description": (
            "Compare l'objectif déclaré de l'athlète à ce que sa forme actuelle "
            "projette, d'après la table de Daniels. Utilise-le avant de "
            "commenter la faisabilité d'une cible : ne l'évalue jamais de tête."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "generate_plan",
        "description": (
            "Construit la semaine d'entraînement avec les agents spécialistes "
            "(course, musculation, nutrition, récupération) et les règles de "
            "charge. N'appelle cet outil que si le profil est suffisant."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "review_training",
        "description": (
            "Compare ce qui était planifié à ce que l'athlète a réellement fait, "
            "d'après Strava et Hevy. Utilise-le pour le suivi, avant de "
            "commenter une séance manquée ou un écart de charge."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": f"Fenêtre en jours, 1 à {MAX_REVIEW_DAYS}.",
                }
            },
        },
    },
    {
        "name": "offer_connector_links",
        "description": (
            "Génère les liens à usage unique pour connecter Strava, Hevy, Terra "
            "ou Google Calendar. Utilise-le quand l'athlète veut brancher ses "
            "données, ou quand tu as besoin de mesures que tu n'as pas. Ne "
            "fabrique jamais d'URL toi-même."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
]


# ─── Implementations ──────────────────────────────────────────────────────────


def _athlete(ctx: ToolContext) -> Any:
    from ..db.models import AthleteModel

    return ctx.db.get(AthleteModel, ctx.athlete_id)


def _update_profile(args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    from .onboarding_extraction import apply_extraction

    athlete = _athlete(ctx)
    if athlete is None:
        return ToolResult(False, "Athlète introuvable.")

    changed = apply_extraction(athlete, args, ctx.db)
    if not changed:
        return ToolResult(
            True,
            "Rien de nouveau n'a été enregistré. Une valeur hors bornes "
            "plausibles est refusée plutôt que corrigée : redemande-la si elle "
            "compte.",
        )
    return ToolResult(True, "Enregistré : " + ", ".join(changed) + ".")


def _assess_goal(_: dict[str, Any], ctx: ToolContext) -> ToolResult:
    from ..core.head_coach_view_builder import build_head_coach_view

    athlete = _athlete(ctx)
    if athlete is None:
        return ToolResult(False, "Athlète introuvable.")

    view = build_head_coach_view(athlete, ctx.db)
    if view.goal_feasibility:
        return ToolResult(True, view.goal_feasibility)

    if view.vdot is None:
        return ToolResult(
            True,
            "Impossible d'évaluer : aucun VDOT mesuré. Il faut un chrono récent "
            "sur une distance connue, ou des sorties Strava récentes.",
        )
    return ToolResult(
        True,
        "Aucun objectif chiffré à évaluer — l'athlète n'a pas donné de temps "
        "cible.",
    )


def _build_week(ctx: ToolContext) -> dict[str, Any]:
    """Run the planning graph. Split out so tests can replace it."""
    from .graph_invoker import DefaultGraphInvoker

    output = DefaultGraphInvoker().invoke(
        "plan_generation",
        ctx.athlete_id,
        f"{ctx.athlete_id}:plan",
        {},
        ctx.db,
    )
    return output if isinstance(output, dict) else {}


def _generate_plan(_: dict[str, Any], ctx: ToolContext) -> ToolResult:
    from ..messaging.plan_renderer import render_week

    try:
        plan = _build_week(ctx)
    except Exception:
        logger.warning("generate_plan_failed", exc_info=True)
        return ToolResult(
            False,
            "La génération du plan a échoué. Dis-le à l'athlète et propose de "
            "réessayer ; ne fabrique pas de séances.",
        )

    if not plan:
        return ToolResult(False, "Le moteur n'a renvoyé aucune semaine.")
    return ToolResult(True, render_week(plan))


def _completed_sessions(ctx: ToolContext, since: date) -> list[dict[str, Any]]:
    """Everything the athlete actually did, from the connectors."""
    from ..db.models import StravaActivityModel

    done: list[dict[str, Any]] = []
    rows = (
        ctx.db.query(StravaActivityModel)
        .filter(StravaActivityModel.athlete_id == ctx.athlete_id)
        .all()
    )
    for row in rows:
        day = row.started_at.date() if row.started_at else None
        if day is None or day < since:
            continue
        done.append(
            {
                "date": day,
                "sport": row.sport_type or "",
                "duration_min": int((row.duration_s or 0) / 60),
                "distance_km": (row.distance_m or 0) / 1000 or None,
            }
        )
    return done


def _review_training(args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    from ..core.adherence import compare_week, describe_week
    from ..db.models import TrainingPlanModel

    raw_days = args.get("days", 7)
    days = raw_days if isinstance(raw_days, int) else 7
    days = max(1, min(MAX_REVIEW_DAYS, days))
    since = date.today() - timedelta(days=days)

    plan = (
        ctx.db.query(TrainingPlanModel)
        .filter(TrainingPlanModel.athlete_id == ctx.athlete_id)
        .order_by(TrainingPlanModel.created_at.desc())
        .first()
    )
    if plan is None:
        return ToolResult(
            True, "Aucun plan enregistré : il n'y a rien à comparer."
        )

    try:
        slots = json.loads(plan.weekly_slots_json or "[]")
    except (TypeError, ValueError):
        return ToolResult(False, "Le plan enregistré est illisible.")

    planned = [
        slot
        for slot in slots
        if isinstance(slot, dict) and str(slot.get("date", ""))[:10] >= since.isoformat()
    ]
    comparison = compare_week(planned, _completed_sessions(ctx, since))
    return ToolResult(True, describe_week(comparison))


def _offer_connector_links(_: dict[str, Any], ctx: ToolContext) -> ToolResult:
    """Mint the one-shot connect links.

    This used to fire automatically at onboarding block 4. With the blocks gone
    it needs a trigger, and the honest one is the coach deciding it needs data
    it does not have.
    """
    from .deep_link_service import connector_links_message

    invitation = connector_links_message(
        ctx.db,
        athlete_id=ctx.athlete_id,
        heading="**Connecte tes données**",
    )
    if invitation is None:
        return ToolResult(True, "Tout est déjà connecté.")
    return ToolResult(True, invitation)


_IMPLEMENTATIONS = {
    "update_profile": _update_profile,
    "assess_goal": _assess_goal,
    "generate_plan": _generate_plan,
    "review_training": _review_training,
    "offer_connector_links": _offer_connector_links,
}


def run_tool(name: str, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    """Execute one tool call. Never raises."""
    implementation = _IMPLEMENTATIONS.get(name)
    if implementation is None:
        return ToolResult(False, f"Outil inconnu : {name}.")

    try:
        return implementation(args or {}, ctx)
    except Exception:
        logger.warning("tool_failed", extra={"tool": name}, exc_info=True)
        return ToolResult(False, f"L'outil {name} a échoué.")
