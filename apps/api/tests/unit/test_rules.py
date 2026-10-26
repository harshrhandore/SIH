from io import BytesIO
from app.modules.verification.rules import evaluate as rules
from app.modules.verification.matching import make_indexes


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
