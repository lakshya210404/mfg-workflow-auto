"""Celery task implementations."""

import logging

from app.tasks.celery_app import celery_app

logger = logging.getLogger("mfg.tasks")


@celery_app.task(name="app.tasks.tasks.run_automation_rules_task", bind=True, max_retries=3)
def run_automation_rules_task(self) -> dict:  # type: ignore[no-untyped-def]
    """Evaluate all enabled automation rules and execute triggered actions."""
    try:
        from app.core.database import SessionLocal
        from app.services.automation_service import evaluate_all_rules

        with SessionLocal() as db:
            results = evaluate_all_rules(db)

        triggered = [r for r in results if r["triggered"]]
        logger.info(
            "Automation run complete | total=%d triggered=%d",
            len(results),
            len(triggered),
        )
        return {"total": len(results), "triggered": len(triggered), "results": results}
    except Exception as exc:
        logger.exception("Error running automation rules: %s", exc)
        raise self.retry(exc=exc, countdown=30)


@celery_app.task(name="app.tasks.tasks.snapshot_kpis_task", bind=True, max_retries=3)
def snapshot_kpis_task(self) -> dict:  # type: ignore[no-untyped-def]
    """Persist a KPI snapshot to the database."""
    try:
        from app.core.database import SessionLocal
        from app.services.kpi_service import snapshot_kpis

        with SessionLocal() as db:
            record = snapshot_kpis(db)

        logger.info("KPI snapshot saved | id=%d", record.id)
        return {"kpi_history_id": record.id}
    except Exception as exc:
        logger.exception("Error saving KPI snapshot: %s", exc)
        raise self.retry(exc=exc, countdown=30)
