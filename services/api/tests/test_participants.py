"""Test: Participants CRUD + Import/Export"""
import io
import uuid


def _name():
    return f"pt-{uuid.uuid4().hex[:6]}"


class TestParticipantsCRUD:
    def test_create_participant(self, client):
        fn, ln = _name(), _name()
        r = client.post("/api/participants", json={
            "branch_id": "B001", "prefix": "นาย",
            "first_name": fn, "last_name": ln,
            "gender": "ชาย", "age": 25, "province": "กรุงเทพมหานคร",
            "privacy_accepted": True,
        })
        assert r.status_code == 201
        assert r.json()["id"] > 0
        assert "ลงทะเบียนสำเร็จ" in r.json()["message"]

    def test_create_duplicate_same_branch(self, client):
        fn, ln = _name(), _name()
        r = client.post("/api/participants", json={
            "branch_id": "B001", "first_name": fn, "last_name": ln, "privacy_accepted": True,
        })
        assert r.status_code == 201
        r = client.post("/api/participants", json={
            "branch_id": "B001", "first_name": fn, "last_name": ln, "privacy_accepted": True,
        })
        assert r.status_code == 409
        assert r.json()["detail"]["error"] == "DUPLICATE"

    def test_create_duplicate_different_branch(self, client):
        fn, ln = _name(), _name()
        r = client.post("/api/participants", json={
            "branch_id": "B001", "first_name": fn, "last_name": ln, "privacy_accepted": True,
        })
        assert r.status_code == 201
        r = client.post("/api/participants", json={
            "branch_id": "B002", "first_name": fn, "last_name": ln, "privacy_accepted": True,
        })
        assert r.status_code == 409
        assert r.json()["detail"]["error"] == "ALREADY_REGISTERED"

    def test_transfer_branch(self, client):
        fn, ln = _name(), _name()
        r = client.post("/api/participants", json={
            "branch_id": "B001", "first_name": fn, "last_name": ln, "privacy_accepted": True,
        })
        pid = r.json()["id"]
        r = client.patch(f"/api/participants/{pid}/transfer", json={"branch_id": "B002"})
        assert r.status_code == 200
        assert r.json()["old_branch"] == "B001"
        assert r.json()["new_branch"] == "B002"

    def test_create_participant_missing_fields(self, client):
        r = client.post("/api/participants", json={
            "branch_id": "B001",
        })
        assert r.status_code == 422

    def test_list_participants(self, client):
        r = client.get("/api/participants")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_list_participants_filter_branch(self, client):
        r = client.get("/api/participants?branch_id=B001")
        assert r.status_code == 200
        for p in r.json():
            assert p["branch_id"] == "B001"

    def test_get_participant(self, client):
        fn, ln = _name(), _name()
        r = client.post("/api/participants", json={
            "branch_id": "B002", "first_name": fn, "last_name": ln,
            "privacy_accepted": True,
        })
        pid = r.json()["id"]

        r = client.get(f"/api/participants/{pid}")
        assert r.status_code == 200
        assert r.json()["first_name"] == fn

    def test_get_participant_not_found(self, client):
        r = client.get("/api/participants/99999")
        assert r.status_code == 404

    def test_update_participant(self, client):
        fn, ln = _name(), _name()
        r = client.post("/api/participants", json={
            "branch_id": "B003", "first_name": fn, "last_name": ln,
            "privacy_accepted": True,
        })
        pid = r.json()["id"]

        r = client.put(f"/api/participants/{pid}", json={
            "branch_id": "B003", "first_name": fn + "u", "last_name": ln,
            "gender": "หญิง", "age": 30, "privacy_accepted": True,
        })
        assert r.status_code == 200
        assert "อัพเดทสำเร็จ" in r.json()["message"]

    def test_update_participant_not_found(self, client):
        r = client.put("/api/participants/99999", json={
            "branch_id": "B001", "first_name": "x", "last_name": "y",
            "privacy_accepted": True,
        })
        assert r.status_code == 404


class TestParticipantsExportImport:
    def test_export_csv(self, client):
        r = client.get("/api/participants/export")
        assert r.status_code == 200
        assert "text/csv" in r.headers["content-type"]
        assert "first_name" in r.text

    def test_export_csv_filter_branch(self, client):
        r = client.get("/api/participants/export?branch_id=B001")
        assert r.status_code == 200

    def test_import_csv(self, client):
        csv_data = "branch_id,first_name,last_name,gender,age,province\nB001,นำเข้า,ทดสอบ,ชาย,20,กรุงเทพมหานคร\nB002,นำเข้า2,ทดสอบ2,หญิง,25,เชียงใหม่"
        r = client.post("/api/participants/import", files={
            "file": ("test.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")
        })
        assert r.status_code == 200
        assert r.json()["created"] == 2

    def test_import_csv_invalid_branch(self, client):
        csv_data = "branch_id,first_name,last_name\nXXX,ผิด,สาขา"
        r = client.post("/api/participants/import", files={
            "file": ("test.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")
        })
        assert r.status_code == 200
        assert len(r.json()["errors"]) > 0

    def test_import_csv_missing_header(self, client):
        csv_data = "name,age\ntest,20"
        r = client.post("/api/participants/import", files={
            "file": ("test.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")
        })
        assert r.status_code == 400

    def test_import_csv_invalid_file(self, client):
        r = client.post("/api/participants/import", files={
            "file": ("test.txt", io.BytesIO(b"hello"), "text/plain")
        })
        assert r.status_code == 400
