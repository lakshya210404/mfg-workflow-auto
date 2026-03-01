#!/usr/bin/env python3
"""
scripts/seed_db.py

Seed the database with default stations and automation rules.
Run inside Docker: docker compose exec api python scripts/seed_db.py
"""

import logging
import sys

sys.path.insert(0, ".")

from app.core.database import SessionLocal
from app.core.logging import setup_logging
from app.models.models import AutomationRule, Station, StationType

setup_logging()
logger = logging.getLogger("mfg.seed")

DEFAULT_STATIONS = [
    {"name": "Cutting-01", "type": StationType.CUTTING},
    {"name": "Cutting-02", "type": StationType.CUTTING},
    {"name": "Assembly-01", "type": StationType.ASSEMBLY},
    {"name": "Assembly-02", "type": StationType.ASSEMBLY},
    {"name": "QA-01", "type": StationType.QA},
    {"name": "Packaging-01", "type": StationType.PACKAGING},
]

DEFAULT_RULES = [
    {
        "name": "High Defect Rate → QA Hold",
        "description": "If defect rate in last 50 events exceeds 15%, hold all QA stations",
        "condition_json": {"type": "defect_rate_spike", "threshold": 0.15, "sample_size": 50},
        "action_json": {"type": "hold_qa_station"},
    },
    {
        "name": "Station Down Too Long → Pause Work Orders",
        "description": "If any station is DOWN >10 minutes, pause all in-progress work orders",
        "condition_json": {"type": "station_downtime", "threshold_minutes": 10},
        "action_json": {"type": "pause_work_orders"},
    },
    {
        "name": "Slow Cycle Time → Flag Bottleneck",
        "description": "If station avg cycle time >30 min, flag as bottleneck",
        "condition_json": {
            "type": "high_cycle_time",
            "threshold_minutes": 30.0,
            "window_minutes": 60,
        },
        "action_json": {"type": "flag_bottleneck"},
    },
]


def seed() -> None:
    """Insert default stations and automation rules if they don't already exist."""
    db = SessionLocal()
    try:
        # Stations
        for s_data in DEFAULT_STATIONS:
            existing = db.query(Station).filter_by(name=s_data["name"]).first()
            if not existing:
                db.add(Station(**s_data))
                logger.info("Created station: %s", s_data["name"])
            else:
                logger.debug("Station already exists: %s", s_data["name"])

        # Automation rules
        for r_data in DEFAULT_RULES:
            existing = db.query(AutomationRule).filter_by(name=r_data["name"]).first()
            if not existing:
                db.add(AutomationRule(**r_data))
                logger.info("Created rule: %s", r_data["name"])
            else:
                logger.debug("Rule already exists: %s", r_data["name"])

        db.commit()
        logger.info("✅ Seed complete")
    except Exception as exc:
        db.rollback()
        logger.exception("Seed failed: %s", exc)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    seed()
