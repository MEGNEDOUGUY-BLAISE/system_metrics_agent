import pytest
from fastapi.testclient import TestClient

from app import api
from app.api import app

client = TestClient(app)

VALID_PAYLOAD = {
    "agent": "system-metrics-agent",
    "event_type": "system_metrics",
    "data": {"cpu": {"percent": 12.5}},
}


@pytest.fixture(autouse=True)
def clear_metrics():
    """Vide le stockage en mémoire avant et après chaque test."""
    api.received_metrics.clear()
    yield
    api.received_metrics.clear()


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ko"}  
# echec volontaire (demonstration)


def test_latest_metrics_empty():
    response = client.get("/metrics/latest")
    assert response.status_code == 404


def test_receive_metrics():
    response = client.post("/metrics", json=VALID_PAYLOAD)
    assert response.status_code == 201
    assert response.json()["total_received"] == 1


def test_latest_metrics_after_post():
    client.post("/metrics", json=VALID_PAYLOAD)
    response = client.get("/metrics/latest")
    assert response.status_code == 200
    body = response.json()
    assert body["agent"] == "system-metrics-agent"
    assert "received_at" in body


def test_get_all_metrics():
    client.post("/metrics", json=VALID_PAYLOAD)
    client.post("/metrics", json=VALID_PAYLOAD)
    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.json()["total"] == 2


def test_receive_metrics_invalid_payload():
    invalid_payload = {"agent": "", "event_type": "x", "data": {}}
    response = client.post("/metrics", json=invalid_payload)
    assert response.status_code == 422
