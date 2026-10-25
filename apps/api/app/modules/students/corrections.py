from datetime import date
from psycopg.types.json import Jsonb
from psycopg import sql
from app.core.algorithms import clean, normalized_name, valid_id, academic_cgpas
from app.core.audit import append
from app.core.errors import fail
from app.db.session import one, many
from app.modules.imports.service import evaluate, make_indexes
from app.modules.students.service import epoch, jsonable, trust_for

ALLOWED = {
    "submitted_apaar_id",
    "submitted_enrollment_no",
    "full_name",
    "parent_name",
    "dob",
    "gender",
    "email",
    "program_id",
    "admission_year",
    "current_year",
    "terms",
}


def correct(conn, user, sid, body):
    conn.execute("SELECT pg_advisory_xact_lock(26263,8)")
    before = one(conn, "SELECT * FROM students WHERE id=%s FOR UPDATE", (sid,))
    before_terms = jsonable(
        many(
            conn,
            "SELECT term_no,sgpa,cgpa,credits FROM academic_performance WHERE student_id=%s ORDER BY term_no",
            (sid,),
        )
    )
    if before["version_no"] != body.expected_version:
        fail("VERSION_CONFLICT", 409)
    if not body.patch or set(body.patch) - ALLOWED:
        fail("IMMUTABLE_FIELD")
    merged = {**before, **body.patch}
    term_count = one(conn, "SELECT count(*) AS n FROM enrolments WHERE student_id=%s", (sid,))["n"]
    if "program_id" in body.patch and str(merged["program_id"]) != str(before["program_id"]) and term_count:
        fail("PROGRAM_HAS_TERMS", 409)
    program = (
        one(
            conn,
            "SELECT *,level||':'||branch AS code FROM programs WHERE id=%s AND institution_id=%s",
            (merged["program_id"], before["institution_id"]),
        )
        if merged["program_id"]
        else None
    )
    if merged["program_id"] and not program:
        fail("NOT_FOUND", 404)
    for field in ["submitted_apaar_id", "submitted_enrollment_no", "full_name", "parent_name", "email", "gender"]:
        merged[field] = clean(merged[field])
    for field in ["submitted_apaar_id", "submitted_enrollment_no"]:
        merged[field] = merged[field].upper() if merged[field] else None
    if isinstance(merged["dob"], str):
        try:
            merged["dob"] = date.fromisoformat(merged["dob"])
        except ValueError:
            fail("INVALID_DATE")
    for field, high in [("admission_year", 2026), ("current_year", program["duration_years"] if program else 4)]:
        value = merged[field]
        if value is not None and (
            not isinstance(value, int) or not (1950 if field == "admission_year" else 1) <= value <= high
        ):
            fail("IMPOSSIBLE_ACADEMIC")
    if merged["gender"] and merged["gender"] not in {"MALE", "FEMALE", "OTHER", "UNDISCLOSED"}:
        fail("INVALID_GENDER")
    refs = many(
        conn,
        "SELECT id,submitted_apaar_id,submitted_enrollment_no,full_name,parent_name,dob FROM students WHERE institution_id=%s AND id<>%s",
        (before["institution_id"], sid),
    )
    claims = {
        r["apaar_id"]: str(r["id"])
        for r in many(conn, "SELECT id,apaar_id FROM students WHERE id<>%s AND apaar_id IS NOT NULL", (sid,))
    }
    evaluated = {**merged, "program_code": program["code"] if program else None}
    findings, candidates, quality = evaluate(evaluated, program, make_indexes(refs, claims))
    conn.execute(
        "UPDATE verification_findings SET resolved_at=now() WHERE student_id=%s AND resolved_at IS NULL", (sid,)
    )
    for finding in findings:
        conn.execute(
            "INSERT INTO verification_checks(code,description,severity,version) VALUES (%s,%s,%s,1) ON CONFLICT DO NOTHING",
            (finding["code"], finding["explanation"], finding["severity"]),
        )
        conn.execute(
            "INSERT INTO verification_findings(student_id,check_code,rule_version,student_version,severity,explanation,evidence) VALUES (%s,%s,1,%s,%s,%s,%s)",
            (
                sid,
                finding["code"],
                before["version_no"] + 1,
                finding["severity"],
                finding["explanation"],
                Jsonb(finding["evidence"]),
            ),
        )
    conn.execute(
        "UPDATE duplicate_candidates SET status='DISMISSED' WHERE (student_a=%s OR student_b=%s) AND status='OPEN'",
        (sid, sid),
    )
    for target, kind, score in candidates:
        a, b = sorted([str(sid), str(target)])
        conn.execute(
            "INSERT INTO duplicate_candidates(student_a,student_b,match_type,score,matched_fields) VALUES (%s,%s,%s,%s,%s) ON CONFLICT(student_a,student_b) DO UPDATE SET status='OPEN',score=EXCLUDED.score,matched_fields=EXCLUDED.matched_fields",
            (a, b, kind, round(score, 2), Jsonb({"source": str(sid), "target": str(target)})),
        )
    merged["apaar_id"] = (
        merged["submitted_apaar_id"]
        if valid_id(merged["submitted_apaar_id"]) and not any(f["code"] == "DUPLICATE_APAAR" for f in findings)
        else None
    )
    merged["enrollment_no"] = (
        merged["submitted_enrollment_no"]
        if not any(f["code"] in {"ENROLLMENT_CONFLICT", "RECORD_ALREADY_EXISTS"} for f in findings)
        else None
    )
    merged["normalized_name"] = normalized_name(merged["full_name"])
    from unidecode import unidecode

    merged["transliterated_name"] = unidecode(merged["normalized_name"])
    merged["data_quality_status"] = quality
    columns = list(ALLOWED - {"terms"}) + [
        "apaar_id",
        "enrollment_no",
        "normalized_name",
        "transliterated_name",
        "data_quality_status",
    ]
    statement = sql.SQL(
        "UPDATE students SET {} ,version_no=version_no+1,updated_at=now() WHERE id=%s RETURNING *"
    ).format(sql.SQL(",").join(sql.SQL("{}=%s").format(sql.Identifier(c)) for c in columns))
    student = one(conn, statement, tuple(merged[c] for c in columns) + (sid,))
    if "terms" in body.patch:
        terms = body.patch["terms"]
        if not program or not isinstance(terms, list) or len({t.get("term_no") for t in terms}) != len(terms):
            fail("INVALID_TERMS")
        conn.execute(
            "DELETE FROM performance_subjects WHERE performance_id IN (SELECT id FROM academic_performance WHERE student_id=%s)",
            (sid,),
        )
        conn.execute("DELETE FROM academic_performance WHERE student_id=%s", (sid,))
        conn.execute("DELETE FROM enrolments WHERE student_id=%s", (sid,))
        ordered = sorted(terms, key=lambda t: t["term_no"])
        cgpas = academic_cgpas([(t["sgpa"], t["credits"]) for t in ordered])
        for term, cgpa in zip(ordered, cgpas):
            if (
                not 1 <= term["term_no"] <= program["total_terms"]
                or not 0 <= float(term["sgpa"]) <= 10
                or not 0 < float(term["credits"]) <= 60
            ):
                fail("IMPOSSIBLE_ACADEMIC")
            year = merged["admission_year"] + (term["term_no"] - 1) // (2 if program["term_type"] == "SEMESTER" else 3)
            eid = one(
                conn,
                "INSERT INTO enrolments(student_id,program_id,academic_year,term_no,term_type) VALUES (%s,%s,%s,%s,%s) RETURNING id",
                (sid, program["id"], year, term["term_no"], program["term_type"]),
            )["id"]
            conn.execute(
                "INSERT INTO academic_performance(student_id,enrolment_id,academic_year,term_no,term_type,credits,sgpa,cgpa) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (sid, eid, year, term["term_no"], program["term_type"], term["credits"], term["sgpa"], cgpa),
            )
    diff = {
        field: {"old": jsonable(before.get(field)), "new": jsonable(merged.get(field))}
        for field in body.patch
        if field != "terms" and jsonable(before.get(field)) != jsonable(merged.get(field))
    }
    if "terms" in body.patch:
        diff["terms"] = {
            "old": before_terms,
            "new": jsonable(
                many(
                    conn,
                    "SELECT term_no,sgpa,cgpa,credits FROM academic_performance WHERE student_id=%s ORDER BY term_no",
                    (sid,),
                )
            ),
        }
    snapshot = {
        **jsonable(student),
        "terms": jsonable(
            many(
                conn,
                "SELECT term_no,sgpa,cgpa,credits FROM academic_performance WHERE student_id=%s ORDER BY term_no",
                (sid,),
            )
        ),
    }
    conn.execute(
        "INSERT INTO record_versions(student_id,version_no,snapshot,changed_fields,changed_by,reason) VALUES (%s,%s,%s,%s,%s,%s)",
        (sid, student["version_no"], Jsonb(snapshot), Jsonb(diff), user["id"], body.reason),
    )
    case = one(conn, "SELECT * FROM review_cases WHERE student_id=%s AND status<>'APPROVED' FOR UPDATE", (sid,))
    if case:
        conn.execute(
            "UPDATE review_cases SET status=CASE WHEN status='CORRECTION_REQUESTED' THEN 'OPEN' ELSE status END,version_no=version_no+1,updated_at=now() WHERE id=%s",
            (case["id"],),
        )
    elif findings:
        conn.execute("INSERT INTO review_cases(student_id,opened_reason) VALUES (%s,%s)", (sid, findings[0]["code"]))
    append(
        conn,
        student["institution_id"],
        user["id"],
        "STUDENT_CORRECTED",
        "student",
        sid,
        body.reason,
        {"changes": diff, "student_version": student["version_no"]},
        sid,
    )
    trust_for(conn, student)
    return dict(
        student=student,
        version_no=student["version_no"],
        changed_fields=diff,
        findings=findings,
        case_status="OPEN" if case or findings else None,
        data_epoch=epoch(conn, student["institution_id"]),
    )
