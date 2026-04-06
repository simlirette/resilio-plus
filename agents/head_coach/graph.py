"""
HEAD COACH GRAPH — LangGraph V1 (lite)
Orchestration principale du système multi-agents Resilio+.

Architecture : hub-and-spoke
- Le Head Coach est le nœud central
- Tous les agents spécialistes sont des nœuds feuilles
- Le Recovery Coach gate chaque séance AVANT la prescription
- Les edge cases interrompent le graph pour une décision humaine (interrupt)

V1 features : StateGraph, nodes, conditional edges, interrupt
V2 features (plus tard) : streaming distribué, persistence externe, parallélisme
"""

import json
from datetime import date
from pathlib import Path
from typing import Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from agents.head_coach.edge_cases.scenario_a_1rm_veto import (
    detect as detect_scenario_a,
)
from agents.head_coach.edge_cases.scenario_a_1rm_veto import (
    run as run_scenario_a,
)
from agents.head_coach.edge_cases.scenario_b_schedule_conflict import (
    detect as detect_scenario_b,
)
from agents.head_coach.edge_cases.scenario_b_schedule_conflict import (
    run as run_scenario_b,
)
from agents.head_coach.edge_cases.scenario_c_acwr_event import (
    detect as detect_scenario_c,
)
from agents.head_coach.edge_cases.scenario_c_acwr_event import (
    run as run_scenario_c,
)
from agents.lifting_coach.agent import LiftingCoachAgent
from agents.running_coach.agent import RunningCoachAgent
from core.acwr import compute_ewma_acwr
from models.athlete_state import AthleteState

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

_MUSCLE_OVERLAP_CACHE: dict | None = None


def _load_muscle_overlap() -> dict:
    """Charge muscle_overlap.json une fois (cache module-level)."""
    global _MUSCLE_OVERLAP_CACHE
    if _MUSCLE_OVERLAP_CACHE is None:
        path = Path(__file__).parents[2] / "data" / "muscle_overlap.json"
        _MUSCLE_OVERLAP_CACHE = json.loads(path.read_text()) if path.exists() else {}
    return _MUSCLE_OVERLAP_CACHE


_AGENT_REGISTRY: dict[str, object] = {
    "running": RunningCoachAgent(),
    "lifting": LiftingCoachAgent(),
}

# ─────────────────────────────────────────────
# NŒUDS DU GRAPH
# ─────────────────────────────────────────────

def node_load_athlete_state(state: AthleteState) -> AthleteState:
    """
    Nœud 1 : Calculer les champs dérivés depuis l'AthleteState.
    L'AthleteState est pré-chargé depuis la DB par l'appelant (API route).
    Ce nœud calcule l'ACWR EWMA et met à jour acwr_computed.
    """
    daily_loads = state.constraint_matrix.schedule.get("_daily_loads_28d", [])
    if daily_loads and isinstance(daily_loads, list):
        _, _, acwr = compute_ewma_acwr(daily_loads)
        state.acwr_computed = acwr
        if state.fatigue.acwr is None:
            state.fatigue.acwr = acwr
    else:
        state.acwr_computed = state.fatigue.acwr
    return state


def node_recovery_gate(state: AthleteState) -> AthleteState:
    """
    Nœud 2 : Recovery Coach évalue le readiness du jour.
    Calcule le Readiness Score et détermine vert/jaune/rouge.
    Modifie l'AthleteState avec fatigue.recovery_score_today et readiness_color.
    """
    # TODO Session 8 : implémenter le calcul complet du Readiness Score
    # Formule : HRV(30%) + Sommeil(25%) + ACWR(25%) + FC repos(10%) + Subjectif(10%)
    return state


