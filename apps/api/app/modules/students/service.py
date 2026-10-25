from app.modules.trust.service import trust_for as trust_for
from app.modules.career.repository import evidenced_skills as evidenced_skills
from app.core.serialization import jsonable as jsonable
from app.db.session import one, many


def epoch(conn, institution):
    return one(
        conn,
        "UPDATE institution_epochs SET data_epoch=data_epoch+1,updated_at=now() WHERE institution_id=%s RETURNING data_epoch",
        (institution,),
    )["data_epoch"]


def passport(conn, student):
    sid = student["id"]
    result = dict(
        profile={
            k: student.get(k)
            for k in [
                "id",
                "full_name",
                "apaar_id",
                "institution_id",
                "institution_name",
                "program",
                "branch",
                "current_year",
                "admission_year",
                "data_quality_status",
                "external_status",
                "version_no",
                "total_terms",
                "term_type",
            ]
        },
        dob=student["dob"],
        email=student["email"],
        officially_verified=False,
    )
    result["terms"] = many(
        conn,
        "SELECT term_no,term_type,academic_year,sgpa,cgpa,credits FROM academic_performance WHERE student_id=%s ORDER BY term_no",
        (sid,),
    )
    result["cgpa"] = result["terms"][-1]["cgpa"] if result["terms"] else None
    for table in ["projects", "internships", "achievements", "scholarships"]:
        result[table] = many(conn, f"SELECT * FROM {table} WHERE student_id=%s ORDER BY id", (sid,))
    result["certificates"] = many(
        conn,
        "SELECT id,title,issuer,issued_on,credential_id,purpose,acceptance_status FROM certificates WHERE student_id=%s ORDER BY created_at",
        (sid,),
    )
    result["skills"] = many(
        conn,
        "SELECT sk.code,sk.label,s.proficiency,s.evidence_kind,s.evidence_id FROM student_skills s JOIN skills sk ON sk.id=s.skill_id WHERE student_id=%s",
        (sid,),
    )
    result["trust"] = trust_for(conn, student)
    result["latest_case"] = one(
        conn, "SELECT * FROM review_cases WHERE student_id=%s ORDER BY created_at DESC LIMIT 1", (sid,)
    )
    return result


def dashboard(conn, institution):
    result = one(
        conn,
        "SELECT count(*)::int AS total,count(*) FILTER(WHERE data_quality_status='PASSED_LOCAL_CHECKS')::int AS clean,count(*) FILTER(WHERE data_quality_status='FLAGGED_FOR_REVIEW')::int AS flagged,count(*) FILTER(WHERE data_quality_status='INCOMPLETE')::int AS incomplete FROM students WHERE institution_id=%s",
        (institution,),
    )
    inst = one(conn, "SELECT expected_records,name FROM institutions WHERE id=%s", (institution,))
    result["institution_name"] = inst["name"]
    result["submission_percent"] = round(min(100, 100 * result["total"] / inst["expected_records"]), 2)
    result["missing_records"] = max(0, inst["expected_records"] - result["total"])
    result.update(
        one(
            conn,
            "SELECT count(*) FILTER(WHERE c.status<>'APPROVED')::int AS pending_reviews,count(*) FILTER(WHERE c.status='CORRECTION_REQUESTED')::int AS pending_corrections FROM review_cases c JOIN students s ON s.id=c.student_id WHERE s.institution_id=%s",
            (institution,),
        )
    )
    result["recent_imports"] = many(
        conn,
        "SELECT id,filename,status,total_rows,clean_rows,flagged_rows,incomplete_rows,created_at FROM import_batches WHERE institution_id=%s ORDER BY created_at DESC LIMIT 5",
        (institution,),
    )
    result["data_epoch"] = one(
        conn, "SELECT data_epoch FROM institution_epochs WHERE institution_id=%s", (institution,)
    )["data_epoch"]
    return result
