"""Pydantic schemas for the Energy Cycle Service (V3-C)."""
from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field


class CheckInInput(BaseModel):
    work_intensity: Literal["light", "normal", "heavy", "exhausting"]
    stress_level: Literal["none", "mild", "significant"]
    legs_feeling: Literal["fresh", "normal", "heavy", "dead"]
    energy_global: Literal["great", "ok", "low", "exhausted"]
    cycle_phase: Optional[Literal["menstrual", "follicular", "ovulation", "luteal"]] = None
    comment: Optional[str] = Field(default=None, max_length=140)


class ReadinessResponse(BaseModel):
    date: date
    objective_score: float = Field(..., ge=0.0, le=100.0)
    subjective_score: float = Field(..., ge=0.0, le=100.0)
    final_readiness: float = Field(..., ge=0.0, le=100.0)
    divergence: float = Field(..., ge=0.0)
    divergence_flag: Literal["none", "moderate", "high"]
    traffic_light: Literal["green", "yellow", "red"]
    allostatic_score: float = Field(..., ge=0.0, le=100.0)
    energy_availability: float
    intensity_cap: float = Field(..., ge=0.0, le=1.0)
    insights: list[str] = Field(default_factory=list)


class HormonalProfileUpdate(BaseModel):
    enabled: bool
    cycle_length_days: int = Field(default=28, ge=21, le=45)
    last_period_start: Optional[date] = None
    tracking_source: Literal["manual", "apple_health"] = "manual"
    notes: Optional[str] = None
