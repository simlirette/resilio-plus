"""CoordinatorService — point d'entrée unique pour tout événement entrant.

Routes événements vers le graphe LangGraph approprié selon journey_phase et overlays.
Gère le lifecycle des thread_ids persistents.
Enforces les transitions journey_phase valides (A2 §Transitions valides).

Public API:
    from app.services.coordinator_service import coordinator_service  # singleton

    result = coordinator_service.dispatch(athlete_id, "chat", {"message": "..."}, db)
    coordinator_service.advance_journey_phase(athlete_id, "onboarding", db)
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from ..db.models import AthleteModel

# ─── Valid journey_phase transitions (A2 §Transitions valides) ────────────────

VALID_TRANSITIONS: dict[str, set[str]] = {
    "signup": {"scope_selection"},
    "scope_selection": {"onboarding"},
    "onboarding": {"baseline_pending_confirmation"},
    "baseline_pending_confirmation": {"baseline_active"},
    "baseline_active": {
        "followup_transition",
        "baseline_active",  # pause courte / extension baseline
        "onboarding",  # sous-compliance > 45j, re-onboarding partiel
    },
    "followup_transition": {
        "steady_state",
        "baseline_active",  # extension baseline si conditions non atteintes
    },
    "steady_state": {
        "baseline_pending_confirmation",  # interruption longue au-delà seuils
        "steady_state",  # tous tours chat + régénération bloc
    },
}

# ─── Thread lifecycle config ──────────────────────────────────────────────────
# Maps graph_name → AthleteModel field that stores the persistent thread_id.
# Graphs not listed here are short-lived (chat_turn) — no persistence.

PERSISTENT_THREAD_FIELDS: dict[str, str] = {
    "onboarding": "active_onboarding_thread_id",
    "recovery_takeover": "active_recovery_thread_id",
    "followup_transition": "active_followup_thread_id",
}


@dataclass
class DispatchResult:
    """Result of a CoordinatorService.dispatch() call."""

    graph_invoked: str | None
    """Name of the LangGraph graph invoked, or None for service-level handling."""

    thread_id: str | None
    """Thread ID used for the invocation. None for service-level events."""

    output: dict[str, Any] | None
    """Graph output dict. None for D1 stubs (pending=True) or service events."""

    pending: bool = False
    """True when the targeted graph is not yet implemented (D2+). Safe to ignore."""


class CoordinatorService:
    """Point d'entrée unique pour tout événement entrant.

    Responsabilités (A2 §Architecture CoordinatorService) :
    1. Routing par journey_phase + overlays → graphe cible.
    2. Thread lifecycle : création d'un nouveau thread ou reprise d'un existant.
    3. Validation des transitions journey_phase.
    4. Enforcement du plafond de pro-activité Head Coach (D11+).
    5. Gestion des mutations overlay (recovery_takeover_active).

    D1 scope : routing matrix + thread lifecycle. Les graphes non encore implémentés
    (onboarding, chat_turn, followup_transition, recovery_takeover) retournent
    pending=True. Le graphe plan_generation est accessible via coaching_service (D4+).
    """

    def __init__(self, *, coaching_service: Any = None) -> None:
        self._coaching_service = coaching_service

    def dispatch(
        self,
        athlete_id: str,
        event_type: str,
        payload: dict[str, Any],
        db: Session,
    ) -> DispatchResult:
        """Route l'événement vers le graphe approprié.

        Args:
            athlete_id:  Athlete DB primary key.
            event_type:  One of: "chat", "system_silent", "system_proactive", "system_injury".
            payload:     Event payload (message, seed_message, injury data, …).
            db:          SQLAlchemy session.

        Returns:
            DispatchResult with graph_invoked, thread_id, output, pending flag.

        Raises:
            ValueError: Athlete not found in DB.
        """
        athlete = db.query(AthleteModel).filter(AthleteModel.id == athlete_id).first()
        if athlete is None:
            raise ValueError(f"Athlete {athlete_id!r} not found")

        # system_injury → activate overlay before routing
        if event_type == "system_injury":
            athlete.recovery_takeover_active = True
            db.commit()

        graph_name = self._resolve_graph(athlete, event_type)

        if graph_name is None:
            return DispatchResult(graph_invoked=None, thread_id=None, output=None)

        thread_id = self._get_or_create_thread(athlete, graph_name, db)
        output = self._invoke_graph(graph_name, athlete_id, thread_id, payload, db)

        return DispatchResult(
            graph_invoked=graph_name,
            thread_id=thread_id,
            output=output,
            pending=output is None,
        )

    def advance_journey_phase(
        self,
        athlete_id: str,
        new_phase: str,
        db: Session,
    ) -> None:
        """Mute journey_phase avec validation de transition.

        Raises:
            ValueError: Athlete not found, or transition not allowed by A2 spec.
        """
        athlete = db.query(AthleteModel).filter(AthleteModel.id == athlete_id).first()
        if athlete is None:
            raise ValueError(f"Athlete {athlete_id!r} not found")

        current = athlete.journey_phase
        allowed = VALID_TRANSITIONS.get(current, set())
        if new_phase not in allowed:
            raise ValueError(
                f"Invalid journey_phase transition: {current!r} → {new_phase!r}. "
                f"Allowed from {current!r}: {sorted(allowed) or '[]'}"
            )
        athlete.journey_phase = new_phase
        db.commit()

    # ─── Internal ─────────────────────────────────────────────────────────────

    def _resolve_graph(self, athlete: AthleteModel, event_type: str) -> str | None:
        """Determine which graph to invoke. Returns graph name or None."""
        # Overlay priority — overrides journey_phase for chat + injury events
        if event_type in ("chat", "system_injury", "system_proactive"):
            if athlete.recovery_takeover_active:
                return "recovery_takeover"
            if athlete.onboarding_reentry_active:
                return "onboarding"

        if event_type == "system_silent":
            return None

        if event_type == "system_injury":
            return "recovery_takeover"

        if event_type in ("chat", "system_proactive"):
            phase = athlete.journey_phase
            if phase in ("signup", "scope_selection"):
                return None
            if phase == "onboarding":
                return "onboarding"
            if phase == "baseline_pending_confirmation":
                return "plan_generation"
            if phase == "baseline_active":
                return "chat_turn"
            if phase == "followup_transition":
                return "followup_transition"
            if phase == "steady_state":
                return "chat_turn"

        return None

    def _get_or_create_thread(
        self,
        athlete: AthleteModel,
        graph_name: str,
        db: Session,
    ) -> str:
        """Return existing persistent thread_id or create a new one.

        Short-lived graphs (chat_turn) get an ephemeral thread that is not
        stored on the athlete model.
        """
        field_name = PERSISTENT_THREAD_FIELDS.get(graph_name)

        if field_name is None:
            # Ephemeral thread — not persisted
            return f"{athlete.id}:{graph_name}:{uuid.uuid4()}"

        existing: str | None = getattr(athlete, field_name, None)
        if existing is not None:
            return existing

        new_thread_id = f"{athlete.id}:{graph_name}:{uuid.uuid4()}"
        setattr(athlete, field_name, new_thread_id)
        db.commit()
        return new_thread_id

    def _invoke_graph(
        self,
        graph_name: str,
        athlete_id: str,
        thread_id: str,
        payload: dict[str, Any],
        db: Session,
    ) -> dict[str, Any] | None:
        """Invoke the target graph and return its output.

        D1: all graphs except plan_generation return None (pending=True).
        Integration with coaching_service for plan_generation is deferred to D4.
        """
        # All graphs are stubs in D1 — implementations added in D3-D10
        return None


# ─── Module-level singleton ───────────────────────────────────────────────────
# Tests should instantiate CoordinatorService() directly to avoid coupling
# to the module-level coaching_service singleton.

coordinator_service = CoordinatorService()
