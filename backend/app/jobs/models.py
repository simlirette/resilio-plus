"""DB models for background job execution logs and athlete state snapshots."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Date, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..db.database import Base


class JobRunModel(Base):
    __tablename__ = "job_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    job_id: Mapped[str] = mapped_column(String, nullable=False)
    athlete_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("athletes.id"), nullable=True)
    job_type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (Index("ix_job_runs_type_created", "job_type", "created_at"),)


class AthleteStateSnapshotModel(Base):
    __tablename__ = "athlete_state_snapshots"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    athlete_id: Mapped[str] = mapped_column(String, ForeignKey("athletes.id", ondelete="CASCADE"), nullable=False)
    snapshot_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    readiness: Mapped[float] = mapped_column(Float, nullable=False)
    strain_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        UniqueConstraint("athlete_id", "snapshot_date", name="uq_snapshot_athlete_date"),
    )
