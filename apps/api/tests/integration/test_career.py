from uuid import uuid4
from dotenv import dotenv_values
from fastapi.testclient import TestClient
from app.main import app
from app.settings import ROOT
from app.db.session import connect, one


def test_career_submission_replay_and_history_keep_score_contract():
    client = TestClient(app)
    signed_in = client.post(
        "/api/v1/auth/login",
        json={"email": "student.riya@example.test", "password": dotenv_values(ROOT / ".env")["DEMO_PASSWORD"]},
    )
    assert signed_in.status_code == 200, signed_in.text
    tokens = signed_in.json()
    student_id = tokens["user"]["student_id"]
    headers = {
        "Authorization": "Bearer " + tokens["access_token"],
        "X-CSRF-Token": tokens["csrf_token"],
        "Idempotency-Key": str(uuid4()),
    }
    path = f"/api/v1/students/{student_id}/career"
    body = {"question": "Can I become a Data Scientist?", "role_code": "DATA_SCIENTIST"}
    response = client.post(path, json=body, headers=headers)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["readiness_percent"] == 74
    assert [step["estimated_weeks"] for step in result["recommended_steps"]] == [2, 3, 1, 2, 3, 1]
    assert client.post(path, json=body, headers=headers).json() == result
    history = client.get(path + "/history", headers=headers)
    assert history.status_code == 200, history.text
    saved = next(row for row in history.json()["items"] if row["session_id"] == result["session_id"])
    assert saved["readiness_percent"] == saved["response"]["readiness_percent"] == 74
    with connect() as conn:
        assert one(conn, "SELECT count(*) AS n FROM career_sessions WHERE id=%s", (result["session_id"],))["n"] == 1
