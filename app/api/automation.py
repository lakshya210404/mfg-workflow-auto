"""Automation Rules API endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import AutomationRule
from app.schemas.schemas import AutomationRuleCreate, AutomationRuleResponse
from app.tasks.tasks import run_automation_rules_task

logger = logging.getLogger("mfg.api.automation")
router = APIRouter(prefix="/automation", tags=["Automation"])


@router.post("/rules", response_model=AutomationRuleResponse, status_code=status.HTTP_201_CREATED)
def create_rule(payload: AutomationRuleCreate, db: Session = Depends(get_db)) -> AutomationRule:
    """Create an automation rule."""
    existing = db.execute(
        select(AutomationRule).where(AutomationRule.name == payload.name)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Rule with name '{payload.name}' already exists",
        )
    rule = AutomationRule(
        name=payload.name,
        description=payload.description,
        condition_json=payload.condition_json,
        action_json=payload.action_json,
        enabled=payload.enabled,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    logger.info("Created automation rule id=%d name=%s", rule.id, rule.name)
    return rule


@router.get("/rules", response_model=list[AutomationRuleResponse])
def list_rules(db: Session = Depends(get_db)) -> list[AutomationRule]:
    """List all automation rules."""
    return list(db.execute(select(AutomationRule)).scalars().all())


@router.post("/rules/run", status_code=status.HTTP_202_ACCEPTED)
def trigger_rules_evaluation() -> dict:
    """Manually trigger an async automation rules evaluation."""
    task = run_automation_rules_task.delay()
    logger.info("Manual automation run triggered | task_id=%s", task.id)
    return {"task_id": task.id, "status": "queued"}


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(rule_id: int, db: Session = Depends(get_db)) -> None:
    """Delete an automation rule."""
    rule = db.get(AutomationRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")
    db.delete(rule)
    db.commit()
    logger.info("Deleted automation rule id=%d", rule_id)
