from datetime import date, datetime

from pydantic import BaseModel, Field

from .athlete import AthleteCreate, AthleteResponse
from .plan import TrainingPlanResponse


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    athlete_id: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class MeResponse(BaseModel):
    athlete_id: str
    email: str
    created_at: datetime
    is_active: bool


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)


class OnboardingRequest(AthleteCreate):
    email: str
    password: str = Field(..., min_length=8)
    plan_start_date: date


class OnboardingResponse(BaseModel):
    athlete: AthleteResponse
    plan: TrainingPlanResponse
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
