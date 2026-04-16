"""Node functions for the LangGraph coaching planning graph.

Each node takes (state: AthleteCoachingState, config: RunnableConfig) and returns a
partial state dict. All domain objects are serialized to/from plain dicts
because LangGraph MemorySaver requires JSON-serializable state.

DB session is passed via config["configurable"]["db"] — never stored in state.
"""
from __future__ import annotations

import dataclasses
import json
import uuid
from datetime import date, timedelta

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from ..agents.base import AgentContext, AgentRecommendation
from ..agents.head_coach import HeadCoach, WeeklyPlan
from ..core.acwr import ACWRResult, ACWRStatus
from ..core.acwr import compute_acwr as _compute_acwr
from ..core.conflict import Conflict, ConflictSeverity, detect_conflicts
from ..core.fatigue import aggregate_fatigue
from ..core.goal_analysis import analyze_goals
from ..core.periodization import get_current_phase
from ..routes._agent_factory import build_agents
from ..schemas.athlete import AthleteProfile, Sport
from ..schemas.fatigue import FatigueScore
from ..schemas.plan import WorkoutSlot
from .state import AthleteCoachingState

# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------


def _acwr_to_dict(acwr: ACWRResult) -> dict:
    return {
        "ratio": acwr.ratio,
        "status": acwr.status.value,
        "acute_7d": acwr.acute_7d,
        "chronic_28d": acwr.chronic_28d,
        "max_safe_weekly_load": acwr.max_safe_weekly_load,
    }


def _acwr_from_dict(d: dict) -> ACWRResult:
    return ACWRResult(
        ratio=d["ratio"],
        status=ACWRStatus(d["status"]),
        acute_7d=d["acute_7d"],
        chronic_28d=d["chronic_28d"],
        max_safe_weekly_load=d["max_safe_weekly_load"],
    )


def _conflict_to_dict(c: Conflict) -> dict:
    return {
        "severity": c.severity.value,
        "rule": c.rule,
        "agents": c.agents,
        "message": c.message,
    }


def _conflict_from_dict(d: dict) -> Conflict:
    return Conflict(
        severity=ConflictSeverity(d["severity"]),
        rule=d["rule"],
        agents=d.get("agents", []),
        message=d.get("message", ""),
    )


def _rec_to_dict(r: AgentRecommendation) -> dict:
    return {
        "agent_name": r.agent_name,
        "weekly_load": r.weekly_load,
        "fatigue_score": r.fatigue_score.model_dump(),
        "suggested_sessions": [s.model_dump(mode="json") for s in r.suggested_sessions],
        "readiness_modifier": r.readiness_modifier,
        "notes": r.notes,
    }


def _rec_from_dict(d: dict) -> AgentRecommendation:
    fatigue = FatigueScore(**d["fatigue_score"])
    sessions = [WorkoutSlot.model_validate(s) for s in d.get("suggested_sessions", [])]
    return AgentRecommendation(
        agent_name=d["agent_name"],
        weekly_load=d["weekly_load"],
        fatigue_score=fatigue,
        suggested_sessions=sessions,
        readiness_modifier=d.get("readiness_modifier", 1.0),
        notes=d.get("notes", ""),
    )


def _weekly_plan_to_dict(plan: WeeklyPlan) -> dict:
    return {
        "phase": plan.phase.phase.value,
        "acwr": _acwr_to_dict(plan.acwr),
        "global_fatigue": dataclasses.asdict(plan.global_fatigue),
        "conflicts": [_conflict_to_dict(c) for c in plan.conflicts],
        "sessions": [s.model_dump(mode="json") for s in plan.sessions],
        "readiness_level": plan.readiness_level,
        "notes": plan.notes,
    }


def _athlete_from_dict(d: dict) -> AthleteProfile:
    return AthleteProfile.model_validate(d)


# ---------------------------------------------------------------------------
# Node 1: analyze_profile
# ---------------------------------------------------------------------------


def analyze_profile(state: AthleteCoachingState, config: RunnableConfig) -> dict:
    """Compute goal-driven sport budgets from athlete profile."""
    athlete = _athlete_from_dict(state["athlete_dict"])
    budgets_enum = analyze_goals(athlete)
    budgets = {sport.value: hours for sport, hours in budgets_enum.items()}
    return {
        "budgets": budgets,
        "messages": [AIMessage(f"Budgets calculés: {budgets}")],
    }


# ---------------------------------------------------------------------------
# Node 2: compute_acwr
# ---------------------------------------------------------------------------


def compute_acwr(state: AthleteCoachingState, config: RunnableConfig) -> dict:
    """Compute ACWR from load history + projected weekly load from recommendations."""
    recs = [_rec_from_dict(d) for d in state.get("recommendations_dicts", [])]
    weekly_load = sum(r.weekly_load for r in recs)
    load_history = list(state.get("load_history", []))
    acwr = _compute_acwr(load_history + [weekly_load])
    return {
        "acwr_dict": _acwr_to_dict(acwr),
        "messages": [AIMessage(f"ACWR calculé: ratio={acwr.ratio}, status={acwr.status.value}")],
    }


