"""Fixed SQL for students transactions."""

from app.db.session import one, many
from app.core.errors import fail


def evidence(conn, student_id, section):
    if section == "certificates":
        return passport_certificates(conn, (student_id,))
    if section == "skills":
        return passport_student_skills(conn, (student_id,))
    queries = {
        "projects": "SELECT * FROM projects WHERE student_id=%s ORDER BY id",
        "internships": "SELECT * FROM internships WHERE student_id=%s ORDER BY id",
        "achievements": "SELECT * FROM achievements WHERE student_id=%s ORDER BY id",
        "scholarships": "SELECT * FROM scholarships WHERE student_id=%s ORDER BY id",
    }
    if section not in queries:
        fail("NOT_FOUND", 404)
    return many(conn, queries[section], (student_id,))


def epoch_institution_epochs(conn, params=()):
    return one(
        conn,
        "UPDATE institution_epochs SET data_epoch=data_epoch+1,updated_at=now() WHERE institution_id=%s RETURNING data_epoch",
        params,
    )


def passport_academic_performance(conn, params=()):
    return many(
        conn,
        "SELECT term_no,term_type,academic_year,sgpa,cgpa,credits FROM academic_performance WHERE student_id=%s ORDER BY term_no",
        params,
    )


def passport_certificates(conn, params=()):
    return many(
        conn,
        "SELECT id,title,issuer,issued_on,credential_id,purpose,acceptance_status FROM certificates WHERE student_id=%s ORDER BY created_at",
        params,
    )


def passport_student_skills(conn, params=()):
    return many(
        conn,
        "SELECT sk.code,sk.label,s.proficiency,s.evidence_kind,s.evidence_id FROM student_skills s JOIN skills sk ON sk.id=s.skill_id WHERE student_id=%s",
        params,
    )


def passport_review_cases(conn, params=()):
    return one(conn, "SELECT * FROM review_cases WHERE student_id=%s ORDER BY created_at DESC LIMIT 1", params)


def dashboard_students(conn, params=()):
    return one(
        conn,
        "SELECT count(*)::int AS total,count(*) FILTER(WHERE data_quality_status='PASSED_LOCAL_CHECKS')::int AS clean,count(*) FILTER(WHERE data_quality_status='FLAGGED_FOR_REVIEW')::int AS flagged,count(*) FILTER(WHERE data_quality_status='INCOMPLETE')::int AS incomplete FROM students WHERE institution_id=%s",
        params,
    )


def dashboard_institutions(conn, params=()):
    return one(conn, "SELECT expected_records,name FROM institutions WHERE id=%s", params)


def dashboard_review_cases(conn, params=()):
    return one(
        conn,
        "SELECT count(*) FILTER(WHERE c.status<>'APPROVED')::int AS pending_reviews,count(*) FILTER(WHERE c.status='CORRECTION_REQUESTED')::int AS pending_corrections FROM review_cases c JOIN students s ON s.id=c.student_id WHERE s.institution_id=%s",
        params,
    )


def dashboard_import_batches(conn, params=()):
    return many(
        conn,
        "SELECT id,filename,status,total_rows,clean_rows,flagged_rows,incomplete_rows,created_at FROM import_batches WHERE institution_id=%s ORDER BY created_at DESC LIMIT 5",
        params,
    )


def dashboard_institution_epochs(conn, params=()):
    return one(conn, "SELECT data_epoch FROM institution_epochs WHERE institution_id=%s", params)


def search_institution_epochs(conn, params=()):
    return one(
        conn,
        "SELECT coalesce(sum(data_epoch),0) AS e FROM institution_epochs WHERE institution_id=ANY(%s::uuid[])",
        params,
    )


def student_by_id_students(conn, params=()):
    return one(conn, "SELECT id FROM students WHERE apaar_id=%s", params)


def versions_record_versions(conn, params=()):
    return many(
        conn,
        "SELECT version_no,changed_fields,reason,created_at,changed_by FROM record_versions WHERE student_id=%s ORDER BY version_no DESC LIMIT %s OFFSET %s",
        params,
    )


def versions_record_versions_2(conn, params=()):
    return one(conn, "SELECT count(*) AS n FROM record_versions WHERE student_id=%s", params)