def node_detect_conflicts(state: AthleteState) -> AthleteState:
    """
    Nœud 3 : Détecter les conflits sur 3 couches.
    Couche 1 : Scheduling (sessions > jours disponibles)
    Couche 2 : Overlap musculaire (jours consécutifs)
    Couche 3 : Fatigue cumulée (ACWR zones caution/danger)
    """
    conflicts = []

    # ── Couche 1 : Scheduling ────────────────────────────────────────────────
    available_days = [
        day for day, avail in state.profile.available_days.items()
        if avail.available
    ]
    sessions_planned = sum(
        1 for sessions in state.constraint_matrix.schedule.values()
        if isinstance(sessions, dict) and sessions.get("assigned")
    )
    if sessions_planned > len(available_days):
        conflicts.append({
            "layer": "scheduling",
            "severity": "warning",
            "message": (
                f"{sessions_planned} sessions planifiées pour "
                f"{len(available_days)} jours disponibles."
            ),
        })

    # ── Couche 2 : Overlap musculaire ────────────────────────────────────────
    _load_muscle_overlap()
    schedule = state.constraint_matrix.schedule
    day_order = [
        "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
    ]
    for i, day in enumerate(day_order[:-1]):
        next_day = day_order[i + 1]
        today_session = schedule.get(day, {})
        next_session = schedule.get(next_day, {})
        if not isinstance(today_session, dict) or not isinstance(next_session, dict):
            continue
        today_muscles = set(today_session.get("primary_muscles", []))
        next_muscles = set(next_session.get("primary_muscles", []))
        overlap = today_muscles & next_muscles
        if overlap:
            conflicts.append({
                "layer": "muscle_overlap",
                "severity": "warning",
                "days": [day, next_day],
                "muscles": sorted(overlap),
                "message": (
                    f"Overlap musculaire {day}/{next_day} : "
                    f"{', '.join(sorted(overlap))} sollicités < 24h d'intervalle."
                ),
            })

    # ── Couche 3 : Fatigue (ACWR) ────────────────────────────────────────────
    acwr = state.acwr_computed or state.fatigue.acwr or 0.0
    if acwr > 1.5:
        conflicts.append({
            "layer": "fatigue",
            "severity": "danger",
            "acwr": acwr,
            "message": (
                f"ACWR = {acwr:.2f} > 1.5 — zone danger. "
                "Risque de blessure élevé. Réduction de charge obligatoire."
            ),
        })
    elif acwr > 1.3:
        conflicts.append({
            "layer": "fatigue",
            "severity": "caution",
            "acwr": acwr,
            "message": (
                f"ACWR = {acwr:.2f} entre 1.3 et 1.5 — zone attention. "
                "Surveiller la récupération cette semaine."
            ),
        })

    state.pending_conflicts = conflicts
    state.conflicts_resolved = len(conflicts) == 0
    return state


def node_check_edge_cases(state: AthleteState) -> AthleteState:
    """
    Nœud 4 : Vérifier les scénarios extrêmes.
    Si un edge case est détecté → interrupt + attente décision humaine.
    """
    # Scénario A : Test 1RM + veto rouge Recovery Coach
    if detect_scenario_a(state):
        return run_scenario_a(state)  # Déclenche interrupt()

    # Scénario B : Jours indisponibles imprévus
    unavailable_days = state.reported_unavailable_days or []
    if unavailable_days and detect_scenario_b(state, unavailable_days):
        return run_scenario_b(state, unavailable_days)  # Déclenche interrupt()

    # Scénario C : ACWR rouge + événement imminent
    if detect_scenario_c(state):
        return run_scenario_c(state)  # Déclenche interrupt()

    return state


def node_process_human_decision(state: AthleteState) -> AthleteState:
    """
    Nœud 5 : Traiter la décision humaine après un interrupt.
    user_input peut être :
    - "CONFIRM" → appliquer la recommandation
    - "OTHER_OPTIONS" → générer des alternatives et re-interrupt
    - "CUSTOM: <texte>" → valider et appliquer la décision custom
    """
    decision = state.pending_decision
    user_input = state.user_decision_input or ""

    if not user_input or not decision:
        return state

    if user_input == "CONFIRM":
        state.pending_decision["status"] = "confirmed"
        state.decision_log.append({
            "conflict_id": decision["conflict_id"],
            "decision": "confirmed_recommendation",
            "timestamp": date.today().isoformat(),
        })

    elif user_input == "OTHER_OPTIONS":
        # Importer les alternatives depuis le module correspondant
        from agents.head_coach.edge_cases import get_alternatives_for_conflict
        alternatives = get_alternatives_for_conflict(decision["conflict_id"], state)
        state.pending_decision["alternatives"] = alternatives
        state.pending_decision["status"] = "awaiting_user_input"
        return interrupt(state)  # Re-interrupt avec les alternatives

    elif user_input.startswith("CUSTOM:"):
        custom_text = user_input.replace("CUSTOM:", "").strip()
        # Valider que la décision custom ne viole pas les hard rules
        if decision.get("hard_rule_override_possible", True):
            state.pending_decision["user_choice"] = custom_text
            state.pending_decision["status"] = "confirmed"
            state.decision_log.append({
                "conflict_id": decision["conflict_id"],
                "decision": "custom",
                "custom_text": custom_text,
                "timestamp": date.today().isoformat(),
            })
        else:
            # Hard rule : ne peut pas être overridé
            state.pending_decision["warning"] = (
                "Cette décision viole une règle absolue du système. "
                "Choisissez parmi les options proposées."
            )
            return interrupt(state)

    state.pending_decision = None
    state.user_decision_input = None
    return state


