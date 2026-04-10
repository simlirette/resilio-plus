# Backend — FastAPI

## Structure

```
backend/
├── app/
│   ├── agents/       # Coaching agents (Head, Running, Lifting, Swimming, Biking, Nutrition, Recovery)
│   ├── connectors/   # Strava, Hevy, Terra, Apple Health
│   ├── core/         # Business logic (ACWR, fatigue, periodization, conflict, security)
│   ├── db/           # SQLAlchemy models + SQLite/PostgreSQL engine
│   ├── models/       # V3 SQLAlchemy models (energy, hormonal, allostatic)
│   ├── routes/       # FastAPI routers
│   ├── schemas/      # Pydantic schemas
│   ├── services/     # Service layer
│   ├── dependencies.py
│   └── main.py
└── README.md
```

## Running locally (from project root)

```bash
# Option 1 — recommended
poetry run uvicorn backend.app.main:app --reload

# Option 2 — explicit PYTHONPATH
PYTHONPATH=backend poetry run uvicorn app.main:app --reload
```

API available at: http://localhost:8000  
Swagger docs at: http://localhost:8000/docs

## Alembic migrations

```bash
# Run from project root
PYTHONPATH=backend poetry run alembic upgrade head
```

## Docker

```bash
# From project root
docker-compose up -d
```

Services:
- PostgreSQL: localhost:5432
- Backend API: localhost:8000
- Frontend: localhost:4000

## Tests

```bash
poetry run pytest tests/ -v --tb=short
```
