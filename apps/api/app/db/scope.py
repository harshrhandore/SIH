"""Database-backed institution, ownership and case-grant authorization."""

import jwt
from app.core.errors import fail
from app.db.session import one
from app.settings import settings


def allow(user, *roles):
    if user["role_code"] not in roles:
        fail("CAPABILITY_FORBIDDEN", 403)


def scope_ids(user):
    if user["role_code"] in {"OPERATOR", "STUDENT"}:
        return [user["institution_id"]]
    return user["assigned_institutions"] if user["role_code"] == "OFFICER" else []


def institution_scope(user, institution_id=None, admin=False):
    if admin and user["role_code"] == "ADMIN":
        return [institution_id] if institution_id else None
    ids = scope_ids(user)
    if institution_id and str(institution_id) not in {str(i) for i in ids}:
        fail("SCOPE_FILTER_FORBIDDEN", 403)
    return [institution_id] if institution_id else ids


def student_scope(conn, user, student_id, request=None):
    student = one(
        conn,
        "SELECT s.*,p.name AS program,p.branch,p.total_terms,p.duration_years,p.term_type,i.name AS institution_name FROM students s LEFT JOIN programs p ON p.id=s.program_id JOIN institutions i ON i.id=s.institution_id WHERE s.id=%s",
        (student_id,),
    )
    if not student:
        fail("NOT_FOUND", 404)
    role = user["role_code"]
    permitted = role in {"OPERATOR", "OFFICER"} and student["institution_id"] in scope_ids(user)
    permitted = permitted or role == "STUDENT" and student["id"] == user["student_id"]
    if role == "ADMIN" and request:
        try:
            grant = jwt.decode(
                request.headers.get("x-case-access", ""),
                settings.grant_secret,
                algorithms=["HS256"],
                audience="case-access",
            )
            case = one(conn, "SELECT * FROM review_cases WHERE id=%s AND status='ESCALATED'", (grant["case_id"],))
            permitted = bool(
                case
                and grant["sub"] == str(user["id"])
                and grant["student_id"] == str(student["id"])
                and grant["version"] == case["version_no"]
            )
        except (jwt.InvalidTokenError, KeyError):
            permitted = False
    if not permitted:
        fail("NOT_FOUND", 404)
    return student