def node_delegate_to_agents(state: AthleteState) -> AthleteState:
    """
    Nœud 6 : Head Coach délègue la prescription aux agents spécialistes actifs.
    En S5 : Running + Lifting uniquement (stubs déterministes sans LLM).
    En S6+ : tous les agents avec prescriptions LLM.
    """
    active_sports = state.profile.active_sports or ["running", "lifting"]
    partial_plans = {}

    for sport in active_sports:
        agent = _AGENT_REGISTRY.get(sport)
        if agent is not None:
            partial_plans[sport] = agent.run(state)

    state.partial_plans = partial_plans
    return state


def node_resolve_conflicts(state: AthleteState) -> AthleteState:
    """
    Nœud 7 : Résoudre les conflits inter-agents.
    Menu de résolution (dans l'ordre) :
    1. Swap de jours
    2. Changer le split
    3. Réduire l'intensité (Z3→Z2, Tier 3→Tier 1)
    4. Réduire le volume (-20-30%)
    5. Substituer les exercices
    6. Supprimer la séance (dernier recours)
    Circuit breaker : max 2 itérations.
    """
    # TODO Session 9 : implémenter la résolution complète
    return state


def node_merge_plans(state: AthleteState) -> AthleteState:
    """
    Nœud 8 : Fusionner les plans partiels en un plan unifié.
    Valider que le plan respecte la constraint_matrix.
    """
    # TODO Session 9 : implémenter la fusion
    return state


def node_nutrition_prescription(state: AthleteState) -> AthleteState:
    """
    Nœud 9 : Nutrition Coach prescrit les macros et repas.
    Reçoit le plan d'entraînement VALIDÉ — jamais en parallèle.
    """
    # TODO Session 15 : implémenter le Nutrition Coach
    return state


def node_present_plan_to_user(state: AthleteState) -> AthleteState:
    """
    Nœud 10 : Présenter le plan complet à l'utilisateur.
    L'utilisateur confirme, demande des modifications, ou pose des questions.
    """
    # Toujours interrompre ici pour validation utilisateur du plan complet
    state.pending_decision = {
        "conflict_id": "PLAN_CONFIRMATION",
        "situation": "Plan hebdomadaire prêt pour validation.",
        "recommendation": "Confirmer le plan ou demander des ajustements.",
        "status": "awaiting_user_input",
    }
    return interrupt(state)


def node_deploy_plan(state: AthleteState) -> AthleteState:
    """
    Nœud 11 : Déployer le plan vers les apps externes.
    - Push séances lifting → Hevy (JSON compatible)
    - Push séances course → Garmin Connect (JSON compatible)
    - Sauvegarder en DB
    """
    # TODO Session 9 : implémenter le déploiement
    return state


# ─────────────────────────────────────────────
# FONCTIONS DE ROUTING (EDGES CONDITIONNELS)
# ─────────────────────────────────────────────

def route_after_recovery_gate(
    state: AthleteState,
) -> Literal["check_edge_cases", "recovery_blocked"]:
    """
    Après le Recovery Gate : si veto ROUGE absolu → fin (repos forcé).
    Sinon : continuer vers la détection de conflits.
    """
    if state.fatigue.recovery_score_today < 30:
        # Score < 30 = veto absolu, même le Head Coach ne peut pas override
        return "recovery_blocked"
    return "check_edge_cases"


def route_after_edge_cases(
    state: AthleteState,
) -> Literal["delegate_to_agents", "process_human_decision"]:
    """
    Après la vérification des edge cases : si une décision est en attente → attendre.
    Sinon : déléguer aux agents.
    """
    if state.pending_decision and state.pending_decision.get("status") == "awaiting_user_input":
        return "process_human_decision"
    return "delegate_to_agents"


def route_after_conflict_resolution(
    state: AthleteState,
) -> Literal["merge_plans", "delegate_to_agents"]:
    """
    Après la résolution : si une nouvelle itération est nécessaire → re-déléguer.
    Max 2 itérations (circuit breaker).
    """
    iterations = state.resolution_iterations
    if iterations >= 2:
        # Circuit breaker : résolution d'autorité basée sur priority_hierarchy
        return "merge_plans"
    if state.conflicts_resolved:
        return "merge_plans"
    return "delegate_to_agents"


