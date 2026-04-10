#!/usr/bin/env bash
set -e

# Create DB tables if they don't exist (idempotent; works for both SQLite and postgres)
python -c "
from app.db.database import Base, engine
from app.db import models  # noqa — registers all ORM classes with Base
Base.metadata.create_all(engine)
print('DB ready.')
"

exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
