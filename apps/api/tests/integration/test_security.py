from pathlib import Path
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from dotenv import dotenv_values
from fastapi.testclient import TestClient
import psycopg
import pytest
from app.main import app
from app.settings import ROOT
from app.db.session import connect, one
from app.cli import owner_url
from app.core.audit import append, verify
from db.seed.fixtures import uid

client = TestClient(app)


def login(email):
    r = client.post(
        "/api/v1/auth/login", json={"email": email, "password": dotenv_values(ROOT / ".env")["DEMO_PASSWORD"]}
    )
    assert r.status_code == 200, r.text
    value = r.json()
    return value, {
        "Authorization": "Bearer " + value["access_token"],
        "X-CSRF-Token": value["csrf_token"],
        "Idempotency-Key": str(uuid4()),
    }


def test_runtime_immutable_privileges():
    for statement in [
        "UPDATE audit_events SET reason=reason",
        "DELETE FROM audit_events WHERE false",
        "TRUNCATE audit_events",
        "UPDATE audit_chains SET head_seq=head_seq",
        "DELETE FROM record_versions WHERE false",
        "UPDATE review_decisions SET reason=reason",
    ]:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            with connect() as conn:
                conn.execute(statement)


def test_scope_and_forged_token():
    _, operator = login("operator.b@example.test")
    sid = str(uid("student", 1))
    institution = str(uid("institution", 0))
    for path in [
        "/students/" + sid,
        "/students/" + sid + "/trust",
        "/students/" + sid + "/versions",
        "/students/" + sid + "/timeline",
        "/students/" + sid + "/career/history",
    ]:
        assert client.get("/api/v1" + path, headers=operator).status_code == 404
    assert client.get("/api/v1/students/search?institution_id=" + institution, headers=operator).status_code == 403
    assert client.get("/api/v1/auth/me", headers={"Authorization": operator["Authorization"] + "x"}).status_code == 401
    _, student = login("student.riya@example.test")
    assert client.get("/api/v1/students/" + str(uid("student", 2)), headers=student).status_code == 404
    _, admin = login("admin@example.test")
    assert client.get("/api/v1/students/" + sid, headers=admin).status_code == 404
    rows = client.get("/api/v1/cases", headers=admin).json()["items"]
    assert all("student_id" not in r and "full_name" not in r and "dob" not in r and "email" not in r for r in rows)


def test_refresh_reuse_revokes_family():
    value, headers = login("operator.a@example.test")
    r = client.post("/api/v1/auth/refresh", headers=headers, json={"refresh_token": value["refresh_token"]})
    assert r.status_code == 200
    fresh = r.json()
    assert (
        client.post("/api/v1/auth/refresh", headers=headers, json={"refresh_token": value["refresh_token"]}).status_code
        == 401
    )
    assert (
        client.get("/api/v1/auth/me", headers={"Authorization": "Bearer " + fresh["access_token"]}).status_code == 401
    )


def test_csrf_and_origin():
    _, headers = login("student.riya@example.test")
    headers.pop("X-CSRF-Token")
    assert client.post("/api/v1/auth/logout", headers=headers, json={}).status_code == 403
    assert (
        client.post(
            "/api/v1/auth/login",
            headers={"Origin": "https://invalid.example.test"},
            json={"email": "a", "password": "b"},
        ).status_code
        == 403
    )


def test_concurrent_audit_appends():
    institution = uid("institution", 1)

    def write(i):
        with connect() as conn:
            append(
                conn,
                institution,
                uid("user", "officer"),
                "AUDIT_CONCURRENCY_TEST",
                "institution",
                institution,
                "Synthetic concurrency regression check.",
                {"index": i},
            )

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(write, range(100)))
    with connect() as conn:
        result = verify(conn, institution)
        assert result["valid"] and result["events_checked"] >= 101


def test_term_guard():
    with pytest.raises(psycopg.errors.RaiseException, match="ENROLMENT_MISMATCH"):
        with connect() as conn:
            conn.execute(
                "INSERT INTO academic_performance(student_id,enrolment_id,academic_year,term_no,term_type,credits,sgpa,cgpa) SELECT %s,id,2022,1,'SEMESTER',22,8,8 FROM enrolments WHERE student_id=%s LIMIT 1",
                (uid("student", 2), uid("student", 1)),
            )


def test_program_oversight_denominator_and_state_trend():
    _, admin = login("admin@example.test")
    program = str(uid("program", "0:BTECH:CSE"))
    institution = str(uid("institution", 0))
    response = client.get(
        "/api/v1/oversight", params={"institution_id": institution, "program_id": program}, headers=admin
    )
    assert response.status_code == 200, response.text
    result = response.json()
    with connect() as conn:
        actual = one(conn, "SELECT count(*) AS n FROM students WHERE program_id=%s", (program,))["n"]
        expected = one(
            conn, "SELECT expected_records AS n FROM program_expected_records WHERE program_id=%s", (program,)
        )["n"]
    assert result["total"] == 1 and result["items"][0]["total"] == actual
    assert result["items"][0]["missing_records"] == max(0, expected - actual)
    wrong = client.get(
        "/api/v1/oversight", params={"institution_id": str(uid("institution", 1)), "program_id": program}, headers=admin
    )
    assert wrong.status_code == 422
    quality = client.get("/api/v1/analytics/data-quality?state=Maharashtra", headers=admin)
    assert quality.status_code == 200, quality.text
    assert quality.json()["trend"] and all(point["clean_percent"] == 100 for point in quality.json()["trend"])


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


