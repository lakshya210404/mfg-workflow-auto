"""Work Orders API endpoints."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import WorkOrder, WorkOrderStatus
from app.schemas.schemas import WorkOrderCreate, WorkOrderResponse

logger = logging.getLogger("mfg.api.work_orders")
router = APIRouter(prefix="/work-orders", tags=["Work Orders"])


@router.post("/", response_model=WorkOrderResponse, status_code=status.HTTP_201_CREATED)
def create_work_order(payload: WorkOrderCreate, db: Session = Depends(get_db)) -> WorkOrder:
    """Create a new manufacturing work order."""
    wo = WorkOrder(product_type=payload.product_type, priority=payload.priority)
    db.add(wo)
    db.commit()
    db.refresh(wo)
    logger.info("Created work order id=%d type=%s", wo.id, wo.product_type)
    return wo


@router.get("/", response_model=list[WorkOrderResponse])
def list_work_orders(
    status_filter: WorkOrderStatus | None = Query(default=None, alias="status"),
    from_date: datetime | None = Query(default=None),
    to_date: datetime | None = Query(default=None),
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
) -> list[WorkOrder]:
    """List work orders with optional filters."""
    q = select(WorkOrder)
    if status_filter:
        q = q.where(WorkOrder.status == status_filter)
    if from_date:
        q = q.where(WorkOrder.created_at >= from_date)
    if to_date:
        q = q.where(WorkOrder.created_at <= to_date)
    q = q.order_by(WorkOrder.created_at.desc()).limit(limit)
    return list(db.execute(q).scalars().all())


@router.get("/{work_order_id}", response_model=WorkOrderResponse)
def get_work_order(work_order_id: int, db: Session = Depends(get_db)) -> WorkOrder:
    """Fetch a single work order by ID."""
    wo = db.get(WorkOrder, work_order_id)
    if not wo:
        raise HTTPException(status_code=404, detail=f"Work order {work_order_id} not found")
    return wo
