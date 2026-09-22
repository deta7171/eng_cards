def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    assert "Server-Timing" in resp.headers


def test_health_db(client):
    resp = client.get("/api/health/db")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["db_query_ms"] >= 0
