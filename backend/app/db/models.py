from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from .database import Base


class UserModel(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    athlete_id = Column(String, ForeignKey("athletes.id"), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False,
                        default=lambda: datetime.now(timezone.utc))

    athlete = relationship("AthleteModel", back_populates="user")
    refresh_tokens = relationship("RefreshTokenModel", back_populates="user",
                                  cascade="all, delete-orphan")
    reset_tokens = relationship("PasswordResetTokenModel", back_populates="user",
                                cascade="all, delete-orphan")


class RefreshTokenModel(Base):
    __tablename__ = "refresh_tokens"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String, unique=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False,
                        default=lambda: datetime.now(timezone.utc))
    revoked = Column(Boolean, nullable=False, default=False)

    user = relationship("UserModel", back_populates="refresh_tokens")


class PasswordResetTokenModel(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String, unique=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, nullable=False, default=False)

    user = relationship("UserModel", back_populates="reset_tokens")


class AthleteModel(Base):
    __tablename__ = "athletes"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    age = Column(Integer, nullable=False)
    sex = Column(String, nullable=False)
    weight_kg = Column(Float, nullable=False)
    height_cm = Column(Float, nullable=False)
    primary_sport = Column(String, nullable=False)
    target_race_date = Column(Date, nullable=True)
    hours_per_week = Column(Float, nullable=False)
    sleep_hours_typical = Column(Float, default=7.0)
    stress_level = Column(Integer, default=5)
    job_physical = Column(Boolean, default=False)
    max_hr = Column(Integer, nullable=True)
    resting_hr = Column(Integer, nullable=True)
    ftp_watts = Column(Integer, nullable=True)
    vdot = Column(Float, nullable=True)
    css_per_100m = Column(Float, nullable=True)
    coaching_mode = Column(String, nullable=False, default="full")
    # JSON-serialized list fields
    sports_json = Column(Text, nullable=False)
    goals_json = Column(Text, nullable=False)
    available_days_json = Column(Text, nullable=False)
    equipment_json = Column(Text, nullable=False, default="[]")
    # Relationships
    user = relationship("UserModel", back_populates="athlete", uselist=False, cascade="all, delete-orphan")
    plans = relationship("TrainingPlanModel", back_populates="athlete", cascade="all, delete-orphan")
    nutrition_plans = relationship("NutritionPlanModel", back_populates="athlete", cascade="all, delete-orphan")
    reviews = relationship("WeeklyReviewModel", back_populates="athlete", cascade="all, delete-orphan")
    credentials = relationship("ConnectorCredentialModel", back_populates="athlete", cascade="all, delete-orphan")
    session_logs = relationship("SessionLogModel", back_populates="athlete", cascade="all, delete-orphan")
    # V3 relationships
    energy_snapshots = relationship("EnergySnapshotModel", back_populates="athlete", cascade="all, delete-orphan")
    hormonal_profile = relationship("HormonalProfileModel", back_populates="athlete", uselist=False, cascade="all, delete-orphan")
    allostatic_entries = relationship("AllostaticEntryModel", back_populates="athlete", cascade="all, delete-orphan")
    external_plans = relationship("ExternalPlanModel", back_populates="athlete", cascade="all, delete-orphan")
    head_coach_messages = relationship("HeadCoachMessageModel", back_populates="athlete", cascade="all, delete-orphan")


class TrainingPlanModel(Base):
    __tablename__ = "training_plans"

    id = Column(String, primary_key=True)
    athlete_id = Column(String, ForeignKey("athletes.id"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    phase = Column(String, nullable=False)
    total_weekly_hours = Column(Float, nullable=False)
    acwr = Column(Float, nullable=False)
    weekly_slots_json = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), nullable=False,
                        default=lambda: datetime.now(timezone.utc))
    # Relationships
    athlete = relationship("AthleteModel", back_populates="plans")
    reviews = relationship("WeeklyReviewModel", back_populates="plan")


class NutritionPlanModel(Base):
    __tablename__ = "nutrition_plans"

    id = Column(String, primary_key=True)
    athlete_id = Column(String, ForeignKey("athletes.id"), nullable=False)
    weight_kg = Column(Float, nullable=False)
    targets_json = Column(Text, nullable=False)
    # Relationships
    athlete = relationship("AthleteModel", back_populates="nutrition_plans")


