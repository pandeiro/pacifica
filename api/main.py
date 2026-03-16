import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from logging_config import configure_logging, get_logger
from routes.tides import router as tides_router

# Configure logging on startup
configure_logging()
logger = get_logger("api")

# Get version from environment (baked into Docker image)
APP_VERSION = os.getenv("APP_VERSION", "dev")

app = FastAPI(title="Pacifica API", version=APP_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(tides_router)


@app.get("/api/health")
async def health_check():
    logger.debug("Health check requested")
    return {"status": "healthy", "service": "pacifica-api", "version": APP_VERSION}


@app.get("/api/version")
async def get_version():
    logger.info("Version endpoint called")
    return {"version": APP_VERSION, "service": "pacifica-api", "api_version": "v1"}


@app.get("/api/v1/conditions")
async def get_conditions():
    logger.info("Conditions endpoint called")
    return {"message": "Conditions endpoint - stub implementation"}


@app.get("/api/v1/sightings")
async def get_sightings():
    logger.info("Sightings endpoint called")
    return {"message": "Sightings endpoint - stub implementation"}


@app.get("/api/v1/activity-scores")
async def get_activity_scores():
    logger.info("Activity scores endpoint called")
    return {"message": "Activity scores endpoint - stub implementation"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=4900)
