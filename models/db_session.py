"""
DATABASE CONNECTION — Resilio+
Configuration async SQLAlchemy + PostgreSQL.
La DATABASE_URL est lue depuis les variables d'environnement.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from core.config import settings
from models.database import Base

# ─────────────────────────────────────────────
# ENGINE
# ─────────────────────────────────────────────

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,        # True en dev uniquement
    pool_pre_ping=True,           # Vérifie la connexion avant usage
    poolclass=NullPool if settings.TESTING else None,  # NullPool pour les tests
)


# ─────────────────────────────────────────────
# SESSION FACTORY
# ─────────────────────────────────────────────

AsyncSessionFactory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,        # Évite les lazy load après commit
)


# ─────────────────────────────────────────────
# DEPENDENCY FASTAPI
# ─────────────────────────────────────────────

async def get_db() -> AsyncSession:
    """
    Dependency FastAPI pour injecter une session DB dans les routes.

    Usage dans un router :
        @router.get("/athletes/{id}")
        async def get_athlete(id: UUID, db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ─────────────────────────────────────────────
# INIT DB (dev/tests uniquement)
# ─────────────────────────────────────────────

async def init_db() -> None:
    """
    Crée toutes les tables. À utiliser en dev et tests uniquement.
    En production, utiliser Alembic migrations.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_db() -> None:
    """Supprime toutes les tables. Tests uniquement."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
