"""DB models for background job execution logs and athlete state snapshots."""
from datetime import datetime, timezone

from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint

from ..db.database import Base


class JobRunModel(Base):
    __tablename__ = "job_runs"

    id = Column(String, primary_key=True)
    job_id = Column(String, nullable=False)
    athlete_id = Column(String, ForeignKey("athletes.id"), nullable=True)
    job_type = Column(String, nullable=False)
    status = Column(String, nullable=False)  # ok, error, timeout
    started_at = Column(DateTime(timezone=True), nullable=False)
    duration_ms = Column(Integer, nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False,
                        default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_job_runs_type_created", "job_type", "created_at"),
    )


class AthleteStateSnapshotModel(Base):
    __tablename__ = "athlete_state_snapshots"

    id = Column(String, primary_key=True)
    athlete_id = Column(String, ForeignKey("athletes.id", ondelete="CASCADE"), nullable=False)
    snapshot_date = Column(Date, nullable=False)
    readiness = Column(Float, nullable=False)
    strain_json = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False,
                        default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("athlete_id", "snapshot_date", name="uq_snapshot_athlete_date"),
    )
