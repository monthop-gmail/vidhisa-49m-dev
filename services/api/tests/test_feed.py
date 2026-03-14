"""Test: Feed endpoint"""


def test_feed(client):
    r = client.get("/api/feed", params={"limit": 5})
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) <= 5
    if data:
        first = data[0]
        assert "id" in first
        assert "message" in first
        assert "minutes" in first
        assert "type" in first
        assert "timestamp" in first
        assert first["type"] in ("individual", "bulk")


def test_feed_default_limit(client):
    r = client.get("/api/feed")
    assert r.status_code == 200
    data = r.json()
    assert len(data) <= 20
