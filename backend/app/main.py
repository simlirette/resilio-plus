import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.sync_scheduler import setup_scheduler
from .routes.auth import router as auth_router
from .routes.onboarding import router as onboarding_router
from .routes.athletes import router as athletes_router
from .routes.connectors import router as connectors_router
from .routes.plans import router as plans_router
from .routes.reviews import router as reviews_router
from .routes.nutrition import router as nutrition_router
from .routes.recovery import router as recovery_router
from .routes.sessions import router as sessions_router
from .routes.analytics import router as analytics_router
from .routes.food_search import router as food_search_router
from .routes.workflow import router as workflow_router
from .routes.mode import router as mode_router
from .routes.checkin import router as checkin_router
from .routes.external_plan import router as external_plan_router
from .routes.strain import router as strain_router
from .routes.integrations import router as integrations_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = setup_scheduler()
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)


app = FastAPI(title="Resilio Plus API", version="0.1.0", lifespan=lifespan)

_raw = os.environ.get(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:4000,http://localhost:8081,http://localhost:19000",
)
_ALLOWED_ORIGINS = [o.strip() for o in _raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth_router)
app.include_router(onboarding_router)   # MUST be before athletes_router
app.include_router(athletes_router)
app.include_router(connectors_router)
app.include_router(plans_router)
app.include_router(reviews_router)
app.include_router(nutrition_router)
app.include_router(recovery_router)
app.include_router(sessions_router)
app.include_router(analytics_router)
app.include_router(food_search_router)
app.include_router(workflow_router)
app.include_router(mode_router)
app.include_router(checkin_router)
app.include_router(external_plan_router)
app.include_router(strain_router)
app.include_router(integrations_router)
