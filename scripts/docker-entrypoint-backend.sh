#!/usr/bin/env bash
set -e

# Create SQLite tables if they don't exist (idempotent)
python -c "
from app.db.database import Base, engine
from app.db import models  # noqa — registers all ORM classes with Base
Base.metadata.create_all(engine)
print('DB ready.')
"

exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
