"""SQLAlchemy models V3 — nouvelles tables pour AthleteState V3.

Tables créées :
- energy_snapshots        : historique des EnergySnapshot par athlète
- hormonal_profiles       : profil hormonal par athlète (1:1)
- allostatic_entries      : historique quotidien allostatic (28 jours) par athlète

Référence : docs/resilio-v3-master.md — sections 3.2, 4.3, 5.2, 7.1
"""
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.database import Base


class EnergySnapshotModel(Base):
    __tablename__ = "energy_snapshots"

    id = Column(String, primary_key=True)
    athlete_id = Column(String, ForeignKey("athletes.id"), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    allostatic_score = Column(Float, nullable=False)
    cognitive_load = Column(Float, nullable=False)
    energy_availability = Column(Float, nullable=False)
    cycle_phase = Column(String, nullable=True)
    sleep_quality = Column(Float, nullable=False)
    recommended_intensity_cap = Column(Float, nullable=False)
    veto_triggered = Column(Boolean, nullable=False, default=False)
    veto_reason = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    athlete = relationship("AthleteModel", back_populates="energy_snapshots")


class HormonalProfileModel(Base):
    __tablename__ = "hormonal_profiles"

    id = Column(String, primary_key=True)
    athlete_id = Column(String, ForeignKey("athletes.id"), nullable=False, unique=True)
    enabled = Column(Boolean, nullable=False, default=False)
    cycle_length_days = Column(Integer, nullable=False, default=28)
    current_cycle_day = Column(Integer, nullable=True)
    current_phase = Column(String, nullable=True)
    last_period_start = Column(Date, nullable=True)
    tracking_source = Column(String, nullable=False, default="manual")
    notes = Column(Text, nullable=True)

    athlete = relationship("AthleteModel", back_populates="hormonal_profile")


class AllostaticEntryModel(Base):
    __tablename__ = "allostatic_entries"

    id = Column(String, primary_key=True)
    athlete_id = Column(String, ForeignKey("athletes.id"), nullable=False)
    entry_date = Column(Date, nullable=False)
    allostatic_score = Column(Float, nullable=False)
    components_json = Column(Text, nullable=False, default="{}")  # JSON dict des composantes
    intensity_cap_applied = Column(Float, nullable=False, default=1.0)

    athlete = relationship("AthleteModel", back_populates="allostatic_entries")

    __table_args__ = (UniqueConstraint("athlete_id", "entry_date"),)
