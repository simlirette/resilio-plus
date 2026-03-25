# Backend — FastAPI

> **Status**: Placeholder — implemented in Phase 2.

This directory will contain the FastAPI application for Resilio Plus.

## Planned structure (Phase 2+)

```
backend/
├── resilio/
│   ├── agents/          # AI agent implementations
│   ├── api/             # FastAPI routes
│   ├── connectors/      # Strava, Hevy, FatSecret, Apple Health
│   ├── core/            # Business logic (fatigue, periodization, conflict)
│   ├── schemas/         # Pydantic models
│   └── db/              # SQLAlchemy + SQLite
└── Dockerfile
```

## Running (Phase 2+)

```bash
poetry run uvicorn backend.resilio.main:app --reload
```
