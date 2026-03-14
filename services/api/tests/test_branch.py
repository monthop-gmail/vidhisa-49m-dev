"""Test: Branch Admin endpoints"""


def test_pending_valid_branch(client):
    r = client.get("/api/branch/B001/pending")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    for item in data:
        assert item["status"] == "pending"
        assert "id" in item
        assert "type" in item
        assert "name" in item
        assert "minutes" in item


def test_pending_empty_branch(client):
    r = client.get("/api/branch/BXXX/pending")
    assert r.status_code == 200
    assert r.json() == []
