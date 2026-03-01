"""Tests for the /work-orders endpoints."""

import pytest
from fastapi.testclient import TestClient


class TestCreateWorkOrder:
    def test_create_success(self, client: TestClient) -> None:
        resp = client.post("/work-orders", json={"product_type": "Widget-A", "priority": 3})
        assert resp.status_code == 201
        data = resp.json()
        assert data["product_type"] == "Widget-A"
        assert data["priority"] == 3
        assert data["status"] == "PENDING"
        assert data["id"] is not None

    def test_create_default_priority(self, client: TestClient) -> None:
        resp = client.post("/work-orders", json={"product_type": "Gear-XL"})
        assert resp.status_code == 201
        assert resp.json()["priority"] == 1

    def test_create_invalid_priority_too_high(self, client: TestClient) -> None:
        resp = client.post("/work-orders", json={"product_type": "Widget-A", "priority": 99})
        assert resp.status_code == 422

    def test_create_invalid_priority_zero(self, client: TestClient) -> None:
        resp = client.post("/work-orders", json={"product_type": "Widget-A", "priority": 0})
        assert resp.status_code == 422

    def test_create_missing_product_type(self, client: TestClient) -> None:
        resp = client.post("/work-orders", json={"priority": 1})
        assert resp.status_code == 422


class TestListWorkOrders:
    def test_list_empty(self, client: TestClient) -> None:
        resp = client.get("/work-orders")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_returns_all(self, client: TestClient) -> None:
        client.post("/work-orders", json={"product_type": "A"})
        client.post("/work-orders", json={"product_type": "B"})
        resp = client.get("/work-orders")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_filter_by_status(self, client: TestClient) -> None:
        client.post("/work-orders", json={"product_type": "Widget-A"})
        resp = client.get("/work-orders", params={"status": "PENDING"})
        assert resp.status_code == 200
        for wo in resp.json():
            assert wo["status"] == "PENDING"

    def test_filter_by_invalid_status(self, client: TestClient) -> None:
        resp = client.get("/work-orders", params={"status": "BOGUS"})
        assert resp.status_code == 422


class TestGetWorkOrder:
    def test_get_existing(self, client: TestClient, sample_work_order: dict) -> None:
        wo_id = sample_work_order["id"]
        resp = client.get(f"/work-orders/{wo_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == wo_id

    def test_get_nonexistent(self, client: TestClient) -> None:
        resp = client.get("/work-orders/99999")
        assert resp.status_code == 404
