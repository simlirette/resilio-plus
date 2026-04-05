"""
FastAPI application stub — Resilio+
S11 complétera : auth JWT, middleware CORS, autres routers.
"""

from fastapi import FastAPI

from api.v1.connectors import router as connectors_router

app = FastAPI(title="Resilio+", version="0.1.0")

app.include_router(
    connectors_router,
    prefix="/api/v1/connectors",
    tags=["connectors"],
)
