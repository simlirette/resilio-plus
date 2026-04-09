"""
AUTH ROUTES — Resilio+
POST /register  — Create athlete account
POST /login     — Obtain JWT access token
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import create_access_token, hash_password, verify_password
from models.database import Athlete
from models.db_session import get_db

router = APIRouter()


class RegisterRequest(BaseModel):
    email: str
    password: str
    first_name: str
    age: int
    sex: str
    weight_kg: float
    height_cm: float


class RegisterResponse(BaseModel):
    id: str
    email: str
    first_name: str
    access_token: str


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Athlete).where(Athlete.email == body.email))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Email already registered")

    athlete = Athlete(
        email=body.email,
        password_hash=hash_password(body.password),
        first_name=body.first_name,
        age=body.age,
        sex=body.sex,
        weight_kg=body.weight_kg,
        height_cm=body.height_cm,
        profile_data={},
        available_days={},
    )
    db.add(athlete)
    await db.commit()
    await db.refresh(athlete)

    return RegisterResponse(
        id=str(athlete.id),
        email=athlete.email,
        first_name=athlete.first_name,
        access_token=create_access_token(athlete.id),
    )


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Athlete).where(Athlete.email == body.email))
    athlete = result.scalar_one_or_none()
    if athlete is None or not verify_password(body.password, athlete.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return LoginResponse(access_token=create_access_token(athlete.id))
