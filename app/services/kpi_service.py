"""KPI calculation service."""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.models import Event, EventType, KPIHistory, Station, StationStatus, WorkOrder, WorkOrderStatus
from app.schemas.schemas import BottleneckInfo, BottleneckResponse, KPISummary

logger = logging.getLogger("mfg.kpi")


def calculate_kpi_summary(db: Session, window_hours: int = 24) -> KPISummary:
    """
    Compute KPI snapshot over the last ``window_hours``.

    Returns throughput, cycle time, defect rate, downtime, station counts.
    """
    since = datetime.now(tz=timezone.utc) - timedelta(hours=window_hours)

    # Completed work orders in window
    completed_wos = (
        db.execute(
            select(WorkOrder).where(
                WorkOrder.status == WorkOrderStatus.COMPLETED,
                WorkOrder.completed_at >= since,
            )
        )
        .scalars()
        .all()
    )
    completed_count = len(completed_wos)
    throughput = completed_count / window_hours if window_hours > 0 else 0.0

    # Average cycle time (started_at -> completed_at)
    cycle_times: list[float] = []
    for wo in completed_wos:
        if wo.started_at and wo.completed_at:
            delta = (wo.completed_at - wo.started_at).total_seconds() / 60.0
            cycle_times.append(delta)
    avg_cycle_time = sum(cycle_times) / len(cycle_times) if cycle_times else 0.0

    # Defect rate from last 50 events
    recent_events = (
        db.execute(
            select(Event)
            .where(Event.timestamp >= since)
            .order_by(Event.timestamp.desc())
            .limit(50)
        )
        .scalars()
        .all()
    )
    defect_count = sum(1 for e in recent_events if e.type == EventType.DEFECT_FOUND)
    defect_rate = (defect_count / len(recent_events) * 100) if recent_events else 0.0

    # Downtime: sum of machine_down events' duration from payload
    down_events = (
        db.execute(
            select(Event).where(
                Event.type == EventType.MACHINE_DOWN,
                Event.timestamp >= since,
            )
        )
        .scalars()
        .all()
    )
    total_downtime = sum(
        (e.payload or {}).get("duration_minutes", 5) for e in down_events
    )

    # Station counts
    all_stations = db.execute(select(Station)).scalars().all()
    active = sum(1 for s in all_stations if s.status == StationStatus.RUNNING)
    down = sum(1 for s in all_stations if s.status == StationStatus.DOWN)

    logger.info(
        "KPI summary computed | completed=%d throughput=%.2f defect_rate=%.2f%%",
        completed_count,
        throughput,
        defect_rate,
    )

    return KPISummary(
        throughput_per_hour=round(throughput, 4),
        avg_cycle_time_minutes=round(avg_cycle_time, 2),
        defect_rate_percent=round(defect_rate, 2),
        total_downtime_minutes=round(total_downtime, 2),
        completed_work_orders=completed_count,
        active_stations=active,
        stations_down=down,
    )


def identify_bottlenecks(db: Session, window_hours: int = 24) -> BottleneckResponse:
    """
    Identify bottleneck stations by average step completion time.

    A station is flagged if its average cycle time exceeds the configured threshold.
    """
    from app.core.config import settings

    since = datetime.now(tz=timezone.utc) - timedelta(hours=window_hours)

    # STEP_COMPLETED events carry duration_minutes in payload
    step_events = (
        db.execute(
            select(Event).where(
                Event.type == EventType.STEP_COMPLETED,
                Event.timestamp >= since,
                Event.station_id.isnot(None),
            )
        )
        .scalars()
        .all()
    )

    # Group by station
    station_times: dict[int, list[float]] = {}
    for ev in step_events:
        duration = (ev.payload or {}).get("duration_minutes", 0.0)
        station_times.setdefault(ev.station_id, []).append(duration)  # type: ignore[arg-type]

    bottlenecks: list[BottleneckInfo] = []
    for station_id, durations in station_times.items():
        avg = sum(durations) / len(durations)
        if avg > settings.cycle_time_threshold_minutes:
            station = db.get(Station, station_id)
            if not station:
                continue
            bottlenecks.append(
                BottleneckInfo(
                    station_id=station_id,
                    station_name=station.name,
                    station_type=station.type.value,
                    avg_cycle_time_minutes=round(avg, 2),
                    event_count=len(durations),
                    recommendation=(
                        f"Station '{station.name}' avg cycle time "
                        f"{avg:.1f} min exceeds threshold "
                        f"{settings.cycle_time_threshold_minutes:.1f} min. "
                        "Consider adding parallel capacity or reducing batch size."
                    ),
                )
            )

    bottlenecks.sort(key=lambda b: b.avg_cycle_time_minutes, reverse=True)
    logger.info("Bottleneck analysis found %d bottlenecks", len(bottlenecks))
    return BottleneckResponse(bottlenecks=bottlenecks, analysis_window_hours=window_hours)


def snapshot_kpis(db: Session) -> KPIHistory:
    """Persist current KPI snapshot to kpi_history table."""
    summary = calculate_kpi_summary(db)
    record = KPIHistory(
        throughput=summary.throughput_per_hour,
        defect_rate=summary.defect_rate_percent / 100,
        downtime_minutes=summary.total_downtime_minutes,
        avg_cycle_time=summary.avg_cycle_time_minutes,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    logger.info("KPI snapshot saved | id=%d", record.id)
    return record