class WeeklyReviewModel(Base):
    __tablename__ = "weekly_reviews"

    id = Column(String, primary_key=True)
    athlete_id = Column(String, ForeignKey("athletes.id"), nullable=False)
    plan_id = Column(String, ForeignKey("training_plans.id"), nullable=True)
    week_start = Column(Date, nullable=False)
    week_number = Column(Integer, nullable=False, default=1)
    planned_hours = Column(Float, nullable=False, default=0.0)
    actual_hours = Column(Float, nullable=True)
    acwr = Column(Float, nullable=True)
    adjustment_applied = Column(Float, nullable=True)
    readiness_score = Column(Float, nullable=True)
    hrv_rmssd = Column(Float, nullable=True)
    sleep_hours_avg = Column(Float, nullable=True)
    athlete_comment = Column(Text, default="")
    results_json = Column(Text, nullable=False, default="{}")
    # Relationships
    athlete = relationship("AthleteModel", back_populates="reviews")
    plan = relationship("TrainingPlanModel", back_populates="reviews")


class ConnectorCredentialModel(Base):
    __tablename__ = "connector_credentials"

    id = Column(String, primary_key=True)
    athlete_id = Column(String, ForeignKey("athletes.id"), nullable=False)
    provider = Column(String, nullable=False)          # "strava"|"hevy"|"fatsecret"|"terra"
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    expires_at = Column(Integer, nullable=True)        # Unix timestamp
    extra_json = Column(Text, nullable=False, default="{}")
    # Relationships
    athlete = relationship("AthleteModel", back_populates="credentials")

    __table_args__ = (UniqueConstraint("athlete_id", "provider"),)


class SessionLogModel(Base):
    __tablename__ = "session_logs"

    id = Column(String, primary_key=True)
    athlete_id = Column(String, ForeignKey("athletes.id"), nullable=False)
    plan_id = Column(String, ForeignKey("training_plans.id"), nullable=True)
    session_id = Column(String, nullable=False, index=True)
    actual_duration_min = Column(Integer, nullable=True)
    skipped = Column(Boolean, nullable=False, default=False)
    rpe = Column(Integer, nullable=True)
    notes = Column(Text, nullable=False, default="")
    actual_data_json = Column(Text, nullable=False, default="{}")
    logged_at = Column(DateTime(timezone=True), nullable=False,
                       default=lambda: datetime.now(timezone.utc))
    external_session_id = Column(String, ForeignKey("external_sessions.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    athlete = relationship("AthleteModel", back_populates="session_logs")
    plan = relationship("TrainingPlanModel")
    external_session = relationship("ExternalSessionModel", back_populates="log")

    __table_args__ = (UniqueConstraint("athlete_id", "session_id"),)


# Import V3 models so SQLAlchemy's mapper registry can resolve the
# back-references declared on AthleteModel above.
from app.models.schemas import (  # noqa: E402, F401
    AllostaticEntryModel,
    EnergySnapshotModel,
    HormonalProfileModel,
    ExternalPlanModel,
    ExternalSessionModel,
    HeadCoachMessageModel,
)


class FoodCacheModel(Base):
    __tablename__ = "food_cache"

    id = Column(String, primary_key=True)         # "usda_789" etc.
    source = Column(String, nullable=False)        # "usda" | "off" | "fcen"
    name = Column(String, nullable=False)
    name_en = Column(String, nullable=True)
    name_fr = Column(String, nullable=True)
    calories_per_100g = Column(Float, nullable=False)
    protein_g = Column(Float, nullable=False)
    carbs_g = Column(Float, nullable=False)
    fat_g = Column(Float, nullable=False)
    fiber_g = Column(Float, nullable=True)
    sodium_mg = Column(Float, nullable=True)
    sugar_g = Column(Float, nullable=True)
    cached_at = Column(DateTime(timezone=True), nullable=False)
    ttl_hours = Column(Integer, nullable=True)     # NULL = permanent (FCÉN)
