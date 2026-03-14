"""Test: Organizations CRUD"""
import uuid


def test_list_organizations(client):
    r = client.get("/api/organizations")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_organization_fields(client):
    r = client.get("/api/organizations")
    data = r.json()
    org = data[0]
    assert "id" in org
    assert "name" in org
    assert "org_type" in org
    assert "branch_id" in org
    assert "total_minutes" in org
    assert "total_records" in org


def test_get_organization(client):
    r = client.get("/api/organizations/ORG001")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == "ORG001"
    assert "สาธิต" in data["name"]
    assert data["total_minutes"] >= 0


def test_get_organization_not_found(client):
    r = client.get("/api/organizations/NOTEXIST")
    assert r.status_code == 404


def test_create_organization(client):
    uid = uuid.uuid4().hex[:6]
    body = {
        "id": f"T{uid}",
        "name": f"องค์กรทดสอบ {uid}",
        "org_type": "โรงเรียน",
        "branch_id": "B001",
        "province": "กรุงเทพมหานคร",
    }
    r = client.post("/api/organizations", json=body)
    assert r.status_code == 201
    data = r.json()
    assert data["id"] == body["id"]


def test_create_duplicate_organization(client):
    r = client.post("/api/organizations", json={
        "id": "ORG001",
        "name": "ซ้ำ",
        "branch_id": "B001",
    })
    assert r.status_code == 409


def test_update_organization(client):
    r = client.put("/api/organizations/ORG001", json={
        "id": "ORG001",
        "name": "โรงเรียนสาธิต มศว (อัพเดท)",
        "org_type": "โรงเรียน",
        "branch_id": "B001",
    })
    assert r.status_code == 200

    # Verify
    r2 = client.get("/api/organizations/ORG001")
    assert "อัพเดท" in r2.json()["name"]


def test_update_organization_not_found(client):
    r = client.put("/api/organizations/NOTEXIST", json={
        "id": "NOTEXIST",
        "name": "ไม่มี",
        "branch_id": "B001",
    })
    assert r.status_code == 404


def test_org_leaderboard(client):
    r = client.get("/api/leaderboard?type=org&limit=5")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "org_id" in data[0]
        assert "name" in data[0]
        assert "minutes" in data[0]


def test_org_markers(client):
    r = client.get("/api/markers")
    data = r.json()
    orgs = [m for m in data if m["type"] == "org"]
    assert len(orgs) > 0
    o = orgs[0]
    assert "id" in o
    assert "name" in o
    assert "org_type" in o
    assert isinstance(o["lat"], float)
    assert isinstance(o["lng"], float)
