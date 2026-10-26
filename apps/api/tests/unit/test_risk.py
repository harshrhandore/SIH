from datetime import date
from app.core.algorithms import certificate_confidence
from app.modules.certificates.fraud import evaluate
from db.seed.fixtures import pdf_bytes


def test_confidence():
    fields = dict(name="Riya Sharma", issuer="Shiksham Demo Academy", date="2026-06-20", credential_id="SYNDS-0018")
    value, _, guard = certificate_confidence(fields, dict(full_name="Riya Sharma", dob=date(2004, 6, 15)), "2026-10-25")
    assert value == 95 and guard
    fields["name"] = None
    assert certificate_confidence(fields, dict(full_name="Riya Sharma", dob=date(2004, 6, 15)), "2026-10-25")[0] < 85


def test_genuine_and_tampered_reason_evidence():
    student = dict(full_name="Riya Sharma", dob="2004-06-15")
    genuine = evaluate(pdf_bytes(), "application/pdf", student)
    assert genuine["confidence"] == 95 and genuine["verified"] and genuine["risk"]["score"] == 0
    fake = evaluate(pdf_bytes(name="Kunal Mehta", tampered=True), "application/pdf", student)
    assert fake["risk"]["score"] == 83
    assert {r["code"] for r in fake["risk"]["reasons"]} == {"NAME_MISMATCH", "PDF_EDIT_METADATA", "PDF_EDITOR_TOOL"}
    assert fake["extracted"]["name"] == "Kunal Mehta"


def test_missing_name_is_review_not_accusation():
    # Deliberately empty explicit name label, rather than inferring from the student.
    report = evaluate(pdf_bytes(name=" "), "application/pdf", dict(full_name="Riya Sharma", dob="2004-06-15"))
    assert not report["verified"] and report["verdict"] in {"NEEDS_REVIEW", "UNREADABLE"}
    assert "NAME_MISMATCH" not in {r["code"] for r in report["risk"]["reasons"]}
