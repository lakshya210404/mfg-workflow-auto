"""Stations API endpoints."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import Station
from app.schemas.schemas import StationCreate, StationResponse, StationUpdate

logger = logging.getLogger("mfg.api.stations")
router = APIRouter(prefix="/stations", tags=["Stations"])


@router.post("/", response_model=StationResponse, status_code=status.HTTP_201_CREATED)
def create_station(payload: StationCreate, db: Session = Depends(get_db)) -> Station:
    """Register a new manufacturing station."""
    existing = db.execute(select(Station).where(Station.name == payload.name)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Station with name '{payload.name}' already exists",
        )
    station = Station(name=payload.name, type=payload.type)
    db.add(station)
    db.commit()
    db.refresh(station)
    logger.info("Created station id=%d name=%s", station.id, station.name)
    return station


@router.get("/", response_model=list[StationResponse])
def list_stations(db: Session = Depends(get_db)) -> list[Station]:
    """List all registered stations."""
    return list(db.execute(select(Station)).scalars().all())


@router.get("/{station_id}", response_model=StationResponse)
def get_station(station_id: int, db: Session = Depends(get_db)) -> Station:
    """Fetch a single station by ID."""
    station = db.get(Station, station_id)
    if not station:
        raise HTTPException(status_code=404, detail=f"Station {station_id} not found")
    return station


@router.patch("/{station_id}", response_model=StationResponse)
def update_station_status(
    station_id: int, payload: StationUpdate, db: Session = Depends(get_db)
) -> Station:
    """Update station status and refresh heartbeat."""
    station = db.get(Station, station_id)
    if not station:
        raise HTTPException(status_code=404, detail=f"Station {station_id} not found")
    station.status = payload.status
    station.last_heartbeat_at = datetime.now(tz=timezone.utc)
    db.commit()
    db.refresh(station)
    logger.info("Station %d status updated to %s", station_id, payload.status)
    return station
