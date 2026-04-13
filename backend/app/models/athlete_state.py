"""AthleteState V1 — Source de vérité unique pour les données athlète.

Modèles principaux :
  AthleteState      — agrégat racine (9 sections)
  AgentView         — vue filtrée typée par agent
  get_agent_view()  — matrice d'accès pour 8 agents

Sous-modèles :
  SyncSource, AthleteMetrics, ConnectorSnapshot, PlanSnapshot,
  AllostaticSummary, DailyJournal, AllostaticComponents, EnergyCheckIn

Modèles V3 conservés (compatibilité) :
  EnergySnapshot, HormonalProfile, AllostaticEntry, RecoveryVetoV3,
  AthleteStateV3 (déprécié — utiliser AthleteState)
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from ..schemas.athlete import AthleteProfile
from ..schemas.connector import HevyWorkout, StravaActivity
from ..schemas.fatigue import FatigueScore
from ..schemas.plan import WorkoutSlot

# ---------------------------------------------------------------------------
# Types littéraux partagés
# ---------------------------------------------------------------------------

CyclePhase = Literal["menstrual", "follicular", "ovulation", "luteal"]
TrafficLight = Literal["green", "yellow", "red"]
TrackingSource = Literal["manual", "apple_health"]

WorkIntensity = Literal["light", "normal", "heavy", "exhausting"]
StressLevel = Literal["none", "mild", "significant"]


class EnergyCheckIn(BaseModel):
    """Daily check-in — work load, stress, optional cycle phase."""

    work_intensity: WorkIntensity
    stress_level: StressLevel
    cycle_phase: Optional[CyclePhase] = None


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
# AllostaticComponents  (section 5.2 / 7.1)
# ---------------------------------------------------------------------------


class AllostaticComponents(BaseModel):
    """Six sub-scores contributing to the daily allostatic score (each 0–100)."""

    hrv: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    sleep: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    work: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    stress: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    cycle: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    ea: Optional[float] = Field(default=None, ge=0.0, le=100.0)


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
    components: AllostaticComponents
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


# DEPRECATED: Use AthleteState instead. Kept for V3 compatibility.
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
# SyncSource  (metadata sur la dernière sync par connecteur)
# ---------------------------------------------------------------------------

SyncSourceName = Literal["strava", "hevy", "terra", "manual"]
SyncStatus = Literal["ok", "error", "stale"]


class SyncSource(BaseModel):
    """Tracks the last successful sync for one external data source."""

    name: SyncSourceName
    last_synced_at: datetime
    status: SyncStatus


# ---------------------------------------------------------------------------
# AthleteMetrics  (valeurs brutes Terra + métriques calculées)
# ---------------------------------------------------------------------------


class AthleteMetrics(BaseModel):
    """Raw connector values + derived metrics for today."""

    date: date
    # Raw Terra
    hrv_rmssd: Optional[float] = None
    hrv_history_7d: list[float] = Field(default_factory=list)
    sleep_hours: Optional[float] = None
    terra_sleep_score: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    resting_hr: Optional[float] = None
    # Computed
    acwr: Optional[float] = None
    acwr_status: Optional[Literal["safe", "caution", "danger"]] = None
    readiness_score: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    fatigue_score: Optional[FatigueScore] = None


# ---------------------------------------------------------------------------
# ConnectorSnapshot  (dernière synchro des connecteurs)
# ---------------------------------------------------------------------------


class ConnectorSnapshot(BaseModel):
    """Last known data from all external connectors."""

    strava_last_activity: Optional[StravaActivity] = None
    strava_activities_7d: list[StravaActivity] = Field(default_factory=list)
    hevy_last_workout: Optional[HevyWorkout] = None
    hevy_workouts_7d: list[HevyWorkout] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# PlanSnapshot  (plan du jour et de la semaine)
# ---------------------------------------------------------------------------


class PlanSnapshot(BaseModel):
    """Today's and this week's planned sessions."""

    today: list[WorkoutSlot] = Field(default_factory=list)
    week: list[WorkoutSlot] = Field(default_factory=list)
    week_number: int = 1
    phase: str = "base"


# ---------------------------------------------------------------------------
# AllostaticSummary  (historique 28 jours + tendance)
# ---------------------------------------------------------------------------

AllostaticTrend = Literal["improving", "stable", "declining"]


class AllostaticSummary(BaseModel):
    """28-day allostatic history with computed trend."""

    history_28d: list[AllostaticEntry] = Field(default_factory=list)
    trend: AllostaticTrend = "stable"
    avg_score_7d: float = Field(default=0.0, ge=0.0, le=100.0)


# ---------------------------------------------------------------------------
# DailyJournal  (check-in structuré + commentaire libre)
# ---------------------------------------------------------------------------


class DailyJournal(BaseModel):
    """Daily athlete journal: structured check-in + free-text comment."""

    date: date
    check_in: Optional[EnergyCheckIn] = None
    comment: Optional[str] = Field(default=None, max_length=2000)
    mood_score: Optional[int] = Field(default=None, ge=1, le=10)


# ---------------------------------------------------------------------------
# AthleteState  (source de vérité unique — section 7.1)
# ---------------------------------------------------------------------------


class AthleteState(BaseModel):
    """Single source of truth for all athlete data.

    Persisted snapshot — refreshed on every sync, falls back to last known
    version when connectors are unavailable.
    """

    athlete_id: str
    last_synced_at: datetime
    sync_sources: list[SyncSource] = Field(default_factory=list)

    # Domain sections
    profile: AthleteProfile
    metrics: AthleteMetrics
    connectors: ConnectorSnapshot
    plan: PlanSnapshot
    recovery: RecoveryVetoV3

    # Optional sections
    energy: Optional[EnergySnapshot] = None
    hormonal: Optional[HormonalProfile] = None
    allostatic: AllostaticSummary = Field(default_factory=AllostaticSummary)
    journal: Optional[DailyJournal] = None


# ---------------------------------------------------------------------------
# AgentView + get_agent_view()  (section 7.2)
# ---------------------------------------------------------------------------


class AgentView(BaseModel):
    """Typed filtered view of AthleteState for a specific agent.

    Only sections the agent is authorized to see are populated.
    All other sections are None. extra="forbid" prevents unauthorized access.
    """

    model_config = ConfigDict(extra="forbid")

    agent: str
    profile: Optional[AthleteProfile] = None
    metrics: Optional[AthleteMetrics] = None
    connectors: Optional[ConnectorSnapshot] = None
    plan: Optional[PlanSnapshot] = None
    energy: Optional[EnergySnapshot] = None
    recovery: Optional[RecoveryVetoV3] = None
    hormonal: Optional[HormonalProfile] = None
    allostatic: Optional[AllostaticSummary] = None
    journal: Optional[DailyJournal] = None


_AGENT_VIEWS: dict[str, set[str]] = {
    "head_coach": {"profile", "metrics", "connectors", "plan", "energy", "recovery", "hormonal", "allostatic", "journal"},
    "running":    {"profile", "metrics", "connectors", "plan", "hormonal"},
    "lifting":    {"profile", "metrics", "connectors", "plan", "hormonal"},
    "swimming":   {"profile", "metrics", "connectors", "plan"},
    "biking":     {"profile", "metrics", "connectors", "plan"},
    "nutrition":  {"profile", "plan", "energy", "hormonal"},
    "recovery":   {"profile", "metrics", "connectors", "plan", "energy", "recovery", "hormonal", "allostatic", "journal"},
    "energy":     {"profile", "metrics", "energy", "recovery", "hormonal", "allostatic", "journal"},
}


def get_agent_view(state: AthleteState, agent: str) -> AgentView:
    """Return a typed filtered view of AthleteState for the given agent.

    - Known agents → populated sections per _AGENT_VIEWS matrix
    - Unknown agents → AgentView with all sections None
    """
    allowed = _AGENT_VIEWS.get(agent, set())
    return AgentView(
        agent=agent,
        **{k: getattr(state, k) for k in allowed},
    )
