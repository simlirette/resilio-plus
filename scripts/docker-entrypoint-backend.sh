#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-prod}"

echo "[entrypoint] running alembic migrations..."
alembic upgrade head

case "$MODE" in
  prod)
    WORKERS="${WEB_CONCURRENCY:-2}"
    echo "[entrypoint] starting gunicorn with $WORKERS uvicorn workers..."
    exec gunicorn app.main:app \
      --worker-class uvicorn.workers.UvicornWorker \
      --workers "$WORKERS" \
      --bind "${HOST:-0.0.0.0}:${PORT:-8000}" \
      --timeout 60 \
      --graceful-timeout 30 \
      --access-logfile - \
      --error-logfile -
    ;;
  dev)
    echo "[entrypoint] starting uvicorn with --reload..."
    exec uvicorn app.main:app \
      --host "${HOST:-0.0.0.0}" \
      --port "${PORT:-8000}" \
      --reload
    ;;
  *)
    echo "[entrypoint] unknown mode: $MODE (expected: prod|dev)" >&2
    exit 2
    ;;
esac
