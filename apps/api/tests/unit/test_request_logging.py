import json
from fastapi.testclient import TestClient
from app.main import app
from app.core import logging as telemetry


def test_request_logs_are_allowlisted_and_origin_rejections_are_logged(monkeypatch):
    messages = []
    monkeypatch.setattr(telemetry.logger, "info", messages.append)
    client = TestClient(app)
    rejected = client.post(
        "/api/v1/auth/login?token=private-query-value",
        headers={"Origin": "https://invalid.example.test", "Authorization": "Bearer private-header-value"},
        json={"email": "private-email@example.test", "password": "private-body-value"},
    )
    assert rejected.status_code == 403
    assert len(messages) == 1
    logged = json.loads(messages[0])
    assert set(logged) == {"request_id", "status", "took_ms"}
    assert logged["status"] == 403 and logged["took_ms"] >= 0
    assert logged["request_id"] == rejected.json()["error"]["request_id"]
    assert "private" not in messages[0]


def test_success_log_matches_response_request_id(monkeypatch):
    messages = []
    monkeypatch.setattr(telemetry.logger, "info", messages.append)
    response = TestClient(app).get("/api/v1/health/live")
    assert response.status_code == 200
    assert json.loads(messages[0])["request_id"] == response.headers["x-request-id"]
