"""AthleteState V3 — Nouveaux modèles Pydantic.

Ajoute : EnergySnapshot, HormonalProfile, AllostaticEntry, RecoveryVetoV3, AthleteStateV3
Étend  : get_agent_view() avec les vues V3 (energy_coach, recovery_coach, nutrition_coach)

Référence : docs/resilio-v3-master.md — sections 3.2, 4.3, 5.2, 7.1, 7.2
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Types littéraux partagés
# ---------------------------------------------------------------------------

CyclePhase = Literal["menstrual", "follicular", "ovulation", "luteal"]
TrafficLight = Literal["green", "yellow", "red"]
TrackingSource = Literal["manual", "apple_health"]

# ---------------------------------------------------------------------------
# EnergySnapshot  (section 3.2 / 3.5)
# ---------------------------------------------------------------------------


class EnergySnapshot(BaseModel):
    """Snapshot produit par l'Energy Coach et attaché à AthleteState.

    Contient la charge allostatique courante, l'EA, la charge cognitive et
    le cap d'intensité recommandé pour la journée.
    """

    timestamp: datetime
    allostatic_score: float = Field(..., ge=0.0, le=100.0)
    cognitive_load: float = Field(..., ge=0.0, le=100.0)
    energy_availability: float  # kcal/kg FFM — pas de borne absolue
    cycle_phase: Optional[CyclePhase] = None
    sleep_quality: float = Field(..., ge=0.0, le=100.0)
    recommended_intensity_cap: float = Field(..., ge=0.0, le=1.0)
    veto_triggered: bool
    veto_reason: Optional[str] = None


# ---------------------------------------------------------------------------
# HormonalProfile  (section 4.3)
# ---------------------------------------------------------------------------


class HormonalProfile(BaseModel):
    """Profil du cycle hormonal féminin dans AthleteState.

    Si enabled=False, le cycle n'est pas pris en compte dans les prescriptions.
    """

    enabled: bool
    cycle_length_days: int = Field(default=28, ge=21, le=45)
    current_cycle_day: Optional[int] = Field(default=None, ge=1, le=45)
    current_phase: Optional[CyclePhase] = None
    last_period_start: Optional[date] = None
    tracking_source: TrackingSource = "manual"
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# AllostaticEntry  (section 5.2 / 7.1)
# ---------------------------------------------------------------------------


class AllostaticEntry(BaseModel):
    """Un enregistrement quotidien dans l'historique allostatic (28 jours).

    intensity_cap_applied : cap effectivement appliqué ce jour-là (0.0–1.0).
    components : détail des six sous-scores (hrv, sleep, work, stress, cycle, ea).
    """

    date: date
    allostatic_score: float = Field(..., ge=0.0, le=100.0)
    components: dict  # {"hrv": float, "sleep": float, ...}
    intensity_cap_applied: float = Field(..., ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# RecoveryVetoV3  (section 2.2 / 7.1)
# ---------------------------------------------------------------------------


class RecoveryVetoV3(BaseModel):
    """Veto élargi du Recovery Coach V3.

    Intègre HRV, ACWR, Energy Availability, charge allostatique et phase cycle.
    status / composantes : "green" | "yellow" | "red"
    """

    status: TrafficLight
    hrv_component: TrafficLight
    acwr_component: TrafficLight
    ea_component: TrafficLight
    allostatic_component: TrafficLight
    cycle_component: Optional[TrafficLight] = None
    final_intensity_cap: float = Field(..., ge=0.0, le=1.0)
    veto_triggered: bool
    veto_reasons: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# AthleteStateV3  (section 7.1)
# ---------------------------------------------------------------------------


class AthleteStateV3(BaseModel):
    """Extension V3 de l'AthleteState.

    Hérite du concept V2 mais est défini ici de façon indépendante pour la
    branche v3, sans modifier les modèles existants (frontend/routes/agents).

    Champs obligatoires : athlete_id, recovery_coach_veto
    Champs optionnels V3 : energy_snapshot, hormonal_profile, allostatic_history
    """

    athlete_id: str
    energy_snapshot: Optional[EnergySnapshot] = None
    hormonal_profile: Optional[HormonalProfile] = None
    allostatic_history: list[AllostaticEntry] = Field(default_factory=list)
    recovery_coach_veto: RecoveryVetoV3


# ---------------------------------------------------------------------------
# get_agent_view()  (section 7.2)
# ---------------------------------------------------------------------------

_AGENT_VIEWS: dict[str, list[str] | str] = {
    "head_coach": "FULL",
    "energy_coach": [
        "energy_snapshot",
        "hormonal_profile",
        "allostatic_history",
        "sleep_data",
        "nutrition_summary",
    ],
    "recovery_coach": [
        "hrv_data",
        "sleep_data",
        "acwr",
        "energy_snapshot",      # nouveau V3
        "hormonal_profile",     # nouveau V3
        "fatigue_snapshots",
    ],
    "nutrition_coach": [
        "nutrition_profile",
        "training_today",
        "energy_snapshot",      # EA en temps réel
        "hormonal_profile",     # besoins nutritionnels par phase
        "body_composition",
    ],
    # Agents inchangés vs V2 — vues minimales non étendues
    "running_coach": [
        "training_today",
        "acwr",
        "vdot",
        "fatigue_snapshots",
    ],
    "lifting_coach": [
        "training_today",
        "acwr",
        "fatigue_snapshots",
    ],
    "swimming_coach": [
        "training_today",
        "acwr",
    ],
    "biking_coach": [
        "training_today",
        "acwr",
    ],
}


def get_agent_view(state: AthleteStateV3, agent: str) -> list[str] | str:
    """Retourne la vue autorisée pour un agent donné.

    - head_coach → "FULL" (accès complet)
    - agents connus → liste de clés
    - agent inconnu → []
    """
    return _AGENT_VIEWS.get(agent, [])
