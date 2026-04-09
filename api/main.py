"""
FastAPI application — Resilio+
S11: auth JWT, CORS middleware, OpenAPI metadata.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.v1.apple_health import router as apple_health_router
from api.v1.athletes import router as athletes_router
from api.v1.auth import router as auth_router
from api.v1.connectors import router as connectors_router
from api.v1.files import router as files_router
from api.v1.food import router as food_router
from api.v1.plan import router as plan_router
from api.v1.workflow import router as workflow_router

app = FastAPI(
    title="Resilio+",
    version="0.11.0",
    description=(
        "Multi-agent hybrid coaching platform for endurance and strength athletes. "
        "Orchestrates 7 specialist AI coaches (running, lifting, swimming, cycling, "
        "nutrition, recovery) under a Head Coach that manages ACWR, fatigue, and periodization."
    ),
    contact={"name": "Resilio+", "email": "simon@resilio.app"},
    openapi_tags=[
        {"name": "auth", "description": "JWT authentication — register and login"},
        {"name": "athletes", "description": "Athlete profile (authenticated)"},
        {"name": "plan", "description": "Workout plan generation (running, lifting, recovery)"},
        {"name": "workflow", "description": "Head Coach workflow — weekly review loop"},
        {"name": "connectors", "description": "Third-party integrations (Strava, Hevy)"},
        {"name": "apple-health", "description": "Apple Health data ingestion"},
        {"name": "files", "description": "GPX / FIT file import"},
        {"name": "food", "description": "Food search (USDA / Open Food Facts)"},
    ],
)

# CORS — allow Next.js dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(athletes_router, prefix="/api/v1/athletes", tags=["athletes"])
app.include_router(connectors_router, prefix="/api/v1/connectors", tags=["connectors"])
app.include_router(apple_health_router, prefix="/api/v1/connectors", tags=["apple-health"])
app.include_router(files_router, prefix="/api/v1/connectors", tags=["files"])
app.include_router(food_router, prefix="/api/v1/connectors", tags=["food"])
app.include_router(plan_router, prefix="/api/v1/plan", tags=["plan"])
app.include_router(workflow_router, prefix="/api/v1/workflow", tags=["workflow"])
