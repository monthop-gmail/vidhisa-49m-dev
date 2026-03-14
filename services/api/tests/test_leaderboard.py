"""Test: Leaderboard endpoint"""


def test_leaderboard_branch(client):
    r = client.get("/api/leaderboard", params={"type": "branch", "limit": 5})
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) <= 5
    if data:
        first = data[0]
        assert "rank" in first
        assert "branch_id" in first
        assert "branch_name" in first
        assert "minutes" in first
        assert first["rank"] == 1
        # descending order
        minutes = [d["minutes"] for d in data]
        assert minutes == sorted(minutes, reverse=True)


def test_leaderboard_org(client):
    r = client.get("/api/leaderboard", params={"type": "org", "limit": 5})
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    if data:
        first = data[0]
        assert "rank" in first
        assert "name" in first
        assert "minutes" in first
