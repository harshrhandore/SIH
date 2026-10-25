"""Students HTTP operations."""

from app.core.http import listing, pagination, idem
from time import perf_counter
from uuid import UUID
from fastapi import Request, Depends
from unidecode import unidecode
from app.settings import settings
from app.db.session import connect, one, many
from app.core.errors import fail
from app.core.security import authenticated, allow, institution_scope, student_scope, reason
from app.core.cache import cache, preferences
from app.core.algorithms import normalized_name, valid_id
from app.modules.students.service import passport, dashboard, jsonable
from app.schemas import SearchResponse
from app.modules.students.schemas import Patch
from fastapi import APIRouter

router = APIRouter(tags=["students"])


@router.get("/dashboard")
def get_dashboard(institution_id: UUID | None = None, user=Depends(authenticated)):
    allow(user, "OPERATOR", "OFFICER")
    ids = institution_scope(user, institution_id)
    if not institution_id and user["role_code"] == "OFFICER":
        fail("INSTITUTION_REQUIRED")
    with connect() as conn:
        return dashboard(conn, ids[0])


@router.get("/students/search", response_model=SearchResponse)
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
    user=Depends(authenticated),
):
    allow(user, "OPERATOR", "OFFICER")
    offset = pagination(page, page_size)
    ids = institution_scope(user, institution_id)
    if len(q) > 100 or q and len(q.strip()) < 2:
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
        data_epoch = one(
            conn,
            "SELECT coalesce(sum(data_epoch),0) AS e FROM institution_epochs WHERE institution_id=ANY(%s::uuid[])",
            (ids,),
        )["e"]
        key = (
            str(user["id"]),
            user["role_code"],
            tuple(str(i) for i in ids),
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


@router.get("/students/{student_id}")
def student(student_id: UUID, request: Request, user=Depends(authenticated)):
    with connect() as conn:
        return passport(conn, student_scope(conn, user, student_id, request))


@router.get("/student/{apaar_id}")
def student_by_id(apaar_id: str, request: Request, user=Depends(authenticated)):
    if not valid_id(apaar_id):
        fail("INVALID_SYNTHETIC_ID")
    with connect() as conn:
        row = one(conn, "SELECT id FROM students WHERE apaar_id=%s", (apaar_id,))
        if not row:
            fail("NOT_FOUND", 404)
        return passport(conn, student_scope(conn, user, row["id"], request))


@router.get("/students/{student_id}/versions")
def versions(student_id: UUID, request: Request, page: int = 1, page_size: int = 25, user=Depends(authenticated)):
    offset = pagination(page, page_size)
    with connect() as conn:
        student_scope(conn, user, student_id, request)
        rows = many(
            conn,
            "SELECT version_no,changed_fields,reason,created_at,changed_by FROM record_versions WHERE student_id=%s ORDER BY version_no DESC LIMIT %s OFFSET %s",
            (student_id, page_size, offset),
        )
        return listing(
            rows,
            one(conn, "SELECT count(*) AS n FROM record_versions WHERE student_id=%s", (student_id,))["n"],
            page,
            page_size,
        )


@router.patch("/students/{student_id}")
def patch_student(student_id: UUID, body: Patch, request: Request, user=Depends(authenticated)):
    allow(user, "OPERATOR")
    reason(body.reason)
    from app.modules.students.corrections import correct

    with connect() as conn:
        student_scope(conn, user, student_id, request)
        return idem(conn, user, request, body.model_dump(), lambda key: correct(conn, user, student_id, body))
