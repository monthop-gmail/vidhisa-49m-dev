"""Test: Health + Swagger"""


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_swagger_ui(client):
    r = client.get("/docs")
    assert r.status_code == 200


def test_openapi_json(client):
    r = client.get("/openapi.json")
    assert r.status_code == 200
    data = r.json()
    assert data["info"]["title"] == "Vithisa 49M API"
