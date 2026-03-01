"""Tests for the /stations endpoints."""

from fastapi.testclient import TestClient


class TestCreateStation:
    def test_create_success(self, client: TestClient) -> None:
        resp = client.post("/stations", json={"name": "Cutting-01", "type": "CUTTING"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Cutting-01"
        assert data["type"] == "CUTTING"
        assert data["status"] == "IDLE"

    def test_create_duplicate_name(self, client: TestClient) -> None:
        client.post("/stations", json={"name": "Cutting-01", "type": "CUTTING"})
        resp = client.post("/stations", json={"name": "Cutting-01", "type": "ASSEMBLY"})
        assert resp.status_code == 409

    def test_create_invalid_type(self, client: TestClient) -> None:
        resp = client.post("/stations", json={"name": "Badstation", "type": "NUCLEAR"})
        assert resp.status_code == 422


class TestListStations:
    def test_list_empty(self, client: TestClient) -> None:
        resp = client.get("/stations")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_returns_created(self, client: TestClient) -> None:
        client.post("/stations", json={"name": "QA-01", "type": "QA"})
        resp = client.get("/stations")
        assert len(resp.json()) == 1


class TestUpdateStationStatus:
    def test_update_status(self, client: TestClient, sample_station: dict) -> None:
        sid = sample_station["id"]
        resp = client.patch(f"/stations/{sid}", json={"status": "RUNNING"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "RUNNING"

    def test_update_nonexistent(self, client: TestClient) -> None:
        resp = client.patch("/stations/99999", json={"status": "RUNNING"})
        assert resp.status_code == 404