def test_multiple_offers_count_one_student():
    with connect() as conn:
        conn.execute("BEGIN")
        student = uid("student", 1)
        program = uid("program", "0:BTECH:CSE")
        for suffix, amount in [("A", 12), ("B", 13)]:
            conn.execute(
                "INSERT INTO placements(student_id,company,role,package_lpa,placement_year,offer_status) VALUES (%s,%s,'Synthetic regression role',%s,2026,'OFFERED')",
                (student, "Synthetic regression " + suffix, amount),
            )
        conn.execute("SELECT refresh_demo_views()")
        row = one(
            conn,
            "SELECT * FROM mv_placements WHERE institution_id=%s AND program_id=%s AND year=2026",
            (uid("institution", 0), program),
        )
        distinct = one(
            conn,
            "SELECT count(DISTINCT s.id)::int AS n FROM students s JOIN programs p ON p.id=s.program_id JOIN placements pl ON pl.student_id=s.id AND pl.placement_year=s.admission_year+p.duration_years AND pl.offer_status IN ('OFFERED','ACCEPTED') WHERE s.program_id=%s AND s.current_year=p.duration_years AND s.status<>'WITHDRAWN' AND s.admission_year+p.duration_years=2026",
            (program,),
        )["n"]
        assert row["placed_students"] == distinct <= row["eligible_students"]
        conn.rollback()


def test_read_only_sandbox_broker_detects_tamper_without_production_change():
    from app.cli import sandbox

    sandbox("create")
    _, headers = login("operator.a@example.test")
    path = "/api/v1/demo/audit-sandbox/verify?institution_id=" + str(uid("institution", 0))
    clean = client.get(path, headers=headers)
    assert clean.status_code == 200 and clean.json()["valid"]
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with connect() as conn:
            conn.execute("SELECT * FROM demo_sandbox.audit_events")
    sandbox("tamper")
    broken = client.get(path, headers=headers)
    assert broken.status_code == 200 and not broken.json()["valid"]
    assert broken.json()["first_broken_link"]["reason"] == "ROW_HASH_MISMATCH"
    production = client.get("/api/v1/audit/verify-chain?institution_id=" + str(uid("institution", 0)), headers=headers)
    assert production.status_code == 200 and production.json()["valid"]


def test_web_benchmark_is_fixed_read_only_and_idempotent():
    _, headers = login("admin@example.test")
    body = {"dataset": "current", "runs": 20, "cache_mode": "BOTH"}
    started = client.post("/api/v1/demo/benchmarks", headers=headers, json=body)
    assert started.status_code == 202, started.text
    run = started.json()
    completed = client.get("/api/v1/demo/benchmarks/" + run["run_id"], headers=headers)
    assert completed.status_code == 200 and completed.json()["status"] == "COMPLETED", completed.text
    assert completed.json()["result"]["samples_count"] == 20
    before = completed.json()["finished_at"]
    replay = client.post("/api/v1/demo/benchmarks", headers=headers, json=body)
    assert replay.status_code == 202 and replay.json() == run
    assert client.get("/api/v1/demo/benchmarks/" + run["run_id"], headers=headers).json()["finished_at"] == before


def test_benchmark_respects_officer_scope_and_result_ownership(monkeypatch):
    from app.core.security import issue

    actor = uuid4()
    institution = uid("institution", 1)
    with connect() as conn:
        conn.execute(
            "INSERT INTO users(id,email,password_hash,full_name,role_code) VALUES (%s,%s,'unused','Scoped regression officer','OFFICER')",
            (actor, f"benchmark-{actor}@example.test"),
        )
        conn.execute("INSERT INTO user_institutions VALUES (%s,%s)", (actor, institution))
        user = one(conn, "SELECT * FROM users WHERE id=%s", (actor,))
        token = issue(conn, user)
        expected = one(conn, "SELECT count(*) AS n FROM students WHERE institution_id=%s", (institution,))["n"]
    headers = {
        "Authorization": "Bearer " + token["access_token"],
        "X-CSRF-Token": token["csrf_token"],
        "Idempotency-Key": str(uuid4()),
    }
    try:
        started = client.post(
            "/api/v1/demo/benchmarks", headers=headers, json={"dataset": "current", "runs": 20, "cache_mode": "BOTH"}
        )
        assert started.status_code == 202, started.text
        path = "/api/v1/demo/benchmarks/" + started.json()["run_id"]
        completed = client.get(path, headers=headers)
        assert completed.status_code == 200, completed.text
        result = completed.json()
        assert result["status"] == "COMPLETED", result
        assert result["student_count"] == expected
        assert result["institution_scope"] == [str(institution)]
        _, other = login("officer@example.test")
        assert client.get(path, headers=other).status_code == 404
        from app.settings import settings

        monkeypatch.setattr(settings, "demo_controls_enabled", False)
        assert client.get(path, headers=headers).status_code == 404
    finally:
        with connect() as conn:
            conn.execute("UPDATE users SET active=false WHERE id=%s", (actor,))
