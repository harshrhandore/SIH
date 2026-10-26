from uuid import uuid4
from dotenv import dotenv_values
from fastapi.testclient import TestClient
from app.main import app
from app.settings import ROOT

client = TestClient(app)


def login(email):
    r = client.post(
        "/api/v1/auth/login", json={"email": email, "password": dotenv_values(ROOT / ".env")["DEMO_PASSWORD"]}
    )
    assert r.status_code == 200, r.text
    value = r.json()
    return (
        value,
        {
            "Authorization": "Bearer " + value["access_token"],
            "X-CSRF-Token": value["csrf_token"],
            "Idempotency-Key": str(uuid4()),
        },
    )


def test_dashboard_quality_links_and_literal_search():
    _, operator = login("operator.a@example.test")
    dashboard = client.get("/api/v1/dashboard", headers=operator)
    assert dashboard.status_code == 200, dashboard.text
    for quality in ["total", "clean", "flagged", "incomplete"]:
        result = client.get("/api/v1/students/search", params={"quality": quality}, headers=operator)
        assert result.status_code == 200, result.text
        assert result.json()["total"] == dashboard.json()[quality]
    for query in ["%%", "__", "' OR 1=1 --"]:
        result = client.get("/api/v1/students/search", params={"q": query}, headers=operator)
        assert result.status_code == 200 and result.json()["total"] == 0, result.text