def node_recovery_blocked(state: AthleteState) -> AthleteState:
    """Nœud terminal quand Recovery Coach bloque tout (score < 30)."""
    state.pending_decision = {
        "conflict_id": "RECOVERY_ABSOLUTE_BLOCK",
        "situation": (
            f"Recovery Score : {state.fatigue.recovery_score_today}/100.\n"
            "Repos complet obligatoire. Aucune séance possible aujourd'hui."
        ),
        "recommendation": "Repos complet. Prochaine évaluation demain matin.",
        "status": "confirmed",
        "hard_rule_override_possible": False,
    }
    return state


# ─────────────────────────────────────────────
# CONSTRUCTION DU GRAPH
# ─────────────────────────────────────────────

def build_head_coach_graph() -> StateGraph:
    """
    Construit et compile le graph LangGraph du Head Coach.
    Utilise MemorySaver pour la persistence en mémoire (V1).
    En V2 : remplacer par PostgresSaver pour la persistence DB.
    """
    builder = StateGraph(AthleteState)

    # ── Ajouter les nœuds ─────────────────────────────
    builder.add_node("load_state",              node_load_athlete_state)
    builder.add_node("recovery_gate",           node_recovery_gate)
    builder.add_node("check_edge_cases",        node_check_edge_cases)
    builder.add_node("process_human_decision",  node_process_human_decision)
    builder.add_node("delegate_to_agents",      node_delegate_to_agents)
    builder.add_node("resolve_conflicts",       node_resolve_conflicts)
    builder.add_node("merge_plans",             node_merge_plans)
    builder.add_node("nutrition_prescription",  node_nutrition_prescription)
    builder.add_node("present_plan",            node_present_plan_to_user)
    builder.add_node("deploy_plan",             node_deploy_plan)
    builder.add_node("recovery_blocked",        node_recovery_blocked)

    # ── Edges linéaires ───────────────────────────────
    builder.add_edge(START, "load_state")
    builder.add_edge("load_state", "recovery_gate")

    # ── Edges conditionnels ───────────────────────────
    builder.add_conditional_edges(
        "recovery_gate",
        route_after_recovery_gate,
        {
            "check_edge_cases": "check_edge_cases",
            "recovery_blocked": "recovery_blocked",
        }
    )

    builder.add_conditional_edges(
        "check_edge_cases",
        route_after_edge_cases,
        {
            "delegate_to_agents": "delegate_to_agents",
            "process_human_decision": "process_human_decision",
        }
    )

    # Après décision humaine → toujours revérifier les edge cases
    builder.add_edge("process_human_decision", "check_edge_cases")

    # Suite linéaire
    builder.add_edge("delegate_to_agents", "resolve_conflicts")

    builder.add_conditional_edges(
        "resolve_conflicts",
        route_after_conflict_resolution,
        {
            "merge_plans": "merge_plans",
            "delegate_to_agents": "delegate_to_agents",
        }
    )

    builder.add_edge("merge_plans", "nutrition_prescription")
    builder.add_edge("nutrition_prescription", "present_plan")
    builder.add_edge("present_plan", "deploy_plan")
    builder.add_edge("deploy_plan", END)
    builder.add_edge("recovery_blocked", END)

    # ── Compilation avec checkpointer ─────────────────
    checkpointer = MemorySaver()

    return builder.compile(
        checkpointer=checkpointer,
        interrupt_before=["process_human_decision"],  # Suspend avant traitement décision
    )


# ─────────────────────────────────────────────
# BOUCLE HEBDOMADAIRE (WORKFLOW ALTERNATIF)
# ─────────────────────────────────────────────

def build_weekly_review_graph() -> StateGraph:
    """
    Graph simplifié pour le suivi hebdomadaire.
    Différent du graph de création de plan initial.
    TODO Session 10 : implémenter complètement.
    """
    # H1: Collecte (pull Strava, Hevy, Apple Health)
    # H2: Analyse prévu vs réalisé
    # H3: ACWR update + matrice vivante + ajustements
    # H4: Rapport + feedback utilisateur
    # H5: Planification semaine suivante
    pass


# ─────────────────────────────────────────────
# INSTANCE GLOBALE (singleton)
# ─────────────────────────────────────────────

# Instancier une seule fois au démarrage de l'application
head_coach_graph = build_head_coach_graph()
