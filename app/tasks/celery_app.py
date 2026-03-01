"""Celery application and background tasks."""

import logging

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

logger = logging.getLogger("mfg.tasks")

celery_app = Celery(
    "mfg_worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        # Run automation rules every 2 minutes
        "run-automation-rules": {
            "task": "app.tasks.tasks.run_automation_rules_task",
            "schedule": 120.0,
        },
        # Snapshot KPIs every 5 minutes
        "snapshot-kpis": {
            "task": "app.tasks.tasks.snapshot_kpis_task",
            "schedule": 300.0,
        },
    },
)
