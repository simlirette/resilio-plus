#!/usr/bin/env bash
# Start backend in prod mode on a POSIX host (VPS, CI). No Docker.
# Requires: venv with deps installed, .env populated, PostgreSQL reachable.
set -euo pipefail

if [ ! -f .env ]; then
  echo ".env file missing. Copy .env.example to .env and fill in values." >&2
  exit 1
fi

# Load .env into environment.
set -a
. ./.env
set +a

echo "[prod] running alembic migrations..."
PYTHONPATH=backend alembic upgrade head

WORKERS="${WEB_CONCURRENCY:-2}"
echo "[prod] starting gunicorn with $WORKERS uvicorn workers on ${HOST:-0.0.0.0}:${PORT:-8000}..."
PYTHONPATH=backend exec gunicorn app.main:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers "$WORKERS" \
  --bind "${HOST:-0.0.0.0}:${PORT:-8000}" \
  --timeout 120 \
  --graceful-timeout 30 \
  --access-logfile - \
  --error-logfile -
