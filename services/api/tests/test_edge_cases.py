"""Test: Edge cases — transfer, pagination, re-approve, upsert+approved, GGS"""
import uuid


def _uid():
    return f"ec-{uuid.uuid4().hex[:6]}"


def _create_approved_org(client, branch_id="B005"):
    oid = f"EC{uuid.uuid4().hex[:5]}"
    client.post("/api/organizations", json={"id": oid, "name": f"Test-{oid}", "branch_id": branch_id})
    client.patch(f"/api/organizations/{oid}/approve")
    return oid


def _create_approved_participant(client, branch_id="B005"):
    r = client.post("/api/participants", json={
        "branch_id": branch_id, "first_name": _uid(), "last_name": "Edge",
        "privacy_accepted": True,
    })
    pid = r.json()["id"]
    client.patch(f"/api/participants/{pid}/approve")
    return pid


class TestTransferEdgeCases:
    def test_transfer_to_nonexistent_branch(self, client):
        fn, ln = _uid(), _uid()
        r = client.post("/api/participants", json={
            "branch_id": "B001", "first_name": fn, "last_name": ln, "privacy_accepted": True,
        })
        pid = r.json()["id"]
        r = client.patch(f"/api/participants/{pid}/transfer", json={"branch_id": "BXXX"})
        assert r.status_code == 404
        assert r.json()["detail"]["error"] == "BRANCH_NOT_FOUND"

    def test_transfer_not_found(self, client):
        r = client.patch("/api/participants/99999/transfer", json={"branch_id": "B001"})
        assert r.status_code == 404

    def test_transfer_missing_branch(self, client):
        fn, ln = _uid(), _uid()
        r = client.post("/api/participants", json={
            "branch_id": "B001", "first_name": fn, "last_name": ln, "privacy_accepted": True,
        })
        pid = r.json()["id"]
        r = client.patch(f"/api/participants/{pid}/transfer", json={})
        assert r.status_code == 400


class TestPagination:
    def test_records_limit(self, client):
        r = client.get("/api/records?limit=2")
        assert r.status_code == 200
        assert len(r.json()) <= 2

    def test_records_offset(self, client):
        r1 = client.get("/api/records?limit=2&offset=0")
        r2 = client.get("/api/records?limit=2&offset=2")
        assert r1.status_code == 200
        assert r2.status_code == 200
        ids1 = {r["id"] for r in r1.json()}
        ids2 = {r["id"] for r in r2.json()}
        assert ids1.isdisjoint(ids2)  # ไม่ซ้ำกัน

    def test_participants_limit(self, client):
        r = client.get("/api/participants?limit=3")
        assert r.status_code == 200
        assert len(r.json()) <= 3

    def test_participants_offset(self, client):
        r1 = client.get("/api/participants?limit=3&offset=0")
        r2 = client.get("/api/participants?limit=3&offset=3")
        assert r1.status_code == 200
        assert r2.status_code == 200
        ids1 = {p["id"] for p in r1.json()}
        ids2 = {p["id"] for p in r2.json()}
        assert ids1.isdisjoint(ids2)


class TestReApprove:
    def test_reject_then_approve_org(self, client):
        oid = f"EC{uuid.uuid4().hex[:5]}"
        client.post("/api/organizations", json={"id": oid, "name": f"Test-{oid}", "branch_id": "B001"})
        client.patch(f"/api/organizations/{oid}/reject")
        r = client.get(f"/api/organizations/{oid}")
        assert r.json()["status"] == "rejected"

        # Re-approve
        r = client.patch(f"/api/organizations/{oid}/approve")
        assert r.status_code == 200
        r = client.get(f"/api/organizations/{oid}")
        assert r.json()["status"] == "approved"

    def test_reject_then_approve_participant(self, client):
        fn, ln = _uid(), _uid()
        r = client.post("/api/participants", json={
            "branch_id": "B001", "first_name": fn, "last_name": ln, "privacy_accepted": True,
        })
        pid = r.json()["id"]
        client.patch(f"/api/participants/{pid}/reject")
        r = client.get(f"/api/participants/{pid}")
        assert r.json()["status"] == "rejected"

        # Re-approve
        r = client.patch(f"/api/participants/{pid}/approve")
        assert r.status_code == 200
        r = client.get(f"/api/participants/{pid}")
        assert r.json()["status"] == "approved"


class TestUpsertApproved:
    def test_upsert_resets_to_pending(self, client):
        """บันทึกซ้ำวัน org ที่ approved แล้ว → record กลับเป็น pending"""
        oid = _create_approved_org(client)
        name = _uid()

        # Create + approve
        r = client.post("/api/records", json={
            "type": "bulk", "branch_id": "B005", "name": name,
            "org_id": oid, "minutes": 100, "date": "2026-07-01",
        })
        rid = r.json()["id"]
        client.patch(f"/api/records/{rid}/approve", json={"approved_by": "test"})

        # Upsert same org+date → should reset to pending
        r = client.post("/api/records", json={
            "type": "bulk", "branch_id": "B005", "name": name,
            "org_id": oid, "minutes": 200, "date": "2026-07-01",
        })
        assert r.status_code == 201
        assert r.json()["id"] == rid
        assert r.json()["status"] == "pending"


class TestGGS:
    def test_ggs_sources(self, client):
        r = client.get("/api/ggs/sources")
        assert r.status_code == 200
        data = r.json()
        assert len(data) > 0
        assert "branch_id" in data[0]
        assert "branch_name" in data[0]

    def test_ggs_sync_missing_url(self, client):
        r = client.post("/api/ggs/sync", json={})
        assert r.status_code == 400

    def test_ggs_sync_invalid_url(self, client):
        r = client.post("/api/ggs/sync", json={"url": "https://example.com/not-a-sheet"})
        assert r.status_code == 400
