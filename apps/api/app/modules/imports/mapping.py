"""Canonical column mapping and date/value normalization."""

from datetime import date, datetime
from app.core.algorithms import clean

ALIASES = {
    "submitted_apaar_id": "APAAR ID",
    "submitted_enrollment_no": "Enrollment No",
    "full_name": "Student Name",
    "dob": "DOB",
    "parent_name": "Parent Name",
    "program_code": "Program",
    "admission_year": "Admission Year",
    "current_year": "Year",
    "term_no": "Semester",
    "sgpa": "SGPA",
    "credits": "Credits",
    "email": "Email",
    "gender": "Gender",
}

MANDATORY = {"submitted_enrollment_no", "full_name", "dob", "program_code", "admission_year", "current_year"}


def normalized(raw, mapping, date_format="DD/MM/YYYY"):
    out = {k: clean(raw.get(column)) for k, column in mapping.items()}
    out["submitted_apaar_id"] = (out.get("submitted_apaar_id") or "").upper() or None
    out["submitted_enrollment_no"] = " ".join((out.get("submitted_enrollment_no") or "").upper().split()) or None
    try:
        value = out.get("dob")
        out["dob"] = (
            date.fromisoformat(value)
            if value and len(value) == 10 and value[4] == "-"
            else datetime.strptime(value, "%d/%m/%Y").date()
            if value and date_format == "DD/MM/YYYY"
            else None
        )
    except (ValueError, TypeError):
        out["dob"] = None
    return out
