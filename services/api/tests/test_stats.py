"""Test: Stats endpoints"""


def test_stats_total(client):
    r = client.get("/api/stats/total")
    assert r.status_code == 200
    data = r.json()
    assert "total_minutes" in data
    assert "total_records" in data
    assert "total_branches" in data
    assert "total_orgs" in data
    assert isinstance(data["total_minutes"], int)
    assert data["total_minutes"] >= 0


def test_stats_by_province(client):
    r = client.get("/api/stats/by-province")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) > 0
    first = data[0]
    assert "province" in first
    assert "code" in first
    assert "minutes" in first
    assert "records" in first
    # sorted descending by minutes
    minutes = [d["minutes"] for d in data]
    assert minutes == sorted(minutes, reverse=True)


def test_stats_by_group(client):
    r = client.get("/api/stats/by-group")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) > 0
    first = data[0]
    assert "group_id" in first
    assert "group_name" in first
    assert "provinces" in first
    assert "province_codes" in first
    assert "minutes" in first
    assert "branches_count" in first


def test_stats_by_branch(client):
    r = client.get("/api/stats/by-branch")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) > 0
    first = data[0]
    assert "branch_id" in first
    assert "branch_name" in first
    assert "province" in first
    assert "minutes" in first
    # sorted descending
    minutes = [d["minutes"] for d in data]
    assert minutes == sorted(minutes, reverse=True)


def test_stats_daily(client):
    r = client.get("/api/stats/daily")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
