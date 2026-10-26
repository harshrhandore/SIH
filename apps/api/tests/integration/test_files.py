from uuid import uuid4
from dotenv import dotenv_values
from fastapi.testclient import TestClient
from app.main import app
from app.settings import ROOT
from app.db.session import connect, one
from db.seed.fixtures import uid


def test_foreign_files_and_independent_evidence_are_scoped():
    actor = uuid4()
    email = f"file-regression-{actor}@example.test"
    with connect() as conn:
        conn.execute(
            "INSERT INTO users(id,email,password_hash,full_name,role_code,institution_id) SELECT %s,%s,password_hash,'Synthetic file regression',role_code,institution_id FROM users WHERE email='operator.b@example.test'",
            (actor, email),
        )
        foreign = one(conn, "SELECT id FROM certificates WHERE student_id=%s ORDER BY id LIMIT 1", (uid("student", 1),))
        own = one(conn, "SELECT id FROM students WHERE institution_id=%s ORDER BY id LIMIT 1", (uid("institution", 1),))
    client = TestClient(app)
    try:
        response = client.post(
            "/api/v1/auth/login", json={"email": email, "password": dotenv_values(ROOT / ".env")["DEMO_PASSWORD"]}
        )
        assert response.status_code == 200
        headers = {"Authorization": "Bearer " + response.json()["access_token"]}
        assert client.get(f"/api/v1/certificates/{foreign['id']}/file", headers=headers).status_code == 404
        for section in ["projects", "internships", "achievements", "scholarships", "certificates", "skills"]:
            denied = client.get(f"/api/v1/students/{uid('student', 1)}/evidence/{section}", headers=headers)
            assert denied.status_code == 404
            allowed = client.get(f"/api/v1/students/{own['id']}/evidence/{section}", headers=headers)
            assert allowed.status_code == 200 and isinstance(allowed.json()["items"], list)
        core = client.get(f"/api/v1/students/{own['id']}?include_evidence=false", headers=headers)
        assert core.status_code == 200 and "profile" in core.json() and "projects" not in core.json()
        assert client.get(f"/api/v1/students/{own['id']}/evidence/unknown", headers=headers).status_code == 404
    finally:
        with connect() as conn:
            conn.execute("UPDATE users SET active=false WHERE id=%s", (actor,))
