from io import BytesIO
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, TextStringObject
import pytest
from fastapi import HTTPException
from app.modules.certificates.service import inspect_document, evaluate
from app.modules.imports.service import evaluate as rules, make_indexes
from db.seed.fixtures import pdf_bytes


def test_nested_active_pdf_rejected():
    writer = PdfWriter()
    page = writer.add_blank_page(width=595, height=842)
    page[NameObject("/AA")] = DictionaryObject(
        {
            NameObject("/O"): DictionaryObject(
                {NameObject("/S"): NameObject("/JavaScript"), NameObject("/JS"): TextStringObject("app.alert(1)")}
            )
        }
    )
    buf = BytesIO()
    writer.write(buf)
    with pytest.raises(HTTPException) as caught:
        inspect_document(buf.getvalue())
    assert caught.value.status_code == 422


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


def test_missing_mandatory_and_numeric_edges():
    base = dict(
        full_name="Synthetic Person",
        dob="2004-06-15",
        submitted_enrollment_no="SYN-T-001",
        program_code="PGDM:GENERAL",
        admission_year="2022",
        current_year="2",
        submitted_apaar_id="SYN-0000000000018",
        term_no="6",
        sgpa="10",
        credits="20",
    )
    program = dict(duration_years=2, total_terms=6)
    assert rules(base, program, make_indexes([]))[2] == "PASSED_LOCAL_CHECKS"
    findings, _, quality = rules({**base, "admission_year": None}, program, make_indexes([]))
    assert quality == "INCOMPLETE" and findings[0]["code"] == "MISSING_MANDATORY"
    for change in [dict(term_no="7"), dict(sgpa="10.01"), dict(credits="0")]:
        assert "IMPOSSIBLE_ACADEMIC" in {f["code"] for f in rules({**base, **change}, program, make_indexes([]))[0]}
    assert "INVALID_DOB" in {f["code"] for f in rules({**base, "dob": "2030-01-01"}, program, make_indexes([]))[0]}
    assert "IMPOSSIBLE_ACADEMIC" in {
        f["code"] for f in rules({**base, "admission_year": "oops"}, program, make_indexes([]))[0]
    }


def test_excel_dates_preserve_iso():
    from datetime import datetime
    from openpyxl import Workbook
    from app.modules.imports.service import parse, normalized

    book = Workbook()
    sheet = book.active
    sheet.append(["DOB"])
    sheet.append([datetime(2000, 1, 1)])
    buffer = BytesIO()
    book.save(buffer)
    _, rows = parse(buffer.getvalue(), "dates.xlsx")
    assert str(normalized(rows[0], {"dob": "DOB"})["dob"]) == "2000-01-01"
