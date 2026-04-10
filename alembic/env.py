"""
Alembic env.py — Configuration async pour PostgreSQL (asyncpg).

Commandes utiles :
  alembic revision --autogenerate -m "message"  # Générer une migration
  alembic upgrade head                           # Appliquer toutes les migrations
  alembic downgrade -1                           # Rollback d'une migration
  alembic current                                # Version actuelle
"""

import asyncio
from logging.config import fileConfig

from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context
from core.config import settings

# Import Base pour que autogenerate détecte toutes les tables de database.py
from models.database import Base  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Génère le SQL sans connexion DB (pour review avant exécution)."""
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:  # type: ignore[no-untyped-def]
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Exécute les migrations sur la DB async."""
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
