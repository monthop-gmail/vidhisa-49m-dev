"""Tests for /api/branch-view/* endpoints (me-ui public read-only API)."""

import uuid


def _uid() -> str:
    return uuid.uuid4().hex[:6]


def _get_branch_secret(client, branch_id: str) -> str:
    r = client.get(f"/api/branches/{branch_id}/view-link")
    assert r.status_code == 200, r.text
    return r.json()["view_secret"]


def _create_approved_participant(client, branch_id: str, first: str, last: str, member_code: str | None = None) -> int:
    payload = {
        "branch_id": branch_id,
        "first_name": first, "last_name": last,
        "member_code": member_code,
        "phone": "0812345678",
        "email": "test@example.com",
        "line_id": "@testline",
        "privacy_accepted": True,
    }
    r = client.post("/api/participants", json=payload)
    assert r.status_code == 201, r.text
    pid = r.json()["id"]
    r2 = client.patch(f"/api/participants/{pid}/approve")
    assert r2.status_code == 200, r2.text
    return pid


class TestInfoEndpoint:
    def test_valid_secret_returns_branch(self, client):
        secret = _get_branch_secret(client, "B001")
        assert secret and len(secret) == 6
        r = client.get(f"/api/branch-view/B001/{secret}/info")
        assert r.status_code == 200
        data = r.json()
        assert data["branch_id"] == "B001"
        assert "branch_name" in data and "province" in data

    def test_invalid_secret_returns_404(self, client):
        r = client.get("/api/branch-view/B001/WRONG1/info")
        assert r.status_code == 404
        assert r.json()["detail"]["error"] == "INVALID_LINK"

    def test_secret_format_invalid_returns_404(self, client):
        # lowercase / wrong length / contains banned chars (I L O U)
        for bad in ["abc123", "TOOLONG", "IIIIII", "OOOOOO"]:
            r = client.get(f"/api/branch-view/B001/{bad}/info")
            assert r.status_code == 404, f"expected 404 for {bad!r}, got {r.status_code}"

    def test_secret_from_other_branch_returns_404(self, client):
        s_b001 = _get_branch_secret(client, "B001")
        # Use B001's secret on B002 → should fail
        r = client.get(f"/api/branch-view/B002/{s_b001}/info")
        assert r.status_code == 404


class TestParticipantsSearch:
    def test_search_returns_only_approved(self, client):
        secret = _get_branch_secret(client, "B001")
        first = f"first-{_uid()}"
        last = f"last-{_uid()}"
        _create_approved_participant(client, "B001", first, last, member_code="M01")
        r = client.get(f"/api/branch-view/B001/{secret}/participants?q={first}")
        assert r.status_code == 200
        results = r.json()
        assert any(p["first_name"] == first for p in results)

    def test_search_excludes_pii_fields(self, client):
        secret = _get_branch_secret(client, "B001")
        first = f"pii-{_uid()}"
        _create_approved_participant(client, "B001", first, "lastname")
        r = client.get(f"/api/branch-view/B001/{secret}/participants?q={first}")
        assert r.status_code == 200
        for p in r.json():
            assert set(p.keys()) <= {"id", "prefix", "first_name", "last_name", "member_code"}
            for banned in ("phone", "email", "line_id", "age", "sub_district", "district", "province", "enrolled_date"):
                assert banned not in p

    def test_empty_q_returns_empty(self, client):
        secret = _get_branch_secret(client, "B001")
        r = client.get(f"/api/branch-view/B001/{secret}/participants?q=")
        assert r.status_code == 200
        assert r.json() == []

    def test_invalid_secret_returns_404(self, client):
        r = client.get("/api/branch-view/B001/WRONG1/participants?q=anything")
        assert r.status_code == 404


class TestMeEndpoint:
    def test_returns_own_data(self, client):
        secret = _get_branch_secret(client, "B001")
        first = f"me-{_uid()}"
        pid = _create_approved_participant(client, "B001", first, "lastname")
        r = client.get(f"/api/branch-view/B001/{secret}/me/{pid}")
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == pid
        assert data["branch_id"] == "B001"
        assert "stats" in data and "daily_minutes" in data and "recent_records" in data
        # phone is masked
        if data["profile"].get("phone_masked"):
            assert "xxx" in data["profile"]["phone_masked"]

    def test_excludes_pii_in_profile(self, client):
        secret = _get_branch_secret(client, "B001")
        first = f"pri-{_uid()}"
        pid = _create_approved_participant(client, "B001", first, "lastname")
        r = client.get(f"/api/branch-view/B001/{secret}/me/{pid}")
        assert r.status_code == 200
        # Raw 'phone' must not appear (only phone_masked)
        assert "phone" not in r.json()["profile"]
        # IP/device/photo never returned in records
        for rec in r.json()["recent_records"]:
            assert set(rec.keys()) <= {"id", "date", "minutes", "status"}

    def test_cross_branch_id_returns_404(self, client):
        secret_b001 = _get_branch_secret(client, "B001")
        # Create participant in B002, then try to fetch using B001 secret
        first = f"cross-{_uid()}"
        pid_b002 = _create_approved_participant(client, "B002", first, "lastname")
        r = client.get(f"/api/branch-view/B001/{secret_b001}/me/{pid_b002}")
        assert r.status_code == 404

    def test_invalid_secret_returns_404(self, client):
        r = client.get("/api/branch-view/B001/WRONG1/me/1")
        assert r.status_code == 404


class TestMigrationApplied:
    def test_all_branches_have_view_secret(self, client):
        # Sample 5 random branches — each must return a 6-char secret
        for bid in ("B001", "B002", "B003", "B047", "B101"):
            r = client.get(f"/api/branches/{bid}/view-link")
            assert r.status_code == 200, f"{bid}: {r.text}"
            secret = r.json()["view_secret"]
            assert secret and len(secret) == 6
