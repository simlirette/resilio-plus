"""DB management entry points — exposed as Poetry scripts.

Commands:
  poetry run db-migrate     — alembic upgrade head
  poetry run db-seed        — insert dev seed data (Alice + Marc)
  poetry run db-seed-test   — insert minimal test fixture
  poetry run db-reset       — drop schema + migrate + seed-dev (requires --confirm)
"""
from __future__ import annotations

import os
import sys


def _require_db_url() -> str:
    url = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg2://resilio:resilio@localhost:5432/resilio_db",
    )
    return url


def migrate() -> None:
    """Run alembic upgrade head."""
    from alembic.config import Config
    from alembic import command as alembic_cmd

    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", _require_db_url())
    alembic_cmd.upgrade(cfg, "head")
    print("✓ Migrations applied.")


def seed_dev() -> None:
    """Insert dev seed data (Alice + Marc). Idempotent."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from scripts.seed_data.alice import insert_alice
    from scripts.seed_data.marc import insert_marc

    engine = create_engine(_require_db_url())
    with Session(engine) as session:
        insert_alice(session)
        insert_marc(session)
        session.commit()
    engine.dispose()
    print("✓ Dev seed data inserted (Alice + Marc).")


def seed_test() -> None:
    """Insert minimal test fixture. Idempotent."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from scripts.seed_data.test_fixture import insert_test_fixture

    url = os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql+psycopg2://resilio:resilio@localhost:5433/resilio_test",
    )
    engine = create_engine(url)
    with Session(engine) as session:
        insert_test_fixture(session)
        session.commit()
    engine.dispose()
    print("✓ Test fixture inserted.")


def reset() -> None:
    """Drop schema + migrate + seed-dev. Requires --confirm flag."""
    if "--confirm" not in sys.argv:
        print(
            "ERROR: db-reset is destructive. Re-run with --confirm to proceed.\n"
            "  poetry run db-reset --confirm"
        )
        sys.exit(1)

    from sqlalchemy import create_engine, text

    url = _require_db_url()
    engine = create_engine(url)

    print("Dropping all tables...")
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        conn.commit()
    engine.dispose()

    migrate()
    seed_dev()
    print("✓ Database reset complete.")
