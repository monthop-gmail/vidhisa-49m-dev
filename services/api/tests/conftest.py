import os
import pytest
import httpx

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL


@pytest.fixture(scope="session")
def client():
    """Client with admin auth token for all tests."""
    with httpx.Client(base_url=BASE_URL, timeout=10) as c:
        # Login as central admin
        r = c.post("/api/auth/login", json={"username": "admin", "password": "vidhisa2569"})
        if r.status_code == 200:
            token = r.json()["token"]
            c.headers["Authorization"] = f"Bearer {token}"
        yield c
