# Start backend in dev mode on the Windows host (no Docker).
# Requires: Poetry installed, PostgreSQL reachable at $DATABASE_URL.
$ErrorActionPreference = "Stop"

if (-not (Test-Path ".env")) {
    Write-Error ".env file missing. Copy .env.example to .env and fill in values."
}

Write-Host "[dev] installing dependencies via poetry..."
poetry install --no-root

Write-Host "[dev] running alembic migrations..."
$env:PYTHONPATH = "backend"
poetry run alembic upgrade head

Write-Host "[dev] starting uvicorn on http://localhost:8000 ..."
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
