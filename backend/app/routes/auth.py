from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..core.email import send_reset_email
from ..core.security import (
    create_access_token,
    generate_token,
    hash_password,
    hash_token,
    verify_password,
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
    db.add(
        RefreshTokenModel(
            id=str(uuid.uuid4()),
            user_id=user_id,
            token_hash=hash_token(raw),
            expires_at=datetime.now(timezone.utc) + timedelta(days=_REFRESH_TTL_DAYS),
            created_at=datetime.now(timezone.utc),
        )
    )
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
    record = (
        db.query(RefreshTokenModel)
        .filter(
            RefreshTokenModel.token_hash == token_hash,
            RefreshTokenModel.revoked.is_(False),
            RefreshTokenModel.expires_at > datetime.now(timezone.utc),
        )
        .first()
    )

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token"
        )

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


@router.post("/logout")
def logout(req: LogoutRequest, current_id: AuthedId, db: DB) -> dict[str, Any]:
    token_hash = hash_token(req.refresh_token)
    record = (
        db.query(RefreshTokenModel)
        .filter(
            RefreshTokenModel.token_hash == token_hash,
            RefreshTokenModel.revoked.is_(False),
        )
        .first()
    )
    if record is not None:
        record.revoked = True
        db.commit()
    return {"message": "Logged out"}


@router.get("/me", response_model=MeResponse)
def me(current_id: AuthedId, db: DB) -> MeResponse:
    user = db.query(UserModel).filter(UserModel.athlete_id == current_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return MeResponse(
        athlete_id=user.athlete_id,
        email=user.email,
        created_at=user.created_at,
        is_active=user.is_active,
    )


@router.post("/forgot-password")
def forgot_password(req: ForgotPasswordRequest, db: DB) -> dict[str, Any]:
    user = db.query(UserModel).filter(UserModel.email == req.email).first()
    _msg = {"message": "If this email is registered, a reset link has been sent."}

    if user is None:
        return _msg  # no-op — prevent email enumeration

    # Invalidate any existing unused reset tokens
    db.query(PasswordResetTokenModel).filter(
        PasswordResetTokenModel.user_id == user.id,
        PasswordResetTokenModel.used.is_(False),
    ).update({"used": True})

    raw = generate_token()
    db.add(
        PasswordResetTokenModel(
            id=str(uuid.uuid4()),
            user_id=user.id,
            token_hash=hash_token(raw),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
    )
    db.commit()

    base_url = os.getenv("APP_BASE_URL", "http://localhost:3000")
    reset_url = f"{base_url}/reset-password?token={raw}"
    send_reset_email(user.email, reset_url)

    return _msg


@router.post("/reset-password")
def reset_password(req: ResetPasswordRequest, db: DB) -> dict[str, Any]:
    token_hash = hash_token(req.token)
    record = (
        db.query(PasswordResetTokenModel)
        .filter(
            PasswordResetTokenModel.token_hash == token_hash,
            PasswordResetTokenModel.used.is_(False),
            PasswordResetTokenModel.expires_at > datetime.now(timezone.utc),
        )
        .first()
    )

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token"
        )

    record.used = True
    user = db.query(UserModel).filter(UserModel.id == record.user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.hashed_password = hash_password(req.new_password)

    # Revoke all active refresh tokens — password changed, all sessions invalidated
    db.query(RefreshTokenModel).filter(
        RefreshTokenModel.user_id == user.id,
        RefreshTokenModel.revoked.is_(False),
    ).update({"revoked": True})

    db.commit()
    return {"message": "Password updated successfully. Please log in again."}
