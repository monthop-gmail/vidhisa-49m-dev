"""Test: Projection endpoint"""


def test_projection(client):
    r = client.get("/api/projection")
    assert r.status_code == 200
    data = r.json()

    assert data["target_minutes"] == 49_000_000
    assert isinstance(data["current_minutes"], int)
    assert isinstance(data["remaining_minutes"], int)
    assert data["remaining_minutes"] >= 0

    assert "start_date" in data
    assert "today" in data
    assert "deadline" in data
    assert data["deadline"] == "2026-07-31"
    assert data["start_date"] == "2026-03-01"

    assert isinstance(data["days_remaining"], int)
    assert isinstance(data["daily_rate_current"], int)
    assert isinstance(data["daily_rate_needed"], int)
    assert isinstance(data["on_track"], bool)


def test_projection_math(client):
    r = client.get("/api/projection")
    data = r.json()
    # remaining = target - current
    assert data["remaining_minutes"] == max(data["target_minutes"] - data["current_minutes"], 0)
