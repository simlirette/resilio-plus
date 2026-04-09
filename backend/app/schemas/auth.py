from datetime import date

from pydantic import BaseModel, Field

from .athlete import AthleteCreate, AthleteResponse
from .plan import TrainingPlanResponse


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    athlete_id: str


class OnboardingRequest(AthleteCreate):
    email: str
    password: str = Field(..., min_length=8)
    plan_start_date: date


class OnboardingResponse(BaseModel):
    athlete: AthleteResponse
    plan: TrainingPlanResponse
    access_token: str
    token_type: str = "bearer"
