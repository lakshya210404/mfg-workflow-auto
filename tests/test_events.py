"""Tests for the /events endpoints and state side effects."""

from fastapi.testclient import TestClient


class TestIngestEvent:
    def test_work_order_started_updates_status(
        self, client: TestClient, sample_work_order: dict
    ) -> None:
        wo_id = sample_work_order["id"]
        resp = client.post("/events", json={"type": "WORK_ORDER_STARTED", "work_order_id": wo_id})
        assert resp.status_code == 201

        wo = client.get(f"/work-orders/{wo_id}").json()
        assert wo["status"] == "IN_PROGRESS"
        assert wo["started_at"] is not None

    def test_work_order_completed_updates_status(
        self, client: TestClient, sample_work_order: dict
    ) -> None:
        wo_id = sample_work_order["id"]
        client.post("/events", json={"type": "WORK_ORDER_STARTED", "work_order_id": wo_id})
        client.post("/events", json={"type": "WORK_ORDER_COMPLETED", "work_order_id": wo_id})

        wo = client.get(f"/work-orders/{wo_id}").json()
        assert wo["status"] == "COMPLETED"
        assert wo["completed_at"] is not None

    def test_machine_down_updates_station_status(
        self, client: TestClient, sample_station: dict
    ) -> None:
        sid = sample_station["id"]
        resp = client.post("/events", json={
            "type": "MACHINE_DOWN",
            "station_id": sid,
            "payload": {"reason": "jam", "duration_minutes": 5},
        })
        assert resp.status_code == 201

        station = client.get(f"/stations/{sid}").json()
        assert station["status"] == "DOWN"

    def test_machine_up_updates_station_status(
        self, client: TestClient, sample_station: dict
    ) -> None:
        sid = sample_station["id"]
        client.post("/events", json={"type": "MACHINE_DOWN", "station_id": sid})
        client.post("/events", json={"type": "MACHINE_UP", "station_id": sid})

        station = client.get(f"/stations/{sid}").json()
        assert station["status"] == "RUNNING"

    def test_invalid_station_id_returns_404(self, client: TestClient) -> None:
        resp = client.post("/events", json={"type": "MACHINE_DOWN", "station_id": 99999})
        assert resp.status_code == 404

    def test_invalid_work_order_id_returns_404(self, client: TestClient) -> None:
        resp = client.post("/events", json={"type": "WORK_ORDER_STARTED", "work_order_id": 99999})
        assert resp.status_code == 404

    def test_defect_event_with_payload(
        self, client: TestClient, sample_station: dict, sample_work_order: dict
    ) -> None:
        resp = client.post("/events", json={
            "type": "DEFECT_FOUND",
            "station_id": sample_station["id"],
            "work_order_id": sample_work_order["id"],
            "payload": {"severity": "major"},
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["payload"]["severity"] == "major"


class TestListEvents:
    def test_list_empty(self, client: TestClient) -> None:
        resp = client.get("/events")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_filter_by_type(self, client: TestClient, sample_station: dict) -> None:
        sid = sample_station["id"]
        client.post("/events", json={"type": "MACHINE_DOWN", "station_id": sid})
        client.post("/events", json={"type": "MACHINE_UP", "station_id": sid})

        resp = client.get("/events", params={"event_type": "MACHINE_DOWN"})
        assert resp.status_code == 200
        for ev in resp.json():
            assert ev["type"] == "MACHINE_DOWN"
