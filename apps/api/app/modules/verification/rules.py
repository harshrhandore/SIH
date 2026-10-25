"""Deterministic local record checks and ordered, non-merging findings."""

import re
from datetime import date
from typing import Any
from app.core.identifiers import valid_id
from app.modules.verification.matching import name_match, normalized_name, possible_match
from app.modules.imports.mapping import MANDATORY

PRIORITY = [
    "MISSING_MANDATORY",
    "MISSING_APAAR",
    "INVALID_APAAR",
    "DUPLICATE_APAAR",
    "NAME_INCONSISTENCY",
    "ENROLLMENT_CONFLICT",
    "IMPOSSIBLE_ACADEMIC",
    "POSSIBLE_DUPLICATE",
    "RECORD_ALREADY_EXISTS",
    "INVALID_DOB",
    "INVALID_EMAIL",
]

MESSAGES = {
    "MISSING_MANDATORY": "A mandatory field is missing.",
    "MISSING_APAAR": "Synthetic ID is missing.",
    "INVALID_APAAR": "Synthetic ID format/check digit is invalid.",
    "DUPLICATE_APAAR": "Synthetic ID is already claimed.",
    "NAME_INCONSISTENCY": "Submitted name differs from the reference enrollment.",
    "ENROLLMENT_CONFLICT": "Enrollment conflicts with an existing record.",
    "IMPOSSIBLE_ACADEMIC": "Academic values are outside program bounds.",
    "POSSIBLE_DUPLICATE": "Name and corroborating details suggest a possible duplicate.",
    "RECORD_ALREADY_EXISTS": "Matching source record already exists.",
    "INVALID_DOB": "Date of birth is future or outside the permitted admission age range.",
    "INVALID_EMAIL": "Email syntax is invalid.",
}


def evaluate(row, program, indexes):
    ids, enrollments, dobs = indexes
    findings: list[dict[str, Any]] = []
    candidates = []

    def add(code, field="record", value=None, secondary=False):
        if any(f["code"] == code for f in findings):
            return
        findings.append(
            dict(
                code=code,
                field=field,
                severity="WARNING"
                if code in {"NAME_INCONSISTENCY", "POSSIBLE_DUPLICATE", "RECORD_ALREADY_EXISTS"}
                else "ERROR",
                explanation=MESSAGES[code],
                is_primary=not secondary,
                evidence=dict(
                    field=field,
                    submitted_value=str(value) if value is not None else None,
                    expected=MESSAGES[code],
                    related_student_ids=[],
                ),
            )
        )

    missing = [k for k in MANDATORY if not row.get(k)]
    if missing:
        add("MISSING_MANDATORY", ",".join(missing))
    if row.get("dob"):
        dob = date.fromisoformat(str(row["dob"]))
        try:
            admission_year = int(row.get("admission_year") or 2026)
            admission = date(admission_year if 1950 <= admission_year <= 2100 else 2026, 7, 1)
        except (ValueError, TypeError):
            admission = date(2026, 7, 1)
        age = admission.year - dob.year - ((admission.month, admission.day) < (dob.month, dob.day))
        if dob > date(2026, 10, 25) or not 14 <= age <= 80:
            add("INVALID_DOB", "dob", dob)
    if row.get("email") and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", row["email"]):
        add("INVALID_EMAIL", "email", row["email"])
    identifier = row.get("submitted_apaar_id")
    if not identifier:
        add("MISSING_APAAR", "submitted_apaar_id")
    elif not valid_id(identifier):
        add("INVALID_APAAR", "submitted_apaar_id", identifier)
    elif identifier in ids and str(ids[identifier]["id"]) != str(row.get("id")):
        add("DUPLICATE_APAAR", "submitted_apaar_id", identifier)
        candidates.append((ids[identifier]["id"], "EXACT", 100))
    enrollment = row.get("submitted_enrollment_no")
    existing = enrollments.get(enrollment)
    if existing and str(existing["id"]) != str(row.get("id")):
        same_dob = str(row.get("dob")) == str(existing.get("dob"))
        n, guard = name_match(row.get("full_name"), existing.get("full_name"))
        if (
            same_dob
            and normalized_name(row.get("full_name")) != normalized_name(existing.get("full_name"))
            and (70 <= n < 95 or not guard)
        ):
            add("NAME_INCONSISTENCY", "full_name", row.get("full_name"))
            add("ENROLLMENT_CONFLICT", "submitted_enrollment_no", enrollment, True)
        elif not same_dob or normalized_name(row.get("full_name")) != normalized_name(existing.get("full_name")):
            add("ENROLLMENT_CONFLICT", "submitted_enrollment_no", enrollment)
        else:
            add("RECORD_ALREADY_EXISTS", "submitted_enrollment_no", enrollment)
        candidates.append((existing["id"], "EXACT", 100))
    impossible = False
    try:
        if not program:
            impossible = True
        else:
            if row.get("current_year") and not 1 <= int(row["current_year"]) <= program["duration_years"]:
                impossible = True
            if row.get("admission_year") and not 1950 <= int(row["admission_year"]) <= 2026:
                impossible = True
            for field in ["sgpa", "cgpa"]:
                if row.get(field) and not 0 <= float(row[field]) <= 10:
                    impossible = True
            if row.get("term_no") and not 1 <= int(row["term_no"]) <= program["total_terms"]:
                impossible = True
            if row.get("credits") and not 0 < float(row["credits"]) <= 60:
                impossible = True
    except (ValueError, TypeError):
        impossible = True
    if impossible:
        add("IMPOSSIBLE_ACADEMIC")
    if not missing and not candidates:
        for candidate in dobs.get(str(row.get("dob")), [])[:20]:
            if str(candidate["id"]) == str(row.get("id")):
                continue
            score, matched = possible_match(row, candidate)
            if matched:
                add("POSSIBLE_DUPLICATE", "full_name", row.get("full_name"))
                candidates.append((candidate["id"], "POSSIBLE", score))
    findings.sort(key=lambda f: PRIORITY.index(f["code"]))
    for i, f in enumerate(findings):
        f["is_primary"] = i == 0
    quality = "INCOMPLETE" if missing else "FLAGGED_FOR_REVIEW" if findings else "PASSED_LOCAL_CHECKS"
    return findings, candidates, quality
