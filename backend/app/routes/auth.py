from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..core.email import send_reset_email
from ..core.security import (
    create_access_token,
    generate_token,
    hash_password,
    hash_token,
    verify_password,
    verify_token,
)
from ..db.models import PasswordResetTokenModel, RefreshTokenModel, UserModel
from ..dependencies import get_current_athlete_id, get_db
from ..schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    MeResponse,
    RefreshRequest,
    ResetPasswordRequest,
    TokenResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])

DB = Annotated[Session, Depends(get_db)]
AuthedId = Annotated[str, Depends(get_current_athlete_id)]

_REFRESH_TTL_DAYS = int(os.getenv("JWT_REFRESH_TTL_DAYS", "30"))


def _issue_refresh_token(user_id: str, db: Session) -> str:
    """Generate a refresh token, store its hash in DB, return raw token."""
    raw = generate_token()
    db.add(RefreshTokenModel(
        id=str(uuid.uuid4()),
        user_id=user_id,
        token_hash=hash_token(raw),
        expires_at=datetime.now(timezone.utc) + timedelta(days=_REFRESH_TTL_DAYS),
        created_at=datetime.now(timezone.utc),
    ))
    return raw


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: DB) -> TokenResponse:
    user = db.query(UserModel).filter(UserModel.email == req.email).first()
    if user is None or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    user.last_login_at = datetime.now(timezone.utc)
    refresh = _issue_refresh_token(user.id, db)
    db.commit()

    return TokenResponse(
        access_token=create_access_token(athlete_id=user.athlete_id),
        refresh_token=refresh,
        athlete_id=user.athlete_id,
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(req: RefreshRequest, db: DB) -> TokenResponse:
    token_hash = hash_token(req.refresh_token)
    record = db.query(RefreshTokenModel).filter(
        RefreshTokenModel.token_hash == token_hash,
        RefreshTokenModel.revoked.is_(False),
        RefreshTokenModel.expires_at > datetime.now(timezone.utc),
    ).first()

    if record is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid or expired refresh token")

    user = db.query(UserModel).filter(UserModel.id == record.user_id).first()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    # Rotate: revoke old, issue new
    record.revoked = True
    new_refresh = _issue_refresh_token(user.id, db)
    db.commit()

    return TokenResponse(
        access_token=create_access_token(athlete_id=user.athlete_id),
        refresh_token=new_refresh,
        athlete_id=user.athlete_id,
    )
