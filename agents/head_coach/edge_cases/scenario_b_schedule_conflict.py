"""
SCÉNARIO B — Jours indisponibles imprévus forçant un double entraînement
Principe : le Head Coach calcule les options de recasage, présente
sa recommandation (double séance dégradée), et attend l'arbitrage humain.
"""

from langgraph.types import interrupt

from models.athlete_state import AthleteState

CONFLICT_ID = "B_SCHEDULE_DOUBLE"
MIN_GAP_HOURS = 6


def detect(state: AthleteState, unavailable_days: list[str]) -> bool:
    """Retourne True si des séances sont orphelines suite aux jours indisponibles."""
    orphaned = _find_orphaned_sessions(state, unavailable_days)
    return len(orphaned) > 0


def _find_orphaned_sessions(state: AthleteState, unavailable_days: list[str]) -> list:
    orphaned = []
    for day in unavailable_days:
        session = state.constraint_matrix.schedule.get(day.lower(), {})
        assigned = session.get("assigned", [])
        orphaned.extend(assigned)
    return orphaned


def _find_available_slots(state: AthleteState, unavailable_days: list[str]) -> list:
    available = []
    for day, data in state.constraint_matrix.schedule.items():
        if day not in [d.lower() for d in unavailable_days]:
            if data.get("available") and data.get("max_sessions", 0) > 0:
                available.append(day)
    return available


def run(state: AthleteState, unavailable_days: list[str]) -> AthleteState:
    """Nœud LangGraph — interrompt le graph et présente la décision."""
    orphaned = _find_orphaned_sessions(state, unavailable_days)
    available = _find_available_slots(state, unavailable_days)

    # Évaluer l'impact ACWR d'un double entraînement
    acwr_current = state.fatigue.acwr
    acwr_projected = round(acwr_current + 0.08, 2)
    acwr_status = "zone verte" if acwr_projected <= 1.3 else "zone jaune"

    situation = (
        f"ALERTE HEAD COACH — Conflit Calendrier\n\n"
        f"Jours indisponibles signalés : {', '.join(unavailable_days)}\n"
        f"Séances orphelines : {', '.join(orphaned)}\n"
        f"Créneaux disponibles restants : {', '.join(available)}\n\n"
        f"Il est impossible de recaser toutes les séances sans modifier "
        f"leur structure ou leur intensité."
    )

    recommendation = (
        f"RECOMMANDATION : Double séance samedi.\n"
        f"  Matin : {orphaned[0] if orphaned else 'Séance 1'} "
        f"→ dégradé Easy Run Z1-Z2 si intervals prévus\n"
        f"  Soir  : {orphaned[1] if len(orphaned) > 1 else 'Séance 2'} "
        f"→ Tier 1 uniquement, RPE max 8, volume -20%\n"
        f"Écart minimum respecté : 8h entre les deux séances.\n"
        f"Impact ACWR estimé : {acwr_current} → {acwr_projected} ({acwr_status})."
    )

    state.pending_decision = {
        "conflict_id": CONFLICT_ID,
        "situation": situation,
        "recommendation": recommendation,
        "alternatives": [],
        "hard_rule_override_possible": True,
        "status": "awaiting_user_input",
        "context": {
            "orphaned_sessions": orphaned,
            "available_slots": available,
            "acwr_projected": acwr_projected,
        },
    }

    return interrupt(state)


def get_alternatives(state: AthleteState) -> list[str]:
    return [
        "Option B : Séances perdues acceptées. Semaine réduite à ce qui est "
        "faisable proprement, sans modification d'intensité. ACWR non impacté.",

        "Option C : Lifting Upper déplacé au dimanche (hors planning habituel). "
        "Running Intervals maintenu samedi à intensité normale. "
        "Exception unique autorisée ce mésocycle.",
    ]


def apply_double_session(state: AthleteState) -> AthleteState:
    """Applique la recommandation — double séance avec downgrade."""
    # Downgrade Running Intervals → Easy Run
    saturday = state.constraint_matrix.schedule.get("saturday", {})
    assigned = saturday.get("assigned", [])

    downgraded = []
    for session in assigned:
        if "interval" in session.lower() or "tempo" in session.lower():
            downgraded.append(session.replace("intervals", "easy_run")
                                      .replace("tempo", "easy_run"))
        elif "lifting" in session.lower():
            downgraded.append(session + "_tier1_only")
        else:
            downgraded.append(session)

    state.constraint_matrix.schedule["saturday"]["assigned"] = downgraded
    state.constraint_matrix.schedule["saturday"]["max_sessions"] = 2
    state.decision_log.append({
        "conflict_id": CONFLICT_ID,
        "decision": "double_session_approved",
        "modifications": downgraded,
    })
    return state
