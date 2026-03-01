"""SQLAlchemy ORM models for the manufacturing workflow system."""

import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# ── Enums ─────────────────────────────────────────────────────────────────────

class WorkOrderStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    ON_HOLD = "ON_HOLD"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class StationStatus(str, enum.Enum):
    RUNNING = "RUNNING"
    IDLE = "IDLE"
    DOWN = "DOWN"
    HOLD = "HOLD"


class StationType(str, enum.Enum):
    CUTTING = "CUTTING"
    ASSEMBLY = "ASSEMBLY"
    QA = "QA"
    PACKAGING = "PACKAGING"


class EventType(str, enum.Enum):
    WORK_ORDER_STARTED = "WORK_ORDER_STARTED"
    WORK_ORDER_COMPLETED = "WORK_ORDER_COMPLETED"
    STEP_COMPLETED = "STEP_COMPLETED"
    DEFECT_FOUND = "DEFECT_FOUND"
    MACHINE_DOWN = "MACHINE_DOWN"
    MACHINE_UP = "MACHINE_UP"
    MACHINE_IDLE = "MACHINE_IDLE"
    QA_HOLD = "QA_HOLD"


# ── Models ────────────────────────────────────────────────────────────────────

class WorkOrder(Base):
    """Represents a manufacturing work order."""

    __tablename__ = "work_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_type: Mapped[str] = mapped_column(String(100), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=1)  # 1 = low, 5 = critical
    status: Mapped[WorkOrderStatus] = mapped_column(
        Enum(WorkOrderStatus), default=WorkOrderStatus.PENDING, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    events: Mapped[list["Event"]] = relationship("Event", back_populates="work_order")

    __table_args__ = (
        Index("ix_work_orders_status_created", "status", "created_at"),
    )


class Station(Base):
    """Represents a manufacturing station on the factory floor."""

    __tablename__ = "stations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    type: Mapped[StationType] = mapped_column(Enum(StationType), nullable=False, index=True)
    status: Mapped[StationStatus] = mapped_column(
        Enum(StationStatus), default=StationStatus.IDLE, index=True
    )
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    events: Mapped[list["Event"]] = relationship("Event", back_populates="station")


class Event(Base):
    """Immutable event log entry from the factory floor."""

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    type: Mapped[EventType] = mapped_column(Enum(EventType), nullable=False, index=True)
    station_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("stations.id"), nullable=True, index=True
    )
    work_order_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("work_orders.id"), nullable=True, index=True
    )
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    station: Mapped["Station | None"] = relationship("Station", back_populates="events")
    work_order: Mapped["WorkOrder | None"] = relationship("WorkOrder", back_populates="events")

    __table_args__ = (
        Index("ix_events_type_timestamp", "type", "timestamp"),
        Index("ix_events_station_timestamp", "station_id", "timestamp"),
    )


class KPIHistory(Base):
    """Periodic snapshot of key performance indicators."""

    __tablename__ = "kpi_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    throughput: Mapped[float] = mapped_column(Float, default=0.0)          # completed WOs / hour
    defect_rate: Mapped[float] = mapped_column(Float, default=0.0)          # 0–1
    downtime_minutes: Mapped[float] = mapped_column(Float, default=0.0)
    avg_cycle_time: Mapped[float] = mapped_column(Float, default=0.0)       # minutes


class AutomationRule(Base):
    """A configurable rule that triggers an automated action."""

    __tablename__ = "automation_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    condition_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    action_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_triggered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
