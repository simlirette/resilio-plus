from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import (
    BigInteger,
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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True)
    hashed_password: Mapped[str] = mapped_column(String)
    athlete_id: Mapped[str] = mapped_column(String, ForeignKey("athletes.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    athlete: Mapped[AthleteModel] = relationship("AthleteModel", back_populates="user")
    refresh_tokens: Mapped[list[RefreshTokenModel]] = relationship(
        "RefreshTokenModel", back_populates="user", cascade="all, delete-orphan"
    )
    reset_tokens: Mapped[list[PasswordResetTokenModel]] = relationship(
        "PasswordResetTokenModel", back_populates="user", cascade="all, delete-orphan"
    )


class RefreshTokenModel(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(String, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped[UserModel] = relationship("UserModel", back_populates="refresh_tokens")


class PasswordResetTokenModel(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(String, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped[UserModel] = relationship("UserModel", back_populates="reset_tokens")


class AthleteModel(Base):
    __tablename__ = "athletes"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    age: Mapped[int] = mapped_column(Integer)
    sex: Mapped[str] = mapped_column(String)
    weight_kg: Mapped[float] = mapped_column(Float)
    height_cm: Mapped[float] = mapped_column(Float)
    primary_sport: Mapped[str] = mapped_column(String)
    target_race_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    hours_per_week: Mapped[float] = mapped_column(Float)
    sleep_hours_typical: Mapped[float] = mapped_column(Float, default=7.0)
    stress_level: Mapped[int] = mapped_column(Integer, default=5)
    job_physical: Mapped[bool] = mapped_column(Boolean, default=False)
    max_hr: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    resting_hr: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ftp_watts: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    vdot: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    css_per_100m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    coaching_mode: Mapped[str] = mapped_column(String, default="full")
    # JSON-serialized list fields
    sports_json: Mapped[str] = mapped_column(Text)
    goals_json: Mapped[str] = mapped_column(Text)
    available_days_json: Mapped[str] = mapped_column(Text)
    equipment_json: Mapped[str] = mapped_column(Text, default="[]")

    # Relationships
    user: Mapped[Optional[UserModel]] = relationship(
        "UserModel", back_populates="athlete", uselist=False, cascade="all, delete-orphan"
    )
    plans: Mapped[list[TrainingPlanModel]] = relationship(
        "TrainingPlanModel", back_populates="athlete", cascade="all, delete-orphan"
    )
    nutrition_plans: Mapped[list[NutritionPlanModel]] = relationship(
        "NutritionPlanModel", back_populates="athlete", cascade="all, delete-orphan"
    )
    reviews: Mapped[list[WeeklyReviewModel]] = relationship(
        "WeeklyReviewModel", back_populates="athlete", cascade="all, delete-orphan"
    )
    credentials: Mapped[list[ConnectorCredentialModel]] = relationship(
        "ConnectorCredentialModel", back_populates="athlete", cascade="all, delete-orphan"
    )
    session_logs: Mapped[list[SessionLogModel]] = relationship(
        "SessionLogModel", back_populates="athlete", cascade="all, delete-orphan"
    )
    # V3 relationships
    energy_snapshots: Mapped[list[EnergySnapshotModel]] = relationship(
        "EnergySnapshotModel", back_populates="athlete", cascade="all, delete-orphan"
    )
    hormonal_profile: Mapped[Optional[HormonalProfileModel]] = relationship(
        "HormonalProfileModel",
        back_populates="athlete",
        uselist=False,
        cascade="all, delete-orphan",
    )
    allostatic_entries: Mapped[list[AllostaticEntryModel]] = relationship(
        "AllostaticEntryModel", back_populates="athlete", cascade="all, delete-orphan"
    )
    external_plans: Mapped[list[ExternalPlanModel]] = relationship(
        "ExternalPlanModel", back_populates="athlete", cascade="all, delete-orphan"
    )
    head_coach_messages: Mapped[list[HeadCoachMessageModel]] = relationship(
        "HeadCoachMessageModel", back_populates="athlete", cascade="all, delete-orphan"
    )
    apple_health_daily: Mapped[list["AppleHealthDailyModel"]] = relationship(
        "AppleHealthDailyModel", back_populates="athlete", cascade="all, delete-orphan"
    )


class TrainingPlanModel(Base):
    __tablename__ = "training_plans"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    athlete_id: Mapped[str] = mapped_column(String, ForeignKey("athletes.id"))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    phase: Mapped[str] = mapped_column(String)
    total_weekly_hours: Mapped[float] = mapped_column(Float)
    acwr: Mapped[float] = mapped_column(Float)
    weekly_slots_json: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    athlete: Mapped[AthleteModel] = relationship("AthleteModel", back_populates="plans")
    reviews: Mapped[list[WeeklyReviewModel]] = relationship(
        "WeeklyReviewModel", back_populates="plan"
    )


class NutritionPlanModel(Base):
    __tablename__ = "nutrition_plans"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    athlete_id: Mapped[str] = mapped_column(String, ForeignKey("athletes.id"))
    weight_kg: Mapped[float] = mapped_column(Float)
    targets_json: Mapped[str] = mapped_column(Text)

    # Relationships
    athlete: Mapped[AthleteModel] = relationship("AthleteModel", back_populates="nutrition_plans")


class WeeklyReviewModel(Base):
    __tablename__ = "weekly_reviews"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    athlete_id: Mapped[str] = mapped_column(String, ForeignKey("athletes.id"))
    plan_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("training_plans.id"), nullable=True
    )
    week_start: Mapped[date] = mapped_column(Date)
    week_number: Mapped[int] = mapped_column(Integer, default=1)
    planned_hours: Mapped[float] = mapped_column(Float, default=0.0)
    actual_hours: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    acwr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    adjustment_applied: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    readiness_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    hrv_rmssd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sleep_hours_avg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    athlete_comment: Mapped[str] = mapped_column(Text, default="")
    results_json: Mapped[str] = mapped_column(Text, default="{}")

    # Relationships
    athlete: Mapped[AthleteModel] = relationship("AthleteModel", back_populates="reviews")
    plan: Mapped[Optional[TrainingPlanModel]] = relationship(
        "TrainingPlanModel", back_populates="reviews"
    )


class ConnectorCredentialModel(Base):
    __tablename__ = "connector_credentials"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    athlete_id: Mapped[str] = mapped_column(String, ForeignKey("athletes.id"))
    provider: Mapped[str] = mapped_column(String)  # "strava"|"hevy"|"fatsecret"|"terra"
    access_token_enc: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # Fernet ciphertext (Strava only)
    refresh_token_enc: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # Fernet ciphertext (Strava only)
    expires_at: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Unix timestamp
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )  # NULL = never synced
    extra_json: Mapped[str] = mapped_column(Text, default="{}")

    # Relationships
    athlete: Mapped[AthleteModel] = relationship("AthleteModel", back_populates="credentials")

    __table_args__ = (UniqueConstraint("athlete_id", "provider"),)


class StravaActivityModel(Base):
    __tablename__ = "strava_activities"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # "strava_{strava_id}"
    athlete_id: Mapped[str] = mapped_column(
        String, ForeignKey("athletes.id", ondelete="CASCADE")
    )
    strava_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    sport_type: Mapped[str] = mapped_column(String)  # "running"|"biking"|"swimming"
    name: Mapped[str] = mapped_column(String)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    duration_s: Mapped[int] = mapped_column(Integer)
    distance_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    elevation_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_hr: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_hr: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    avg_watts: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    perceived_exertion: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    raw_json: Mapped[str] = mapped_column(Text, default="{}")


class SessionLogModel(Base):
    __tablename__ = "session_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    athlete_id: Mapped[str] = mapped_column(String, ForeignKey("athletes.id"))
    plan_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("training_plans.id"), nullable=True
    )
    session_id: Mapped[str] = mapped_column(String, index=True)
    actual_duration_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    skipped: Mapped[bool] = mapped_column(Boolean, default=False)
    rpe: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    actual_data_json: Mapped[str] = mapped_column(Text, default="{}")
    logged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    external_session_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("external_sessions.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    athlete: Mapped[AthleteModel] = relationship("AthleteModel", back_populates="session_logs")
    plan: Mapped[Optional[TrainingPlanModel]] = relationship("TrainingPlanModel")
    external_session: Mapped[Optional[ExternalSessionModel]] = relationship(
        "ExternalSessionModel", back_populates="log"
    )

    __table_args__ = (UniqueConstraint("athlete_id", "session_id"),)


# ---------------------------------------------------------------------------
# V3 models — consolidated from app.models.schemas (2026-04-16)
# Circular import eliminated: all SQLAlchemy models live here.
# ---------------------------------------------------------------------------


class EnergySnapshotModel(Base):
    __tablename__ = "energy_snapshots"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    athlete_id: Mapped[str] = mapped_column(String, ForeignKey("athletes.id"))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    allostatic_score: Mapped[float] = mapped_column(Float)
    cognitive_load: Mapped[float] = mapped_column(Float)
    energy_availability: Mapped[float] = mapped_column(Float)
    cycle_phase: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    sleep_quality: Mapped[float] = mapped_column(Float)
    recommended_intensity_cap: Mapped[float] = mapped_column(Float)
    veto_triggered: Mapped[bool] = mapped_column(Boolean, default=False)
    veto_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    objective_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    subjective_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    legs_feeling: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    stress_level: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    athlete: Mapped[AthleteModel] = relationship("AthleteModel", back_populates="energy_snapshots")


class HormonalProfileModel(Base):
    __tablename__ = "hormonal_profiles"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    athlete_id: Mapped[str] = mapped_column(String, ForeignKey("athletes.id"), unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    cycle_length_days: Mapped[int] = mapped_column(Integer, default=28)
    current_cycle_day: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    current_phase: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    last_period_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    tracking_source: Mapped[str] = mapped_column(String, default="manual")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    athlete: Mapped[AthleteModel] = relationship(
        "AthleteModel", back_populates="hormonal_profile"
    )


class AllostaticEntryModel(Base):
    __tablename__ = "allostatic_entries"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    athlete_id: Mapped[str] = mapped_column(String, ForeignKey("athletes.id"))
    entry_date: Mapped[date] = mapped_column(Date)
    allostatic_score: Mapped[float] = mapped_column(Float)
    components_json: Mapped[str] = mapped_column(Text, default="{}")
    intensity_cap_applied: Mapped[float] = mapped_column(Float, default=1.0)

    athlete: Mapped[AthleteModel] = relationship(
        "AthleteModel", back_populates="allostatic_entries"
    )

    __table_args__ = (UniqueConstraint("athlete_id", "entry_date"),)


class ExternalPlanModel(Base):
    """Training plan entered manually or imported from file by a Tracking Only athlete."""

    __tablename__ = "external_plans"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    athlete_id: Mapped[str] = mapped_column(String, ForeignKey("athletes.id"))
    title: Mapped[str] = mapped_column(String)
    source: Mapped[str] = mapped_column(String)  # "manual" | "file_import"
    status: Mapped[str] = mapped_column(String, default="active")  # "active" | "archived"
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    athlete: Mapped[AthleteModel] = relationship("AthleteModel", back_populates="external_plans")
    sessions: Mapped[list[ExternalSessionModel]] = relationship(
        "ExternalSessionModel", back_populates="plan", cascade="all, delete-orphan"
    )


class ExternalSessionModel(Base):
    """A single session belonging to an external (non-AI) training plan."""

    __tablename__ = "external_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    plan_id: Mapped[str] = mapped_column(String, ForeignKey("external_plans.id"))
    athlete_id: Mapped[str] = mapped_column(String, ForeignKey("athletes.id"))
    session_date: Mapped[date] = mapped_column(Date)
    sport: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        String, default="planned"
    )  # "planned"|"completed"|"skipped"

    plan: Mapped[ExternalPlanModel] = relationship("ExternalPlanModel", back_populates="sessions")
    log: Mapped[Optional[SessionLogModel]] = relationship(
        "SessionLogModel",
        back_populates="external_session",
        uselist=False,
        passive_deletes=True,
    )


class HeadCoachMessageModel(Base):
    """Proactive Head Coach messages generated by pattern detection."""

    __tablename__ = "head_coach_messages"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    athlete_id: Mapped[str] = mapped_column(String, ForeignKey("athletes.id"))
    pattern_type: Mapped[str] = mapped_column(String)
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)

    athlete: Mapped[AthleteModel] = relationship(
        "AthleteModel", back_populates="head_coach_messages"
    )


class FoodCacheModel(Base):
    __tablename__ = "food_cache"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # "usda_789" etc.
    source: Mapped[str] = mapped_column(String)  # "usda" | "off" | "fcen"
    name: Mapped[str] = mapped_column(String)
    name_en: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    name_fr: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    calories_per_100g: Mapped[float] = mapped_column(Float)
    protein_g: Mapped[float] = mapped_column(Float)
    carbs_g: Mapped[float] = mapped_column(Float)
    fat_g: Mapped[float] = mapped_column(Float)
    fiber_g: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sodium_mg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sugar_g: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cached_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # NULL = permanent (FCÉN rows have no expiry)
    ttl_hours: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class AppleHealthDailyModel(Base):
    """Daily aggregated Apple Health metrics per athlete."""

    __tablename__ = "apple_health_daily"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    athlete_id: Mapped[str] = mapped_column(String, ForeignKey("athletes.id"), nullable=False)
    record_date: Mapped[date] = mapped_column(Date, nullable=False)
    hrv_sdnn_avg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sleep_hours: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rhr_bpm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    body_mass_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    active_energy_kcal: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    athlete: Mapped["AthleteModel"] = relationship("AthleteModel", back_populates="apple_health_daily")

    __table_args__ = (UniqueConstraint("athlete_id", "record_date"),)
