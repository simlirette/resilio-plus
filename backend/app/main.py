from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.auth import router as auth_router
from app.routes.athletes import router as athletes_router
from app.routes.connectors import router as connectors_router
from app.routes.plans import router as plans_router

app = FastAPI(title="Resilio Plus API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(athletes_router)
app.include_router(connectors_router)
app.include_router(plans_router)
