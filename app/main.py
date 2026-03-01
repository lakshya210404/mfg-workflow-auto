"""Manufacturing Workflow Automation System – FastAPI application entry point."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.automation import router as automation_router
from app.api.events import router as events_router
from app.api.health import router as health_router
from app.api.kpis import router as kpis_router
from app.api.stations import router as stations_router
from app.api.work_orders import router as work_orders_router
from app.core.logging import setup_logging

setup_logging()
logger = logging.getLogger("mfg.main")

app = FastAPI(
    title="Manufacturing Workflow Automation System",
    description=(
        "Simulate a factory floor: work orders, stations, real-time events, "
        "KPI analytics, bottleneck detection, and automated rules."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health_router)
app.include_router(work_orders_router)
app.include_router(stations_router)
app.include_router(events_router)
app.include_router(kpis_router)
app.include_router(automation_router)


@app.on_event("startup")
async def startup_event() -> None:
    """Run DB migrations on startup."""
    import subprocess

    logger.info("Running Alembic migrations…")
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        logger.error("Migration failed: %s", result.stderr)
    else:
        logger.info("Migrations complete")
    logger.info("🏭 Manufacturing Workflow API is ready")
