"""Pydantic request/response schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.models.models import (
    EventType,
    StationStatus,
    StationType,
    WorkOrderStatus,
)


# ── WorkOrder ─────────────────────────────────────────────────────────────────

class WorkOrderCreate(BaseModel):
    product_type: str = Field(..., min_length=1, max_length=100)
    priority: int = Field(default=1, ge=1, le=5)


class WorkOrderResponse(BaseModel):
    id: int
    product_type: str
    priority: int
    status: WorkOrderStatus
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None

    model_config = {"from_attributes": True}


# ── Station ───────────────────────────────────────────────────────────────────

class StationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    type: StationType


class StationUpdate(BaseModel):
    status: StationStatus


class StationResponse(BaseModel):
    id: int
    name: str
    type: StationType
    status: StationStatus
    last_heartbeat_at: datetime | None

    model_config = {"from_attributes": True}


# ── Event ─────────────────────────────────────────────────────────────────────

class EventCreate(BaseModel):
    type: EventType
    station_id: int | None = None
    work_order_id: int | None = None
    payload: dict[str, Any] | None = None


class EventResponse(BaseModel):
    id: int
    timestamp: datetime
    type: EventType
    station_id: int | None
    work_order_id: int | None
    payload: dict[str, Any] | None

    model_config = {"from_attributes": True}


# ── KPI ───────────────────────────────────────────────────────────────────────

class KPISummary(BaseModel):
    throughput_per_hour: float
    avg_cycle_time_minutes: float
    defect_rate_percent: float
    total_downtime_minutes: float
    completed_work_orders: int
    active_stations: int
    stations_down: int


class BottleneckInfo(BaseModel):
    station_id: int
    station_name: str
    station_type: str
    avg_cycle_time_minutes: float
    event_count: int
    recommendation: str


class BottleneckResponse(BaseModel):
    bottlenecks: list[BottleneckInfo]
    analysis_window_hours: int


# ── Automation Rules ──────────────────────────────────────────────────────────

class AutomationRuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    condition_json: dict[str, Any]
    action_json: dict[str, Any]
    enabled: bool = True

    @field_validator("condition_json")
    @classmethod
    def validate_condition(cls, v: dict) -> dict:
        if "type" not in v:
            raise ValueError("condition_json must have a 'type' field")
        return v

    @field_validator("action_json")
    @classmethod
    def validate_action(cls, v: dict) -> dict:
        if "type" not in v:
            raise ValueError("action_json must have a 'type' field")
        return v


class AutomationRuleResponse(BaseModel):
    id: int
    name: str
    description: str | None
    condition_json: dict[str, Any]
    action_json: dict[str, Any]
    enabled: bool
    last_triggered_at: datetime | None

    model_config = {"from_attributes": True}


# ── Health ────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    redis: str
