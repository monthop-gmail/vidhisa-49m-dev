"""Test: Records CRUD + Anti-fraud"""
import uuid


def _uid():
    """Generate unique name to avoid cooldown/daily limit conflicts."""
    return f"pytest-{uuid.uuid4().hex[:8]}"


class TestCreateRecord:
    def test_create_individual(self, client):
        r = client.post("/api/records", json={
            "type": "individual",
            "branch_id": "B005",
            "name": _uid(),
            "minutes": 5,
            "date": "2026-03-14",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["status"] == "pending"
        assert data["id"] > 0

    def test_create_bulk(self, client):
        r = client.post("/api/records", json={
            "type": "bulk",
            "branch_id": "B005",
            "name": _uid(),
            "minutes": 100,
            "participant_count": 20,
            "minutes_per_person": 5,
            "date": "2026-03-14",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["status"] == "pending"


class TestAntifraud:
    def test_negative_minutes(self, client):
        r = client.post("/api/records", json={
            "type": "individual",
            "branch_id": "B005",
            "name": _uid(),
            "minutes": -5,
            "date": "2026-03-14",
        })
        assert r.status_code == 422
        assert r.json()["detail"]["error"] == "INVALID_MINUTES"

    def test_zero_minutes(self, client):
        r = client.post("/api/records", json={
            "type": "individual",
            "branch_id": "B005",
            "name": _uid(),
            "minutes": 0,
            "date": "2026-03-14",
        })
        assert r.status_code == 422
        assert r.json()["detail"]["error"] == "INVALID_MINUTES"

    def test_session_limit_exceeded(self, client):
        r = client.post("/api/records", json={
            "type": "individual",
            "branch_id": "B005",
            "name": _uid(),
            "minutes": 10,
            "date": "2026-03-14",
        })
        assert r.status_code == 422
        assert r.json()["detail"]["error"] == "SESSION_LIMIT_EXCEEDED"

    def test_bulk_limit_exceeded(self, client):
        r = client.post("/api/records", json={
            "type": "bulk",
            "branch_id": "B005",
            "name": _uid(),
            "minutes": 100,
            "participant_count": 10,
            "minutes_per_person": 10,
            "date": "2026-03-14",
        })
        assert r.status_code == 422
        assert r.json()["detail"]["error"] == "BULK_LIMIT_EXCEEDED"

    def test_missing_required_fields(self, client):
        r = client.post("/api/records", json={
            "type": "individual",
            "branch_id": "B005",
        })
        assert r.status_code == 422


class TestApproveReject:
    def test_approve(self, client):
        name = _uid()
        r = client.post("/api/records", json={
            "type": "individual",
            "branch_id": "B003",
            "name": name,
            "minutes": 5,
            "date": "2026-03-13",
        })
        assert r.status_code == 201
        record_id = r.json()["id"]

        r = client.patch(f"/api/records/{record_id}/approve", json={
            "approved_by": "pytest_admin",
        })
        assert r.status_code == 200
        assert r.json()["status"] == "approved"

    def test_reject(self, client):
        name = _uid()
        r = client.post("/api/records", json={
            "type": "individual",
            "branch_id": "B003",
            "name": name,
            "minutes": 5,
            "date": "2026-03-13",
        })
        assert r.status_code == 201
        record_id = r.json()["id"]

        r = client.patch(f"/api/records/{record_id}/reject", json={
            "reason": "ทดสอบปฏิเสธจาก pytest",
        })
        assert r.status_code == 200
        assert r.json()["status"] == "rejected"

    def test_approve_not_found(self, client):
        r = client.patch("/api/records/99999/approve", json={
            "approved_by": "test",
        })
        assert r.status_code == 404

    def test_reject_not_found(self, client):
        r = client.patch("/api/records/99999/reject", json={
            "reason": "test",
        })
        assert r.status_code == 404
