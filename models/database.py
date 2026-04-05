"""
DATABASE SCHEMA — Resilio+
Moteur   : PostgreSQL (JSONB natif pour AthleteState)
ORM      : SQLAlchemy 2.0 async
Migrations: Alembic

Principes de design :
- UUID comme clé primaire partout (pas d'integers séquentiels)
- JSONB pour les structures imbriquées complexes (profils, plans)
- Tables relationnelles pour les données time-series (sets, activités, fatigue)
- created_at / updated_at sur toutes les tables
"""

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func

# ─────────────────────────────────────────────
# BASE
# ─────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


class TimestampMixin:
    """Mixin created_at / updated_at pour toutes les tables."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
        onupdate=func.now(), nullable=False
    )


# ─────────────────────────────────────────────
# ENUMS
# ─────────────────────────────────────────────

class MacrocyclePhase(str, enum.Enum):
    base_building = "base_building"
    build = "build"
    peak = "peak"
    taper = "taper"
    race = "race"
    transition = "transition"


class ReadinessColor(str, enum.Enum):
    green = "green"   # >= 75
    yellow = "yellow" # 50-74
    red = "red"       # < 50


class DecisionStatus(str, enum.Enum):
    awaiting = "awaiting_user_input"
    confirmed = "confirmed"
    overridden = "overridden"


class SetType(str, enum.Enum):
    normal = "normal"
    warmup = "warmup"
    dropset = "dropset"
    failure = "failure"


# ─────────────────────────────────────────────
# TABLE : athletes
# Données de profil statiques (changent rarement)
# ─────────────────────────────────────────────

class Athlete(TimestampMixin, Base):
    __tablename__ = "athletes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    sex: Mapped[str] = mapped_column(String(1), nullable=False)       # "M" | "F"
    weight_kg: Mapped[float] = mapped_column(Float, nullable=False)
    height_cm: Mapped[float] = mapped_column(Float, nullable=False)

    # Données calculées mises à jour périodiquement
    body_fat_percent: Mapped[float | None] = mapped_column(Float)
    resting_hr: Mapped[int | None] = mapped_column(Integer)
    max_hr_measured: Mapped[int | None] = mapped_column(Integer)

    # Profils techniques stockés en JSONB (structure complexe et évolutive)
    # Contient : training_history, injuries_history, lifestyle, goals, equipment
    profile_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Disponibilités hebdomadaires (JSONB — structure par jour)
    available_days: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Relations
    states: Mapped[list["AthleteState"]] = relationship(
        back_populates="athlete", order_by="AthleteState.created_at.desc()"
    )
    lifting_sessions: Mapped[list["LiftingSession"]] = relationship(
        back_populates="athlete"
    )
    run_activities: Mapped[list["RunActivity"]] = relationship(
        back_populates="athlete"
    )
    fatigue_snapshots: Mapped[list["FatigueSnapshot"]] = relationship(
        back_populates="athlete", order_by="FatigueSnapshot.snapshot_date.desc()"
    )
    weekly_plans: Mapped[list["WeeklyPlan"]] = relationship(
        back_populates="athlete"
    )
    decision_logs: Mapped[list["DecisionLog"]] = relationship(
        back_populates="athlete"
    )
    connector_credentials: Mapped[list["ConnectorCredential"]] = relationship(
        back_populates="athlete"
    )


# ─────────────────────────────────────────────
# TABLE : athlete_states
# L'AthleteState vivant — snapshot à chaque mise à jour
# JSONB pour les sections complexes, colonnes relationnelles pour les métriques clés
# ─────────────────────────────────────────────

class AthleteState(TimestampMixin, Base):
    __tablename__ = "athlete_states"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    athlete_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("athletes.id"), nullable=False, index=True
    )

    # Phase actuelle (colonnes relationnelles pour le filtrage rapide)
    macrocycle_phase: Mapped[MacrocyclePhase] = mapped_column(
        SAEnum(MacrocyclePhase), nullable=False
    )
    mesocycle_week: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    target_event_date: Mapped[date | None] = mapped_column(Date)

    # Profils techniques (JSONB — running, lifting, swimming, biking, nutrition)
    running_profile: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    lifting_profile: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    swimming_profile: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    biking_profile: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    nutrition_profile: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Volumes hebdomadaires (colonnes pour les calculs ACWR)
    weekly_km_running: Mapped[float] = mapped_column(Float, default=0.0)
    weekly_sessions_lifting: Mapped[int] = mapped_column(Integer, default=0)
    weekly_km_biking: Mapped[float] = mapped_column(Float, default=0.0)
    weekly_km_swimming: Mapped[float] = mapped_column(Float, default=0.0)
    total_training_hours: Mapped[float] = mapped_column(Float, default=0.0)

    # Compliance
    completion_rate_4weeks: Mapped[float | None] = mapped_column(Float)
    nutrition_adherence_7days: Mapped[float | None] = mapped_column(Float)

    # Relation
    athlete: Mapped["Athlete"] = relationship(back_populates="states")


# ─────────────────────────────────────────────
# TABLE : fatigue_snapshots
# Snapshot quotidien de la fatigue — source de vérité pour l'ACWR
# Table relationnelle (time-series, besoin de requêtes par plage de dates)
# ─────────────────────────────────────────────

class FatigueSnapshot(Base):
    __tablename__ = "fatigue_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    athlete_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("athletes.id"), nullable=False, index=True
    )
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Métriques biométriques (Apple Health)
    hrv_rmssd: Mapped[float | None] = mapped_column(Float)
    hr_rest: Mapped[int | None] = mapped_column(Integer)
    sleep_hours: Mapped[float | None] = mapped_column(Float)
    sleep_quality_subjective: Mapped[int | None] = mapped_column(Integer) # 1-10

    # Charge calculée
    acwr_global: Mapped[float | None] = mapped_column(Float)
    acwr_running: Mapped[float | None] = mapped_column(Float)
    acwr_lifting: Mapped[float | None] = mapped_column(Float)
    acwr_biking: Mapped[float | None] = mapped_column(Float)
    weekly_fatigue_score: Mapped[float | None] = mapped_column(Float)
    cns_load_7day_avg: Mapped[float | None] = mapped_column(Float)

    # Fatigue par groupe musculaire (JSONB — structure variable)
    fatigue_by_muscle: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Readiness
    recovery_score: Mapped[float | None] = mapped_column(Float)
    readiness_color: Mapped[ReadinessColor | None] = mapped_column(
        SAEnum(ReadinessColor)
    )
    fatigue_subjective: Mapped[int | None] = mapped_column(Integer)  # 1-10

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relation
    athlete: Mapped["Athlete"] = relationship(back_populates="fatigue_snapshots")


# ─────────────────────────────────────────────
# TABLE : lifting_sessions
# Séances de musculation (Hevy CSV ou API)
# ─────────────────────────────────────────────

class LiftingSession(TimestampMixin, Base):
    __tablename__ = "lifting_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    athlete_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("athletes.id"), nullable=False, index=True
    )

    # Métadonnées de la séance
    hevy_title: Mapped[str] = mapped_column(String(200), nullable=False)
    session_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    duration_minutes: Mapped[int | None] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(Text)

    # Métriques agrégées (calculées à l'ingestion)
    total_volume_kg: Mapped[float | None] = mapped_column(Float)
    total_sets: Mapped[int | None] = mapped_column(Integer)
    avg_rpe: Mapped[float | None] = mapped_column(Float)
    estimated_tss: Mapped[float | None] = mapped_column(Float)

    # Source de la donnée
    source: Mapped[str] = mapped_column(String(20), default="hevy_csv")
    hevy_workout_id: Mapped[str | None] = mapped_column(String(100), unique=True, index=True)

    # Relations
    athlete: Mapped["Athlete"] = relationship(back_populates="lifting_sessions")
    sets: Mapped[list["LiftingSet"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


# ─────────────────────────────────────────────
# TABLE : lifting_sets
# Sets individuels (relationnel pour les requêtes de progression)
# ─────────────────────────────────────────────

class LiftingSet(Base):
    __tablename__ = "lifting_sets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lifting_sessions.id"), nullable=False, index=True
    )

    exercise_title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    superset_id: Mapped[str | None] = mapped_column(String(50))
    set_index: Mapped[int] = mapped_column(Integer, nullable=False)
    set_type: Mapped[SetType] = mapped_column(SAEnum(SetType), nullable=False)

    # Données du set (en kg — conversion lbs→kg à l'ingestion)
    weight_kg: Mapped[float | None] = mapped_column(Float)
    reps: Mapped[int | None] = mapped_column(Integer)
    rpe: Mapped[float | None] = mapped_column(Float)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    distance_km: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(Text)

    # Relation
    session: Mapped["LiftingSession"] = relationship(back_populates="sets")


# ─────────────────────────────────────────────
# TABLE : run_activities
# Activités de course (Strava API)
# ─────────────────────────────────────────────

class RunActivity(TimestampMixin, Base):
    __tablename__ = "run_activities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    athlete_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("athletes.id"), nullable=False, index=True
    )

    # Identifiant Strava
    strava_activity_id: Mapped[str | None] = mapped_column(
        String(100), unique=True, index=True
    )
    activity_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    activity_type: Mapped[str] = mapped_column(String(50), default="run")

    # Métriques clés (colonnes pour les calculs ACWR et TSS)
    distance_km: Mapped[float | None] = mapped_column(Float)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    avg_pace_sec_per_km: Mapped[float | None] = mapped_column(Float)
    avg_hr: Mapped[int | None] = mapped_column(Integer)
    max_hr: Mapped[int | None] = mapped_column(Integer)
    elevation_gain_m: Mapped[float | None] = mapped_column(Float)
    estimated_tss: Mapped[float | None] = mapped_column(Float)
    trimp: Mapped[float | None] = mapped_column(Float)

    # Données complètes Strava (JSONB — laps, streams, best efforts)
    strava_raw: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Relation
    athlete: Mapped["Athlete"] = relationship(back_populates="run_activities")


# ─────────────────────────────────────────────
# TABLE : weekly_plans
# Plan hebdomadaire généré par le Head Coach
# ─────────────────────────────────────────────

class WeeklyPlan(TimestampMixin, Base):
    __tablename__ = "weekly_plans"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    athlete_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("athletes.id"), nullable=False, index=True
    )

    # Semaine du plan
    week_start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    week_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    macrocycle_phase: Mapped[MacrocyclePhase] = mapped_column(
        SAEnum(MacrocyclePhase), nullable=False
    )
    mesocycle_week: Mapped[int] = mapped_column(Integer, nullable=False)

    # Plan complet (JSONB — séances exactes par jour, format Hevy+Runna compatible)
    plan_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Matrice de contraintes de la semaine
    constraint_matrix: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Statut
    is_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user_modifications: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Compliance (rempli en fin de semaine)
    completion_rate: Mapped[float | None] = mapped_column(Float)
    sessions_planned: Mapped[int | None] = mapped_column(Integer)
    sessions_completed: Mapped[int | None] = mapped_column(Integer)

    # Relation
    athlete: Mapped["Athlete"] = relationship(back_populates="weekly_plans")


# ─────────────────────────────────────────────
# TABLE : decision_logs
# Historique des décisions human-in-the-loop (edge cases)
# ─────────────────────────────────────────────

class DecisionLog(TimestampMixin, Base):
    __tablename__ = "decision_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    athlete_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("athletes.id"), nullable=False, index=True
    )

    # Identification du conflit
    conflict_id: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # ex: "A_1RM_RED_VETO"

    # Données du conflit et de la décision
    situation: Mapped[str] = mapped_column(Text, nullable=False)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    alternatives_presented: Mapped[list] = mapped_column(JSONB, default=list)
    user_choice: Mapped[str | None] = mapped_column(Text)
    final_decision: Mapped[dict | None] = mapped_column(JSONB)

    # Statut
    status: Mapped[DecisionStatus] = mapped_column(
        SAEnum(DecisionStatus), default=DecisionStatus.awaiting, nullable=False
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Contexte biométrique au moment de la décision (snapshot)
    biometric_context: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Relation
    athlete: Mapped["Athlete"] = relationship(back_populates="decision_logs")


# ─────────────────────────────────────────────
# TABLE : connector_credentials
# Tokens OAuth (Strava) et clés API (Hevy) par athlète
# Un seul credential par provider par athlète — UniqueConstraint
# ─────────────────────────────────────────────

class ConnectorCredential(TimestampMixin, Base):
    __tablename__ = "connector_credentials"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    athlete_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("athletes.id"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # "strava" | "hevy"

    # OAuth tokens (Strava) — stockage en clair (dev local). Chiffrement prévu en S14.
    access_token: Mapped[str | None] = mapped_column(Text)
    refresh_token: Mapped[str | None] = mapped_column(Text)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # API key (Hevy) — stockage en clair (dev local). Chiffrement prévu en S14.
    api_key: Mapped[str | None] = mapped_column(Text)

    # ID externe de l'athlète chez le provider (ex: Strava athlete ID)
    external_athlete_id: Mapped[str | None] = mapped_column(String(100))

    # Un seul credential par provider par athlète
    __table_args__ = (UniqueConstraint("athlete_id", "provider"),)

    # Relation
    athlete: Mapped["Athlete"] = relationship(back_populates="connector_credentials")
