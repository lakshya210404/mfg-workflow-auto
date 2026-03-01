"""Pytest configuration and shared fixtures."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.main import app

# Use SQLite in-memory for fast, isolated tests
TEST_DB_URL = "sqlite:///./test.db"

engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh DB schema for each test function."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """FastAPI test client with DB override."""
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_station(client):
    """Create and return a sample CUTTING station."""
    resp = client.post("/stations", json={"name": "Test-Cutting-01", "type": "CUTTING"})
    assert resp.status_code == 201
    return resp.json()


@pytest.fixture
def sample_work_order(client):
    """Create and return a sample work order."""
    resp = client.post("/work-orders", json={"product_type": "Widget-Test", "priority": 2})
    assert resp.status_code == 201
    return resp.json()
