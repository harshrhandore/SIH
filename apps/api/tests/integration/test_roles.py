"""Institution catalogue scope is applied before rows are serialized."""

from dotenv import dotenv_values
from fastapi.testclient import TestClient
from app.main import app
from app.settings import ROOT
from db.seed.fixtures import uid

client = TestClient(app)


def login(email):
    result = client.post(
        "/api/v1/auth/login", json={"email": email, "password": dotenv_values(ROOT / ".env")["DEMO_PASSWORD"]}
    )
    assert result.status_code == 200, result.text
    return {"Authorization": "Bearer " + result.json()["access_token"]}


def test_operator_catalogue_is_scoped_and_programs_cannot_cross_institutions():
    headers = login("operator.b@example.test")
    result = client.get("/api/v1/institutions", headers=headers)
    assert result.status_code == 200, result.text
    assert [r["id"] for r in result.json()["items"]] == [str(uid("institution", 1))]
    denied = client.get(f"/api/v1/institutions/{uid('institution', 0)}/programs", headers=headers)
    assert denied.status_code == 404
    allowed = client.get(f"/api/v1/institutions/{uid('institution', 1)}/programs", headers=headers)
    assert allowed.status_code == 200 and allowed.json()["items"]
    assert all(r["institution_id"] == str(uid("institution", 1)) for r in allowed.json()["items"])
    invalid = client.get("/api/v1/institutions?state=UnknownSyntheticState", headers=headers)
    assert invalid.status_code == 422 and invalid.json()["error"]["code"] == "UNKNOWN_STATE"


def test_student_can_list_own_programs_only():
    headers = login("student.riya@example.test")
    assert client.get("/api/v1/institutions", headers=headers).status_code == 403
    own = client.get(f"/api/v1/institutions/{uid('institution', 0)}/programs", headers=headers)
    assert own.status_code == 200 and own.json()["items"]
    assert client.get(f"/api/v1/institutions/{uid('institution', 1)}/programs", headers=headers).status_code == 404
