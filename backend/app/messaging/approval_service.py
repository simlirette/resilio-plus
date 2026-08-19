"""Drive an approval from a chat button back into the paused LangGraph thread.

The channel layer knows only ``(athlete_id, token, resolution)``. Everything
else — which thread is parked, what the proposed plan was, whether a calendar
push is wired — is resolved here.

Approve and reject consume the token immediately. Revise does not: the token
stays open while the athlete types what should change, so tapping *Change* and
then *Approve* still works.
"""
from __future__ import annotations

import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

from sqlalchemy.orm import Session

from .approvals import (
    AlreadyResolvedApprovalError,
    ApprovalOwnershipError,
    ExpiredApprovalError,
    Resolution,
    UnknownApprovalError,
    arm_revision_latch,
    create_approval,
    encode_callback,
    get_open_approval,
    pop_revision_latch,
    resolve,
)
from .base import Button
from .plan_renderer import render_week

logger = logging.getLogger(__name__)

APPROVE_LABEL = "✅ Approve"
REVISE_LABEL = "✏️ Change"
REJECT_LABEL = "❌ Skip this week"

KIND_WEEKLY_PLAN = "weekly_plan"

_REVISION_PROMPT = (
    "What should change? Reply in plain language — for example "
    '"too much volume Wednesday" or "I am travelling Thursday".'
)


class PlanResumer(Protocol):
    """Structural subset of CoachingService used to resume a parked plan."""

    def resume_plan(
        self,
        thread_id: str,
        approved: bool,
        feedback: str | None,
        db: Session,
    ) -> dict[str, Any] | None: ...


class CalendarPusher(Protocol):
    """Callable that writes an approved week to the athlete's calendar."""

    def __call__(
        self,
        athlete_id: str,
        plan: Mapping[str, Any],
        db: Session,
    ) -> Mapping[str, int]: ...


class NotificationSender(Protocol):
    def send(
        self,
        athlete_id: str,
        text: str,
        buttons: list[Button] | None = None,
    ) -> object: ...