# ---------------------------------------------------------------------------
# Node 3: delegate_specialists
# ---------------------------------------------------------------------------


def delegate_specialists(state: AthleteCoachingState, config: RunnableConfig) -> dict:
    """Invoke all sport-specific specialist agents and collect recommendations."""
    athlete = _athlete_from_dict(state["athlete_dict"])
    budgets_str = state.get("budgets", {})

    # Convert string keys back to Sport enum for sport_budgets
    sport_budgets: dict[str, float] = {}
    for key, val in budgets_str.items():
        try:
            sport_budgets[Sport(key).value] = val
        except ValueError:
            sport_budgets[key] = val

    today = date.today()
    end = today + timedelta(days=6)
    phase = get_current_phase(athlete.target_race_date, today)

    context = AgentContext(
        athlete=athlete,
        date_range=(today, end),
        phase=phase.phase.value,
        sport_budgets=sport_budgets,
    )

    agents = build_agents(athlete)
    recs = [a.analyze(context) for a in agents]

    return {
        "recommendations_dicts": [_rec_to_dict(r) for r in recs],
        "messages": [AIMessage(f"{len(recs)} recommandations collectées des agents spécialistes.")],
    }


# ---------------------------------------------------------------------------
# Node 4: merge_recommendations (no-op pass-through)
# ---------------------------------------------------------------------------


def merge_recommendations(state: AthleteCoachingState, config: RunnableConfig) -> dict:
    """No-op pass-through — future hook for cross-agent merging logic."""
    return {}


# ---------------------------------------------------------------------------
# Node 5: detect_conflicts_node
# ---------------------------------------------------------------------------


def detect_conflicts_node(state: AthleteCoachingState, config: RunnableConfig) -> dict:
    """Detect scheduling conflicts between agent recommendations."""
    recs = [_rec_from_dict(d) for d in state.get("recommendations_dicts", [])]
    conflicts = detect_conflicts(recs)
    return {
        "conflicts_dicts": [_conflict_to_dict(c) for c in conflicts],
        "messages": [AIMessage(f"{len(conflicts)} conflits détectés.")],
    }


# ---------------------------------------------------------------------------
# Node 6: resolve_conflicts_node
# ---------------------------------------------------------------------------


def resolve_conflicts_node(state: AthleteCoachingState, config: RunnableConfig) -> dict:
    """Pass-through logging node — actual conflict resolution is handled by HeadCoach._arbitrate in build_proposed_plan.

    This node filters for critical conflicts and logs them, but makes no state
    changes. The duplicate resolution logic previously here has been removed to
    avoid conflicts with _arbitrate's authoritative session-dropping behaviour.
    """
    conflicts = [_conflict_from_dict(d) for d in state.get("conflicts_dicts", [])]
    critical = [c for c in conflicts if c.severity == ConflictSeverity.CRITICAL]
    return {
        "messages": [
            AIMessage(
                f"{len(critical)} conflits critiques détectés — résolution déléguée à HeadCoach._arbitrate."
            )
        ],
    }


# ---------------------------------------------------------------------------
# Node 7: build_proposed_plan
# ---------------------------------------------------------------------------


def build_proposed_plan(state: AthleteCoachingState, config: RunnableConfig) -> dict:
    """Build the proposed WeeklyPlan from recommendations, ACWR, and conflicts."""
    athlete = _athlete_from_dict(state["athlete_dict"])
    recs = [_rec_from_dict(d) for d in state.get("recommendations_dicts", [])]
    conflicts = [_conflict_from_dict(d) for d in state.get("conflicts_dicts", [])]

    acwr_dict = state.get("acwr_dict")
    if acwr_dict:
        acwr = _acwr_from_dict(acwr_dict)
    else:
        acwr = _compute_acwr([])

    # Aggregate fatigue
    global_fatigue = aggregate_fatigue([r.fatigue_score for r in recs])

    # Compute readiness
    readiness_modifier = min((r.readiness_modifier for r in recs), default=1.0)

    # Get phase
    today = date.today()
    phase = get_current_phase(athlete.target_race_date, today)

    # Collect notes
    notes = [r.notes for r in recs if r.notes]

    # Arbitrate sessions using HeadCoach._arbitrate
    hc = HeadCoach(agents=[])
    all_sessions = [s for r in recs for s in r.suggested_sessions]
    sessions = hc._arbitrate(all_sessions, conflicts, acwr, readiness_modifier)
    readiness_level = hc._modifier_to_level(readiness_modifier)

    plan = WeeklyPlan(
        phase=phase,
        acwr=acwr,
        global_fatigue=global_fatigue,
        conflicts=conflicts,
        sessions=sessions,
        readiness_level=readiness_level,
        notes=notes,
    )

    return {
        "proposed_plan_dict": _weekly_plan_to_dict(plan),
        "messages": [
            AIMessage(
                f"Plan proposé: {len(sessions)} séances, phase={phase.phase.value}, readiness={readiness_level}"
            )
        ],
    }


# ---------------------------------------------------------------------------
# Node 8: apply_energy_snapshot
# ---------------------------------------------------------------------------


