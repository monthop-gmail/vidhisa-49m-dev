"""Test: Branches CRUD + Import/Export"""
import csv
import io
import uuid


def test_list_branches(client):
    r = client.get("/api/branches")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_branch_fields(client):
    r = client.get("/api/branches")
    data = r.json()
    b = data[0]
    for field in ["id", "name", "province", "province_code", "total_minutes", "total_records"]:
        assert field in b


def test_get_branch(client):
    r = client.get("/api/branches/B001")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == "B001"
    assert data["total_minutes"] >= 0


def test_get_branch_not_found(client):
    r = client.get("/api/branches/NOTEXIST")
    assert r.status_code == 404


def test_create_branch(client):
    uid = uuid.uuid4().hex[:4]
    body = {
        "id": f"BT{uid}",
        "name": f"สาขาทดสอบ {uid}",
        "province": "กรุงเทพมหานคร",
        "province_code": "TH-10",
    }
    r = client.post("/api/branches", json=body)
    assert r.status_code == 201
    assert r.json()["id"] == body["id"]


def test_create_duplicate_branch(client):
    r = client.post("/api/branches", json={
        "id": "B001",
        "name": "ซ้ำ",
        "province": "กรุงเทพมหานคร",
        "province_code": "TH-10",
    })
    assert r.status_code == 409


def test_update_branch(client):
    r = client.put("/api/branches/B001", json={
        "name": "สาขา 1 กรุงเทพฯ (อัพเดท)",
        "admin_name": "ทดสอบ",
    })
    assert r.status_code == 200
    r2 = client.get("/api/branches/B001")
    assert "อัพเดท" in r2.json()["name"]


def test_update_branch_not_found(client):
    r = client.put("/api/branches/NOTEXIST", json={"name": "ไม่มี"})
    assert r.status_code == 404


def test_export_csv(client):
    r = client.get("/api/branches/export")
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    text = r.text.lstrip("\ufeff")
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    assert len(rows) > 0
    assert "id" in reader.fieldnames
    assert "name" in reader.fieldnames
    assert "province_code" in reader.fieldnames


def test_import_csv_create(client):
    uid = uuid.uuid4().hex[:4]
    csv_content = f"id,name,group_id,province,province_code,latitude,longitude,admin_name,contact\nBI{uid},สาขานำเข้า {uid},,กรุงเทพมหานคร,TH-10,13.75,100.5,,\n"
    r = client.post("/api/branches/import", files={"file": ("branches.csv", csv_content, "text/csv")})
    assert r.status_code == 200
    data = r.json()
    assert data["created"] == 1
    assert data["updated"] == 0


def test_import_csv_update(client):
    csv_content = "id,name,group_id,province,province_code,latitude,longitude,admin_name,contact\nB001,สาขา 1 กรุงเทพฯ (import update),,กรุงเทพมหานคร,TH-10,13.75,100.51,,\n"
    r = client.post("/api/branches/import", files={"file": ("branches.csv", csv_content, "text/csv")})
    assert r.status_code == 200
    assert r.json()["updated"] == 1


def test_import_csv_invalid_group(client):
    csv_content = "id,name,group_id,province,province_code,latitude,longitude,admin_name,contact\nBAD01,สาขาผิด,INVALID,กรุงเทพมหานคร,TH-10,,,,\n"
    r = client.post("/api/branches/import", files={"file": ("branches.csv", csv_content, "text/csv")})
    assert r.status_code == 200
    assert len(r.json()["errors"]) == 1


def test_import_csv_invalid_file(client):
    r = client.post("/api/branches/import", files={"file": ("data.txt", "hello", "text/plain")})
    assert r.status_code == 400


def test_import_csv_missing_header(client):
    csv_content = "id,name\nX001,ทดสอบ\n"
    r = client.post("/api/branches/import", files={"file": ("branches.csv", csv_content, "text/csv")})
    assert r.status_code == 400
