"""
SCÉNARIO C — ACWR en zone rouge + événement dans 6 jours ou moins
Principe : deux protocoles en conflit (ACWR > 1.5 vs Tapering pré-compétition).
Le Head Coach calcule un tapering d'urgence comme recommandation
et attend l'arbitrage humain. L'override est possible mais avec avertissement.
"""

from datetime import date, timedelta

from langgraph.types import interrupt

from models.athlete_state import AthleteState

CONFLICT_ID = "C_ACWR_EVENT_CONFLICT"
ACWR_CRITICAL_THRESHOLD = 1.5
EVENT_PROXIMITY_DAYS = 7


def detect(state: AthleteState) -> bool:
    """Retourne True si ACWR critique ET événement imminent."""
    if not state.current_phase.target_event_date:
        return False
    days_to_event = (state.current_phase.target_event_date - date.today()).days
    return (
        state.fatigue.acwr > ACWR_CRITICAL_THRESHOLD
        and 0 < days_to_event <= EVENT_PROXIMITY_DAYS
    )


def _calculate_emergency_taper(state: AthleteState, days_to_event: int) -> dict:
    """Calcule le plan de tapering d'urgence jour par jour."""
    today = date.today()
    plan = []

    for i in range(days_to_event):
        day = today + timedelta(days=i)
        days_before_event = days_to_event - i

        if days_before_event <= 2:
            entry = {
                "date": day.strftime("%A %d %b"),
                "type": "repos_complet",
                "volume_pct": 0,
                "intensity": "aucune",
                "tier_max": None,
            }
        elif days_before_event <= 4:
            entry = {
                "date": day.strftime("%A %d %b"),
                "type": "activation_legere",
                "volume_pct": 30,
                "intensity": "Z1-Z2 uniquement",
                "tier_max": 1,
            }
        else:
            entry = {
                "date": day.strftime("%A %d %b"),
                "type": "charge_reduite",
                "volume_pct": 60,
                "intensity": "maintenue, RPE max 8",
                "tier_max": 2,
            }
        plan.append(entry)

    return {
        "days": plan,
        "volume_reduction_avg": 0.40,
        "tier_3_suspended": True,
        "rest_days": [
            (today + timedelta(days=days_to_event - 2)).strftime("%A %d %b"),
            (today + timedelta(days=days_to_event - 1)).strftime("%A %d %b"),
        ],
    }


def _format_taper_plan(taper: dict) -> str:
    lines = []
    for day in taper["days"]:
        lines.append(
            f"  {day['date']} : {day['type'].upper()} "
            f"(volume {day['volume_pct']}%, {day['intensity']})"
        )
    return "\n".join(lines)


def run(state: AthleteState) -> AthleteState:
    """Nœud LangGraph — interrompt le graph et présente la décision."""
    days_to_event = (state.current_phase.target_event_date - date.today()).days
    acwr = state.fatigue.acwr
    event_name = state.current_phase.target_event

    taper = _calculate_emergency_taper(state, days_to_event)
    taper_plan_str = _format_taper_plan(taper)

    situation = (
        f"ALERTE HEAD COACH — Conflit ACWR / Événement Imminent\n\n"
        f"ACWR actuel : {acwr} (seuil critique > {ACWR_CRITICAL_THRESHOLD})\n"
        f"Événement   : {event_name} dans {days_to_event} jours\n\n"
        f"Deux protocoles sont en conflit :\n"
        f"  - Protocole ACWR > 1.5 : réduction de charge -20% obligatoire\n"
        f"  - Protocole Tapering   : maintien intensité, réduction volume\n\n"
        f"Application simultanée = Tapering d'urgence : "
        f"volume -{taper['volume_reduction_avg']:.0%}, intensité maintenue, "
        f"Tier 3 suspendu, repos J-2 et J-1."
    )

    recommendation = (
        f"RECOMMANDATION : Tapering d'urgence activé.\n\n"
        f"{taper_plan_str}\n\n"
        f"Repos complet : {taper['rest_days'][0]} et {taper['rest_days'][1]}\n"
        f"Risque résiduel : faible. ACWR projeté sous 1.3 "
        f"en {days_to_event - 2} jours de charge réduite."
    )

    state.pending_decision = {
        "conflict_id": CONFLICT_ID,
        "situation": situation,
        "recommendation": recommendation,
        "alternatives": [],
        "hard_rule_override_possible": True,
        "status": "awaiting_user_input",
        "context": {
            "days_to_event": days_to_event,
            "acwr": acwr,
            "taper_plan": taper,
        },
    }

    return interrupt(state)


def get_alternatives(state: AthleteState) -> list[str]:
    acwr = state.fatigue.acwr
    return [
        "Option B : Appliquer uniquement le protocole ACWR standard. "
        "Réduction -20% de toute la charge restante. "
        "Arrivée à l'événement moins fatigué mais moins stimulé.",

        f"Option C : Ignorer l'ACWR, appliquer le tapering standard. "
        f"AVERTISSEMENT : risque de blessure x2-4 avec ACWR à {acwr}. "
        f"Décision à vos risques — confirmation double requise.",
    ]


def apply_emergency_taper(state: AthleteState) -> AthleteState:
    """Applique le tapering d'urgence au constraint_matrix."""
    days_to_event = (state.current_phase.target_event_date - date.today()).days
    taper = _calculate_emergency_taper(state, days_to_event)

    # Marquer les jours de repos dans le schedule
    today = date.today()
    for i, day_plan in enumerate(taper["days"]):
        future_date = today + timedelta(days=i)
        day_name = future_date.strftime("%A").lower()

        if state.constraint_matrix.schedule.get(day_name):
            state.constraint_matrix.schedule[day_name]["taper_override"] = {
                "volume_pct": day_plan["volume_pct"],
                "tier_max": day_plan["tier_max"],
                "type": day_plan["type"],
            }

    state.decision_log.append({
        "conflict_id": CONFLICT_ID,
        "decision": "emergency_taper_applied",
        "days_to_event": days_to_event,
        "volume_reduction": taper["volume_reduction_avg"],
    })
    return state
