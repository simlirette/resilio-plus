from sqlalchemy import Boolean, Column, Date, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from .database import Base


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
    # JSON-serialized list fields
    sports_json = Column(Text, nullable=False)
    goals_json = Column(Text, nullable=False)
    available_days_json = Column(Text, nullable=False)
    equipment_json = Column(Text, nullable=False)
    # Relationships
    plans = relationship("TrainingPlanModel", back_populates="athlete")
    nutrition_plans = relationship("NutritionPlanModel", back_populates="athlete")
    reviews = relationship("WeeklyReviewModel", back_populates="athlete")
    credentials = relationship("ConnectorCredentialModel", back_populates="athlete")


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
    plan_id = Column(String, ForeignKey("training_plans.id"), nullable=False)
    week_start = Column(Date, nullable=False)
    readiness_score = Column(Float, nullable=True)
    hrv_rmssd = Column(Float, nullable=True)
    sleep_hours_avg = Column(Float, nullable=True)
    athlete_comment = Column(Text, default="")
    results_json = Column(Text, nullable=False)
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
