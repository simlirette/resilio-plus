#!/usr/bin/env bash
# Entrypoint for the backend Docker image.
# Recognized env vars: WEB_CONCURRENCY (gunicorn workers, prod only), HOST, PORT.
set -euo pipefail

MODE="${1:-prod}"

case "$MODE" in
  prod|dev) ;;
  *)
    echo "[entrypoint] unknown mode: $MODE (expected: prod|dev)" >&2
    exit 2
    ;;
esac

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
      --timeout 120 \
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
esac
