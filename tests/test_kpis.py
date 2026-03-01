"""Tests for KPI calculation correctness."""

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.models import Event, EventType, Station, StationStatus, StationType, WorkOrder, WorkOrderStatus
from app.services.kpi_service import calculate_kpi_summary, identify_bottlenecks


def _make_completed_wo(db: Session, minutes_ago: int = 10, cycle_minutes: float = 15.0) -> WorkOrder:
    """Helper: create a completed WO with known cycle time."""
    now = datetime.now(tz=timezone.utc)
    wo = WorkOrder(
        product_type="Test-Widget",
        status=WorkOrderStatus.COMPLETED,
        started_at=now - timedelta(minutes=minutes_ago + cycle_minutes),
        completed_at=now - timedelta(minutes=minutes_ago),
    )
    db.add(wo)
    db.commit()
    db.refresh(wo)
    return wo


def _make_station(db: Session, name: str = "Test-Station") -> Station:
    s = Station(name=name, type=StationType.QA)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


class TestKPICalculation:
    def test_throughput_zero_on_empty_db(self, db_session: Session) -> None:
        summary = calculate_kpi_summary(db_session, window_hours=24)
        assert summary.throughput_per_hour == 0.0
        assert summary.completed_work_orders == 0

    def test_throughput_counts_completed_wos(self, db_session: Session) -> None:
        _make_completed_wo(db_session, minutes_ago=30)
        _make_completed_wo(db_session, minutes_ago=60)
        summary = calculate_kpi_summary(db_session, window_hours=24)
        assert summary.completed_work_orders == 2
        assert summary.throughput_per_hour > 0

    def test_avg_cycle_time_is_correct(self, db_session: Session) -> None:
        _make_completed_wo(db_session, minutes_ago=10, cycle_minutes=20.0)
        _make_completed_wo(db_session, minutes_ago=10, cycle_minutes=40.0)
        summary = calculate_kpi_summary(db_session, window_hours=24)
        assert abs(summary.avg_cycle_time_minutes - 30.0) < 1.0  # avg of 20 + 40

    def test_defect_rate_calculation(self, db_session: Session) -> None:
        station = _make_station(db_session)
        # 10 events: 2 defects → 20%
        for _ in range(2):
            db_session.add(Event(type=EventType.DEFECT_FOUND, station_id=station.id))
        for _ in range(8):
            db_session.add(Event(type=EventType.STEP_COMPLETED, station_id=station.id))
        db_session.commit()

        summary = calculate_kpi_summary(db_session, window_hours=24)
        assert summary.defect_rate_percent == 20.0

    def test_downtime_summed_from_payloads(self, db_session: Session) -> None:
        station = _make_station(db_session, "Down-Station")
        db_session.add(Event(
            type=EventType.MACHINE_DOWN,
            station_id=station.id,
            payload={"duration_minutes": 15},
        ))
        db_session.add(Event(
            type=EventType.MACHINE_DOWN,
            station_id=station.id,
            payload={"duration_minutes": 10},
        ))
        db_session.commit()

        summary = calculate_kpi_summary(db_session, window_hours=24)
        assert summary.total_downtime_minutes == 25.0

    def test_station_counts(self, db_session: Session) -> None:
        db_session.add(Station(name="S1", type=StationType.CUTTING, status=StationStatus.RUNNING))
        db_session.add(Station(name="S2", type=StationType.ASSEMBLY, status=StationStatus.RUNNING))
        db_session.add(Station(name="S3", type=StationType.QA, status=StationStatus.DOWN))
        db_session.commit()

        summary = calculate_kpi_summary(db_session, window_hours=24)
        assert summary.active_stations == 2
        assert summary.stations_down == 1


class TestBottleneckDetection:
    def test_no_bottlenecks_on_empty_db(self, db_session: Session) -> None:
        result = identify_bottlenecks(db_session, window_hours=24)
        assert result.bottlenecks == []

    def test_detects_slow_station(self, db_session: Session) -> None:
        station = _make_station(db_session, "Slow-Assembly")
        # Emit STEP_COMPLETED events with duration > threshold (30 min)
        for _ in range(5):
            db_session.add(Event(
                type=EventType.STEP_COMPLETED,
                station_id=station.id,
                payload={"duration_minutes": 45.0},
            ))
        db_session.commit()

        result = identify_bottlenecks(db_session, window_hours=24)
        assert len(result.bottlenecks) == 1
        bn = result.bottlenecks[0]
        assert bn.station_id == station.id
        assert bn.avg_cycle_time_minutes == 45.0
        assert "recommend" in bn.recommendation.lower()

    def test_fast_station_not_flagged(self, db_session: Session) -> None:
        station = _make_station(db_session, "Fast-QA")
        for _ in range(5):
            db_session.add(Event(
                type=EventType.STEP_COMPLETED,
                station_id=station.id,
                payload={"duration_minutes": 5.0},
            ))
        db_session.commit()

        result = identify_bottlenecks(db_session, window_hours=24)
        assert result.bottlenecks == []
