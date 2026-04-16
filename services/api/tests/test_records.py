"""Test: Records CRUD + Anti-fraud"""
import uuid


def _uid():
    """Generate unique name to avoid cooldown/daily limit conflicts."""
    return f"pytest-{uuid.uuid4().hex[:8]}"


def _create_org(client, branch_id="B005"):
    """Helper: create + approve a test org and return its id."""
    oid = f"OT{uuid.uuid4().hex[:6]}"
    r = client.post("/api/organizations", json={
        "id": oid, "name": f"TestOrg-{oid}", "branch_id": branch_id,
    })
    assert r.status_code == 201
    client.patch(f"/api/organizations/{oid}/approve")
    return oid


def _create_participant(client, branch_id="B005"):
    """Helper: create + approve a test participant and return its id."""
    r = client.post("/api/participants", json={
        "branch_id": branch_id, "first_name": _uid(), "last_name": "Test",
        "privacy_accepted": True,
    })
    assert r.status_code == 201
    pid = r.json()["id"]
    client.patch(f"/api/participants/{pid}/approve")
    return pid


class TestCreateRecord:
    def test_create_individual(self, client):
        pid = _create_participant(client)
        r = client.post("/api/records", json={
            "type": "individual",
            "branch_id": "B005",
            "name": _uid(),
            "participant_id": pid,
            "minutes": 5,
            "date": "2026-03-14",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["status"] == "pending"
        assert data["id"] > 0

    def test_create_bulk(self, client):
        oid = _create_org(client)
        r = client.post("/api/records", json={
            "type": "bulk",
            "branch_id": "B005",
            "name": _uid(),
            "org_id": oid,
            "minutes": 100,
            "participant_count": 20,
            "minutes_per_person": 5,
            "date": "2026-03-14",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["status"] == "pending"

    def test_bulk_without_org_rejected(self, client):
        r = client.post("/api/records", json={
            "type": "bulk", "branch_id": "B005", "name": _uid(),
            "minutes": 100, "date": "2026-03-14",
        })
        assert r.status_code == 422
        assert r.json()["detail"]["error"] == "MISSING_ORG"

    def test_individual_without_participant_rejected(self, client):
        r = client.post("/api/records", json={
            "type": "individual", "branch_id": "B005", "name": _uid(),
            "minutes": 5, "date": "2026-03-14",
        })
        assert r.status_code == 422
        assert r.json()["detail"]["error"] == "MISSING_PARTICIPANT"

    def test_bulk_invalid_org_rejected(self, client):
        r = client.post("/api/records", json={
            "type": "bulk", "branch_id": "B005", "name": _uid(),
            "org_id": "FAKE-ORG", "minutes": 100, "date": "2026-03-14",
        })
        assert r.status_code == 422
        assert r.json()["detail"]["error"] == "ORG_NOT_FOUND"

    def test_individual_invalid_participant_rejected(self, client):
        r = client.post("/api/records", json={
            "type": "individual", "branch_id": "B005", "name": _uid(),
            "participant_id": 99999, "minutes": 5, "date": "2026-03-14",
        })
        assert r.status_code == 422
        assert r.json()["detail"]["error"] == "PARTICIPANT_NOT_FOUND"


class TestAntifraud:
    def test_negative_minutes(self, client):
        pid = _create_participant(client)
        r = client.post("/api/records", json={
            "type": "individual", "branch_id": "B005", "name": _uid(),
            "participant_id": pid, "minutes": -5, "date": "2026-03-14",
        })
        assert r.status_code == 422
        assert r.json()["detail"]["error"] == "INVALID_MINUTES"

    def test_zero_minutes(self, client):
        pid = _create_participant(client)
        r = client.post("/api/records", json={
            "type": "individual", "branch_id": "B005", "name": _uid(),
            "participant_id": pid, "minutes": 0, "date": "2026-03-14",
        })
        assert r.status_code == 422
        assert r.json()["detail"]["error"] == "INVALID_MINUTES"

    def test_session_limit_exceeded(self, client):
        pid = _create_participant(client)
        r = client.post("/api/records", json={
            "type": "individual", "branch_id": "B005", "name": _uid(),
            "participant_id": pid, "minutes": 10, "date": "2026-03-14",
        })
        assert r.status_code == 422
        assert r.json()["detail"]["error"] == "SESSION_LIMIT_EXCEEDED"

    def test_bulk_limit_exceeded(self, client):
        oid = _create_org(client)
        r = client.post("/api/records", json={
            "type": "bulk", "branch_id": "B005", "name": _uid(),
            "org_id": oid, "minutes": 160,
            "participant_count": 10, "minutes_per_person": 16,
            "date": "2026-03-14",
        })
        assert r.status_code == 422
        assert r.json()["detail"]["error"] == "BULK_LIMIT_EXCEEDED"

    def test_missing_required_fields(self, client):
        r = client.post("/api/records", json={
            "type": "individual", "branch_id": "B005",
        })
        assert r.status_code == 422


class TestApproveReject:
    def test_approve(self, client):
        pid = _create_participant(client, "B003")
        r = client.post("/api/records", json={
            "type": "individual", "branch_id": "B003", "name": _uid(),
            "participant_id": pid, "minutes": 5, "date": "2026-03-13",
        })
        assert r.status_code == 201
        record_id = r.json()["id"]

        r = client.patch(f"/api/records/{record_id}/approve", json={
            "approved_by": "pytest_admin",
        })
        assert r.status_code == 200
        assert r.json()["status"] == "approved"

    def test_reject(self, client):
        pid = _create_participant(client, "B003")
        r = client.post("/api/records", json={
            "type": "individual", "branch_id": "B003", "name": _uid(),
            "participant_id": pid, "minutes": 5, "date": "2026-03-13",
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
