"""Offline API rehearsal against the explicit synthetic database; never resets data."""

import json
import sys
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "apps/api")]
from app.main import app
from app.modules.imports.service import ALIASES
from dotenv import dotenv_values
from fastapi.testclient import TestClient


def run():
    password = dotenv_values(ROOT / ".env")["DEMO_PASSWORD"]
    client = TestClient(app)

    def login(email):
        r = client.post("/api/v1/auth/login", json=dict(email=email, password=password))
        assert r.status_code == 200, r.text
        body = r.json()
        return dict(Authorization="Bearer " + body["access_token"], **{"X-CSRF-Token": body["csrf_token"]})

    def call(method, path, headers, **kwargs):
        r = client.request(method, "/api/v1" + path, headers={**headers, "Idempotency-Key": str(uuid4())}, **kwargs)
        assert r.status_code < 300, (path, r.status_code, r.text[:1000])
        return r.json()

    operator = login("operator.a@example.test")
    officer = login("officer@example.test")
    student = login("student.riya@example.test")
    admin = login("admin@example.test")
    manifest = call("GET", "/demo/manifest", operator)
    institution = manifest["institution_a_id"]
    call("GET", "/dashboard", operator)
    batch_list = call("GET", "/imports", operator)["items"]
    if batch_list:
        batch = batch_list[0]["id"]
        detail = call("GET", "/imports/" + batch, operator)
        if detail["status"] == "FAILED":
            call(
                "POST",
                "/import-jobs/" + detail["job"]["id"] + "/retry",
                operator,
                json=dict(reason="Retry after repairing the fixed audit lock privilege helper."),
            )
    else:
        with (ROOT / "fixtures/demo-import-1000.csv").open("rb") as f:
            result = call(
                "POST",
                "/imports",
                operator,
                files={"file": ("demo-import-1000.csv", f, "text/csv")},
                data={"institution_id": institution},
            )
        batch = result["batch_id"]
        call("PUT", f"/imports/{batch}/mapping", operator, json=dict(mapping=ALIASES, date_format="DD/MM/YYYY"))
        call("POST", f"/imports/{batch}/validate", operator, json=dict(confirm_synthetic_data=True))
    report = call("GET", f"/imports/{batch}/report", operator)
    assert (report["clean"], report["flagged"], report["incomplete"], report["all_findings"]) == (880, 110, 10, 140), (
        report
    )
    cases = call("GET", "/cases?q=DEMO-A-0032", officer)["items"]
    assert len(cases) == 1, cases
    case = call("GET", "/cases/" + cases[0]["id"], officer)
    if case["case"]["status"] == "OPEN" and case["student"]["profile"]["version_no"] == 1:
        call(
            "POST",
            "/cases/" + cases[0]["id"] + "/decisions",
            officer,
            json=dict(
                expected_version=case["case"]["version_no"],
                action="REQUEST_CORRECTION",
                reason="Replace the invalid test identifier from the synthetic manifest.",
                requested_fields=["submitted_apaar_id"],
            ),
        )
        call(
            "PATCH",
            "/students/" + case["case"]["student_id"],
            operator,
            json=dict(
                expected_version=1,
                patch=dict(submitted_apaar_id=manifest["correct_to"]),
                reason="Corrected the test identifier from the synthetic manifest.",
            ),
        )
        case = call("GET", "/cases/" + cases[0]["id"], officer)
    if case["case"]["status"] != "APPROVED":
        call(
            "POST",
            "/cases/" + cases[0]["id"] + "/decisions",
            officer,
            json=dict(
                expected_version=case["case"]["version_no"],
                action="APPROVE",
                reason="Rechecked the corrected synthetic identifier; all local checks pass.",
                requested_fields=[],
            ),
        )
    dashboard = call("GET", "/dashboard", operator)
    assert tuple(dashboard[k] for k in ["total", "clean", "flagged", "incomplete", "pending_reviews"]) == (
        10000,
        9881,
        109,
        10,
        119,
    ), dashboard
    first = call("GET", "/students/search?q=Riya%20Sharma", operator)
    second = call("GET", "/students/search?q=Riya%20Sharma", operator)
    assert first["total"] == second["total"] == 1 and second["cache"] == "HIT"
    sid = manifest["showcase_student_id"]
    passport = call("GET", "/students/" + sid, student)
    assert passport["cgpa"] == 8.42 and passport["trust"]["score"] == 91
    guidance = call(
        "POST", "/students/" + sid + "/career", student, json=dict(question="Can I become a Data Scientist?")
    )
    assert guidance["readiness_percent"] == 74
    cert_results = []
    for fixture in ["showcase-genuine.pdf", "showcase-tampered.pdf"]:
        with (ROOT / "fixtures/certificates" / fixture).open("rb") as f:
            uploaded = call(
                "POST",
                "/students/" + sid + "/certificates",
                student,
                files={"file": (fixture, f, "application/pdf")},
                data={"purpose": "TRIAL", "title": "Synthetic trial"},
            )
        result = call("POST", "/certificates/" + uploaded["certificate_id"] + "/verify", student, json={})
        cert_results.append(result)
    assert cert_results[0]["confidence"] == 95 and cert_results[0]["verified"]
    assert cert_results[1]["risk"]["score"] >= 83 and not cert_results[1]["verified"]
    assert call("GET", "/students/" + sid + "/trust", student)["score"] == 91
    assert client.get("/api/v1/students/" + sid, headers=admin).status_code == 404
    other = login("operator.b@example.test")
    assert client.get("/api/v1/students/" + sid, headers=other).status_code == 404
    assert client.get("/api/v1/students/search?institution_id=" + institution, headers=other).status_code == 403
    chain = call("GET", "/audit/verify-chain?institution_id=" + institution, officer)
    assert chain["valid"]
    summary = dict(
        import_report=report,
        dashboard=dashboard,
        search=dict(total=first["total"], miss_ms=first["took_ms"], hit_ms=second["took_ms"]),
        cgpa=passport["cgpa"],
        trust=passport["trust"]["score"],
        readiness=guidance["readiness_percent"],
        genuine_confidence=cert_results[0]["confidence"],
        tampered_risk=cert_results[1]["risk"]["score"],
        chain_valid=chain["valid"],
    )
    (ROOT / "docs/acceptance-results.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    run()
