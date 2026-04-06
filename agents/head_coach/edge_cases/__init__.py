"""
Expose get_alternatives_for_conflict — appelée dans node_process_human_decision
quand l'utilisateur demande d'autres options pour un conflit donné.
"""

from agents.head_coach.edge_cases.scenario_a_1rm_veto import (
    get_alternatives as _alts_a,
)
from agents.head_coach.edge_cases.scenario_b_schedule_conflict import (
    get_alternatives as _alts_b,
)
from agents.head_coach.edge_cases.scenario_c_acwr_event import (
    get_alternatives as _alts_c,
)

_ALTERNATIVES_MAP = {
    "A_1RM_RED_VETO": _alts_a,
    "B_SCHEDULE_DOUBLE": _alts_b,
    "C_ACWR_EVENT_CONFLICT": _alts_c,
}


def get_alternatives_for_conflict(conflict_id: str, state) -> list[str]:
    """Retourne les alternatives pour un conflict_id donné."""
    fn = _ALTERNATIVES_MAP.get(conflict_id)
    if fn is None:
        return []
    return fn(state)
