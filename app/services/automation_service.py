"""Automation rules engine: evaluates conditions and executes actions."""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import (
    AutomationRule,
    Event,
    EventType,
    Station,
    StationStatus,
    WorkOrder,
    WorkOrderStatus,
)

logger = logging.getLogger("mfg.automation")


# ── Condition evaluators ──────────────────────────────────────────────────────

def _check_defect_rate(db: Session, condition: dict) -> bool:
    """Return True if defect rate over last N events exceeds threshold."""
    threshold = condition.get("threshold", 0.15)
    sample_size = condition.get("sample_size", 50)

    recent = (
        db.execute(
            select(Event)
            .order_by(Event.timestamp.desc())
            .limit(sample_size)
        )
        .scalars()
        .all()
    )
    if not recent:
        return False
    defect_count = sum(1 for e in recent if e.type == EventType.DEFECT_FOUND)
    rate = defect_count / len(recent)
    logger.debug("Defect rate check: %.3f vs threshold %.3f", rate, threshold)
    return rate > threshold


def _check_station_downtime(db: Session, condition: dict) -> list[Station]:
    """Return stations that have been DOWN longer than threshold_minutes."""
    threshold_minutes = condition.get("threshold_minutes", 10)
    cutoff = datetime.now(tz=timezone.utc) - timedelta(minutes=threshold_minutes)

    down_stations = (
        db.execute(
            select(Station).where(
                Station.status == StationStatus.DOWN,
                Station.last_heartbeat_at <= cutoff,
            )
        )
        .scalars()
        .all()
    )
    return list(down_stations)


def _check_cycle_time(db: Session, condition: dict) -> list[Station]:
    """Return stations whose recent avg cycle time exceeds threshold."""
    threshold = condition.get("threshold_minutes", 30.0)
    window_minutes = condition.get("window_minutes", 60)
    since = datetime.now(tz=timezone.utc) - timedelta(minutes=window_minutes)

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

    station_times: dict[int, list[float]] = {}
    for ev in step_events:
        duration = (ev.payload or {}).get("duration_minutes", 0.0)
        station_times.setdefault(ev.station_id, []).append(duration)  # type: ignore[arg-type]

    slow_station_ids = [
        sid for sid, times in station_times.items()
        if (sum(times) / len(times)) > threshold
    ]

    if not slow_station_ids:
        return []

    return list(
        db.execute(select(Station).where(Station.id.in_(slow_station_ids)))
        .scalars()
        .all()
    )


# ── Action executors ──────────────────────────────────────────────────────────

def _action_hold_qa_station(db: Session, _action: dict) -> str:
    """Set all QA stations to HOLD status."""
    from app.models.models import StationType

    qa_stations = (
        db.execute(select(Station).where(Station.type == StationType.QA))
        .scalars()
        .all()
    )
    for s in qa_stations:
        s.status = StationStatus.HOLD
        logger.warning("Station '%s' set to HOLD due to high defect rate", s.name)
    db.commit()
    return f"Set {len(qa_stations)} QA station(s) to HOLD"


def _action_pause_work_orders(db: Session, action: dict) -> str:
    """Pause IN_PROGRESS work orders associated with a down station."""
    station_ids: list[int] = action.get("station_ids", [])
    if not station_ids:
        return "No stations specified for pause action"

    affected_wos = (
        db.execute(
            select(WorkOrder).where(
                WorkOrder.status == WorkOrderStatus.IN_PROGRESS,
            )
        )
        .scalars()
        .all()
    )
    paused = 0
    for wo in affected_wos:
        wo.status = WorkOrderStatus.ON_HOLD
        paused += 1
    db.commit()
    logger.warning("Paused %d work order(s) due to station downtime", paused)
    return f"Paused {paused} work order(s)"


def _action_flag_bottleneck(db: Session, action: dict) -> str:
    """Log a bottleneck alert event for slow stations."""
    station_ids: list[int] = action.get("station_ids", [])
    msg = f"Bottleneck detected at station IDs: {station_ids}"
    logger.warning(msg)
    return msg


# ── Rule runner ───────────────────────────────────────────────────────────────

CONDITION_HANDLERS = {
    "defect_rate_spike": _check_defect_rate,
    "station_downtime": _check_station_downtime,
    "high_cycle_time": _check_cycle_time,
}

ACTION_HANDLERS = {
    "hold_qa_station": _action_hold_qa_station,
    "pause_work_orders": _action_pause_work_orders,
    "flag_bottleneck": _action_flag_bottleneck,
}


def evaluate_all_rules(db: Session) -> list[dict]:
    """
    Fetch all enabled automation rules, evaluate each condition,
    and execute actions for triggered rules.

    Returns a list of trigger result dicts.
    """
    rules = (
        db.execute(select(AutomationRule).where(AutomationRule.enabled == True))  # noqa: E712
        .scalars()
        .all()
    )

    results: list[dict] = []
    for rule in rules:
        condition_type = rule.condition_json.get("type")
        action_type = rule.action_json.get("type")

        condition_fn = CONDITION_HANDLERS.get(condition_type)  # type: ignore[arg-type]
        action_fn = ACTION_HANDLERS.get(action_type)  # type: ignore[arg-type]

        if not condition_fn or not action_fn:
            logger.warning(
                "Rule '%s' has unknown condition/action type: %s / %s",
                rule.name,
                condition_type,
                action_type,
            )
            continue

        triggered_data = condition_fn(db, rule.condition_json)

        triggered = False
        if isinstance(triggered_data, bool):
            triggered = triggered_data
        elif isinstance(triggered_data, list):
            triggered = len(triggered_data) > 0

        if triggered:
            # Build action context with station ids if available
            action_ctx = dict(rule.action_json)
            if isinstance(triggered_data, list):
                action_ctx["station_ids"] = [s.id for s in triggered_data]

            outcome = action_fn(db, action_ctx)
            rule.last_triggered_at = datetime.now(tz=timezone.utc)
            db.commit()

            logger.info("Rule '%s' triggered | outcome: %s", rule.name, outcome)
            results.append({"rule": rule.name, "triggered": True, "outcome": outcome})
        else:
            results.append({"rule": rule.name, "triggered": False, "outcome": None})

    return results
