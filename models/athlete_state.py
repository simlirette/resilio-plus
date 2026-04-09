# models/athlete_state.py
"""
AthleteState Pydantic — état LangGraph du Head Coach.

Ce module est DISTINCT de models.database.AthleteState (SQLAlchemy ORM).
- models.athlete_state.AthleteState  → Pydantic, pour LangGraph (ce fichier)
- models.database.AthleteState       → SQLAlchemy ORM, pour la DB
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from models.schemas import AthleteStateSchema


class ConstraintMatrix(BaseModel):
    """Matrice de contraintes hebdomadaire — schedule par jour."""

    model_config = ConfigDict(frozen=False)

    # Clés : noms de jours ("monday", …) ou "_daily_loads_28d" (liste de charges)
    # Exemple monday: {"assigned": ["squat"], "max_hours": 1.5, "primary_muscles": [...]}
    # Exemple _daily_loads_28d: [100.0, 85.0, …]  ← 28 derniers jours de charge TRIMP
    # Any car les valeurs peuvent être dict (sessions) ou list[float] (daily_loads)
    schedule: dict[str, Any] = Field(default_factory=dict)


class AthleteState(AthleteStateSchema):
    """
    État LangGraph du Head Coach — étend AthleteStateSchema avec les champs d'orchestration.

    Mutable (frozen=False) pour que les nœuds du graph puissent écrire directement.
    AthleteStateSchema contient déjà : profile, fatigue, running_profile, lifting_profile, etc.
    """

    model_config = ConfigDict(strict=False, frozen=False)

    # ── Orchestration LangGraph ──────────────────────────────────────────────
    pending_decision: dict | None = None
    pending_conflicts: list[dict] = Field(default_factory=list)
    partial_plans: dict[str, dict] = Field(default_factory=dict)
    decision_log: list[dict] = Field(default_factory=list)
    constraint_matrix: ConstraintMatrix = Field(default_factory=ConstraintMatrix)

    # ── Input de décision humaine ────────────────────────────────────────────
    user_decision_input: str | None = None
    reported_unavailable_days: list[str] = Field(default_factory=list)

    # ── Champs calculés (nœud load_state) ───────────────────────────────────
    acwr_computed: float | None = None

    # ── Circuit breaker résolution de conflits ───────────────────────────────
    resolution_iterations: int = 0
    conflicts_resolved: bool = True

    # ── S9 — Résultats des nœuds orchestration ───────────────────────────────
    recovery_verdict: dict | None = None
    unified_plan: dict | None = None
    conflict_log: list[str] = Field(default_factory=list)
