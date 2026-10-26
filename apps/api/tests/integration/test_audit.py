from datetime import timedelta
from uuid import uuid4
import jwt
from dotenv import dotenv_values
from fastapi.testclient import TestClient
from app.main import app
from app.settings import ROOT, settings
from app.core.clock import utc_now
from app.core.audit import append, verify
from app.db.session import connect, one
from db.seed.fixtures import uid

client = TestClient(app)


def login(email):
    response = client.post(
        "/api/v1/auth/login", json={"email": email, "password": dotenv_values(ROOT / ".env")["DEMO_PASSWORD"]}
    )
    assert response.status_code == 200, response.text
    return response.json(), {"Authorization": "Bearer " + response.json()["access_token"]}


def test_timeline_uses_qualified_student_filter_and_returns_verified_utc_events():
    _, headers = login("operator.a@example.test")
    response = client.get(f"/api/v1/students/{uid('student', 1)}/timeline", headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["verified"] and data["items"] and data["chain_verified_at"].endswith("Z")
    assert all(row["hash_verified"] and row["occurred_at"].endswith("Z") for row in data["items"])
    assert all(len(row["row_hash"]) == 64 for row in data["items"])


def test_admin_audit_metadata_omits_private_fields_and_rejects_broad_grants():
    _, headers = login("admin@example.test")
    response = client.get("/api/v1/audit/events", headers=headers)
    assert response.status_code == 200 and response.json()["items"], response.text
    assert all(set(row) <= {"event_id", "action", "occurred_at", "case_ref"} for row in response.json()["items"])
    response = client.get("/api/v1/audit/events", headers={**headers, "X-Case-Access": "invalid"})
    assert response.status_code == 403 and response.json()["error"]["code"] == "CASE_FILTER_REQUIRED"


def test_foreign_case_filter_does_not_disclose_case_existence():
    _, headers = login("operator.b@example.test")
    with connect() as conn:
        case = one(
            conn,
            "SELECT c.id FROM review_cases c JOIN students s ON s.id=c.student_id WHERE s.institution_id=%s ORDER BY c.id LIMIT 1",
            (uid("institution", 0),),
        )
    response = client.get(
        f"/api/v1/audit/events?institution_id={uid('institution', 1)}&case_id={case['id']}", headers=headers
    )
    assert response.status_code == 404, response.text
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_case_bound_audit_reason_access_stops_after_grant_revocation():
    admin, headers = login("admin@example.test")
    case_id = uuid4()
    other_case_id = uuid4()
    with connect() as conn:
        student = one(
            conn,
            "SELECT s.id,s.institution_id FROM students s LEFT JOIN review_cases c ON c.student_id=s.id WHERE s.institution_id=%s AND c.id IS NULL ORDER BY s.id LIMIT 1",
            (uid("institution", 0),),
        )
        conn.execute(
            "INSERT INTO review_cases(id,student_id,opened_reason,status) VALUES (%s,%s,'SYNTHETIC_AUDIT_REGRESSION','ESCALATED')",
            (case_id, student["id"]),
        )
        conn.execute(
            "INSERT INTO review_cases(id,student_id,opened_reason,status) VALUES (%s,%s,'SYNTHETIC_AUDIT_REGRESSION','APPROVED')",
            (other_case_id, student["id"]),
        )
        append(
            conn,
            student["institution_id"],
            uid("user", "officer"),
            "AUDIT_REGRESSION",
            "student",
            student["id"],
            "Scoped synthetic audit regression.",
            student=student["id"],
        )
    token = jwt.encode(
        dict(
            sub=admin["user"]["id"],
            case_id=str(case_id),
            student_id=str(student["id"]),
            version=1,
            exp=utc_now() + timedelta(minutes=5),
            aud="case-access",
        ),
        settings.grant_secret,
        algorithm="HS256",
    )
    path = f"/api/v1/audit/events?case_id={case_id}"
    try:
        masked = client.get(path, headers=headers)
        assert masked.status_code == 200, masked.text
        assert all("reason" not in row for row in masked.json()["items"])
        granted = client.get(path, headers={**headers, "X-Case-Access": token})
        assert granted.status_code == 200, granted.text
        assert any(row["reason"] == "Scoped synthetic audit regression." for row in granted.json()["items"])
        assert all(row["case_ref"] != str(case_id) for row in granted.json()["items"])
        assert (
            client.get(
                f"/api/v1/audit/events?case_id={other_case_id}", headers={**headers, "X-Case-Access": token}
            ).status_code
            == 404
        )
        assert (
            client.get(f"/api/v1/cases/{other_case_id}", headers={**headers, "X-Case-Access": token}).status_code == 404
        )
        with connect() as conn:
            conn.execute("UPDATE review_cases SET status='OPEN',version_no=version_no+1 WHERE id=%s", (case_id,))
        assert client.get(path, headers={**headers, "X-Case-Access": token}).status_code == 404
    finally:
        with connect() as conn:
            conn.execute("DELETE FROM review_cases WHERE id=ANY(%s::uuid[])", ([case_id, other_case_id],))


def test_system_chain_is_separate_and_verifies_null_institution():
    with connect() as conn:
        system = verify(conn, None)
        institution = verify(conn, uid("institution", 0))
    assert system["exists"] and system["valid"]
    assert system["chain_id"] != institution["chain_id"]
