import os
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from logging_config import configure_logging, get_logger
from routes.tides import router as tides_router
from routes.locations import router as locations_router
from routes.conditions import router as conditions_router
from routes.sun_events import router as sun_events_router
from routes.sightings import router as sightings_router
from routes.scrapers import router as scrapers_router
from routes.live_cams import router as live_cams_router

# Configure logging on startup
configure_logging()
logger = get_logger("api")

# Get version from environment (baked into Docker image)
APP_VERSION = os.getenv("APP_VERSION", "dev")


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Inject a unique request ID into every request for log correlation."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


app = FastAPI(title="Pacifica API", version=APP_VERSION)

app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics (if prometheus-fastapi-instrumentator is installed)
try:
    from prometheus_fastapi_instrumentator import Instrumentator

    Instrumentator(
        should_group_status_codes=False,
        should_ignore_untemplated=True,
        excluded_handlers=["/api/health", "/api/version"],
    ).instrument(app).expose(app, endpoint="/metrics")
    logger.info("prometheus_enabled", endpoint="/metrics")
except ImportError:
    logger.info(
        "prometheus_disabled", reason="prometheus-fastapi-instrumentator not installed"
    )

# Include routers
app.include_router(tides_router)
app.include_router(locations_router)
app.include_router(conditions_router)
app.include_router(sun_events_router)
app.include_router(sightings_router)
app.include_router(scrapers_router)
app.include_router(live_cams_router)


@app.get("/api/health")
async def health_check():
    """Health check with DB connectivity verification.

    Returns healthy only if the API can successfully query PostgreSQL.
    This makes it a true readiness probe for Docker and load balancers.
    """
    from database import engine
    from sqlalchemy import text

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "service": "pacifica-api",
            "version": APP_VERSION,
            "database": "connected",
        }
    except Exception as e:
        logger.error("health_check_db_failed", error=str(e))
        return {
            "status": "unhealthy",
            "service": "pacifica-api",
            "version": APP_VERSION,
            "database": "disconnected",
            "error": str(e),
        }


@app.get("/api/version")
async def get_version():
    logger.info("version_requested")
    return {"version": APP_VERSION, "service": "pacifica-api", "api_version": "v1"}


@app.get("/api/v1/activity-scores")
async def get_activity_scores():
    logger.info("activity_scores_stub")
    return {"message": "Activity scores endpoint - stub implementation"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=4900)
