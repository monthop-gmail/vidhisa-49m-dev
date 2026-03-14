"""Test: Markers endpoint (GPS pins)"""


def test_markers(client):
    r = client.get("/api/markers")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_markers_branch_fields(client):
    r = client.get("/api/markers")
    data = r.json()
    branches = [m for m in data if m["type"] == "branch"]
    assert len(branches) > 0
    b = branches[0]
    assert "name" in b
    assert "province" in b
    assert "lat" in b
    assert "lng" in b
    assert "minutes" in b
    assert isinstance(b["lat"], float)
    assert isinstance(b["lng"], float)
