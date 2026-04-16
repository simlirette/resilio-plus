"""ExternalPlanService — CRUD for manually entered external training plans.

Only used in Tracking Only mode (enforced at HTTP layer via require_tracking_mode).
"""
from __future__ import annotations

import uuid
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..models.schemas import ExternalPlanModel, ExternalSessionModel


class ExternalPlanService:
    @staticmethod
    def create_plan(
        athlete_id: str,
        title: str,
        db: Session,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> ExternalPlanModel:
        """Create a new active external plan, archiving any previous active plan.

        Maintains the XOR invariant: only one active ExternalPlan per athlete.
        (The ModeGuard ensures no active TrainingPlan can coexist in tracking_only mode.)
        """
        # Archive existing active plan(s) for this athlete
        existing = (
            db.query(ExternalPlanModel)
            .filter(
                ExternalPlanModel.athlete_id == athlete_id,
                ExternalPlanModel.status == "active",
            )
            .all()
        )
        for old_plan in existing:
            old_plan.status = "archived"

        new_plan = ExternalPlanModel(
            id=str(uuid.uuid4()),
            athlete_id=athlete_id,
            title=title,
            source="manual",
            status="active",
            start_date=start_date,
            end_date=end_date,
        )
        db.add(new_plan)
        db.commit()
        db.refresh(new_plan)
        return new_plan

    @staticmethod
    def get_active_plan(
        athlete_id: str,
        db: Session,
    ) -> ExternalPlanModel | None:
        """Return the active ExternalPlan for the athlete, or None."""
        return (
            db.query(ExternalPlanModel)
            .filter(
                ExternalPlanModel.athlete_id == athlete_id,
                ExternalPlanModel.status == "active",
            )
            .first()
        )

    @staticmethod
    def add_session(
        plan_id: str,
        athlete_id: str,
        session_date: date,
        sport: str,
        title: str,
        db: Session,
        description: str | None = None,
        duration_min: int | None = None,
    ) -> ExternalSessionModel:
        """Add a session to an active external plan.

        Raises 404 if the plan is not found or doesn't belong to the athlete.
        """
        plan = db.get(ExternalPlanModel, plan_id)
        if not plan or plan.athlete_id != athlete_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="External plan not found",
            )

        session_obj = ExternalSessionModel(
            id=str(uuid.uuid4()),
            plan_id=plan_id,
            athlete_id=athlete_id,
            session_date=session_date,
            sport=sport,
            title=title,
            description=description,
            duration_min=duration_min,
            status="planned",
        )
        db.add(session_obj)
        db.commit()
        db.refresh(session_obj)
        return session_obj

    @staticmethod
    def update_session(
        session_id: str,
        athlete_id: str,
        updates: dict,
        db: Session,
    ) -> ExternalSessionModel:
        """Partially update an external session.

        Only keys present in `updates` are applied (None values are skipped).
        Raises 404 if session not found or doesn't belong to the athlete.
        """
        session_obj = db.get(ExternalSessionModel, session_id)
        if not session_obj or session_obj.athlete_id != athlete_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="External session not found",
            )

        allowed_fields = {"session_date", "sport", "title", "description", "duration_min", "status"}
        for field, value in updates.items():
            if field in allowed_fields and value is not None:
                setattr(session_obj, field, value)

        db.commit()
        db.refresh(session_obj)
        return session_obj

    @staticmethod
    def delete_session(
        session_id: str,
        athlete_id: str,
        db: Session,
    ) -> None:
        """Hard-delete an external session.

        Raises 404 if session not found or doesn't belong to the athlete.
        """
        session_obj = db.get(ExternalSessionModel, session_id)
        if not session_obj or session_obj.athlete_id != athlete_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="External session not found",
            )

        db.delete(session_obj)
        db.commit()
