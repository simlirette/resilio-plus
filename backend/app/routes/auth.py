from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..core.security import create_access_token, verify_password
from ..db.models import UserModel
from ..dependencies import get_db
from ..schemas.auth import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])

DB = Annotated[Session, Depends(get_db)]


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: DB) -> TokenResponse:
    user = db.query(UserModel).filter(UserModel.email == req.email).first()
    if user is None or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token(athlete_id=user.athlete_id)
    return TokenResponse(access_token=token, athlete_id=user.athlete_id)
