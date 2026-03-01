"""Tests for the /health endpoint."""

from fastapi.testclient import TestClient


def test_health_check(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "version" in data
    assert "database" in data
    assert "redis" in data
