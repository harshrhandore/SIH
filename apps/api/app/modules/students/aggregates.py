from app.db.session import one
from app.core.errors import fail


def program_dashboard(conn, program_id, institution_id=None):
    program = one(
        conn,
        "SELECT p.*,e.expected_records FROM programs p JOIN program_expected_records e ON e.program_id=p.id WHERE p.id=%s",
        (program_id,),
    )
    if not program or institution_id and program["institution_id"] != institution_id:
        fail("INVALID_FILTER_COMBINATION")
    result = one(
        conn,
        "SELECT count(*)::int AS total,count(*) FILTER(WHERE data_quality_status='PASSED_LOCAL_CHECKS')::int AS clean,count(*) FILTER(WHERE data_quality_status='FLAGGED_FOR_REVIEW')::int AS flagged,count(*) FILTER(WHERE data_quality_status='INCOMPLETE')::int AS incomplete,count(*) FILTER(WHERE external_status='EXTERNAL_VERIFICATION_PENDING')::int AS external_pending FROM students WHERE program_id=%s",
        (program_id,),
    )
    result["institution_id"] = program["institution_id"]
    result["program_id"] = program_id
    result["submission_percent"] = round(min(100, 100 * result["total"] / program["expected_records"]), 2)
    result["missing_records"] = max(0, program["expected_records"] - result["total"])
    result["pending_reviews"] = one(
        conn,
        "SELECT count(*)::int AS n FROM review_cases c JOIN students s ON s.id=c.student_id WHERE s.program_id=%s AND c.status<>'APPROVED'",
        (program_id,),
    )["n"]
    return result
