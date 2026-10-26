"""Fixed SQL statements for reviews transactions."""

from app.db.session import one, many


def source_snapshot(conn, student_id):
    return one(
        conn,
        "SELECT r.normalized_data,b.reference_snapshot,b.filename FROM import_rows r JOIN import_batches b ON b.id=r.batch_id WHERE r.student_id=%s ORDER BY b.created_at DESC LIMIT 1",
        (student_id,),
    )


def case_detail_review_cases(conn, params=()):
    return one(
        conn,
        "SELECT c.*,s.institution_id,s.full_name,s.submitted_apaar_id,i.name AS institution_name FROM review_cases c JOIN students s ON s.id=c.student_id JOIN institutions i ON i.id=s.institution_id WHERE c.id=%s",
        params,
    )


def case_detail_verification_findings(conn, params=()):
    return many(
        conn,
        "SELECT check_code AS code,severity,explanation,evidence FROM verification_findings WHERE student_id=%s AND resolved_at IS NULL",
        params,
    )


def case_detail_duplicate_candidates(conn, params=()):
    return many(
        conn,
        "SELECT id,match_type,score,status FROM duplicate_candidates WHERE (student_a=%s OR student_b=%s) AND status='OPEN'",
        params,
    )


def case_detail_record_versions(conn, params=()):
    return many(
        conn,
        "SELECT version_no,changed_fields,reason,created_at FROM record_versions WHERE student_id=%s ORDER BY version_no",
        params,
    )


def case_detail_review_decisions(conn, params=()):
    return many(
        conn, "SELECT action,reason,created_at FROM review_decisions WHERE case_id=%s ORDER BY created_at", params
    )


def case_access_review_cases(conn, params=()):
    return one(
        conn,
        "SELECT c.*,s.institution_id FROM review_cases c JOIN students s ON s.id=c.student_id WHERE c.id=%s FOR UPDATE OF c",
        params,
    )


def case_access_review_decisions(conn, params=()):
    return conn.execute(
        "INSERT INTO review_decisions(case_id,reviewer_id,action,reason,case_version) VALUES (%s,%s,'ACCESS_ESCALATED',%s,%s)",
        params,
    )


def work_review_cases(conn, params=()):
    return one(conn, "SELECT * FROM review_cases WHERE id=%s FOR UPDATE", params)


def work_verification_findings(conn, params=()):
    return one(conn, "SELECT 1 FROM verification_findings WHERE student_id=%s AND resolved_at IS NULL LIMIT 1", params)


def work_duplicate_candidates(conn, params=()):
    return one(
        conn,
        "SELECT 1 FROM duplicate_candidates WHERE (student_a=%s OR student_b=%s) AND status='OPEN' LIMIT 1",
        params,
    )


def work_review_cases_2(conn, params=()):
    return one(
        conn,
        "UPDATE review_cases SET status=%s,version_no=version_no+1,updated_at=now(),escalated_at=CASE WHEN %s='ESCALATED' THEN now() ELSE escalated_at END WHERE id=%s RETURNING *",
        params,
    )


def work_review_decisions(conn, params=()):
    return one(
        conn,
        "INSERT INTO review_decisions(case_id,reviewer_id,action,reason,case_version) VALUES (%s,%s,%s,%s,%s) RETURNING id",
        params,
    )


def work_review_cases_3(conn, params=()):
    return one(conn, "SELECT * FROM review_cases WHERE id=%s FOR UPDATE", params)


def work_duplicate_candidates_2(conn, params=()):
    return one(conn, "SELECT * FROM duplicate_candidates WHERE id=%s FOR UPDATE", params)


def work_duplicate_candidates_3(conn, params=()):
    return conn.execute("UPDATE duplicate_candidates SET status=%s WHERE id=%s", params)


def work_review_cases_4(conn, params=()):
    return conn.execute("UPDATE review_cases SET version_no=version_no+1,updated_at=now() WHERE id=%s", params)


def work_review_decisions_2(conn, params=()):
    return conn.execute(
        "INSERT INTO review_decisions(case_id,reviewer_id,action,reason,case_version) VALUES (%s,%s,%s,%s,%s)", params
    )
