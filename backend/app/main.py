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
from .routes.food import router as food_router
from .routes.workflow import router as workflow_router
from .routes.mode import router as mode_router
from .routes.checkin import router as checkin_router
from .routes.external_plan import router as external_plan_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = setup_scheduler()
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)


app = FastAPI(title="Resilio Plus API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
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
app.include_router(food_router)
app.include_router(workflow_router)
app.include_router(mode_router)
app.include_router(checkin_router)
app.include_router(external_plan_router)
