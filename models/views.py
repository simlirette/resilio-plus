"""
AGENT VIEWS — Resilio+
Filtrage de l'AthleteState par agent (token economy §2.3 du master doc).
Chaque agent reçoit uniquement les champs pertinents à son domaine.
"""
from collections.abc import Callable
from enum import Enum

from models.schemas import AthleteStateSchema


class AgentType(str, Enum):
    head_coach = "head_coach"
    running_coach = "running_coach"
    lifting_coach = "lifting_coach"
    swimming_coach = "swimming_coach"
    biking_coach = "biking_coach"
    nutrition_coach = "nutrition_coach"
    recovery_coach = "recovery_coach"


def _head_coach_view(state: AthleteStateSchema) -> dict:
    return state.model_dump(mode="python")


def _running_view(state: AthleteStateSchema) -> dict:
    return {
        "identity": state.profile.model_dump(
            include={"first_name", "age", "sex", "weight_kg"}
        ),
        "goals": state.profile.goals.model_dump(),
        "constraints": {
            "injuries_history": [i.model_dump() for i in state.profile.injuries_history]
        },
        "equipment": state.profile.equipment.model_dump(),
        "available_days": {
            k: v.model_dump() for k, v in state.profile.available_days.items()
        },
        "running_profile": state.running_profile.model_dump(),
        "fatigue": {
            "acwr_by_sport_running": state.fatigue.acwr_by_sport.running,
            "hrv_rmssd_today": state.fatigue.hrv_rmssd_today,
            "recovery_score_today": state.fatigue.recovery_score_today,
        },
        "current_phase": state.current_phase.model_dump(),
    }


def _lifting_view(state: AthleteStateSchema) -> dict:
    return {
        "identity": state.profile.model_dump(
            include={"first_name", "age", "sex", "weight_kg"}
        ),
        "goals": state.profile.goals.model_dump(),
        "constraints": {
            "injuries_history": [i.model_dump() for i in state.profile.injuries_history]
        },
        "equipment": state.profile.equipment.model_dump(),
        "available_days": {
            k: v.model_dump() for k, v in state.profile.available_days.items()
        },
        "lifting_profile": state.lifting_profile.model_dump(),
        "fatigue": {
            "acwr_by_sport_lifting": state.fatigue.acwr_by_sport.lifting,
            "fatigue_by_muscle": state.fatigue.fatigue_by_muscle,
            "cns_load_7day_avg": state.fatigue.cns_load_7day_avg,
            "recovery_score_today": state.fatigue.recovery_score_today,
        },
        "current_phase": state.current_phase.model_dump(),
    }


def _swimming_view(state: AthleteStateSchema) -> dict:
    return {
        "identity": state.profile.model_dump(
            include={"first_name", "age", "sex", "weight_kg"}
        ),
        "goals": state.profile.goals.model_dump(),
        "constraints": {
            "injuries_history": [i.model_dump() for i in state.profile.injuries_history]
        },
        "equipment": state.profile.equipment.model_dump(),
        "swimming_profile": state.swimming_profile.model_dump(),
        "fatigue": {
            "hrv_rmssd_today": state.fatigue.hrv_rmssd_today,
            "recovery_score_today": state.fatigue.recovery_score_today,
        },
        "current_phase": state.current_phase.model_dump(),
    }


def _biking_view(state: AthleteStateSchema) -> dict:
    return {
        "identity": state.profile.model_dump(
            include={"first_name", "age", "sex", "weight_kg"}
        ),
        "goals": state.profile.goals.model_dump(),
        "constraints": {
            "injuries_history": [i.model_dump() for i in state.profile.injuries_history]
        },
        "equipment": state.profile.equipment.model_dump(),
        "biking_profile": state.biking_profile.model_dump(),
        "fatigue": {
            "acwr_by_sport_biking": state.fatigue.acwr_by_sport.biking,
            "hrv_rmssd_today": state.fatigue.hrv_rmssd_today,
            "recovery_score_today": state.fatigue.recovery_score_today,
        },
        "current_phase": state.current_phase.model_dump(),
    }


def _nutrition_view(state: AthleteStateSchema) -> dict:
    return {
        "identity": state.profile.model_dump(
            include={"first_name", "age", "sex", "weight_kg"}
        ),
        "goals": state.profile.goals.model_dump(),
        "constraints": {
            "injuries_history": [i.model_dump() for i in state.profile.injuries_history]
        },
        "nutrition_profile": state.nutrition_profile.model_dump(),
        "weekly_volumes": state.weekly_volumes.model_dump(),
        "current_phase": state.current_phase.model_dump(),
    }


def _recovery_view(state: AthleteStateSchema) -> dict:
    return {
        "identity": state.profile.model_dump(
            include={"first_name", "age", "sex", "weight_kg"}
        ),
        "constraints": {
            "injuries_history": [i.model_dump() for i in state.profile.injuries_history]
        },
        "fatigue": state.fatigue.model_dump(),
        "weekly_volumes": state.weekly_volumes.model_dump(),
        "compliance": state.compliance.model_dump(),
        "current_phase": state.current_phase.model_dump(),
    }


AGENT_VIEW_MAP: dict[AgentType, Callable[[AthleteStateSchema], dict]] = {
    AgentType.head_coach: _head_coach_view,
    AgentType.running_coach: _running_view,
    AgentType.lifting_coach: _lifting_view,
    AgentType.swimming_coach: _swimming_view,
    AgentType.biking_coach: _biking_view,
    AgentType.nutrition_coach: _nutrition_view,
    AgentType.recovery_coach: _recovery_view,
}


def get_agent_view(state: AthleteStateSchema, agent: AgentType) -> dict:
    """Filtre l'AthleteState selon les permissions de l'agent (master doc §2.3)."""
    return AGENT_VIEW_MAP[agent](state)
