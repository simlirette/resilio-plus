"""
FastAPI application stub — Resilio+
S11 complétera : auth JWT, middleware CORS, autres routers.
"""

from fastapi import FastAPI

from api.v1.apple_health import router as apple_health_router
from api.v1.connectors import router as connectors_router
from api.v1.files import router as files_router
from api.v1.food import router as food_router

app = FastAPI(title="Resilio+", version="0.1.0")

app.include_router(
    connectors_router,
    prefix="/api/v1/connectors",
    tags=["connectors"],
)
app.include_router(
    apple_health_router,
    prefix="/api/v1/connectors",
    tags=["apple-health"],
)
app.include_router(
    files_router,
    prefix="/api/v1/connectors",
    tags=["files"],
)
app.include_router(
    food_router,
    prefix="/api/v1/connectors",
    tags=["food"],
)
