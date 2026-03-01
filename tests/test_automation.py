"""Tests for automation rules API and engine."""

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.models import (
    AutomationRule,
    Event,
    EventType,
    Station,
    StationStatus,
    StationType,
    WorkOrder,
    WorkOrderStatus,
)
from app.services.automation_service import evaluate_all_rules

DEFECT_RULE = {
    "name": "Test Defect Rule",
    "condition_json": {"type": "defect_rate_spike", "threshold": 0.10, "sample_size": 10},
    "action_json": {"type": "hold_qa_station"},
}

DOWNTIME_RULE = {
    "name": "Test Downtime Rule",
    "condition_json": {"type": "station_downtime", "threshold_minutes": 1},
    "action_json": {"type": "pause_work_orders"},
}


class TestAutomationRulesAPI:
    def test_create_rule(self, client: TestClient) -> None:
        resp = client.post("/automation/rules", json=DEFECT_RULE)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == DEFECT_RULE["name"]
        assert data["enabled"] is True

    def test_create_duplicate_rule(self, client: TestClient) -> None:
        client.post("/automation/rules", json=DEFECT_RULE)
        resp = client.post("/automation/rules", json=DEFECT_RULE)
        assert resp.status_code == 409

    def test_create_rule_missing_condition_type(self, client: TestClient) -> None:
        bad_rule = {
            "name": "Bad",
            "condition_json": {"threshold": 0.1},  # missing 'type'
            "action_json": {"type": "hold_qa_station"},
        }
        resp = client.post("/automation/rules", json=bad_rule)
        assert resp.status_code == 422

    def test_list_rules(self, client: TestClient) -> None:
        client.post("/automation/rules", json=DEFECT_RULE)
        resp = client.get("/automation/rules")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_delete_rule(self, client: TestClient) -> None:
        create_resp = client.post("/automation/rules", json=DEFECT_RULE)
        rule_id = create_resp.json()["id"]
        del_resp = client.delete(f"/automation/rules/{rule_id}")
        assert del_resp.status_code == 204
        assert len(client.get("/automation/rules").json()) == 0

    def test_delete_nonexistent_rule(self, client: TestClient) -> None:
        resp = client.delete("/automation/rules/99999")
        assert resp.status_code == 404


class TestAutomationEngine:
    def _add_rule(self, db: Session, rule_data: dict) -> AutomationRule:
        rule = AutomationRule(**rule_data)
        db.add(rule)
        db.commit()
        db.refresh(rule)
        return rule

    def test_defect_rule_triggers_qa_hold(self, db_session: Session) -> None:
        """High defect rate should set QA stations to HOLD."""
        # Create a QA station
        qa = Station(name="QA-Test", type=StationType.QA, status=StationStatus.RUNNING)
        db_session.add(qa)
        db_session.commit()

        # Create defect events exceeding threshold (>10% of 10 = at least 2)
        for _ in range(4):  # 40% defect rate
            db_session.add(Event(type=EventType.DEFECT_FOUND))
        for _ in range(6):
            db_session.add(Event(type=EventType.STEP_COMPLETED))
        db_session.commit()

        self._add_rule(db_session, {
            "name": "Defect Spike Test",
            "condition_json": {"type": "defect_rate_spike", "threshold": 0.10, "sample_size": 10},
            "action_json": {"type": "hold_qa_station"},
        })

        results = evaluate_all_rules(db_session)
        assert any(r["triggered"] for r in results)

        db_session.refresh(qa)
        assert qa.status == StationStatus.HOLD

    def test_downtime_rule_pauses_work_orders(self, db_session: Session) -> None:
        """Station down too long should pause IN_PROGRESS work orders."""
        # Create a station that's been DOWN for a while
        old_time = datetime.now(tz=timezone.utc) - timedelta(minutes=20)
        station = Station(
            name="Down-Station",
            type=StationType.ASSEMBLY,
            status=StationStatus.DOWN,
            last_heartbeat_at=old_time,
        )
        db_session.add(station)

        # Create an IN_PROGRESS work order
        wo = WorkOrder(product_type="Test", status=WorkOrderStatus.IN_PROGRESS)
        db_session.add(wo)
        db_session.commit()

        self._add_rule(db_session, {
            "name": "Downtime Pause Test",
            "condition_json": {"type": "station_downtime", "threshold_minutes": 5},
            "action_json": {"type": "pause_work_orders"},
        })

        results = evaluate_all_rules(db_session)
        assert any(r["triggered"] for r in results)

        db_session.refresh(wo)
        assert wo.status == WorkOrderStatus.ON_HOLD

    def test_disabled_rule_does_not_trigger(self, db_session: Session) -> None:
        """Disabled rules must never trigger."""
        # Create lots of defects
        for _ in range(10):
            db_session.add(Event(type=EventType.DEFECT_FOUND))
        db_session.commit()

        rule = AutomationRule(
            name="Disabled Rule",
            condition_json={"type": "defect_rate_spike", "threshold": 0.0, "sample_size": 10},
            action_json={"type": "hold_qa_station"},
            enabled=False,  # disabled!
        )
        db_session.add(rule)
        db_session.commit()

        results = evaluate_all_rules(db_session)
        assert results == []  # no enabled rules
