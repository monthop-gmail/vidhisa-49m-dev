"""Test: Admin approval flow — org, participant, record ต้อง approved ก่อนใช้งาน"""
import uuid


def _uid():
    return f"af-{uuid.uuid4().hex[:6]}"


class TestOrgApprovalFlow:
    def test_new_org_is_pending(self, client):
        oid = f"AF{uuid.uuid4().hex[:5]}"
        r = client.post("/api/organizations", json={
            "id": oid, "name": f"Test-{oid}", "branch_id": "B001",
        })
        assert r.status_code == 201
        r = client.get(f"/api/organizations/{oid}")
        assert r.json()["status"] == "pending"

    def test_pending_org_cannot_record(self, client):
        oid = f"AF{uuid.uuid4().hex[:5]}"
        client.post("/api/organizations", json={
            "id": oid, "name": f"Test-{oid}", "branch_id": "B001",
        })
        r = client.post("/api/records", json={
            "type": "bulk", "branch_id": "B001", "name": "test",
            "org_id": oid, "minutes": 100, "date": "2026-06-01",
        })
        assert r.status_code == 422
        assert r.json()["detail"]["error"] == "ORG_NOT_APPROVED"

    def test_approved_org_can_record(self, client):
        oid = f"AF{uuid.uuid4().hex[:5]}"
        client.post("/api/organizations", json={
            "id": oid, "name": f"Test-{oid}", "branch_id": "B001",
        })
        client.patch(f"/api/organizations/{oid}/approve")
        r = client.post("/api/records", json={
            "type": "bulk", "branch_id": "B001", "name": "test",
            "org_id": oid, "minutes": 100, "date": "2026-06-01",
        })
        assert r.status_code == 201

    def test_reject_org(self, client):
        oid = f"AF{uuid.uuid4().hex[:5]}"
        client.post("/api/organizations", json={
            "id": oid, "name": f"Test-{oid}", "branch_id": "B001",
        })
        r = client.patch(f"/api/organizations/{oid}/reject")
        assert r.status_code == 200
        assert r.json()["status"] == "rejected"

    def test_org_list_has_status(self, client):
        r = client.get("/api/organizations")
        assert r.status_code == 200
        for o in r.json()[:5]:
            assert "status" in o
            assert o["status"] in ("pending", "approved", "rejected")


class TestParticipantApprovalFlow:
    def test_new_participant_is_pending(self, client):
        fn, ln = _uid(), _uid()
        r = client.post("/api/participants", json={
            "branch_id": "B001", "first_name": fn, "last_name": ln,
            "privacy_accepted": True,
        })
        assert r.status_code == 201
        pid = r.json()["id"]
        r = client.get(f"/api/participants/{pid}")
        assert r.json()["status"] == "pending"

    def test_pending_participant_cannot_record(self, client):
        fn, ln = _uid(), _uid()
        r = client.post("/api/participants", json={
            "branch_id": "B001", "first_name": fn, "last_name": ln,
            "privacy_accepted": True,
        })
        pid = r.json()["id"]
        r = client.post("/api/records", json={
            "type": "individual", "branch_id": "B001", "name": f"{fn} {ln}",
            "participant_id": pid, "minutes": 5, "date": "2026-06-01",
        })
        assert r.status_code == 422
        assert r.json()["detail"]["error"] == "PARTICIPANT_NOT_APPROVED"

    def test_approved_participant_can_record(self, client):
        fn, ln = _uid(), _uid()
        r = client.post("/api/participants", json={
            "branch_id": "B001", "first_name": fn, "last_name": ln,
            "privacy_accepted": True,
        })
        pid = r.json()["id"]
        client.patch(f"/api/participants/{pid}/approve")
        r = client.post("/api/records", json={
            "type": "individual", "branch_id": "B001", "name": f"{fn} {ln}",
            "participant_id": pid, "minutes": 5, "date": "2026-06-01",
        })
        assert r.status_code == 201

    def test_reject_participant(self, client):
        fn, ln = _uid(), _uid()
        r = client.post("/api/participants", json={
            "branch_id": "B001", "first_name": fn, "last_name": ln,
            "privacy_accepted": True,
        })
        pid = r.json()["id"]
        r = client.patch(f"/api/participants/{pid}/reject")
        assert r.status_code == 200
        assert r.json()["status"] == "rejected"

    def test_participant_list_has_status(self, client):
        r = client.get("/api/participants?limit=5")
        assert r.status_code == 200
        for p in r.json():
            assert "status" in p


class TestRecordApprovalFlow:
    def test_record_pending_then_approve(self, client):
        # Use existing approved org B001-00
        r = client.post("/api/records", json={
            "type": "bulk", "branch_id": "B001", "name": "FlowTest",
            "org_id": "B001-00", "minutes": 50, "date": "2026-06-10",
        })
        assert r.status_code == 201
        rid = r.json()["id"]
        assert r.json()["status"] == "pending"

        r = client.patch(f"/api/records/{rid}/approve", json={"approved_by": "test"})
        assert r.status_code == 200
        assert r.json()["status"] == "approved"

    def test_record_pending_then_reject(self, client):
        r = client.post("/api/records", json={
            "type": "bulk", "branch_id": "B001", "name": "FlowTest2",
            "org_id": "B001-00", "minutes": 50, "date": "2026-06-11",
        })
        rid = r.json()["id"]
        r = client.patch(f"/api/records/{rid}/reject", json={"reason": "test"})
        assert r.status_code == 200
        assert r.json()["status"] == "rejected"
