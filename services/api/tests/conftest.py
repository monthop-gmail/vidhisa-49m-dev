import os
import pytest
import httpx

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL


@pytest.fixture(scope="session")
def client():
    """Client with admin auth token + ensure PLJ-B001 exists for tests."""
    with httpx.Client(base_url=BASE_URL, timeout=10) as c:
        # Login as central admin
        r = c.post("/api/auth/login", json={"username": "admin", "password": "vidhisa2569"})
        if r.status_code == 200:
            token = r.json()["token"]
            c.headers["Authorization"] = f"Bearer {token}"

        # Ensure PLJ-B001 exists (auto-approved) for tests that reference it
        check = c.get("/api/organizations/PLJ-B001")
        if check.status_code == 404:
            c.post("/api/organizations", json={
                "id": "PLJ-B001",
                "name": "สถาบันพลังจิตตานุภาพ สาขา 1 (test)",
                "org_type": "สถาบันพลังจิตตานุภาพ",
                "branch_id": "B001",
            })
            c.patch("/api/organizations/PLJ-B001/approve")

        yield c
