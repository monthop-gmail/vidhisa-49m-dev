"""Test: Organizations CRUD + Import/Export"""
import csv
import io
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
    # Use PLJ-B001 which is auto-created
    r = client.get("/api/organizations/PLJ-B001")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == "PLJ-B001"
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
    # PLJ-B001 already exists (auto-created)
    r = client.post("/api/organizations", json={
        "id": "PLJ-B001",
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


def test_export_csv(client):
    r = client.get("/api/organizations/export")
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    text = r.text.lstrip("\ufeff")
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    assert len(rows) > 0
    assert "id" in reader.fieldnames
    assert "name" in reader.fieldnames
    assert "branch_id" in reader.fieldnames


def test_import_csv_create(client):
    uid = uuid.uuid4().hex[:6]
    csv_content = f"id,name,org_type,branch_id,province,latitude,longitude,contact\nIMP{uid},องค์กรนำเข้า,โรงเรียน,B001,กรุงเทพมหานคร,13.75,100.5,\n"
    r = client.post("/api/organizations/import", files={"file": ("orgs.csv", csv_content, "text/csv")})
    assert r.status_code == 200
    data = r.json()
    assert data["created"] == 1
    assert data["updated"] == 0
    assert len(data["errors"]) == 0


def test_import_csv_update(client):
    csv_content = "id,name,org_type,branch_id,province,latitude,longitude,contact\nPLJ-B001,สถาบันพลังจิตตานุภาพ (ทดสอบ),สถาบันพลังจิตตานุภาพ,B001,,,,\n"
    r = client.post("/api/organizations/import", files={"file": ("orgs.csv", csv_content, "text/csv")})
    assert r.status_code == 200
    data = r.json()
    assert data["updated"] == 1


def test_import_csv_invalid_branch(client):
    csv_content = "id,name,org_type,branch_id,province,latitude,longitude,contact\nBAD001,องค์กรผิด,โรงเรียน,INVALID,,,,\n"
    r = client.post("/api/organizations/import", files={"file": ("orgs.csv", csv_content, "text/csv")})
    assert r.status_code == 200
    data = r.json()
    assert data["created"] == 0
    assert len(data["errors"]) == 1


def test_import_csv_invalid_file(client):
    r = client.post("/api/organizations/import", files={"file": ("orgs.txt", "hello", "text/plain")})
    assert r.status_code == 400


def test_import_csv_missing_header(client):
    csv_content = "id\nX001\n"
    r = client.post("/api/organizations/import", files={"file": ("orgs.csv", csv_content, "text/csv")})
    assert r.status_code == 400


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