@dataclass(frozen=True, slots=True)
class ApprovalOutcome:
    """What actually happened for one button press or revision message."""

    resolution: str
    """One of approve / revise / reject, or "ignored" for a dead token."""

    message: str
    """The text sent back to the athlete."""

    calendar: dict[str, int] | None = None
    """Calendar sync counts, when a push happened."""

    new_token: str | None = None
    """Token of the follow-up approval, when a revised week was re-sent."""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ApprovalService:
    """Resolve approval tokens and carry out the decision they carry."""

    def __init__(
        self,
        db: Session,
        *,
        notifier: NotificationSender,
        coaching: PlanResumer | None = None,
        calendar_pusher: CalendarPusher | None = None,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        self._db = db
        self._notifier = notifier
        self._coaching = coaching
        self._calendar_pusher = calendar_pusher
        self._clock = clock

    # ─── Outbound ────────────────────────────────────────────────────────────

    def send_plan_for_approval(
        self,
        *,
        athlete_id: str,
        thread_id: str,
        kind: str = KIND_WEEKLY_PLAN,
        plan: Mapping[str, Any] | None,
        degraded_sources: Sequence[str] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> str:
        """Text the week with approve / change / skip buttons; return the token."""
        token = create_approval(
            self._db,
            athlete_id=athlete_id,
            thread_id=thread_id,
            kind=kind,
            payload=payload,
            clock=self._clock,
        )
        text = render_week(plan, degraded_sources=degraded_sources)
        self._notifier.send(athlete_id, text, self.buttons_for(token))
        return token

    @staticmethod
    def buttons_for(token: str) -> list[Button]:
        """Return the approve / change / skip keyboard for one approval token."""
        return [
            Button(label=APPROVE_LABEL, token=encode_callback(token, "approve")),
            Button(label=REVISE_LABEL, token=encode_callback(token, "revise")),
            Button(label=REJECT_LABEL, token=encode_callback(token, "reject")),
        ]

    # ─── Inbound ─────────────────────────────────────────────────────────────

    def handle_button(
        self,
        *,
        athlete_id: str,
        channel: str,
        external_id: str,
        token: str,
        resolution: Resolution,
    ) -> ApprovalOutcome:
        """Act on a tapped approval button.

        Raises:
            ApprovalOwnershipError: the token belongs to another athlete.
        """
        if resolution == "revise":
            return self._begin_revision(
                athlete_id=athlete_id,
                channel=channel,
                external_id=external_id,
                token=token,
            )

        try:
            approval = resolve(
                self._db,
                token=token,
                resolution=resolution,
                athlete_id=athlete_id,
                clock=self._clock,
            )
        except ApprovalOwnershipError:
            logger.warning("approval_cross_athlete_denied")
            raise
        except (
            UnknownApprovalError,
            ExpiredApprovalError,
            AlreadyResolvedApprovalError,
        ) as exc:
            return self._ignore(athlete_id, exc)

        if resolution == "reject":
            return self._finish(
                athlete_id,
                "reject",
                "Skipped — nothing was written to your calendar. "
                "Text me whenever you want to plan a different week.",
            )

        return self._approve(athlete_id, approval.thread_id, approval.kind)

    def handle_revision_text(
        self,
        *,
        athlete_id: str,
        channel: str,
        external_id: str,
        token: str,
        text: str,
    ) -> ApprovalOutcome:
        """Feed the athlete's free-text change request into the revise path."""
        # Defensive: the caller normally popped the latch to find this token,
        # but clearing it again keeps a failed pop from stranding the identity.
        pop_revision_latch(self._db, channel=channel, external_id=external_id)
        try:
            approval = resolve(
                self._db,
                token=token,
                resolution="revise",
                athlete_id=athlete_id,
                clock=self._clock,
            )
        except ApprovalOwnershipError:
            logger.warning("approval_cross_athlete_denied")
            raise
        except (
            UnknownApprovalError,
            ExpiredApprovalError,
            AlreadyResolvedApprovalError,
        ) as exc:
            return self._ignore(athlete_id, exc)

        revised = self._resume(approval.thread_id, approved=False, feedback=text)
        new_token = self.send_plan_for_approval(
            athlete_id=athlete_id,
            thread_id=approval.thread_id,
            kind=approval.kind,
            plan=revised,
        )
        return ApprovalOutcome(
            resolution="revise",
            message=render_week(revised),
            new_token=new_token,
        )

    def take_pending_revision_token(
        self,
        *,
        channel: str,
        external_id: str,
    ) -> str | None:
        """Pop the revision latch for an identity, if one is armed."""
        return pop_revision_latch(self._db, channel=channel, external_id=external_id)

    # ─── Internals ───────────────────────────────────────────────────────────

    def _begin_revision(
        self,
        *,
        athlete_id: str,
        channel: str,
        external_id: str,
        token: str,
    ) -> ApprovalOutcome:
        approval = get_open_approval(self._db, token=token, clock=self._clock)
        if approval is None:
            return self._ignore(athlete_id, AlreadyResolvedApprovalError())
        if approval.athlete_id != athlete_id:
            logger.warning("approval_cross_athlete_denied")
            raise ApprovalOwnershipError

        arm_revision_latch(
            self._db,
            channel=channel,
            external_id=external_id,
            token=token,
        )
        return self._finish(athlete_id, "revise", _REVISION_PROMPT)

    def _approve(
        self,
        athlete_id: str,
        thread_id: str,
        kind: str,
    ) -> ApprovalOutcome:
        final_plan = self._resume(thread_id, approved=True, feedback=None)

        if self._calendar_pusher is None:
            return self._finish(
                athlete_id,
                "approve",
                "Plan approved. No calendar is connected yet, so nothing was "
                "written — connect Google Calendar and I will push it there.",
            )

        report = dict(self._calendar_pusher(athlete_id, final_plan or {}, self._db))
        summary = (
            f"Plan approved and written to your Resilio Training calendar — "
            f"{report.get('created', 0)} created, {report.get('updated', 0)} updated, "
            f"{report.get('deleted', 0)} removed."
        )
        outcome = self._finish(athlete_id, "approve", summary)
        return ApprovalOutcome(
            resolution=outcome.resolution,
            message=outcome.message,
            calendar=report,
        )

    def _resume(
        self,
        thread_id: str,
        *,
        approved: bool,
        feedback: str | None,
    ) -> dict[str, Any] | None:
        coaching = self._coaching
        if coaching is None:
            from ..services.coaching_service import coaching_service

            coaching = coaching_service
            self._coaching = coaching
        try:
            return coaching.resume_plan(thread_id, approved, feedback, self._db)
        finally:
            self._settle()

    def _settle(self) -> None:
        """Close any transaction a graph node left open (``Session.refresh``)."""
        if self._db.in_transaction():
            self._db.commit()

    def _ignore(self, athlete_id: str, error: Exception) -> ApprovalOutcome:
        message = _DEAD_TOKEN_MESSAGES.get(
            type(error),
            "That button is no longer active. Text me and we will pick it up from there.",
        )
        self._notifier.send(athlete_id, message)
        return ApprovalOutcome(resolution="ignored", message=message)

    def _finish(
        self,
        athlete_id: str,
        resolution: str,
        message: str,
    ) -> ApprovalOutcome:
        self._notifier.send(athlete_id, message)
        return ApprovalOutcome(resolution=resolution, message=message)


_DEAD_TOKEN_MESSAGES: dict[type, str] = {
    ExpiredApprovalError: (
        "That plan expired before it was answered. Ask me for a fresh week "
        "whenever you are ready."
    ),
    AlreadyResolvedApprovalError: "That one is already handled — nothing changed.",
    UnknownApprovalError: (
        "I do not recognise that button any more. Ask me for a fresh week."
    ),
}
