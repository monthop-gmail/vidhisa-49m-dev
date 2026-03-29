"""Test: Records list, export, import, upsert, 9-field sessions"""
import io
import uuid


def _uid():
    return f"pytest-{uuid.uuid4().hex[:8]}"


def _create_org(client, branch_id="B005"):
    oid = f"OT{uuid.uuid4().hex[:6]}"
    r = client.post("/api/organizations", json={"id": oid, "name": f"Test-{oid}", "branch_id": branch_id})
    assert r.status_code == 201
    client.patch(f"/api/organizations/{oid}/approve")
    return oid


def _create_participant(client, branch_id="B005"):
    r = client.post("/api/participants", json={
        "branch_id": branch_id, "first_name": _uid(), "last_name": "Test", "privacy_accepted": True,
    })
    assert r.status_code == 201
    pid = r.json()["id"]
    client.patch(f"/api/participants/{pid}/approve")
    return pid


class TestRecordsList:
    def test_list_all(self, client):
        r = client.get("/api/records")
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        assert len(r.json()) > 0

    def test_list_filter_type_bulk(self, client):
        r = client.get("/api/records?record_type=bulk")
        assert r.status_code == 200
        for rec in r.json():
            assert rec["type"] == "bulk"

    def test_list_filter_type_individual(self, client):
        r = client.get("/api/records?record_type=individual")
        assert r.status_code == 200
        for rec in r.json():
            assert rec["type"] == "individual"

    def test_list_filter_branch(self, client):
        r = client.get("/api/records?branch_id=B001")
        assert r.status_code == 200

    def test_list_filter_status(self, client):
        r = client.get("/api/records?status=approved")
        assert r.status_code == 200
        for rec in r.json():
            assert rec["status"] == "approved"


class TestRecordsExport:
    def test_export_all(self, client):
        r = client.get("/api/records/export")
        assert r.status_code == 200
        assert "text/csv" in r.headers["content-type"]

    def test_export_bulk(self, client):
        r = client.get("/api/records/export?record_type=bulk")
        assert r.status_code == 200
        assert "morning_male" in r.text

    def test_export_individual(self, client):
        r = client.get("/api/records/export?record_type=individual")
        assert r.status_code == 200


class TestRecordsImport:
    def test_import_csv(self, client):
        csv_data = "type,branch_id,name,minutes,date,morning_male\nbulk,B001,ImportTest,500,2026-05-01,100"
        r = client.post("/api/records/import", files={
            "file": ("test.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")
        })
        assert r.status_code == 200
        assert r.json()["created"] == 1

    def test_import_csv_missing_header(self, client):
        csv_data = "name,minutes\ntest,5"
        r = client.post("/api/records/import", files={
            "file": ("test.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")
        })
        assert r.status_code == 400

    def test_import_csv_invalid_branch(self, client):
        csv_data = "type,branch_id,name,minutes,date\nbulk,XXX,test,5,2026-05-01"
        r = client.post("/api/records/import", files={
            "file": ("test.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")
        })
        assert r.status_code == 200
        assert len(r.json()["errors"]) > 0

    def test_import_csv_invalid_file(self, client):
        r = client.post("/api/records/import", files={
            "file": ("test.txt", io.BytesIO(b"hello"), "text/plain")
        })
        assert r.status_code == 400


class TestRecordsUpsert:
    def test_upsert_create_then_update(self, client):
        oid = _create_org(client)
        name = _uid()
        # Create
        r = client.post("/api/records", json={
            "type": "bulk", "branch_id": "B005", "name": name,
            "org_id": oid, "minutes": 100, "participant_count": 20,
            "morning_male": 10, "morning_female": 10,
            "date": "2026-06-01",
        })
        assert r.status_code == 201
        first_id = r.json()["id"]
        assert "บันทึกสำเร็จ" in r.json()["message"]

        # Upsert (same org+name+date)
        r = client.post("/api/records", json={
            "type": "bulk", "branch_id": "B005", "name": name,
            "org_id": oid, "minutes": 200, "participant_count": 40,
            "morning_male": 20, "morning_female": 20,
            "date": "2026-06-01",
        })
        assert r.status_code == 201
        assert r.json()["id"] == first_id
        assert "อัพเดต" in r.json()["message"]


class TestRecords9Fields:
    def test_bulk_9_fields(self, client):
        oid = _create_org(client)
        name = _uid()
        r = client.post("/api/records", json={
            "type": "bulk", "branch_id": "B005", "name": name,
            "org_id": oid, "minutes": 500, "participant_count": 100,
            "morning_male": 30, "morning_female": 40, "morning_unspecified": 10,
            "afternoon_male": 20, "afternoon_female": 25, "afternoon_unspecified": 5,
            "evening_male": 10, "evening_female": 15, "evening_unspecified": 5,
            "date": "2026-06-02",
        })
        assert r.status_code == 201

        # Verify via list
        r = client.get(f"/api/records?branch_id=B005")
        records = [rec for rec in r.json() if rec["name"] == name]
        assert len(records) == 1
        rec = records[0]
        assert rec["morning_male"] == 30
        assert rec["afternoon_female"] == 25
        assert rec["evening_unspecified"] == 5

    def test_individual_session_fields(self, client):
        pid = _create_participant(client)
        name = _uid()
        r = client.post("/api/records", json={
            "type": "individual", "branch_id": "B005", "name": name,
            "participant_id": pid, "minutes": 5,
            "morning_male": 1,
            "date": "2026-06-03",
        })
        assert r.status_code == 201

        r = client.get("/api/records?branch_id=B005&record_type=individual")
        records = [rec for rec in r.json() if rec["name"] == name]
        assert len(records) == 1
        assert records[0]["morning_male"] == 1
        assert records[0]["afternoon_male"] == 0
        assert records[0]["evening_male"] == 0
