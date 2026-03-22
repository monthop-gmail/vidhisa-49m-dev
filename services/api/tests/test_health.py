"""Test: Health + Swagger"""

from datetime import datetime


def test_health(client):
    r = client.get("/api/healthz")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "timestamp" in data
    assert "version" in data
    assert data["version"] == "0.1.0"
    datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))


def test_swagger_ui(client):
    r = client.get("/docs")
    assert r.status_code == 200


def test_openapi_json(client):
    r = client.get("/openapi.json")
    assert r.status_code == 200
    data = r.json()
    assert data["info"]["title"] == "Vidhisa 49M API"
