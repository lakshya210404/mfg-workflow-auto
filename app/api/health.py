"""Health check endpoint."""

import logging

import redis as redis_lib
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.schemas.schemas import HealthResponse

logger = logging.getLogger("mfg.api.health")
router = APIRouter(tags=["Health"])

APP_VERSION = "1.0.0"


@router.get("/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)) -> HealthResponse:
    """Return service health including DB and Redis connectivity."""
    db_status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        logger.error("DB health check failed: %s", exc)
        db_status = f"error: {exc}"

    redis_status = "ok"
    try:
        r = redis_lib.from_url(settings.redis_url, socket_connect_timeout=2)
        r.ping()
    except Exception as exc:
        logger.error("Redis health check failed: %s", exc)
        redis_status = f"error: {exc}"

    return HealthResponse(
        status="healthy" if db_status == "ok" and redis_status == "ok" else "degraded",
        version=APP_VERSION,
        database=db_status,
        redis=redis_status,
    )
