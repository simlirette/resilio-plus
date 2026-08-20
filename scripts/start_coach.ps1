# Start the V4 text coach on this machine.
#
#   .\scripts\start_coach.ps1
#
# Brings up Postgres, migrates to head, runs the preflight, and starts the
# backend in polling mode. Ctrl+C stops the backend; the database keeps running
# (stop it with: docker compose stop db).
#
# ASCII only on purpose: PowerShell 5.1 reads .ps1 as ANSI when there is no BOM,
# and a stray em dash breaks the parser in a way that reads as a quoting bug.
# ErrorActionPreference stays Continue because docker and alembic write progress
# to stderr, which "Stop" would treat as a fatal error; exit codes are checked
# explicitly instead.

$ErrorActionPreference = "Continue"
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

$venv = "C:\Users\simon\AppData\Local\pypoetry\Cache\virtualenvs\resilio-8kDCl3fk-py3.13\Scripts"
$python = Join-Path $venv "python.exe"
if (-not (Test-Path $python)) {
    Write-Host "[coach] Poetry venv not found at $venv - run 'poetry install' first." -ForegroundColor Red
    exit 1
}

# On Windows, WSL can own [::1]:5432, and 'localhost' resolves there first -
# which looks exactly like a dead database ("server closed the connection
# unexpectedly") while docker reports it healthy. Pin the IPv4 loopback.
if (-not $env:DATABASE_URL) {
    $env:DATABASE_URL = "postgresql+psycopg2://resilio:resilio@127.0.0.1:5432/resilio_db"
}
elseif ($env:DATABASE_URL -match "@localhost:") {
    $env:DATABASE_URL = $env:DATABASE_URL -replace "@localhost:", "@127.0.0.1:"
    Write-Host "[coach] DATABASE_URL used 'localhost' - switched to 127.0.0.1 for this run." -ForegroundColor Yellow
    Write-Host "[coach] Change it in .env too, or every other tool hits the same wall." -ForegroundColor Yellow
}
if (-not $env:TELEGRAM_MODE) { $env:TELEGRAM_MODE = "polling" }
if (-not $env:PUBLIC_BASE_URL) { $env:PUBLIC_BASE_URL = "http://127.0.0.1:8000" }
$env:PYTHONPATH = "backend"

Write-Host "[coach] starting Postgres ..." -ForegroundColor Cyan
docker compose up -d db *>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[coach] 'docker compose up -d db' failed. Is Docker Desktop running?" -ForegroundColor Red
    exit 1
}

Write-Host "[coach] waiting for Postgres ..." -ForegroundColor Cyan
$ready = $false
foreach ($attempt in 1..30) {
    docker compose exec -T db pg_isready -U resilio -d resilio_db *>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) { $ready = $true; break }
    Start-Sleep -Seconds 1
}
if (-not $ready) {
    Write-Host "[coach] Postgres did not come up. Check: docker compose logs db" -ForegroundColor Red
    exit 1
}

Write-Host "[coach] applying migrations ..." -ForegroundColor Cyan
& $python -m alembic upgrade head
if ($LASTEXITCODE -ne 0) {
    Write-Host "[coach] migration failed." -ForegroundColor Red
    exit 1
}

Write-Host "[coach] preflight ..." -ForegroundColor Cyan
& $python scripts\bootstrap_v4.py --check
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[coach] Fill the missing settings in .env, then re-run." -ForegroundColor Yellow
    Write-Host "[coach] Generate the secrets with: python scripts\bootstrap_v4.py --keys" -ForegroundColor Yellow
    exit 1
}

# --env-file is not optional: the preflight above reads .env itself, so without
# it the server starts "configured" by every check and still cannot see
# ANTHROPIC_API_KEY, TELEGRAM_BOT_TOKEN or the Google settings.
Write-Host "[coach] backend on http://127.0.0.1:8000 - Ctrl+C to stop" -ForegroundColor Green
& $python -m uvicorn app.main:app --env-file .env --host 127.0.0.1 --port 8000
