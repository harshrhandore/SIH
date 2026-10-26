"""Authentication contract and family revocation regressions."""

from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import pytest
from app.db.session import connect
from dotenv import dotenv_values
from fastapi.testclient import TestClient
from app.main import app
from app.settings import ROOT

client = TestClient(app)


def test_openapi_distinguishes_protected_bearer_routes_from_public_login():
    schema = client.get("/openapi.json").json()
    assert schema["components"]["securitySchemes"]["HTTPBearer"]["scheme"] == "bearer"
    assert schema["paths"]["/api/v1/audit/events"]["get"]["security"] == [{"HTTPBearer": []}]
    assert not schema["paths"]["/api/v1/auth/login"]["post"].get("security")


@pytest.fixture
def account():
    identifier = uuid4()
    email = f"auth-regression-{identifier}@example.test"
    with connect() as conn:
        conn.execute(
            "INSERT INTO users(id,email,password_hash,full_name,role_code,institution_id) SELECT %s,%s,password_hash,'Synthetic auth regression',role_code,institution_id FROM users WHERE email='operator.b@example.test'",
            (identifier, email),
        )
    yield email
    with connect() as conn:
        conn.execute("UPDATE users SET active=false WHERE id=%s", (identifier,))


def sign_in(email):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": dotenv_values(ROOT / ".env")["DEMO_PASSWORD"]},
    )
    assert response.status_code == 200, response.text
    return response.json()


def headers(tokens):
    return {"Authorization": "Bearer " + tokens["access_token"], "X-CSRF-Token": tokens["csrf_token"]}


def test_auth_public_contract_contains_no_private_user_fields(account):
    tokens = sign_in(account)
    assert tokens["token_type"] == "bearer" and tokens["expires_in"] == 900
    assert set(tokens["user"]) == {
        "id",
        "email",
        "full_name",
        "role",
        "institution_id",
        "student_id",
        "assigned_institutions",
    }
    me = client.get("/api/v1/auth/me", headers=headers(tokens))
    assert me.status_code == 200 and me.json() == tokens["user"]


def test_password_limit_counts_utf8_bytes():
    for password in ["a" * 73, "Ã©" * 37]:
        response = client.post("/api/v1/auth/login", json={"email": f"{uuid4()}@example.test", "password": password})
        assert response.status_code == 422, response.text
        assert response.json()["error"]["code"] == "PASSWORD_TOO_LONG"


def test_concurrent_refresh_reuse_commits_family_revocation(account):
    tokens = sign_in(account)

    def rotate(_):
        return client.post(
            "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}, headers=headers(tokens)
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(rotate, range(2)))
    assert sorted(r.status_code for r in results) == [200, 401]
    rejected = next(r for r in results if r.status_code == 401)
    assert rejected.json()["error"]["code"] == "REFRESH_REUSED"
    rotated = next(r.json() for r in results if r.status_code == 200)
    assert client.get("/api/v1/auth/me", headers=headers(rotated)).status_code == 401


def test_logout_current_family_preserves_other_session_then_all_revokes_it(account):
    first, second = sign_in(account), sign_in(account)
    response = client.post("/api/v1/auth/logout", json={"all_sessions": False}, headers=headers(first))
    assert response.status_code == 200 and response.json() == {"logged_out": True}
    assert client.get("/api/v1/auth/me", headers=headers(first)).status_code == 401
    assert client.get("/api/v1/auth/me", headers=headers(second)).status_code == 200
    third = sign_in(account)
    assert client.post("/api/v1/auth/logout", json={"all_sessions": True}, headers=headers(second)).status_code == 200
    assert client.get("/api/v1/auth/me", headers=headers(second)).status_code == 401
    assert client.get("/api/v1/auth/me", headers=headers(third)).status_code == 401