def apply_energy_snapshot(state: AthleteCoachingState, config: RunnableConfig) -> dict:
    """Apply today's energy snapshot to scale session durations if intensity cap < 1.0."""
    athlete_id = state["athlete_id"]
    db = config.get("configurable", {}).get("db")

    # Import via importlib to ensure we use the app. module path (same as the one
    # loaded by pytest), avoiding SQLAlchemy double-table-registration conflicts.
    import importlib

    _ecs_mod = importlib.import_module("app.services.energy_cycle_service")
    _EnergyCycleService = _ecs_mod.EnergyCycleService
    svc = _EnergyCycleService()
    snapshot = svc.get_today_snapshot(athlete_id, db)

    if snapshot is None:
        return {
            "energy_snapshot_dict": None,
            "messages": [AIMessage("Pas de check-in énergie aujourd'hui — plan non modifié.")],
        }

    cap = float(snapshot.recommended_intensity_cap)
    snapshot_dict = {
        "intensity_cap": cap,
        "veto_triggered": bool(snapshot.veto_triggered),
        "objective_score": float(snapshot.objective_score)
        if snapshot.objective_score is not None
        else None,
        "subjective_score": float(snapshot.subjective_score)
        if snapshot.subjective_score is not None
        else None,
        "allostatic_score": float(snapshot.allostatic_score),
        "energy_availability": float(snapshot.energy_availability),
    }

    # Scale session durations if cap < 1.0
    proposed = state.get("proposed_plan_dict")
    if proposed and cap < 1.0:
        sessions = proposed.get("sessions", [])
        scaled = []
        for s in sessions:
            new_duration = max(1, int(s["duration_min"] * cap))
            scaled.append({**s, "duration_min": new_duration})
        proposed = {**proposed, "sessions": scaled}

        return {
            "energy_snapshot_dict": snapshot_dict,
            "proposed_plan_dict": proposed,
            "messages": [
                AIMessage(f"Energy snapshot appliqué: intensity_cap={cap:.2f}, séances ajustées.")
            ],
        }

    return {
        "energy_snapshot_dict": snapshot_dict,
        "messages": [AIMessage(f"Energy snapshot chargé: intensity_cap={cap:.2f}.")],
    }


# ---------------------------------------------------------------------------
# Node 9: present_to_athlete
# ---------------------------------------------------------------------------


def present_to_athlete(state: AthleteCoachingState, config: RunnableConfig) -> dict:
    """Present the proposed plan to the athlete and wait for approval (interrupt handled by graph)."""
    return {
        "messages": [AIMessage("Plan présenté à l'athlète — en attente de validation.")],
    }


# ---------------------------------------------------------------------------
# Node 10: revise_plan
# ---------------------------------------------------------------------------


def revise_plan(state: AthleteCoachingState, config: RunnableConfig) -> dict:
    """Clear the proposed plan so the graph loops back to rebuild it with feedback."""
    feedback = state.get("human_feedback", "")
    return {
        "human_approved": False,
        "human_feedback": None,
        "proposed_plan_dict": None,
        "messages": [
            AIMessage(f"Plan rejeté par l'athlète. Feedback: {feedback}. Replanification en cours…")
        ],
    }


# ---------------------------------------------------------------------------
# Node 11: finalize_plan
# ---------------------------------------------------------------------------


def finalize_plan(state: AthleteCoachingState, config: RunnableConfig) -> dict:
    """Persist the approved plan to the database and return final_plan_dict."""
    if not state.get("human_approved"):
        raise ValueError("Cannot finalize: human_approved is False")

    # Lazy import via app. path to avoid SQLAlchemy double-table-registration.
    # Import V3 models FIRST so the mapper can resolve EnergySnapshotModel
    # back-references on AthleteModel when TrainingPlanModel is instantiated.
    import importlib

    importlib.import_module("app.models.schemas")  # registers V3 SA models
    _db_models = importlib.import_module("app.db.models")
    TrainingPlanModel = _db_models.TrainingPlanModel
    db = config.get("configurable", {}).get("db")
    if db is None:
        raise ValueError("finalize_plan: config['configurable']['db'] is required")
    athlete_id = state["athlete_id"]
    plan_dict = state["proposed_plan_dict"]

    today = date.today()
    end_date = today + timedelta(days=6)

    sessions = plan_dict.get("sessions", [])
    total_weekly_hours = sum(s.get("duration_min", 0) for s in sessions) / 60.0
    acwr_val = plan_dict.get("acwr", {}).get("ratio", 0.0)

    plan_id = str(uuid.uuid4())
    plan_model = TrainingPlanModel(
        id=plan_id,
        athlete_id=athlete_id,
        start_date=today,
        end_date=end_date,
        phase=plan_dict.get("phase", "general_prep"),
        total_weekly_hours=total_weekly_hours,
        acwr=acwr_val,
        weekly_slots_json=json.dumps(sessions),
        status="active",
    )

    db.add(plan_model)
    db.commit()
    db.refresh(plan_model)

    final_plan_dict = {**plan_dict, "db_plan_id": plan_model.id}

    return {
        "final_plan_dict": final_plan_dict,
        "messages": [AIMessage(f"Plan finalisé et persisté (id={plan_model.id}).")],
    }
