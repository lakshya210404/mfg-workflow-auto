"""Events API endpoints."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import Event, EventType, Station, StationStatus, WorkOrder, WorkOrderStatus
from app.schemas.schemas import EventCreate, EventResponse

logger = logging.getLogger("mfg.api.events")
router = APIRouter(prefix="/events", tags=["Events"])


def _apply_event_side_effects(event: Event, db: Session) -> None:
    """Update WorkOrder / Station state based on event type (synchronous fast-path)."""
    now = datetime.now(tz=timezone.utc)

    if event.type == EventType.WORK_ORDER_STARTED and event.work_order_id:
        wo = db.get(WorkOrder, event.work_order_id)
        if wo and wo.status == WorkOrderStatus.PENDING:
            wo.status = WorkOrderStatus.IN_PROGRESS
            wo.started_at = now

    elif event.type == EventType.WORK_ORDER_COMPLETED and event.work_order_id:
        wo = db.get(WorkOrder, event.work_order_id)
        if wo:
            wo.status = WorkOrderStatus.COMPLETED
            wo.completed_at = now

    elif event.type == EventType.MACHINE_DOWN and event.station_id:
        station = db.get(Station, event.station_id)
        if station:
            station.status = StationStatus.DOWN
            station.last_heartbeat_at = now

    elif event.type == EventType.MACHINE_UP and event.station_id:
        station = db.get(Station, event.station_id)
        if station:
            station.status = StationStatus.RUNNING
            station.last_heartbeat_at = now

    elif event.type == EventType.MACHINE_IDLE and event.station_id:
        station = db.get(Station, event.station_id)
        if station:
            station.status = StationStatus.IDLE
            station.last_heartbeat_at = now


@router.post("/", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
def ingest_event(payload: EventCreate, db: Session = Depends(get_db)) -> Event:
    """Ingest a manufacturing floor event."""
    # Validate FK references
    if payload.station_id:
        station = db.get(Station, payload.station_id)
        if not station:
            raise HTTPException(status_code=404, detail=f"Station {payload.station_id} not found")
    if payload.work_order_id:
        wo = db.get(WorkOrder, payload.work_order_id)
        if not wo:
            raise HTTPException(
                status_code=404, detail=f"Work order {payload.work_order_id} not found"
            )

    event = Event(
        type=payload.type,
        station_id=payload.station_id,
        work_order_id=payload.work_order_id,
        payload=payload.payload,
    )
    db.add(event)
    _apply_event_side_effects(event, db)
    db.commit()
    db.refresh(event)

    logger.info(
        "Event ingested | id=%d type=%s station=%s wo=%s",
        event.id,
        event.type,
        payload.station_id,
        payload.work_order_id,
    )
    return event


@router.get("/", response_model=list[EventResponse])
def list_events(
    limit: int = 100,
    event_type: EventType | None = None,
    station_id: int | None = None,
    db: Session = Depends(get_db),
) -> list[Event]:
    """List recent events with optional filters."""
    q = select(Event).order_by(Event.timestamp.desc())
    if event_type:
        q = q.where(Event.type == event_type)
    if station_id:
        q = q.where(Event.station_id == station_id)
    q = q.limit(limit)
    return list(db.execute(q).scalars().all())
