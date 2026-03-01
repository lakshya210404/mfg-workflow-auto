"""KPI API endpoints."""

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.schemas import BottleneckResponse, KPISummary
from app.services.kpi_service import calculate_kpi_summary, identify_bottlenecks

logger = logging.getLogger("mfg.api.kpis")
router = APIRouter(prefix="/kpis", tags=["KPIs"])


@router.get("/summary", response_model=KPISummary)
def get_kpi_summary(
    window_hours: int = Query(default=24, ge=1, le=168),
    db: Session = Depends(get_db),
) -> KPISummary:
    """
    Return KPI summary for the specified time window.

    - **throughput_per_hour**: completed work orders per hour
    - **avg_cycle_time_minutes**: average time from WO start to completion
    - **defect_rate_percent**: defect events as % of last 50 events
    - **total_downtime_minutes**: cumulative machine downtime in window
    - **completed_work_orders**: total WOs completed in window
    - **active_stations** / **stations_down**: station health counts
    """
    return calculate_kpi_summary(db, window_hours=window_hours)


@router.get("/bottlenecks", response_model=BottleneckResponse)
def get_bottlenecks(
    window_hours: int = Query(default=24, ge=1, le=168),
    db: Session = Depends(get_db),
) -> BottleneckResponse:
    """
    Identify bottleneck stations where average cycle time exceeds the threshold.

    Returns stations with recommendations to add capacity or reduce batch size.
    """
    return identify_bottlenecks(db, window_hours=window_hours)
