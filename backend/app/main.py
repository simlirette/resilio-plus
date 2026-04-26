# Observability MUST be configured before anything else imports logging
from .observability.logging_config import configure_logging as _configure_logging

_configure_logging()

from .observability.sentry import init_sentry as _init_sentry

_init_sentry()

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .jobs.scheduler import setup_scheduler
from .observability.correlation import CorrelationIdMiddleware
from .observability.metrics import MetricsMiddleware
from .routes.admin import router as admin_router
from .routes.analytics import router as analytics_router
from .routes.athletes import router as athletes_router
from .routes.auth import router as auth_router
from .routes.checkin import router as checkin_router
from .routes.chat import router as chat_router
from .routes.connectors import router as connectors_router
from .routes.coordinator import router as coordinator_router
from .routes.external_plan import router as external_plan_router
from .routes.food_search import router as food_search_router
from .routes.health import router as health_router
from .routes.integrations import router as integrations_router
from .routes.mode import router as mode_router
from .routes.nutrition import router as nutrition_router
from .routes.onboarding import router as onboarding_router
from .routes.onboarding_d7 import router as onboarding_d7_router
from .routes.plans import router as plans_router
from .routes.recovery import router as recovery_router
from .routes.reviews import router as reviews_router
from .routes.sessions import router as sessions_router
from .routes.strain import router as strain_router
from .routes.strava import router as strava_router
from .routes.workflow import router as workflow_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
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

# Middleware stack — FastAPI applies in reverse registration order.
# Desired runtime flow on a request: CORS → CorrelationId → Metrics → handler.
# So add CORS first (outermost), then CorrelationId, then Metrics last (innermost).
app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(MetricsMiddleware)

app.include_router(auth_router)
app.include_router(onboarding_router)  # MUST be before athletes_router
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
app.include_router(strava_router)
app.include_router(chat_router)
app.include_router(onboarding_d7_router)
app.include_router(coordinator_router)
app.include_router(admin_router)
app.include_router(health_router)
