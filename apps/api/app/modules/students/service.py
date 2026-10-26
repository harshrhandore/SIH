from app.modules.students import repository
from app.modules.trust.service import trust_for as trust_for
from app.modules.career.repository import evidenced_skills as evidenced_skills
from app.core.serialization import jsonable as jsonable
from app.db.session import one, many
from app.core.http import listing, pagination, idem
from time import perf_counter
from uuid import UUID
from fastapi import Request
from unidecode import unidecode
from app.settings import settings
from app.db.session import connect
from app.core.errors import fail
from app.core.security import allow, institution_scope, student_scope, reason
from app.core.cache import cache, preferences
from app.core.algorithms import normalized_name, valid_id
from app.modules.students.schemas import Patch


def epoch(conn, institution):
    return repository.epoch_institution_epochs(conn, (institution,))["data_epoch"]


def passport(conn, student, include_evidence=True):
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
    result["terms"] = repository.passport_academic_performance(conn, (sid,))
    result["cgpa"] = result["terms"][-1]["cgpa"] if result["terms"] else None
    if include_evidence:
        for section in ["projects", "internships", "achievements", "scholarships", "certificates", "skills"]:
            result[section] = repository.evidence(conn, sid, section)
    result["trust"] = trust_for(conn, student)
    result["latest_case"] = repository.passport_review_cases(conn, (sid,))
    return result


def dashboard(conn, institution):
    result = repository.dashboard_students(conn, (institution,))
    inst = repository.dashboard_institutions(conn, (institution,))
    result["institution_name"] = inst["name"]
    result["submission_percent"] = round(min(100, 100 * result["total"] / inst["expected_records"]), 2)
    result["missing_records"] = max(0, inst["expected_records"] - result["total"])
    result.update(repository.dashboard_review_cases(conn, (institution,)))
    result["recent_imports"] = repository.dashboard_import_batches(conn, (institution,))
    result["data_epoch"] = repository.dashboard_institution_epochs(conn, (institution,))["data_epoch"]
    return result


def get_dashboard(institution_id: UUID | None = None, user=None):
    allow(user, "OPERATOR", "OFFICER")
    ids = institution_scope(user, institution_id)
    if not institution_id and user["role_code"] == "OFFICER":
        fail("INSTITUTION_REQUIRED")
    with connect() as conn:
        return dashboard(conn, ids[0])


def search(
    request: Request,
    q: str = "",
    institution_id: UUID | None = None,
    program_id: UUID | None = None,
    branch: str | None = None,
    current_year: int | None = None,
    quality: str | None = None,
    page: int = 1,
    page_size: int = 25,
    sort: str = "name",
    user=None,
):
    allow(user, "OPERATOR", "OFFICER")
    offset = pagination(page, page_size)
    ids = institution_scope(user, institution_id)
    if len(q) > 100 or (q and len(q.strip()) < 2):
        fail("QUERY_TOO_SHORT")
    if sort not in {"name", "admission_year"}:
        fail("UNKNOWN_SORT")
    q = q.strip()
    branch = branch or None
    quality_aliases = {
        "total": None,
        "clean": "PASSED_LOCAL_CHECKS",
        "flagged": "FLAGGED_FOR_REVIEW",
        "incomplete": "INCOMPLETE",
        "PASSED_LOCAL_CHECKS": "PASSED_LOCAL_CHECKS",
        "FLAGGED_FOR_REVIEW": "FLAGGED_FOR_REVIEW",
        "INCOMPLETE": "INCOMPLETE",
    }
    if quality is not None and quality not in quality_aliases:
        fail("UNKNOWN_QUALITY_FILTER")
    quality = quality_aliases.get(quality) if quality else None
    with connect() as conn:
        data_epoch = repository.search_institution_epochs(conn, (ids,))["e"]
        key = (
            str(user["id"]),
            user["role_code"],
            tuple((str(i) for i in ids)),
            data_epoch,
            q,
            branch,
            current_year,
            str(program_id),
            page,
            page_size,
            sort,
            quality,
        )
        result = (
            None
            if settings.demo_controls_enabled
            and (request.headers.get("x-demo-cache") == "bypass" or preferences.get(str(user["sid"])) is False)
            else cache.get(key)
        )
        hit = bool(result)
        if result is None:
            escaped = (normalized_name(q) or q.casefold()).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            transliterated = unidecode(escaped)
            predicate = "s.institution_id=ANY(%s::uuid[]) AND (%s='' OR s.normalized_name LIKE %s OR s.transliterated_name LIKE %s OR s.apaar_id=%s OR s.submitted_enrollment_no=%s) AND (%s::uuid IS NULL OR s.program_id=%s) AND (%s::text IS NULL OR p.branch=%s) AND (%s::int IS NULL OR s.current_year=%s)"
            params: tuple = (
                ids,
                q,
                "%" + escaped + "%",
                "%" + transliterated + "%",
                q.upper(),
                q.upper(),
                program_id,
                program_id,
                branch,
                branch,
                current_year,
                current_year,
            )
            predicate += " AND (%s::text IS NULL OR s.data_quality_status=%s)"
            params += (quality, quality)
            total = one(
                conn,
                "SELECT count(*)::int AS n FROM students s LEFT JOIN programs p ON p.id=s.program_id WHERE "
                + predicate,
                params,
            )["n"]
            order = "s.normalized_name ASC,s.id ASC" if sort == "name" else "s.admission_year DESC,s.id ASC"
            rows = many(
                conn,
                "SELECT s.id,s.full_name,s.apaar_id,s.institution_id,p.name AS program,p.branch,s.current_year,s.data_quality_status,s.external_status,s.version_no FROM students s LEFT JOIN programs p ON p.id=s.program_id WHERE "
                + predicate
                + " ORDER BY "
                + order
                + " LIMIT %s OFFSET %s",
                params + (page_size, offset),
            )
            result = jsonable(listing(rows, total, page, page_size, data_epoch=data_epoch))
            cache.put(key, result)
    return {
        **result,
        "cache": "HIT" if hit else "MISS",
        "took_ms": round((perf_counter() - request.state.started) * 1000, 3),
    }


def student(student_id: UUID, request: Request, user=None, include_evidence=True):
    with connect() as conn:
        return passport(conn, student_scope(conn, user, student_id, request), include_evidence)


def student_evidence(student_id, section, request, user):
    with connect() as conn:
        student_scope(conn, user, student_id, request)
        return dict(items=repository.evidence(conn, student_id, section))


def student_by_id(apaar_id: str, request: Request, user=None):
    if not valid_id(apaar_id):
        fail("INVALID_SYNTHETIC_ID")
    with connect() as conn:
        row = repository.student_by_id_students(conn, (apaar_id,))
        if not row:
            fail("NOT_FOUND", 404)
        return passport(conn, student_scope(conn, user, row["id"], request))


def versions(student_id: UUID, request: Request, page: int = 1, page_size: int = 25, user=None):
    offset = pagination(page, page_size)
    with connect() as conn:
        student_scope(conn, user, student_id, request)
        rows = repository.versions_record_versions(conn, (student_id, page_size, offset))
        return listing(rows, repository.versions_record_versions_2(conn, (student_id,))["n"], page, page_size)


def patch_student(student_id: UUID, body: Patch, request: Request, user=None):
    allow(user, "OPERATOR")
    reason(body.reason)
    from app.modules.students.corrections import correct

    with connect() as conn:
        student_scope(conn, user, student_id, request)
        return idem(conn, user, request, body.model_dump(), lambda key: correct(conn, user, student_id, body))
