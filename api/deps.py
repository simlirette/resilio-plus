"""
FASTAPI DEPENDENCIES — Resilio+
Shared dependencies for authenticated endpoints.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import decode_access_token
from models.database import Athlete
from models.db_session import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_athlete(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Athlete:
    """Decode Bearer JWT → fetch Athlete from DB. Raises 401 if invalid or not found."""
    athlete_id = decode_access_token(token)
    result = await db.execute(select(Athlete).where(Athlete.id == athlete_id))
    athlete = result.scalar_one_or_none()
    if athlete is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Athlete not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return athlete
